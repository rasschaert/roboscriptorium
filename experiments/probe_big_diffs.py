"""Probe: the largest stretches where a book's output differs from its reference.

    uv run python experiments/probe_big_diffs.py work/<book> <first chapter> <last chapter>
"""

import json
import sys
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium.book import Book
from roboscriptorium.evaluate import _words_with_breaks
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters

book = Book.load(Path(sys.argv[1]))
first, last = int(sys.argv[2]), int(sys.argv[3])
reference = load_chapters(Golden.load(book.golden).text_dir)[first - 1 : last]
doc = json.loads((book.stages / "document.json").read_text())
blocks = doc["blocks"] if isinstance(doc, dict) else doc
out = [b["text"] for b in blocks if "text" in b and "parts" not in b]  # headings have parts
ref_words, _ = _words_with_breaks([p for ch in reference for p in ch.paragraphs])
out_words, _ = _words_with_breaks(out)
ops = []
for op in Levenshtein.opcodes(out_words, ref_words):
    if op.tag == "equal":
        continue
    got = " ".join(out_words[op.src_start : op.src_end])
    want = " ".join(ref_words[op.dest_start : op.dest_end])
    ops.append((Levenshtein.distance(got, want), got, want))
total = sum(c for c, _, _ in ops)
print(f"{len(ops)} differing stretches, {total} char edits")
for size in (1, 3, 10, 50, 200):
    print(f"  stretches of ≥{size} edits: {sum(c for c, _, _ in ops if c >= size)} edits")
for c, got, want in sorted(ops, reverse=True)[:12]:
    print(f"{c:6}  {got[:110]!r}\n        → {want[:110]!r}")
