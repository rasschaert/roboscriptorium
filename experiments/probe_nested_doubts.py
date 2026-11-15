"""`quotemarks.Nested` on real pages, no models: the book's double-mark width, which mark
its quotations are set in, and what it offers over the text layer's lines, a layer token
kept with its marks only where the third reading has it so (standing in for the build's
text and the readings' agreement).

    uv run python experiments/probe_nested_doubts.py <book> [first-last]
"""

import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pymupdf

from roboscriptorium import ocrcheck, quotemarks, readers
from roboscriptorium.book import Book
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import cached_text_layer, line_words, page_words

book = Book.load(Path("work") / sys.argv[1])
first, last = map(int, sys.argv[2].split("-")) if len(sys.argv) > 2 else book.body_pages
pages = [p for p in cached_text_layer(book.source, book.stages / "textlayer.json") if first <= p.number <= last]
# A reader's words per page (its lines are keyed by box, not by index): a layer token it
# doesn't have as written loses its marks here, so the two readings disagree on it.
seen: dict[int, set[str]] = {}
for key, text in json.loads((book.stages / "third-reading.json").read_text())["lines"].items():
    seen.setdefault(int(key.split(":")[0]), set()).update(text.split())


def agreed(page: int, text: str) -> str:
    return " ".join(t if t in seen.get(page, ()) else t.strip("“”\"") for t in text.split())


for p in pages:
    p.lines[:] = [replace(ln, text=agreed(p.number, ln.text)) for ln in p.lines]
layer = {SourceRef(p.number, k): ln.text for p in pages for k, ln in enumerate(p.lines)}
nested = quotemarks.Nested(Path(tempfile.mkdtemp()) / "quote-marks.json")
nested.survey(book.source, pages, {"layer": layer})
print(f"{book.root.name}: double mark {nested._usual}, quotations set in {'double' if nested._outer == 'd' else 'single'} marks")
offered = []
with pymupdf.open(book.source) as doc:
    for page in pages:
        pdf_page = doc[page.number - 1]
        words = line_words(page_words(pdf_page, page), page)
        boxes = readers.line_boxes(pdf_page, page)
        for k, line in enumerate(page.lines):
            found = nested.doubts(
                pdf_page, page.number, k, line.text, [],
                lambda a0, a1, w=words[k], b=boxes[k], t=line.text: ocrcheck._box(w, b, t, a0, a1),
            )  # fmt: skip
            offered += [(page.number, line.text[a0:a1], vs[0]) for a0, a1, vs in found]
print(f"{len(offered)} offered on {len(pages)} pages:", offered[:40])
