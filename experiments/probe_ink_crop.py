"""Line crops from the page's ink (`ink_crop.py`) against the crops a book's
readings were made from, on a golden book's pages: the lines are read again from the
ink crops into a fresh cache, and both readings are scored against the aligned
reference. The old reading is the book's own cache entry for the line, under whichever
crop it was read from (the layer box with its pad, or `crop_span`).

    PYTHONPATH=experiments uv run python experiments/probe_ink_crop.py <book dir> <first> <last> <chapters> [glm|qwen]

With qwen, ROBO_READ_VIA reads through a hosted build.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import pymupdf
from rapidfuzz.distance import Levenshtein

from ink_crop import use_ink_crops

from roboscriptorium import ocrcheck, pdf
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef

book_dir, first, last, chapters = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
which = sys.argv[5] if len(sys.argv) > 5 else "glm"
book = Book.load(book_dir)
settings = Settings.from_env()
stage = book.stages / ("second-reading.json" if which == "glm" else "third-reading.json")
old = json.loads(stage.read_text())
pages = [
    p
    for p in pdf.cached_text_layer(book.source, book.stages / "textlayer.json")
    if first <= p.number <= last
]
c0, c1 = (int(x) for x in chapters.split("-"))
truth = align(pages, load_chapters(Golden.load(book.golden).text_dir)[c0 - 1 : c1])

box_crop_span = ocrcheck.crop_span
before = {}
with pymupdf.open(book.source) as doc:
    for p in pages:
        boxes = ocrcheck.line_boxes(doc[p.number - 1], p)
        for k, line in enumerate(p.lines):
            box = boxes[k]
            text = hashlib.sha1(line.text.encode()).hexdigest()[:10]
            base = f"{p.number}:{k}:{text}:" + ",".join(f"{v:.0f}" for v in box)
            top, bottom = box_crop_span(boxes, k)
            cut = f"{base}:{top:.1f}-{bottom:.1f}"
            if cut in old["lines"]:
                before[SourceRef(p.number, k)] = old["lines"][cut]
            elif base in old["lines"]:
                before[SourceRef(p.number, k)] = old["lines"][base]
via = "-via-hosted" if which == "qwen" and settings.read_via else ""
out = Path("work/probes/ink-crop") / f"{book_dir.name}-{first}-{last}-{which}{via}.json"
out.parent.mkdir(parents=True, exist_ok=True)
start = time.time()
box_crop_span = ocrcheck.crop_span
use_ink_crops(book.source)
new = ocrcheck.line_readings(
    book.source, pages, set(before), old["model"], settings.ollama_url, out,
    old.get("prompt", ""), settings.read_via if which == "qwen" else "",
)  # fmt: skip
print(f"{which}: {len(before)} lines with an earlier reading; read again in {time.time() - start:.0f} s")
rows = []
for ref, was in before.items():
    t = truth[ref]
    line = next(p for p in pages if p.number == ref.page).lines[ref.line].text
    if t.role == "body" and 0.7 < len(t.truth) / max(1, len(line)) < 1.4:
        rows.append((normalise(t.truth), normalise(was), normalise(new[ref])))
chars = sum(len(t) for t, _, _ in rows)
for i, name in ((1, "earlier crop"), (2, "ink crop")):
    d = [Levenshtein.distance(r[i], r[0]) for r in rows]
    print(f"  {name}: {len(rows)} body lines, CER {sum(d) / max(1, chars):.2%}, exact {d.count(0)}")
worse = [r for r in rows if Levenshtein.distance(r[2], r[0]) > Levenshtein.distance(r[1], r[0])]
better = [r for r in rows if Levenshtein.distance(r[2], r[0]) < Levenshtein.distance(r[1], r[0])]
print(f"  better on {len(better)}, worse on {len(worse)}")
for t, a, b in worse[:8]:
    print(f"    worse: truth {t!r}\n           was {a!r}\n           now {b!r}")
for t, a, b in better[:5]:
    print(f"    better: truth {t!r}\n            was {a!r}\n            now {b!r}")
