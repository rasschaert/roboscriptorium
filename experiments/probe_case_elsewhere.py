"""How the book capitalises a word elsewhere, as a signal for a case error: for each case
error a tuning bench left (its errors.jsonl), the forms of the word that differs in case
across the book as built (`stages/document.json`), and whether the book's most frequent
form is the print's. No models.

    uv run python experiments/probe_case_elsewhere.py work/bench/tuning-….errors.jsonl
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[^\W\d_]+")


def differing(got: str, want: str) -> str | None:
    """The word of `want` whose case `got` changes ("SS" in "SS-chef")."""
    gw, ww = WORD.findall(got), WORD.findall(want)
    if len(gw) != len(ww):
        return None
    diff = [w for g, w in zip(gw, ww) if g != w and g.casefold() == w.casefold()]
    return diff[0] if len(diff) == 1 else None


def text(book: str) -> str:
    doc = json.loads((Path("work") / book / "stages/document.json").read_text())
    return "\n".join(b.get("text", "") for b in doc["blocks"])


def forms(book_text: str, word: str, want: str) -> Counter:
    """The forms of `word` in the book, as a whole word; where the print joins it to a
    hyphen ("SS-chef"), only where the book does too, so a pronoun "u" leaves "U-bocht"."""
    joined = re.search(rf"(?<![^\W\d_]){re.escape(word)}-", want) is not None
    tail = "-" if joined else r"(?![^\W\d_])"
    found = re.findall(rf"(?<![^\W\d_])({re.escape(word)}){tail}", book_text, re.IGNORECASE)
    return Counter(found)


if __name__ == "__main__":
    rows = [json.loads(line) for line in open(sys.argv[1])]
    rows = [r for r in rows if r["cause"] == "case"]
    books: dict[str, str] = {}
    tally = Counter()
    for r in rows:
        word = differing(r["got"], r["want"])
        if word is None:
            print(f"  ?  {r['book'][:24]:24} p{r['page']} {r['got']!r} → {r['want']!r}")
            tally["unclear"] += 1
            continue
        if r["book"] not in books:
            books[r["book"]] = text(r["book"])
        variants = dict(forms(books[r["book"]], word, r["want"]))
        # Sentence-initial capitals say nothing about small capitals: a lower-case word
        # capitalised only at its first letter is left out of the count.
        variants = {
            w: n
            for w, n in variants.items()
            if not (len(w) > 1 and w[0].isupper() and w[1:].islower() and word[1:].islower())
        }
        top = max(variants, key=variants.get) if variants else None
        verdict = "print" if top == word else ("other" if top else "none")
        tally[(verdict, "asked" if r["asked"] else "silent")] += 1
        print(
            f"  {verdict:5} {'asked' if r['asked'] else 'SILENT':6} {r['book'][:24]:24} "
            f"p{r['page']:<4} {r['got']!r} → {r['want']!r}  forms {variants}"
        )
    print()
    for k, n in sorted(tally.items(), key=str):
        print(f"{k}: {n}")
