"""Tall text-layer fragments (drop caps, big initials) and what line grouping makes of them.

Per book: fragments over 1.6× the page's median height, split into those whose
first span alone is tall (an initial set in the line) and the rest, and how many
visual lines hold text from more than one text-layer line beside a tall one.
"""

import statistics
import sys
from pathlib import Path

import pymupdf

from roboscriptorium.pdf import Line, _visual_lines

TALL = 1.6

for book in sys.argv[1:]:
    initial = other = glued = 0
    examples = []
    with pymupdf.open(Path(book) / "source.pdf") as doc:
        for index, page in enumerate(doc):
            frags, spans = [], []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line["spans"]).strip()
                    if text:
                        frags.append(Line(text, *line["bbox"]))
                        spans.append([s for s in line["spans"] if s["text"].strip()])
            if len(frags) < 5:
                continue
            median = statistics.median(f.y1 - f.y0 for f in frags)
            for f, ss in zip(frags, spans, strict=True):
                if f.y1 - f.y0 <= TALL * median:
                    continue
                rest = ss[1:]
                if rest and max(s["bbox"][3] - s["bbox"][1] for s in rest) <= TALL * median:
                    initial += 1
                else:
                    other += 1
                    if len(examples) < 4:
                        examples.append(f"p{index + 1} {f.text[:40]!r} h {f.y1 - f.y0:.0f}/{median:.0f}")
                for ln in _visual_lines(frags):
                    if ln.y0 <= f.y0 and f.y1 <= ln.y1 and ln.text != f.text and f.text in ln.text:
                        glued += 1
    print(f"{Path(book).name}: initial-in-line {initial}, other tall {other}, glued {glued}")
    for e in examples:
        print("   ", e)
