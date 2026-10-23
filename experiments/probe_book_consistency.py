"""Would a book's own spellings catch the errors no reader doubts? (a deep-research idea,
2026-10-23). No models: each tuning slice built warm, as the bench builds it.

A word is flagged when the book's output spells it this way at most `RARE` times while a
close variant (the same letters without their accents, without a hyphen, or one letter
apart in a word of `MIN_LETTERS` or more) occurs at least `COMMON` times. Scored against
the latest tuning bench's errors: how many unasked one-word errors are flagged (their right
form common elsewhere in the book), and how many flags fall on words the bench counts right.

    uv run python experiments/probe_book_consistency.py [errors.jsonl]
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
WORD = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")


def bare(word: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn"
    )


def variants(word: str, counts: Counter) -> list[str]:
    """The book's common words that `word` could be an OCR slip of."""
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
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_errors()
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
