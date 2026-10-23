"""Would a book's own spellings catch the errors no reader doubts? (a deep-research idea,
2026-10-23). No models: each tuning slice built warm, as the bench builds it.

A word is flagged when the book's output spells it this way at most `RARE` times while a
close variant (the same letters without their accents, without a hyphen, or one letter
apart in a word of `MIN_LETTERS` or more) occurs at least `COMMON` times. Scored against
the latest tuning bench's errors: how many unasked one-word errors are flagged (their right
form common elsewhere in the book), and how many flags fall on words the bench counts right.

    uv run python experiments/probe_book_consistency.py [errors.jsonl] [--marks]

`--pairs` (Fable's mined confusion pairs) flags a word the readers swapped for another
in some other tuning book's errors, where that other word occurs in this book.

`--marks` (Argon's narrowing) flags only a reading that lacks a diaeresis or a letter outside
ASCII (ë, ï, ı, ł, ç …) its common variant has; acute and grave accents vary by emphasis
in Dutch, so they never flag.
"""

import json
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"

from rapidfuzz.distance import Levenshtein  # noqa: E402

from roboscriptorium import bench  # noqa: E402
from roboscriptorium.golden import scoring  # noqa: E402

RARE, COMMON, MIN_LETTERS = 1, 3, 5
MARKS = "--marks" in sys.argv
PAIRS = "--pairs" in sys.argv
# Accents that mark emphasis or stress, which a book may set on one occurrence only.
STRESS = {"\u0301", "\u0300"}
WORD = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")


def bare(word: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn"
    )


def lost_mark(word: str, other: str) -> bool:
    """Whether `other` is `word` with a diaeresis or a non-ASCII letter `word` lacks."""
    if bare(other) != bare(word) or other == word:
        return False
    extra = [c for c in unicodedata.normalize("NFD", other) if ord(c) > 127]
    return bool(extra) and not set(extra) <= STRESS and len(other) == len(word)


def variants(word: str, counts: Counter) -> list[str]:
    """The book's common words that `word` could be an OCR slip of."""
    if MARKS:
        return [o for o, n in counts.items() if n >= COMMON and lost_mark(word, o)]
    out = []
    key = bare(word).replace("-", "")
    for other, n in counts.items():
        if n < COMMON or other == word:
            continue
        if bare(other).replace("-", "") == key:
            out.append(other)
        elif len(word) >= MIN_LETTERS and abs(len(other) - len(word)) <= 1:
            if Levenshtein.distance(word, other, score_cutoff=1) <= 1:
                out.append(other)
    return out


def latest_errors() -> Path:
    runs = sorted(Path("work/bench").glob("tuning-*.errors.jsonl"))
    return runs[-1]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = Path(args[0]) if args else latest_errors()
    errors = [json.loads(x) for x in path.read_text().splitlines()]
    totals: Counter = Counter()
    examples = []
    for spec in bench.SETS["tuning"]:
        name = spec.split(":")[0]
        run = scoring.build(f"work/{spec}", bench.unseen(scoring.Settings.from_env(), name))
        doc = scoring.scored(run.book, run.stages)
        words = [w.lower() for p in doc.paragraphs for w in WORD.findall(p.text)]
        counts = Counter(words)
        rare = {w for w, n in counts.items() if n <= RARE}
        if PAIRS:
            swapped = {}
            for e in errors:
                g, w = WORD.findall(e["got"] or ""), WORD.findall(e["want"] or "")
                if e["book"] != name and len(g) == 1 and len(w) == 1 and g[0] != w[0]:
                    swapped.setdefault(g[0].lower(), set()).add(w[0].lower())
            flagged = {
                w: [y for y in swapped[w] if counts[y]] for w in counts
                if w in swapped and any(counts[y] for y in swapped[w])
            }  # fmt: skip
        else:
            flagged = {w: v for w in rare if (v := variants(w, counts))}
        wrong_got = Counter()
        for e in errors:
            if e["book"] != name or e["size"] != 1:
                continue
            got, want = (WORD.findall(e["got"] or ""), WORD.findall(e["want"] or ""))
            if len(got) != 1 or len(want) != 1:
                continue
            g, w = got[0].lower(), want[0].lower()
            wrong_got[g] += 1
            kind = "asked" if e["asked"] else "unasked"
            totals[f"{kind} one-word errors"] += 1
            if g in flagged and w in flagged[g]:
                totals[f"{kind} caught"] += 1
                examples.append((name[:20], e["page"], kind, g, w, e["cause"]))
        totals["flags"] += len(flagged)
        totals["flags on errors"] += sum(1 for w in flagged if w in wrong_got)
        print(f"{name[:40]:40} words {len(words):6}  flags {len(flagged):4}", flush=True)
    print("\n", dict(totals))
    for x in examples:
        print("  ", x)
