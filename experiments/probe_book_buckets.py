"""Would a book's answers, counted by kind of change and the readers reading it, settle
its other questions right?

Each answered line is held out in turn; the buckets (`trust.book_buckets`) come from the
book's other answers, and the held-out line's suspects the arbiter asked are decided
by them where they can be (`trust.by_book`). Then every open question is tried with
all answers. No models; reads the book's cached suspects and its review answers.

    uv run python experiments/probe_book_buckets.py work/ex-minnaar
"""

import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import corrections, trust, trustdata
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections

BELOW = Settings().ocr_ask_below


def main(book_dir: str) -> None:
    book = Book.load(Path(book_dir))
    raw = json.loads((book.stages / "ocr-check.json").read_text())
    suspects = [trustdata.suspect({"suspect": s}) for s in raw]
    answers = Corrections(book.corrections_path)
    rows = [
        r
        for r in trust.rows_from(suspects, corrections.answered(answers, suspects))
        if r["settled"]
    ]
    lines = {(r["suspect"]["page"], r["suspect"]["line"]) for r in rows}
    held = Counter()
    for line in sorted(lines):
        mine = [r for r in rows if (r["suspect"]["page"], r["suspect"]["line"]) == line]
        buckets = trust.book_buckets([r for r in rows if r not in mine])
        for r in mine:
            s = trustdata.suspect(r)
            if s.choice != "review":
                continue
            (got,) = trust.by_book([s], buckets, BELOW)
            if got.choice == "review":
                held["asked"] += 1
            else:
                held["right" if r["right"][1 + s.others.index(got.chosen)] else "wrong"] += 1
    print(f"answered suspects the arbiter asked, each line held out: {dict(held)}")
    buckets = trust.book_buckets(rows)
    for key, (a, n) in sorted(buckets.items(), key=lambda kv: -kv[1][1]):
        if n >= trust.BUCKET_MIN:
            print(f"  {key[0]:8} {'+'.join(key[1]) or '-':16} {a}/{n}")
    open_ = [s for s in suspects if s.choice == "review" and (s.page, s.line) not in lines]
    decided = [s for s in trust.by_book(open_, buckets, BELOW) if s.choice != "review"]
    print(f"open: {len(open_)} asked suspects, {len(decided)} settled by the book's answers")
    for s in decided:
        print(f"  p{s.page} {s.ours!r} → {s.chosen!r}")


if __name__ == "__main__":
    main(sys.argv[1])
