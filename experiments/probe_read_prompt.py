"""Read-prompt and crop variants for the line reader, on the frozen reader set (`tryout.py`).

Each variant rewrites the book's frozen prompt or the line's crop (rendered at another
resolution from the PDF, upscaled, contrast-stretched, given a margin); the same model
reads every line with it,
and each is scored against the set's truth like a tryout candidate. Readings are cached
per model and variant in work/tryout/reader-v<N>/prompts/; results go to
tryouts/results.jsonl with the variant named.

    uv run python experiments/probe_read_prompt.py <model> [variant …]
"""

import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tryout import GIT, READER_VERSION, WORK, _commit, load_set, score  # noqa: E402

import pymupdf  # noqa: E402
from PIL import Image, ImageFilter, ImageOps  # noqa: E402

from roboscriptorium import ocrcheck  # noqa: E402
from roboscriptorium.book import Book  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.pdf import cached_text_layer  # noqa: E402

EXACT = (
    " Copy each word as printed even where it looks misspelt, unusual or old-fashioned:"
    " never correct, complete or modernise a word, and never add or drop a letter."
)


def _neighbours(items: list[dict]) -> dict[str, tuple[str, str]]:
    """The text layer's lines above and below each item's line."""
    out, layers = {}, {}
    for i in items:
        name, page, line = i["id"].rsplit(":", 2)
        if name not in layers:
            book = Book.load(Path("work") / name)
            layers[name] = {
                p.number: p
                for p in cached_text_layer(book.source, book.stages / "textlayer.json")
            }
        lines = layers[name][int(page)].lines
        k = int(line)
        above = lines[k - 1].text if k > 0 else ""
        below = lines[k + 1].text if k + 1 < len(lines) else ""
        out[i["id"]] = (above, below)
    return out


def _png(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _edit(fn):
    """A crop variant made from the frozen crop."""
    return lambda i: _png(fn(Image.open(io.BytesIO(i["png"])).convert("RGB")))


def _rendered(dpi: int):
    """A crop variant rendered anew from the PDF at `dpi`, cut as the OCR check cuts it
    (the box and span are in the item's cache key)."""
    docs: dict[str, pymupdf.Document] = {}

    def crop(i: dict) -> bytes:
        name = i["book"]
        if name not in docs:
            docs[name] = pymupdf.open(Book.load(Path("work") / name).source)
        parts = i["cache_key"].split(":")
        page, box = int(parts[0]), [float(v) for v in parts[3].split(",")]
        em = box[3] - box[1]
        if len(parts) > 4:
            top, bottom = (float(v) for v in parts[4].split("-"))
        else:
            top, bottom = box[1] - ocrcheck.LINE_PAD, box[3] + ocrcheck.LINE_PAD
        clip = pymupdf.Rect(box[0] - em, top, box[2] + em, bottom)
        return docs[name][page - 1].get_pixmap(dpi=dpi, clip=clip).tobytes("png")

    return crop


def _margin(image: Image.Image) -> Image.Image:
    return ImageOps.expand(image, border=(16, 24), fill="white")


def crops() -> dict:
    """Crop variants: each makes the PNG an item is read from."""
    up = lambda k: (lambda im: im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS))  # noqa: E731
    return {
        "dpi300": _rendered(ocrcheck.DPI),
        "dpi450": _rendered(450),
        "dpi600": _rendered(600),
        "up2": _edit(up(2)),
        "contrast": _edit(lambda im: ImageOps.autocontrast(im.convert("L"), cutoff=1)),
        "sharpen": _edit(lambda im: im.filter(ImageFilter.UnsharpMask(radius=2, percent=80))),
        "margin": _edit(_margin),
    }


def variants(items: list[dict]) -> dict:
    around = _neighbours(items)

    def context(prompt: str, i: dict) -> str:
        above, below = around[i["id"]]
        return (
            prompt
            + f" For context only, not to transcribe: the line above reads «{above}» and the"
            f" line below «{below}» (an OCR reading, which may be wrong)."
        )

    return {
        "base": lambda prompt, i: prompt,
        "exact": lambda prompt, i: prompt + EXACT,
        "context": context,
        "layer": lambda prompt, i: prompt
        + f" An OCR layer read this line as «{i['layer']}»; it may be wrong, so read the image.",
        "exact+context": lambda prompt, i: context(prompt + EXACT, i),
    }


def read(model: str, name: str, make, items: list[dict], books: dict) -> dict[str, str]:
    safe = model.replace(":", "_").replace("/", "_")
    cache = WORK / f"reader-v{READER_VERSION}" / "prompts" / f"{safe}@{name}.json"
    done = json.loads(cache.read_text()) if cache.exists() else {}
    settings = Settings.from_env()
    todo = [i for i in items if i["id"] not in done]

    prompt_of, crop_of = make

    # Rendered on this thread: PyMuPDF isn't thread-safe; only the model calls are pooled.
    pngs = {i["id"]: crop_of(i) for i in todo}

    def one(i):
        prompt = prompt_of(books[i["book"]]["prompt"], i)
        return i["id"], ocrcheck.transcribe(pngs[i["id"]], model, settings.ollama_url, prompt)

    workers = ocrcheck.HOSTED_WORKERS if model.startswith("openrouter:") else 1
    with ThreadPoolExecutor(workers) as pool:
        for n, (k, text) in enumerate(pool.map(one, todo), 1):
            done[k] = text
            if n % 50 == 0 or n == len(todo):
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(done, ensure_ascii=False))
                print(f"  {name}: {n}/{len(todo)}", flush=True)
    return done


def main() -> None:
    model, wanted = sys.argv[1], sys.argv[2:]
    books, items = load_set()
    frozen = lambda i: i["png"]  # noqa: E731
    found = {n: (v, frozen) for n, v in variants(items).items()}
    found |= {n: (found["base"][0], c) for n, c in crops().items()}
    names = wanted or list(found)
    readings = {n: read(model, n, found[n], items, books) for n in names}
    layer = {i["id"]: i["layer"] for i in items}
    rows = [score("text layer", layer, items, {})]
    rows += [
        score(n, r, items, {"base": readings["base"]} if n != "base" and "base" in readings else {})
        for n, r in readings.items()
    ]
    print(f"\n{'variant':16} {'hard right':>10} {'hard CER':>9} {'control right':>13} "
          f"{'control CER':>11} {'quote lines wrong':>17}")  # fmt: skip
    for r in rows:
        h, c = r["hard"], r["control"]
        print(f"{r['model']:16} {h['right']:>4}/{h['lines']:<5} {h['cer']:9.3%} "
              f"{c['right']:>6}/{c['lines']:<6} {c['cer']:11.3%} "
              f"{h['quote_lines_wrong'] + c['quote_lines_wrong']:17}")  # fmt: skip
    with (GIT / "results.jsonl").open("a") as f:
        for r in rows[1:]:
            stamp = datetime.now(UTC).isoformat(timespec="seconds")
            record = {"role": "reader", "set": f"reader-v{READER_VERSION}", "commit": _commit(),
                      "when": stamp, "prompt_variant": r["model"], **r, "model": model}  # fmt: skip
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
