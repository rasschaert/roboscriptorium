"""Where Stella's build and Claude's whole-page reading of its body pages differ
(`work/probes/claude-stella/readings/`, the user's permission for this probe only).
No models: the build from its caches. Claude read one near-perfect page in 17 against
golden references (docs/decisions.md, 2026-10-15), so a difference is mostly the
pipeline's error, to be checked on the scan, not assumed.

Both sides are compared as one text, Claude's pages joined in order (a word broken at a
page's foot joined to the next page's first), each difference sorted by kind and placed
on the page Claude read it on.

    uv run python experiments/compare_stella_claude.py
Writes work/probes/claude-stella/differences.jsonl.
"""

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).parent))
from probe_page_reader import BREAK, stream_of_doc, tokens_of_markdown  # noqa: E402

from roboscriptorium import pipeline  # noqa: E402
from roboscriptorium.book import Book  # noqa: E402

DIR = Path("work/probes/claude-stella")
QUOTES = "‘’“”\"'‚„«»"


def claude_stream() -> tuple[list[str], list[int]]:
    """Claude's words and breaks over the body pages, and each token's page."""
    words, pages = [], []
    for n in range(5, 72):
        tokens = tokens_of_markdown((DIR / "readings" / f"stella-{n}.txt").read_text())
        while tokens and tokens[0] == BREAK and words and words[-1] != BREAK:
            tokens = tokens[1:]
        # A word broken at the previous page's foot goes on here.
        if words and words[-1].endswith("-") and words[-1] != BREAK and tokens:
            words[-1] = words[-1][:-1] + tokens.pop(0)
        if words and words[-1] == BREAK and tokens and tokens[0][:1].islower():
            words.pop(), pages.pop()  # a paragraph going on over the page
        words += tokens
        pages += [n] * len(tokens)
    return words, pages


def bare(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def kind(ours: str, theirs: str) -> str:
    if BREAK in ours or BREAK in theirs:
        return "paragraph break"
    if not ours or not theirs:
        return "missing words" if not ours else "extra words"
    if ours.replace(" ", "") == theirs.replace(" ", ""):
        return "word spacing"
    if ours.replace("-", "") == theirs.replace("-", ""):
        return "hyphen"
    strip = lambda s: re.sub(rf"[{QUOTES}]", "", s)  # noqa: E731
    if strip(ours) == strip(theirs):
        return "quotes"
    if re.sub(r"\W", "", ours) == re.sub(r"\W", "", theirs):
        return "punctuation"
    if bare(ours) == bare(theirs):
        return "accents"
    return "letters"


book = Book.load(Path("work/stella"))
stages = pipeline.run(book)
ours = stream_of_doc(stages.doc)
theirs, page_of = claude_stream()
rows, sizes = [], Counter()
for op in Levenshtein.opcodes(ours, theirs):
    if op.tag == "equal":
        continue
    a = " ".join(ours[op.src_start : op.src_end])
    b = " ".join(theirs[op.dest_start : op.dest_end])
    page = page_of[min(op.dest_start, len(page_of) - 1)]
    before = " ".join(t for t in theirs[max(0, op.dest_start - 6) : op.dest_start] if t != BREAK)
    after = " ".join(t for t in theirs[op.dest_end : op.dest_end + 6] if t != BREAK)
    k = kind(a, b)
    rows.append({"page": page, "kind": k, "ours": a, "claude": b, "before": before, "after": after})
    sizes[k] += 1
(DIR / "differences.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
words = sum(t != BREAK for t in theirs)
print(f"{len(rows)} differences over {words} words, 67 pages ({len(rows) / 67:.2f} a page)")
for k, n in sizes.most_common():
    print(f"  {n:4}  {k}")
print()
for r in rows:
    print(f"  p{r['page']:<3} {r['kind']:15} ours {r['ours']!r:28} claude {r['claude']!r:28} …{r['before'][-30:]}|{r['after'][:30]}")
