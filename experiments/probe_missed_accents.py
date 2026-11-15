"""Accents every reader drops ("zíjn", "één": 105 of the tuning bench's 604 unasked errors
are a dropped mark, 36 of them where no reading differed, so nothing could ask). Does the
accent-zone fit (`probe_accent_fit.measures`) find them among plain words? Positives: the
bench's unasked dropped-mark errors, located on their page by the word the build has.
Negatives: a sample of each book's body words with a vowel, absent from the error log,
given the mark an emphasis would put there ("ij" → "íj", a doubled vowel both, else the
first vowel). Prints the AUC and, at the false-alarm rates a book could bear, the share of
dropped marks found. No models.

    PYTHONPATH=experiments uv run python experiments/probe_missed_accents.py <bench errors.jsonl> [negatives per book]
"""

import json
import random
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pymupdf
from probe_accent_fit import measures
from sklearn.metrics import roc_auc_score

from roboscriptorium import pdf as pdflayer
from roboscriptorium import pipeline, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/missed-accents.jsonl")
ACUTE = "\u0301"
PUNCT = "'’‘“”\".,;:!?()"


def strip(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


def stressed(word: str) -> str | None:
    """The word as an emphasis would mark it, or None where it has no vowel to mark."""
    m = re.search(r"ij|([aeou])\1|[aeiou]", word, re.I)
    if not m:
        return None
    hit = m.group()
    new = hit[0] + ACUTE + hit[1] if hit.lower() == "ij" else "".join(c + ACUTE for c in hit)
    return unicodedata.normalize("NFC", word[: m.start()] + new + word[m.end() :])


def main():
    errors = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
    per_book = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    settings = Settings.from_env()
    done = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            row = json.loads(line)
            done.setdefault(row["book"], []).append(row)
    for name in dict.fromkeys(e["book"] for e in errors):
        if name in done:
            continue
        book = Book.load(Path("work") / name)
        layer = cached_text_layer(book.source, book.stages / "textlayer.json")
        body = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
        judge = pipeline._alarm("render", settings, book, body)
        if judge is None:
            continue
        texts = {p.number: p for p in layer}
        mine = [e for e in errors if e["book"] == name]
        dropped = [e for e in mine if not e["asked"] and e["got"] != e["want"] and strip(e["want"]) == e["got"]]
        known = {(e["page"], strip(e["got"]).lower()) for e in mine}
        rows = []
        with pymupdf.open(book.source) as doc:
            def measure(page: int, word: tuple, marked: str, plain: str):
                ink = rendercheck.place_ink(doc[page - 1], word[:4], texts.get(page))
                return None if ink is None else measures(judge._face, judge._match, ink, marked, plain)

            for e in dropped:
                bare, want = e["got"].strip(PUNCT), e["want"].strip(PUNCT)
                every = pdflayer.page_words(doc[e["page"] - 1], texts.get(e["page"]))
                clean = [w[4].strip(PUNCT) for w in every]
                words = [w for w, c in zip(every, clean, strict=True) if c == bare]
                if len(words) > 1 and e["before"].split():
                    # The same word twice on a page: the one after the error's word before.
                    last = e["before"].split()[-1].strip(PUNCT)
                    words = [w for i, w in enumerate(every) if clean[i] == bare and i and clean[i - 1] == last]
                if len(words) != 1 or len(bare) != len(want):
                    continue
                m = measure(e["page"], words[0], want, bare)
                if m:
                    rows.append({"book": name, "page": e["page"], "word": bare, "marked": want, "print_marked": True, "check": e["check"], **m})
            random.seed(0)
            pool = [(p.number, w) for p in body for w in pdflayer.page_words(doc[p.number - 1], p)]
            for page, w in random.sample(pool, min(len(pool), per_book * 2)):
                bare = w[4].strip(PUNCT)
                marked = stressed(bare) if bare.isalpha() and strip(bare) == bare else None
                if marked is None or (page, bare.lower()) in known:
                    continue
                m = measure(page, w, marked, bare)
                if m:
                    rows.append({"book": name, "page": page, "word": bare, "marked": marked, "print_marked": False, "check": None, **m})
                if sum(not r["print_marked"] for r in rows) >= per_book:
                    break
        with OUT.open("a") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[name] = rows
        print(f"{name}: {sum(r['print_marked'] for r in rows)} dropped marks placed, {sum(not r['print_marked'] for r in rows)} plain words", flush=True)
    rows = [r for rs in done.values() for r in rs]
    y = np.array([r["print_marked"] for r in rows])
    print(f"{int(y.sum())} dropped marks, {int((~y).sum())} plain words")
    for k in ("cosine", "signed", "mass", "whole"):
        x = np.array([r[k] for r in rows])
        line = f"  {k:7} AUC {roc_auc_score(y, x):.3f};"
        for rate in (0.01, 0.003, 0.001):
            cut = np.quantile(x[~y], 1 - rate)
            line += f" found at {rate:.1%} false alarms: {int((x[y] > cut).sum())} of {int(y.sum())};"
        print(line)
    for check in (None, "ours", "other"):
        sub = [r for r in rows if r["print_marked"] and r["check"] == check]
        print(f"  dropped marks with check={check}: {len(sub)}, cosine median {np.median([r['cosine'] for r in sub]) if sub else float('nan'):.2f}")
    neg = sorted((r for r in rows if not r["print_marked"]), key=lambda r: -r["cosine"])[:15]
    print("  plain words that look most marked:", [(r["book"][:10], r["page"], r["word"], round(r["cosine"], 2)) for r in neg])


if __name__ == "__main__":
    main()
