"""Does a vision decision model find where a book's body starts and ends?

Usage: uv run python experiments/probe_body_range.py MODEL (an Ollama decision model, or
llama:<imajev name>@<port> for llama-server)

`book.toml`'s `body_pages` is the label: the pages around each end of the range (four
outside, three inside) of every scanned golden book but the test set, asked the
page-type question below; "body" and "chapter_start" count as inside.
Results in work/probes/body-range-<model>.json.
"""

import json
import sys
import time
from pathlib import Path

from roboscriptorium.book import Book
from roboscriptorium.clients import decide, llama
from roboscriptorium.pdf import render_png

TEST = "het-geluid-van-bananen"
INSIDE = {"body", "chapter_start"}
Q = {"page": decide.choice("This is a scanned page of a printed book. What kind of page is it?", {
    "cover": "The front cover",
    "back_cover": "The back cover or binding",
    "blank": "An empty page, possibly with faint show-through or a small stamp",
    "title_page": "A title page or half-title: the book's title, author, publisher",
    "front_matter": "Copyright page, colophon, dedication, table of contents, preface",
    "chapter_start": "A page of running text on which a new chapter begins, with its heading or a large opening",
    "body": "A page of running text that continues without a new chapter",
    "back_matter": "Notes, index, appendix, advertisements after the text",
    "library_or_scan": "A library card, due-date slip, barcode, ownership stamp or digitisation notice"})}

model = sys.argv[1]
if model.startswith("llama:"):
    name, port = model.removeprefix("llama:").split("@")
    client = llama.ReadoutClient(name, f"http://127.0.0.1:{port}")
else:
    client = decide.for_model(model, "http://127.0.0.1:11434")

items = []
for toml in sorted(Path("work").glob("*/book.toml")):
    if toml.parent.name.startswith(TEST) or "calibre" in toml.parent.name:
        continue
    book = Book.load(toml.parent)
    first, last = book.body_pages
    pages = [*range(first - 4, first + 3), *range(last - 2, last + 5)]
    for n in sorted({p for p in pages if p >= 1}):
        items.append((toml.parent.name, book.source, n, first <= n <= last))

out = Path(f"work/probes/body-range-{model.replace(':', '_').replace('@', '_')}.json")
done = {(r["book"], r["page"]): r for r in json.loads(out.read_text())} if out.exists() else {}
t0 = time.time()
for name, source, n, inside in items:
    if (name, n) in done:
        continue
    try:
        png = render_png(source, n)
    except Exception:
        continue
    a = client.decide("A scanned page from a printed book.", Q, image_png=png)["page"]
    done[(name, n)] = {"book": name, "page": n, "inside": inside, "answer": a.value,
                       "confidence": a.confidence}  # fmt: skip
    out.write_text(json.dumps(list(done.values())))
rows = list(done.values())
right = sum((r["answer"] in INSIDE) == r["inside"] for r in rows)
print(f"{model}: {right}/{len(rows)} right, {(time.time() - t0) / max(1, len(rows)):.1f} s/page")
for r in rows:
    if (r["answer"] in INSIDE) != r["inside"]:
        side = "inside" if r["inside"] else "outside"
        print(f"  {r['book'][:28]:28} p{r['page']:<4} {side:7} → {r['answer']} ({r['confidence']:.2f})")
