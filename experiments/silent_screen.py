"""The short test for anything meant to see what no reader sees: the lines holding a
bench run's silent errors (wrong in the built book, no question asked) and clean lines
of the same pages, read by a model with a prompt. Per reading: how many silent errors it
reads as the print has them (`rescued`), how many it reads as the build does, and how
many clean lines it reads otherwise than the reference (the noise it would bring). A model
is worth a seat for what it rescues, not for its own error rate: its readings would go
to the judges as one more version where they differ.

    uv run python experiments/silent_screen.py build <bench errors.jsonl> [most errors]
    PYTHONPATH=experiments uv run python experiments/silent_screen.py truths
    uv run python experiments/silent_screen.py run <model> [variant …]
    uv run python experiments/silent_screen.py report

`build` needs no model and freezes work/probes/silent-screen/{items.json, crops/}.
Variants (`VARIANTS`): the book's own read prompt ("book"), prompts that tell the model
to copy without reading ("copy", "marks"), the crop at twice its size ("zoom"), and a
model's own prompt in place of the book's ("ocr").
Answers are kept per model and variant (work/probes/silent-screen/answers/), so a run
stopped goes on where it was. About 1.5 s a line on a warm model.
"""

import hashlib
import io
import json
import random
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("work/probes/silent-screen")
CONTROLS = 0.5
MIN_LENGTH = 25
VARIANTS = {
    "book": "",
    "copy": (
        " Do not read it as language: copy it mark by mark, as if the words were in a "
        "language you do not know. Never replace a word by a likelier one."
    ),
    "marks": (
        " Look twice at what is easy to miss: an accent on a single letter set for "
        "emphasis, three quote ticks where a quotation opens inside another, a hyphen "
        "inside a word, small capitals (write them as capitals). Add none that is not printed."
    ),
    "zoom": "",
    # A model with a prompt of its own (PaddleOCR-VL): that prompt alone.
    "ocr": None,
    # Baidu's Unlimited-OCR-2, a whole-page model: the one prompt its card gives.
    "parse": None,
    # Surya OCR 2: its trained prompt for a crop (surya/inference/prompts.py, BLOCK_PROMPT);
    # it answers in HTML, which `html_text` reduces to the line.
    "surya": None,
}
OWN_PROMPTS = {
    "ocr": "OCR:",
    "parse": "Multi page parsing.",
    "surya": "OCR this block image to HTML.",
}


def html_text(answer: str) -> str:
    """An HTML answer's text on one line: tags dropped, entities read."""
    import html
    import re

    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", answer)).split())
STRAIGHT = str.maketrans("‘’“”", "''\"\"")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def fold(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).translate(STRAIGHT).split())


