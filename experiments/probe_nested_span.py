"""`quotemarks.span` on the labelled word edges of `quote_marks_data.py`: per book, the
width of its double marks (edges the reference and the layer both set double), and how
many nested marks and how many plain double ones measure `RATIO` times that or more.
No models.

    uv run python experiments/probe_nested_span.py [book …]
"""

import json
import statistics
import sys
from pathlib import Path

import pymupdf

from roboscriptorium import quotemarks
from roboscriptorium.book import Book
from roboscriptorium.pdf import cached_text_layer, line_words, page_words

DATA = Path("work/probes/quote-marks")
total = [0, 0, 0, 0]
for path in sorted(DATA.glob("*.json")):
    if sys.argv[1:] and path.stem not in sys.argv[1:]:
        continue
    rows = [r for r in json.loads(path.read_text()) if "d" in r["truth"]]
    if sum(r["truth"] in ("sd", "ds") for r in rows) == 0:
        continue
    book = Book.load(Path("work") / path.stem)
    pages = {p.number: p for p in cached_text_layer(book.source, book.stages / "textlayer.json")}
    got = []
    with pymupdf.open(book.source) as doc:
        held = None
        for r in rows:
            if held is None or held[0] != r["page"]:
                held = (r["page"], line_words(page_words(doc[r["page"] - 1], pages[r["page"]]), pages[r["page"]]))
            w = held[1][r["line"]][r["word"]]
            got.append((r, quotemarks.span(doc[r["page"] - 1], w[:4], r["opening"])))
    plain = [s for r, s in got if r["truth"] == "d" and r["layer"] == "d" and s]
    if len(plain) < quotemarks.FEWEST:
        continue
    usual = statistics.median(plain)
    cut = quotemarks.RATIO * usual
    nest = [(r, s) for r, s in got if r["truth"] in ("sd", "ds")]
    lacking = [(r, s) for r, s in nest if r["layer"] != r["truth"]]
    doubles = [s for r, s in got if r["truth"] == "d" and s is not None]
    found = sum(s is not None and s >= cut for _, s in lacking)
    false = sum(s >= cut for s in doubles)
    total = [total[0] + found, total[1] + len(lacking), total[2] + false, total[3] + len(doubles)]
    print(f"{path.stem[:28]:28} double {usual:.2f}; nested the layer lacks found {found} of {len(lacking)} (all nested {sum(s is not None and s >= cut for _, s in nest)} of {len(nest)}); plain doubles offered {false} of {len(doubles)}; missed: {[(r['page'], r['text'], None if s is None else round(s / usual, 2)) for r, s in lacking if s is None or s < cut][:6]}", flush=True)
print(f"all: nested the layer lacks found {total[0]} of {total[1]}; plain doubles offered {total[2]} of {total[3]}")
