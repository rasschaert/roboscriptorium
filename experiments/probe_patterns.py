"""Would one question per pattern save the reviewer questions without settling lines wrong?

A pattern is one exact substitution between the text layer's version and another
(`trust.pair`: "'we'→'wc'"). Walking a book's answered OCR questions in page order, a
question is skipped when every asked stretch of its line holds a pattern the reviewer has
already answered the same way at least `need` times and never the other way: taken where
it was always the print, left where it never was. Each skipped line is checked against
the reviewer's own answer to it. No models; reads the book's cached suspects and answers.

    uv run python experiments/probe_patterns.py work/ex-minnaar work/stella
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

from roboscriptorium import trust, trustdata
from roboscriptorium.book import Book


def walk(book_dir: str, need: int) -> tuple[int, int, int, list[str]]:
    book = Book.load(Path(book_dir))
    raw = json.loads((book.stages / "ocr-check.json").read_text())
    suspects = [trustdata.suspect({"suspect": s}) for s in raw]
    rows = trustdata.rows_from(suspects, trustdata.answered(book, suspects))
    asked = [r for r in rows if r["suspect"]["choice"] == "review"]
    lines: dict[tuple, list[dict]] = defaultdict(list)
    for r in asked:
        lines[(r["suspect"]["page"], r["suspect"]["line"])].append(r)
    taken: dict[str, int] = defaultdict(int)  # the pattern's version was the print
    left: dict[str, int] = defaultdict(int)  # it was offered and wasn't
    answered = skipped = wrong = 0
    slips = []
    for key in sorted(lines):
        group = lines[key]
        guesses = []
        for r in group:
            s = r["suspect"]
            versions = [s["ours"], *s["others"]]
            pats = [trust.pair(s["ours"], v) for v in versions]
            sure = [
                k for k, p in enumerate(pats)
                if k and taken[p] >= need and not left[p]
            ]  # fmt: skip
            if len(sure) == 1:
                guesses.append(sure[0])
            elif all(left[p] >= need and not taken[p] for p in pats[1:]):
                guesses.append(0)
            else:
                guesses.append(None)
        if all(g is not None for g in guesses) and all(r["settled"] for r in group):
            skipped += 1
            if not all(r["right"][g] for r, g in zip(group, guesses)):
                wrong += 1
                s = group[0]["suspect"]
                slips.append(f"p{s['page']} {s['ours']!r} {s['others']} → {group[0]['truth']!r}")
            continue
        answered += 1
        for r in group:
            if not r["settled"]:
                continue
            s = r["suspect"]
            for k, v in enumerate(s["others"], 1):
                p = trust.pair(s["ours"], v)
                if r["right"][k]:
                    taken[p] += 1
                else:
                    left[p] += 1
    return answered, skipped, wrong, slips


def main(books: list[str]) -> None:
    for need in (1, 2, 3):
        for b in books:
            answered, skipped, wrong, slips = walk(b, need)
            print(f"need {need}  {Path(b).name:12} asked {answered:3}  skipped {skipped:3}  "
                  f"of them wrong {wrong}")
            for s in slips[:8]:
                print("     ", s)


if __name__ == "__main__":
    main(sys.argv[1:])
