"""`accentmarks.Marks.doubts` on real pages, no models: what it offers, and how long it takes.

    uv run python experiments/probe_accent_doubts.py <book> [--stages] [page …]

`--stages` keeps the fits where the build reads them (`stages/accent-marks.json`), so a
later build or trust-data run with `ROBO_ACCENT_DOUBTS=1` finds them made.
"""

import sys
import time
from pathlib import Path

import pymupdf

from roboscriptorium import accentmarks, ocrcheck, pipeline, readers
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer, page_words
from roboscriptorium.readers import line_words

name, wanted = sys.argv[1], [int(a) for a in sys.argv[2:] if not a.startswith("--")]
book = Book.load(Path("work") / name)
layer = cached_text_layer(book.source, book.stages / "textlayer.json")
whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
judge = pipeline._alarm("render", Settings.from_env(), book, whole)
held = book.stages / "accent-marks.json" if "--stages" in sys.argv else Path("work/probes/accent-doubts") / f"{name}.json"
marks = accentmarks.Marks(judge, held)
Path("work/probes/accent-doubts").mkdir(parents=True, exist_ok=True)
started, words_seen, offered = time.time(), 0, []
with pymupdf.open(book.source) as doc:
    for page in (p for p in whole if not wanted or p.number in wanted):
        pdf_page = doc[page.number - 1]
        words = line_words(page_words(pdf_page, page), page)
        boxes = readers.line_boxes(pdf_page, page)
        for k, line in enumerate(page.lines):
            words_seen += len(line.text.split())
            found = marks.doubts(
                pdf_page, page.number, k, line.text, [],
                lambda a0, a1, w=words[k], b=boxes[k], t=line.text: ocrcheck._box(w, b, t, a0, a1),
            )  # fmt: skip
            offered += [(page.number, line.text[a0:a1], vs[0]) for a0, a1, vs in found]
        marks.save()
marks.save()
took = time.time() - started
print(f"{words_seen} words in {took:.0f} s ({1000 * took / max(1, words_seen):.0f} ms a word); {len(offered)} offered:")
for row in offered[:60]:
    print("  ", row)
