"""Label each text-layer line body / other by aligning it to the golden reference.

Usage: uv run python experiments/label_lines.py work/sense-and-sensibility--tauchnitz-1864
Writes stages/line-labels.json. A line is "body" when at least half its words
align with the reference, "other" when none do, otherwise "unsure".
"""
import json, sys
from pathlib import Path
from rapidfuzz.distance import Levenshtein
from roboscriptorium.book import Book
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.golden.manifest import Golden

book = Book.load(Path(sys.argv[1]))
pages = cached_text_layer(book.source, book.stages / "textlayer.json")
first, last = book.body_pages
ref = [w for ch in load_chapters(Golden.load(book.golden).text_dir) for p in ch.paragraphs for w in normalise(p).split()]
words, owner = [], []
lines = []
for p in pages:
    if not first <= p.number <= last: continue
    for i, ln in enumerate(p.lines):
        lines.append((p.number, i))
        for w in normalise(ln.text).split():
            words.append(w); owner.append(len(lines) - 1)
matched = [0] * len(lines); total = [0] * len(lines)
for o in owner: total[o] += 1
for op in Levenshtein.opcodes(words, ref):
    if op.tag == "equal":
        for k in range(op.src_start, op.src_end): matched[owner[k]] += 1
labels = {}
for idx, (pg, i) in enumerate(lines):
    frac = matched[idx] / total[idx] if total[idx] else 0
    labels[f"{pg}:{i}"] = "body" if frac >= 0.5 else ("other" if frac == 0 else "unsure")
from collections import Counter
print(Counter(labels.values()))
(book.stages / "line-labels.json").write_text(json.dumps(labels))
