"""Reworked dropped idea 4 (the user, 2026-11-15): the extra signals that picked better but
saved no questions as arbiter columns (the book's vocabulary, a character language model,
the render judge's fit) put where asking is decided instead. Per settled trust-data place,
the held-out arbiter's pick and sureness (as `probe_book_vocab.py` scores them), then a
second model, trained on the other books, says how likely that pick is right from its
sureness and margin plus the signals. Questions needed to leave no more silent errors than
today's sureness ordering leaves at the rule's number, by each ordering; `--control` puts
random signals in their place, so the gain of re-ranking alone is seen apart.

    PYTHONPATH=experiments uv run python experiments/probe_ask_signals.py [--control]
"""

import argparse
import json
import math
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
from probe_book_vocab import SETTINGS, rule, scored, vocabulary
from probe_char_lm import AROUND, Model, counts, reference_text
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium.book import Book
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable

FIT = Path("work/probes/render-fit")


def lm_margin(model, s, k: int) -> float:
    if model is None:
        return math.nan
    before = s.original[max(0, s.start - AROUND) : s.start]
    after = s.original[s.end : s.end + AROUND]
    scores = [model.logp(before + v + after) for v in [s.ours, *s.others]]
    return scores[k] - max((x for i, x in enumerate(scores) if i != k), default=scores[k])


def fit_margin(fits: dict, s, k: int) -> float:
    versions = [s.ours, *s.others]
    m = fits.get(f"{s.page}|{s.line}|{s.start}|{json.dumps(versions, ensure_ascii=False)}")
    if not m or len(m["fits"]) != len(versions):
        return math.nan
    f = m["fits"]
    return f[k] - max((x for i, x in enumerate(f) if i != k), default=f[k])


def vocab_margin(words: Counter, s, k: int) -> float:
    def rarest(text: str) -> float:
        ws = [w.strip("'’-") for w in text.lower().split()]
        return min((math.log1p(words[w]) for w in ws if w), default=0.0)

    versions = [s.ours, *s.others]
    mine = rarest(versions[k])
    return mine - max((rarest(v) for i, v in enumerate(versions) if i != k), default=mine)


def questions_to(order_sure: np.ndarray, wrong: np.ndarray, target: int) -> int:
    """Questions asked least sure first until no more than `target` wrong picks are left."""
    left = int(wrong.sum())
    if left <= target:
        return 0
    for n, i in enumerate(np.argsort(order_sure), 1):
        left -= int(wrong[i])
        if left <= target:
            return n
    return len(order_sure)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    a = ap.parse_args()
    names = [n for n in SPECS if not usable(n, SETTINGS)]
    books = {n: rows_of(n, SETTINGS) for n in names}
    language = {n: Book.load(Path("work") / n).language[:2] for n in names}
    per_book, totals = {}, {}
    for n in names:
        try:
            per_book[n] = counts(reference_text(n))
            totals.setdefault(language[n], Counter()).update(per_book[n])
        except Exception:
            pass
    lms = {}
    for n in names:
        held = Counter(totals.get(language[n], Counter()))
        if n in per_book:
            held.subtract(per_book[n])
        lms[n] = Model(+held) if held else None
    fits = {n: json.loads((FIT / f"{n}.json").read_text()) if (FIT / f"{n}.json").exists() else {} for n in names}
    words = {n: vocabulary(n) for n in names}
    # Per book: the held-out arbiter's probabilities, then each row's signals.
    table = {}
    for name, rows in books.items():
        train_rows = [r for m in books if m != name and trainable(m) for r in books[m]]
        probs = scored(train_rows, rows, None, False)
        feats, wrong = [], []
        for r, p in zip(rows, probs, strict=True):
            k = int(p.argmax())
            ranked = sorted(p, reverse=True)
            base = [float(p.max()), float(ranked[0] - (ranked[1] if len(ranked) > 1 else 0))]
            if a.control:
                rng = np.random.default_rng(zlib.crc32(f"{name}|{r['s'].page}|{r['s'].line}|{r['s'].start}".encode()))
                extra = list(rng.normal(0, 1, 3))
            else:
                extra = [lm_margin(lms[name], r["s"], k), fit_margin(fits[name], r["s"], k), vocab_margin(words[name], r["s"], k)]
            feats.append(base + extra)
            wrong.append(not r["right"][k])
        table[name] = (np.array(feats), np.array(wrong), rule(rows)[1])
        print(name, flush=True)
    tot = Counter()
    for name, (X, wrong, asked) in table.items():
        others = [m for m in table if m != name and trainable(m)]
        Xt = np.vstack([table[m][0] for m in others])
        yt = np.concatenate([~table[m][1] for m in others])
        model = HistGradientBoostingClassifier(max_depth=3, min_samples_leaf=50, random_state=0)
        p_right = model.fit(Xt, yt).predict_proba(X)[:, 1]
        today_order = X[:, 0]
        left_today = int(wrong.sum()) - int(wrong[np.argsort(today_order)[:asked]].sum())
        tot["questions today"] += asked
        tot["silent today at the rule's"] += left_today
        tot["questions, re-ranked"] += questions_to(p_right, wrong, left_today)
        tot["questions, sureness alone"] += questions_to(today_order, wrong, left_today)
    print("totals:", dict(tot))


if __name__ == "__main__":
    main()
