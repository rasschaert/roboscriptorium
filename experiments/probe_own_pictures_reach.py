"""How many silent errors could a word's picture against the book's other pictures of the
same reading reach at all? Counts the tuning bench's one-token silent errors by how often
the built word stands in the book's text layer (body pages). No models, no pictures.

    uv run python experiments/probe_own_pictures_reach.py <bench errors.jsonl>
"""

import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium.book import Book
from roboscriptorium.pdf import cached_text_layer

STRAIGHT = str.maketrans("‘’“”", "''\"\"")
errors = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
reach, total = Counter(), Counter()
shown = []
for name in dict.fromkeys(e["book"] for e in errors):
    book = Book.load(Path("work") / name)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json")
    counts = Counter(
        t.translate(STRAIGHT)
        for p in layer
        if book.body_pages[0] <= p.number <= book.body_pages[1]
        for ln in p.lines
        for t in ln.text.split()
    )
    for e in errors:
        if e["book"] != name or e["asked"]:
            continue
        got, want = e["got"].strip(), e["want"].strip()
        if not got or " " in got or " " in want:
            total["not one token"] += 1
            continue
        total[e["cause"]] += 1
        n = counts[got]
        band = "0" if n == 0 else "1" if n == 1 else "2-4" if n < 5 else "5-19" if n < 20 else "20+"
        reach[(e["cause"], band)] += 1
        if n >= 5:
            shown.append((e["cause"], got, want, n, counts[want.translate(STRAIGHT)]))
for cause, n in total.most_common():
    print(f"{cause:28} {n:4}", {b: reach[(cause, b)] for b in ("0", "1", "2-4", "5-19", "20+") if reach[(cause, b)]})
for row in sorted(shown)[:80]:
    print("  ", row)
