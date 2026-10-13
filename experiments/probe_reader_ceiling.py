"""What a perfect reader could still gain: the wrong words a tuning slice keeps after
review (no question catches them), split by whether any reader doubted the place (a
suspect on its lines sharing a word with it) and by kind of error.

Wrong words on undoubted reading errors (letters, words, punctuation, quotes) are the
ones only a better reader fixes; doubted ones the arbiter and the review can reach.
Warm builds, no model calls.

    uv run python experiments/probe_reader_ceiling.py [spec …]
"""

import re
import sys
from collections import Counter

from roboscriptorium import bench, quality
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring

READING = {"letters", "words", "punctuation", "quotes"}


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def doubted(error, suspects) -> bool:
    if error.lines is None:
        return False
    words = _words(error.got) | _words(error.want)
    for s in suspects:
        if s.page != error.page or not error.lines[0] <= s.line <= error.lines[1]:
            continue
        place = _words(s.ours).union(*(_words(o) for o in s.others))
        if not words or words & place:
            return True
    return False


if __name__ == "__main__":
    specs = sys.argv[1:] or bench.SETS["tuning"]
    base = Settings.from_env()
    total: Counter = Counter()
    for spec in specs:
        run = scoring.build(f"work/{spec}", bench.unseen(base, spec.split(":")[0]))
        book: Counter = Counter()
        for e in run.errors:
            if any(quality.catches(f, e) for f in run.found):
                continue
            kind = quality.category(e)
            side = "doubted" if doubted(e, run.stages.suspects) else "undoubted"
            group = "reading" if kind in READING else "other"
            book[side, group] += quality.size(e)
            book["kind", kind, side] += quality.size(e)
        total.update(book)
        print(
            f"{run.name[:36]:36} left {sum(v for k, v in book.items() if k[0] != 'kind'):4}"
            f"  undoubted reading {book['undoubted', 'reading']:4}"
            f"  doubted reading {book['doubted', 'reading']:4}"
            f"  undoubted other {book['undoubted', 'other']:4}"
            f"  doubted other {book['doubted', 'other']:4}",
            flush=True,
        )
    left = sum(v for k, v in total.items() if k[0] != "kind")
    print(f"\nwrong words left after review: {left}")
    for side in ("undoubted", "doubted"):
        for group in ("reading", "other"):
            n = total[side, group]
            print(f"  {side:9} {group:7} {n:5}  {n / max(1, left):5.1%}")
    print("\nby kind:")
    for (_, kind, side), n in sorted(
        ((k, v) for k, v in total.items() if k[0] == "kind"), key=lambda kv: -kv[1]
    ):
        print(f"  {kind:14} {side:9} {n:5}")
