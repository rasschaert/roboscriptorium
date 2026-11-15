"""Can a vision judge settle where two sets of line-role trees disagree? A sample of the
tuning lines the old and the grown trees call differently (`sorter_disagree.py`), each
shown as a band of its page with the line framed, asked of a judge "running text, a
heading, or not part of the text?", scored against the reference beside both sets.
Answers cached in work/probes/sorter-judge/. A line is shown only where the text layer's
line at its index sits where the labelled line does (missing lines shift indices).
`--page` shows the whole page instead of a band, so the line's place on the page and the
page's other lines are in sight; `--dry` writes the images to work/probes/sorter-judge/png/
and asks nothing.

    uv run python experiments/sorter_judge_probe.py <old dir> <new dir> [judge] [sample] [--page] [--dry]
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

import pymupdf

from roboscriptorium import bench, sorter
from roboscriptorium.book import Book
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.roles import DecisionCache
from roboscriptorium.sorterdata import lines
from sorter_disagree import calls

OUT = Path("work/probes/sorter-judge")
flags = {a for a in sys.argv[1:] if a.startswith("--")}
args = [a for a in sys.argv[1:] if not a.startswith("--")]
whole, dry = "--page" in flags, "--dry" in flags
old_dir, new_dir = Path(args[0]), Path(args[1])
judge = args[2] if len(args) > 2 else "clef:27b"
size = int(args[3]) if len(args) > 3 else 100
settings = Settings.from_env()
client = decide.for_model(judge, settings.ollama_url)
OUT.mkdir(parents=True, exist_ok=True)
cache = DecisionCache(OUT / "decisions.jsonl")
QUESTION = (
    ("The image is a scanned printed book's page. " if whole else "The image is a band cut from a scanned printed book's page. ")
    + "What is the line framed in "
    "red: part of the book's running text, a heading (a chapter or part title, a chapter "
    "number), or not part of the text (a page number, a running head repeated atop pages, "
    "a speck, a caption)?"
)
OPTIONS = {
    "body": "running text",
    "heading": "a heading",
    "other": "not part of the text: a page number, running head, speck or caption",
}

apart = []
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    try:
        rows = lines(spec)
        old = calls(sorter.load(sorter.without(old_dir / "line-roles.pkl", name)), rows)
        new = calls(sorter.load(sorter.without(new_dir / "line-roles.pkl", name)), rows)
    except Exception:
        continue
    apart += [(name, r, o, n) for r, o, n in zip(rows, old, new, strict=True) if o != n]
random.seed(0)
sample = random.sample(apart, min(size, len(apart)))
results, skipped = [], 0
layers: dict[str, dict] = {}
for name, r, old, new in sample:
    if name not in layers:
        book = Book.load(Path("work") / name)
        tl = json.loads((book.stages / "textlayer.json").read_text())
        layers[name] = (book, {p["number"]: p for p in tl["pages"]})
    book, pages = layers[name]
    page = pages.get(r["page"])
    if page is None or r["line"] >= len(page["lines"]):
        skipped += 1
        continue
    ln = page["lines"][r["line"]]
    if abs(ln["y0"] / page["height"] - r["f"]["y"]) > 0.03:
        skipped += 1
        continue
    state = {"book": name, "page": r["page"], "line": r["line"], "text": ln["text"]}
    if whole:
        state["view"] = "page"
    question = {"role": decide.choice(QUESTION, OPTIONS)}
    key = cache.key(judge, question, state)
    answer = cache.get(key)
    if answer is None or dry:
        with pymupdf.open(book.source) as doc:
            pg = doc[r["page"] - 1]
            high = ln["y1"] - ln["y0"]
            band = pymupdf.Rect(0, ln["y0"] - 4 * high, pg.rect.width, ln["y1"] + 4 * high) & pg.rect
            pg.draw_rect(pymupdf.Rect(ln["x0"] - 2, ln["y0"] - 1, ln["x1"] + 2, ln["y1"] + 1), color=(1, 0, 0), width=1)
            # The whole page at about 1,400 pixels on its long side, the band at twice its size.
            zoom = 1400 / max(pg.rect.width, pg.rect.height) if whole else 2
            png = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=None if whole else band).tobytes("png")
        if dry:
            (OUT / "png").mkdir(exist_ok=True)
            (OUT / "png" / f"{name}-{r['page']}-{r['line']}{'-page' if whole else ''}.png").write_bytes(png)
            continue
        got = client.decide(state, question, image_png=png)["role"]
        answer = {"value": got.value, "confidence": got.confidence}
        cache.put(key, answer)
    results.append((name, r["label"], old, new, answer["value"], answer["confidence"]))
c = Counter()
for _, lab, old, new, said, _ in results:
    c["places"] += 1
    c["old right"] += old == lab
    c["new right"] += new == lab
    c["judge right"] += said == lab
print(f"{judge}: {dict(c)}; skipped {skipped} whose line couldn't be placed")
for name, lab, old, new, said, conf in results:
    if said != lab:
        print(f"  wrong: {name[:24]:24} print {lab}, old {old}, new {new}, said {said} ({conf:.2f})")
