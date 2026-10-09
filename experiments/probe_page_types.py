"""Probe a vision decision model on page types for a hand-labelled sample.

Usage: uv run python experiments/probe_page_types.py MODEL (an Ollama decision model, or
llama:<imajev name>@<port> for llama-server)
Labels: Tauchnitz front/back matter from a contact sheet, chapter starts from
the text layer; Stella pages as described in AGENTS.md. 23 pages, ~4 s each.
"""

import json, sys, time
from collections import Counter
from pathlib import Path
from roboscriptorium.clients import decide, llama
from roboscriptorium.pdf import render_png

model = sys.argv[1]
TAU = Path("work/retired/sense-and-sensibility--tauchnitz-1864/source.pdf")
STE = Path("work/stella/source.pdf")
chapters = {7, 11, 17, 21, 26, 29, 33, 37, 40, 46, 52, 56, 61, 67, 72, 79, 85, 90, 95, 103, 110, 118, 126, 133, 139, 145, 152, 159, 163, 175, 183, 194, 201, 209, 217, 224, 232, 245, 253, 258, 266, 273, 278, 287, 303, 309, 317, 324, 328, 339}
gold = {}
for n in range(1, 350):
    gold[(TAU, n)] = {1: "cover", 2: "library_or_scan", 3: "title_page", 4: "blank", 5: "title_page", 6: "blank",
                      347: "library_or_scan", 348: "library_or_scan", 349: "back_cover"}.get(n, "chapter_start" if n in chapters else "body")
for n in range(1, 77):
    g = {1: "cover", 3: "library_or_scan", 4: "front_matter", 5: "chapter_start", 73: "blank", 74: "blank", 75: "library_or_scan", 76: "back_cover"}.get(n)
    if g is None and 6 <= n <= 71: g = "body"
    if g: gold[(STE, n)] = g
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
SAMPLE = {(TAU, n) for n in (1, 2, 3, 4, 5, 6, 7, 8, 11, 100, 175, 200, 347, 348, 349)} | {(STE, n) for n in (1, 3, 4, 5, 30, 74, 75, 76)}
gold = {k: v for k, v in gold.items() if k in SAMPLE}
if model.startswith("llama:"):
    name, port = model.removeprefix("llama:").split("@")
    client = llama.ReadoutClient(name, f"http://127.0.0.1:{port}")
else:
    client = decide.for_model(model, "http://127.0.0.1:11434")
rows, t0 = [], time.time()
for (pdf, n), g in gold.items():
    t1 = time.time()
    a = client.decide("A scanned page from a printed book.", Q, image_png=render_png(pdf, n))["page"]
    rows.append((pdf.parent.name, n, g, a.value, a.confidence))
    print(f"  {pdf.parent.name[:10]} p{n}: {g} → {a.value} ({a.confidence:.2f}) {time.time() - t1:.1f}s", flush=True)
print(f"{model}: {len(rows)} pages, {(time.time() - t0) / len(rows) * 1000:.0f} ms/page")
for book in ("sense-and-sensibility--tauchnitz-1864", "stella"):
    r = [x for x in rows if x[0] == book]
    print(f"  {book}: {sum(g == p for _, _, g, p, _ in r)}/{len(r)} exact")
    conf = Counter((g, p) for _, _, g, p, _ in r if g != p)
    for (g, p), c in conf.most_common(8): print(f"     {c:3}× {g} → {p}")
    print("     non-body pages:", [(n, g, p, round(c, 2)) for _, n, g, p, c in r if g not in ("body", "chapter_start")])
Path("work/probes").mkdir(exist_ok=True)
json.dump(rows, open(f"work/probes/pages-{model.replace(':', '_').replace('@', '_')}.json", "w"))
