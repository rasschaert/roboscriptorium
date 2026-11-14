"""How likely each version of a place is in its language, as arbiter columns (the user's
idea, 2026-11-14: "they should take into consideration whether something contentious has
one or more options that are just very unlikely based on language rules"). A character
n-gram model per language, from the golden books' reference text, each book scored by a
model without its own reference (its counts taken out of the language's). Per version:
the log-likelihood of the line around it, and its margin over the best other version.
Two arbiters on the same held-out folds as `probe_book_vocab.py`, today's features
against today's plus these; `--control` puts random columns in their place.

    PYTHONPATH=experiments uv run python experiments/probe_char_lm.py [--control]
"""

import argparse
import math
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
from probe_book_vocab import READINGS, SEATS, SETTINGS, rule, silent_at
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.book import Book
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable

ORDER = 5
# Characters of the line either side of the place that the likelihood reads.
AROUND = 12


def counts(text: str) -> Counter:
    """Every n-gram of orders 1 to ORDER, the text padded at its start."""
    padded = " " * (ORDER - 1) + text
    out: Counter = Counter()
    for n in range(1, ORDER + 1):
        for i in range(len(padded) - n + 1):
            out[padded[i : i + n]] += 1
    return out


class Model:
    """Interpolated n-gram likelihoods from counts (`counts`), add-one at the bottom."""

    def __init__(self, grams: Counter):
        self.grams = grams
        self.chars = sum(v for k, v in grams.items() if len(k) == 1)
        self.vocab = sum(1 for k in grams if len(k) == 1) + 1

    def logp(self, text: str) -> float:
        padded = " " * (ORDER - 1) + text
        total = 0.0
        for i in range(ORDER - 1, len(padded)):
            p = (self.grams.get(padded[i], 0) + 1) / (self.chars + self.vocab)
            for n in range(2, ORDER + 1):
                ctx = padded[i - n + 1 : i]
                seen = self.grams.get(ctx, 0)
                if seen:
                    p = 0.6 * self.grams.get(ctx + padded[i], 0) / seen + 0.4 * p
            total += math.log(p)
        return total


def reference_text(book: str) -> str:
    golden = Golden.load(Book.load(Path("work") / book).golden)
    return "\n".join(
        part for ch in load_chapters(golden.text_dir) for part in [ch.heading, *ch.paragraphs]
    )


def columns(s, k: int, model: Model | None, control: bool) -> list[float]:
    versions = [s.ours, *s.others]
    if control:
        rng = np.random.default_rng(zlib.crc32(f"{versions[0]}|{versions[k]}|{k}".encode()))
        return list(rng.uniform(-20, 0, 2))
    if model is None:
        return [math.nan, math.nan]
    before = s.original[max(0, s.start - AROUND) : s.start]
    after = s.original[s.end : s.end + AROUND]
    scores = [model.logp(before + v + after) for v in versions]
    rival = max((x for i, x in enumerate(scores) if i != k), default=scores[k])
    return [scores[k], scores[k] - rival]


_COLS: dict[tuple[int, int], list[float]] = {}


def scored(train_rows, rows, extra, models, control):
    def cols(r, k):
        if not extra:
            return []
        key = (id(r), k)
        if key not in _COLS:
            _COLS[key] = columns(r["s"], k, models.get(r["book"]), control)
        return _COLS[key]

    suspects = [r["s"] for r in train_rows]
    right = [r["right"] for r in train_rows]
    names = [r["book"] for r in train_rows]
    X, y = trust.training_matrix(suspects, right, names, READINGS, SEATS)
    if extra:
        added = [cols(r, k) for b in dict.fromkeys(names) for r in train_rows if r["book"] == b
                 for k in range(len(r["right"]))]  # fmt: skip
        X = np.hstack([X, np.array(added)])
    pairs = trust.pairs_table(suspects, right, names)
    Xt, owner = [], []
    for i, r in enumerate(rows):
        for k in range(len(r["right"])):
            Xt.append(trust.features(r["s"], k, pairs, READINGS, SEATS) + cols(r, k))
            owner.append(i)
    model = HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )
    probs = model.fit(X, y).predict_proba(np.array(Xt))[:, 1]
    out = [[] for _ in rows]
    for p, i in zip(probs, owner, strict=True):
        out[i].append(p)
    return [np.array(p) / max(sum(p), 1e-9) for p in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    a = ap.parse_args()
    names = [n for n in SPECS if not usable(n, SETTINGS)]
    language = {n: Book.load(Path("work") / n).language[:2] for n in names}
    per_book = {}
    for n in names:
        try:
            per_book[n] = counts(reference_text(n))
        except Exception as e:  # a book without a golden reference: no columns
            print(f"{n}: no reference ({e})")
    totals: dict[str, Counter] = {}
    for n, c in per_book.items():
        totals.setdefault(language[n], Counter()).update(c)
    # Each book's model without its own reference.
    models = {}
    for n in names:
        held = Counter(totals.get(language[n], Counter()))
        if n in per_book:
            held.subtract(per_book[n])
        models[n] = Model(+held) if held else None
    print("models:", {lang: sum(v for k, v in c.items() if len(k) == 1) for lang, c in totals.items()}, flush=True)
    books = {n: rows_of(n, SETTINGS) for n in names}
    tot, changed = Counter(), []
    for name, rows in books.items():
        silent, asked = rule(rows)
        train_rows = [r for n in books if n != name and trainable(n) for r in books[n]]
        pa = scored(train_rows, rows, False, models, a.control)
        pb = scored(train_rows, rows, True, models, a.control)
        cells = []
        for lab, n in (("rule's", asked), ("none", 0), ("half", asked // 2)):
            x, y_ = silent_at(rows, pa, n), silent_at(rows, pb, n)
            tot[f"today@{lab}"] += x
            tot[f"+lm@{lab}"] += y_
            cells.append(f"{x}/{y_}")
        # Questions each needs to leave no more silent errors than today does at the rule's.
        target = silent_at(rows, pa, asked)
        need = [next(n for n in range(len(rows) + 1) if silent_at(rows, p, n) <= target)
                for p in (pa, pb)]  # fmt: skip
        tot["today questions"] += need[0]
        tot["+lm questions"] += need[1]
        print(f"{name[:34]:34} {silent:4}/{asked:<4}  " + "  ".join(cells)
              + f"  questions {need[0]}/{need[1]}", flush=True)  # fmt: skip
        for r, x, y_ in zip(rows, pa, pb, strict=True):
            if int(x.argmax()) != int(y_.argmax()):
                v = [r["s"].ours, *r["s"].others]
                changed.append((name, v, v[int(x.argmax())], v[int(y_.argmax())], r["right"][int(y_.argmax())]))
    print("totals:", dict(tot))
    fixed = [c for c in changed if c[4]]
    print(f"best version changed on {len(changed)} suspects: right now on {len(fixed)}, wrong now on {len(changed) - len(fixed)}")
    for c in changed[:50]:
        print(f"  {'FIXED' if c[4] else 'BROKE'} {c[0][:16]:16} {c[1]}  {c[2]!r} → {c[3]!r}")


if __name__ == "__main__":
    main()