def build(errors_path: str, most: int) -> None:
    import pymupdf

    from roboscriptorium import readers
    from roboscriptorium.book import Book
    from roboscriptorium.pdf import cached_text_layer

    rng = random.Random(7)
    rows = [json.loads(x) for x in Path(errors_path).read_text().splitlines()]
    bad, wanted = defaultdict(set), defaultdict(list)
    for r in rows:
        if r["lines"]:
            bad[r["book"]].update((r["page"], n) for n in range(r["lines"][0], r["lines"][1] + 1))
        if not r["asked"] and r["lines"] and r["lines"][0] == r["lines"][1] and r["got"].strip() and r["want"].strip():
            wanted[r["book"]].append(r)
    picked = [r for rs in wanted.values() for r in rs]
    picked = rng.sample(picked, min(most, len(picked)))
    (ROOT / "crops").mkdir(parents=True, exist_ok=True)
    items = []
    for name in dict.fromkeys(r["book"] for r in picked):
        book = Book.load(Path("work") / name)
        pages = {p.number: p for p in cached_text_layer(book.source, book.stages / "textlayer.json")}
        prompt = json.loads((book.stages / "third-reading.json").read_text())["prompt"]
        mine = [r for r in picked if r["book"] == name]
        with pymupdf.open(book.source) as doc:
            def add(page: int, k: int, **more):
                boxes = readers.line_boxes(doc[page - 1], pages[page])
                png = readers._line_crop(doc, page, boxes[k], readers.crop_span(boxes, k))
                iid = f"{name}:{page}:{k}"
                (ROOT / "crops" / f"{sha(iid)}.png").write_bytes(png)
                items.append({"id": iid, "book": name, "prompt": prompt, "layer": pages[page].lines[k].text, **more})

            placed = 0
            for r in mine:
                page = pages.get(r["page"])
                k = r["lines"][0]
                # The bench's line numbers are the build's; kept only where the layer's
                # line there holds the build's words.
                if page is None or k >= len(page.lines) or r["got"] not in fold(page.lines[k].text):
                    continue
                add(r["page"], k, stratum="silent", got=r["got"], want=r["want"], cause=r["cause"])
                placed += 1
            pool = [
                (n, k)
                for n in sorted({r["page"] for r in mine})
                if n in pages
                for k, ln in enumerate(pages[n].lines)
                if (n, k) not in bad[name] and len(ln.text) >= MIN_LENGTH
            ]
            for n, k in rng.sample(pool, min(len(pool), round(placed * CONTROLS))):
                add(n, k, stratum="clean")
        print(name, placed, "silent errors placed of", len(mine), flush=True)
    (ROOT / "items.json").write_text(json.dumps({"errors": errors_path, "items": items}, ensure_ascii=False))
    print(len(items), "lines:", Counter(i["stratum"] for i in items), Counter(i.get("cause") for i in items if i["stratum"] == "silent").most_common())


def truths() -> None:
    """Each item's line as the reference has it (`truth`), where the aligner places it:
    what a clean line is compared with, the layer being wrong itself now and then."""
    from tryout import slice_of

    from roboscriptorium import bench, disagreements
    from roboscriptorium.golden import scoring
    from roboscriptorium.golden.align import align
    from roboscriptorium.golden.manifest import Golden
    from roboscriptorium.golden.reference import load_chapters
    from roboscriptorium.ir import SourceRef
    from roboscriptorium.pdf import cached_text_layer

    data = json.loads((ROOT / "items.json").read_text())
    for name in dict.fromkeys(i["book"] for i in data["items"]):
        spec = next(s for s in bench.SETS["tuning"] if s.split(":")[0] == name)
        book, (first, last), chapters = slice_of(spec)
        pages = [p for p in cached_text_layer(book.source, book.stages / "textlayer.json") if first <= p.number <= last]
        reference = load_chapters(Golden.load(book.golden).text_dir)
        if chapters:
            reference = reference[chapters[0] - 1 : chapters[1]]
        reference, _ = disagreements.patch(reference, scoring.verdicts(book))
        labels = align(pages, reference)
        for i in data["items"]:
            if i["book"] == name:
                _, page, k = i["id"].rsplit(":", 2)
                found = labels.get(SourceRef(int(page), int(k)))
                i["truth"] = found.truth if found and found.truth else None
        print(name, flush=True)
    (ROOT / "items.json").write_text(json.dumps(data, ensure_ascii=False))
    clean = [i for i in data["items"] if i["stratum"] == "clean"]
    print(sum(bool(i["truth"]) for i in clean), "of", len(clean), "clean lines placed;", sum(fold(i["truth"]) != fold(i["layer"]) for i in clean if i["truth"]), "where the layer itself differs")


def answers(model: str, variant: str) -> dict[str, str]:
    path = ROOT / "answers" / f"{model.replace('/', '_').replace(':', '_')}--{variant}.jsonl"
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[row["id"]] = row["text"]
    return out


