"""Surya OCR 2's layout of a page as a second opinion on line roles: of the lines the
line-role trees get wrong (against the golden labels, `sorterdata`), how many lie in a
block Surya labels right (its rescues), and of the lines they get right, how many it
labels otherwise (its noise).

Pages: per bench book, those holding a tree error on a heading or a furniture line (by
the trees trained without the book where it is a tuning book), up to `ERROR_PAGES`, and
`CLEAN_PAGES` without one. Surya's answers are kept per page in work/probes/surya-layout/,
so a stopped run goes on where it was; `--dry` checks the inputs and asks nothing.

    uv run python experiments/probe_surya_layout.py [--dry] [book …]
    uv run python experiments/probe_surya_layout.py --all [--dry]   # every labelled page, for the trees
"""

import base64
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import httpx
import pymupdf

from roboscriptorium import bench, sorter, sorterdata
from roboscriptorium.book import Book
from roboscriptorium.config import Settings

MODEL = "hf.co/datalab-to/surya-ocr-2-gguf:latest"
OUT = Path("work/probes/surya-layout")
ERROR_PAGES = 8
CLEAN_PAGES = 2
# Surya's card: no wider than 2048 px.
WIDTH = 1600
# Its trained prompt and label set (datalab-to/surya, surya/inference/prompts.py).
PROMPT = (
    "Output the layout of this image as JSON. Each entry is a dict with "
    '"label", "bbox", and "count" fields. Bbox is x0 y0 x1 y1, normalized 0-1000.'
)
LABELS = [
    "Caption", "Footnote", "Equation-Block", "List-Group", "Page-Header", "Page-Footer",
    "Image", "Section-Header", "Table", "Text", "Complex-Block", "Code-Block", "Form",
    "Table-Of-Contents", "Figure", "Chemical-Block", "Diagram", "Bibliography", "Blank-Page",
]  # fmt: skip
SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": LABELS},
            "bbox": {"type": "string"},
            "count": {"type": "integer"},
        },
        "required": ["label", "bbox", "count"],
    },
}
# Surya's labels as the trees' three roles.
ROLE = {"Section-Header": "heading", "Page-Header": "other", "Page-Footer": "other"}


def role_of(label: str | None) -> str:
    return "none" if label is None else ROLE.get(label, "body")


def trees_for(name: str) -> sorter.Sorter:
    path = Path(Settings.from_env().sorter_model)
    own = sorter.without(path, name)
    return sorter.load(own if own.exists() else path)


def pages_to_ask(spec: str) -> tuple[list[dict], list[str], list[int]]:
    name = spec.split(":")[0]
    rows = sorterdata.lines(spec)
    said = sorterdata.predict(trees_for(name), rows)
    wrong = {
        r["page"]
        for r, p in zip(rows, said, strict=True)
        if p != r["label"] and "body" in (p, r["label"]) and {p, r["label"]} != {"body"}
    }
    rng = random.Random(name)
    errors = sorted(rng.sample(sorted(wrong), min(ERROR_PAGES, len(wrong))))
    clean = sorted({r["page"] for r in rows} - wrong)
    return rows, said, errors + sorted(rng.sample(clean, min(CLEAN_PAGES, len(clean))))


def layout(book: Book, number: int, url: str) -> list[dict]:
    path = OUT / book.root.name / f"{number}.json"
    if path.exists():
        return json.loads(path.read_text())
    doc = pymupdf.open(book.source)
    page = doc[number - 1]
    png = page.get_pixmap(matrix=pymupdf.Matrix(WIDTH / page.rect.width, WIDTH / page.rect.width))
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "images": [base64.b64encode(png.tobytes("png")).decode()],
        "stream": False,
        "format": SCHEMA,
        "options": {"num_predict": 4096, "temperature": 0},
    }
    started = time.time()
    resp = httpx.post(f"{url}/api/generate", json=payload, timeout=900)
    resp.raise_for_status()
    blocks = whole_blocks(resp.json()["response"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blocks))
    print(f"  {book.root.name} p{number}: {len(blocks)} blocks, {time.time() - started:.1f} s")
    return blocks


def whole_blocks(text: str) -> list[dict]:
    """The blocks of an answer; one cut off at `num_predict` keeps its complete blocks."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        end = text.rfind("}")
        while end > 0:
            try:
                return json.loads(text[: end + 1] + "]")
            except json.JSONDecodeError:
                end = text.rfind("}", 0, end)
        return []


def label_at(blocks: list[dict], x: float, y: float) -> str | None:
    """The label of the smallest block holding the point (shares of the page)."""
    holding = []
    for b in blocks:
        try:
            x0, y0, x1, y1 = (int(v) / 1000 for v in b["bbox"].split())
        except ValueError:
            continue
        if x0 <= x <= x1 and y0 <= y <= y1:
            holding.append(((x1 - x0) * (y1 - y0), b["label"]))
    return min(holding)[1] if holding else None


def every_page(dry: bool) -> None:
    """Surya's layout of every page the line-role trees have labelled lines of
    (`sorterdata`: the bench's slices and the training-only ones), kept per page."""
    url = Settings.from_env().ollama_url
    specs = bench.SETS["tuning"] + bench.SETS["validation"] + sorterdata.EXTRA
    todo = []
    for spec in specs:
        name = spec.split(":")[0]
        book = Book.load(Path("work") / name)
        pages = sorted({r["page"] for r in sorterdata.lines(spec)})
        left = [n for n in pages if not (OUT / name / f"{n}.json").exists()]
        print(f"{name}: {len(pages)} pages, {len(left)} to ask", flush=True)
        todo += [(book, n) for n in left]
    print(f"{len(todo)} pages to ask", flush=True)
    if dry:
        return
    for k, (book, number) in enumerate(todo):
        layout(book, number, url)
        if k % 100 == 0:
            print(f"{k} of {len(todo)}", flush=True)


def main(args: list[str]) -> None:
    dry = "--dry" in args
    if "--all" in args:
        every_page(dry)
        return
    wanted = [a for a in args if not a.startswith("--")]
    specs = [s for s in bench.SETS["tuning"] + bench.SETS["validation"]]
    specs = [s for s in specs if not wanted or s.split(":")[0] in wanted]
    url = Settings.from_env().ollama_url
    tally: Counter = Counter()
    examples: list[str] = []
    for spec in specs:
        name = spec.split(":")[0]
        book = Book.load(Path("work") / name)
        rows, said, pages = pages_to_ask(spec)
        print(f"{name}: {len(pages)} pages", flush=True)
        if dry:
            continue
        for number in pages:
            blocks = layout(book, number, url)
            for r, trees in zip(rows, said, strict=True):
                if r["page"] != number:
                    continue
                f = r["f"]
                # The line's middle: its top plus a little, its centre across.
                x, y = 0.5 + f["centre_offset"], min(1.0, f["y"] + 0.006)
                surya = role_of(label_at(blocks, x, y))
                gold = r["label"]
                tally[("trees right" if trees == gold else "trees wrong", surya == gold)] += 1
                if trees != gold and surya == gold and len(examples) < 40:
                    examples.append(f"{name} p{number} l{r['line']}: {gold}, trees {trees}")
    if dry:
        return
    print()
    for (trees, ok), n in sorted(tally.items()):
        print(f"{trees:12} Surya {'right' if ok else 'wrong'}: {n}")
    print("rescues, examples:")
    for e in examples:
        print("  " + e)


if __name__ == "__main__":
    main(sys.argv[1:])
