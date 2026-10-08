"""Line crops cut short at the neighbouring line (`ocrcheck.crop_span`) against the old
crops, on a golden book's pages: the lines whose crop changed are read again into a
fresh cache and scored with the old readings against the aligned reference.

    uv run python experiments/probe_crop_span.py <book dir> <first> <last> <chapters> [glm|qwen]

With qwen, ROBO_READ_VIA reads through a hosted build.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import pymupdf
from rapidfuzz.distance import Levenshtein

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

changed = {}
with pymupdf.open(book.source) as doc:
    for p in pages:
        boxes = ocrcheck.line_boxes(doc[p.number - 1], p)
        for k, line in enumerate(p.lines):
            box = boxes[k]
            if line.text.strip() and ocrcheck.crop_span(boxes, k) != (
                box[1] - ocrcheck.LINE_PAD,
                box[3] + ocrcheck.LINE_PAD,
            ):
                text = hashlib.sha1(line.text.encode()).hexdigest()[:10]
                base = f"{p.number}:{k}:{text}:" + ",".join(f"{v:.0f}" for v in box)
                changed[SourceRef(p.number, k)] = base
via = "-via-hosted" if which == "qwen" and settings.read_via else ""
out = Path("work/probes/crop-span") / f"{book_dir.name}-{first}-{last}-{which}{via}.json"
out.parent.mkdir(parents=True, exist_ok=True)
start = time.time()
new = ocrcheck.line_readings(
    book.source, pages, set(changed), old["model"], settings.ollama_url, out, old.get("prompt", ""),
    settings.read_via if which == "qwen" else "",
)
print(f"{which}: {len(changed)} of {sum(len(p.lines) for p in pages)} lines have a new crop; "
      f"read in {time.time() - start:.0f} s")
rows = []
for ref, base in changed.items():
    t = truth[ref]
    line = next(p for p in pages if p.number == ref.page).lines[ref.line].text
    if t.role == "body" and base in old["lines"] and 0.7 < len(t.truth) / max(1, len(line)) < 1.4:
        rows.append((normalise(t.truth), normalise(old["lines"][base]), normalise(new[ref])))
chars = sum(len(t) for t, _, _ in rows)
for i, name in ((1, "old crop"), (2, "new crop")):
    d = [Levenshtein.distance(r[i], r[0]) for r in rows]
    print(f"  {name}: {len(rows)} body lines, CER {sum(d) / max(1, chars):.2%}, exact {d.count(0)}")
worse = [(r[0], r[1], r[2]) for r in rows if Levenshtein.distance(r[2], r[0]) > Levenshtein.distance(r[1], r[0])]
better = [(r[0], r[1], r[2]) for r in rows if Levenshtein.distance(r[2], r[0]) < Levenshtein.distance(r[1], r[0])]
print(f"  better on {len(better)}, worse on {len(worse)}")
for t, a, b in worse[:6]:
    print(f"    worse: truth {t!r}\n           old {a!r}\n           new {b!r}")
for t, a, b in better[:4]:
    print(f"    better: truth {t!r}\n            old {a!r}\n            new {b!r}")