def run(model: str, variants: list[str]) -> None:
    from PIL import Image

    from roboscriptorium import readers
    from roboscriptorium.config import Settings

    settings = Settings.from_env()
    items = json.loads((ROOT / "items.json").read_text())["items"]
    (ROOT / "answers").mkdir(exist_ok=True)
    for variant in variants:
        have = answers(model, variant)
        path = ROOT / "answers" / f"{model.replace('/', '_').replace(':', '_')}--{variant}.jsonl"
        with path.open("a") as f:
            for n, item in enumerate(items):
                if item["id"] in have:
                    continue
                png = (ROOT / "crops" / f"{sha(item['id'])}.png").read_bytes()
                if variant == "zoom":
                    image = Image.open(io.BytesIO(png))
                    held = io.BytesIO()
                    image.resize((image.width * 2, image.height * 2), Image.LANCZOS).save(held, "PNG")
                    png = held.getvalue()
                prompt = OWN_PROMPTS[variant] if VARIANTS[variant] is None else item["prompt"] + VARIANTS[variant]
                if variant == "surya":
                    text = html_text(_whole_answer(png, model, settings.ollama_url, prompt))
                else:
                    text = readers.transcribe(png, model, settings.ollama_url, prompt)
                f.write(json.dumps({"id": item["id"], "text": text}, ensure_ascii=False) + "\n")
                f.flush()
                if n % 50 == 0:
                    print(f"{model} {variant}: line {n} of {len(items)}", flush=True)
        print(f"{model} {variant}: done", flush=True)
    report()


def _whole_answer(png: bytes, model: str, url: str, prompt: str) -> str:
    """A model's whole answer for a crop, every line of it (`readers.transcribe` keeps the
    first): an HTML answer may open on a tag alone."""
    import base64

    import httpx

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [base64.b64encode(png).decode()],
        "stream": False,
        "think": False,
        "options": {"num_predict": 512, "temperature": 0},
    }
    resp = httpx.post(f"{url}/api/generate", json=payload, timeout=600)
    resp.raise_for_status()
    return resp.json()["response"]


def report() -> None:
    items = json.loads((ROOT / "items.json").read_text())["items"]
    silent = [i for i in items if i["stratum"] == "silent"]
    clean = [i for i in items if i["stratum"] == "clean"]
    print(f"{len(silent)} silent errors, {len(clean)} clean lines")
    rescued_by = {}
    for path in sorted((ROOT / "answers").glob("*.jsonl")):
        model, variant = path.stem.rsplit("--", 1)
        got = {}
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            got[row["id"]] = fold(row["text"])
        seen = [i for i in silent if i["id"] in got]
        if not seen:
            continue
        # The print's words read, and not just because the build's are part of them.
        rescued = {i["id"] for i in seen if i["want"] in got[i["id"]] and not (i["got"] in got[i["id"]] and i["want"] in i["got"])}
        rescued = {i["id"] for i in seen if i["id"] in rescued and (i["got"] not in got[i["id"]] or i["got"] in i["want"])}
        as_built = sum(i["got"] in got[i["id"]] for i in seen) - sum(1 for i in seen if i["id"] in rescued and i["got"] in i["want"])
        noisy = [i for i in clean if i["id"] in got and got[i["id"]] != fold(i.get("truth") or i["layer"])]
        by_cause = Counter(i["cause"] for i in seen if i["id"] in rescued)
        rescued_by[f"{model} {variant}"] = rescued
        print(
            f"{model[:34]:34} {variant:6} rescues {len(rescued):3} of {len(seen)}, reads as the build {as_built:3}; "
            f"clean lines read otherwise {len(noisy)} of {sum(i['id'] in got for i in clean)}; rescued by cause {dict(by_cause.most_common(6))}"
        )
    if len(rescued_by) > 1:
        every = set().union(*rescued_by.values())
        print(f"rescued by at least one: {len(every)} of {len(silent)}")
        left = Counter(i["cause"] for i in silent if i["id"] not in every)
        print("  never rescued, by cause:", dict(left.most_common(8)))


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 200)
    elif sys.argv[1] == "truths":
        truths()
    elif sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3:] or ["book"])
    else:
        report()
