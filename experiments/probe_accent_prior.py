"""Why training on the accent offers made the arbiter ask about accents the readers do
read, and whether keeping the offers' substitution counts apart undoes it. An offer
(`accentmarks.py`) and a reader's version share a substitution ("'i'→'í'"), so the
arbiter's count of how often that substitution is the print pools them. Each tuning book
scored by trees trained on the others (`train_ocr_trust.py`'s way), three ways: trained
without the offers' places; with them; with them and the substitution of a version no
reader has counted under its own key. What each does at the accent places, under 0.9
sure counted as asked. No models; each book's counts are kept in
work/probes/accent-prior.json as they come, so a stopped run goes on.

    ROBO_TRUST_DATA=work/probes/ocr-trust-accents uv run python experiments/probe_accent_prior.py
"""

import functools
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from roboscriptorium import trust
from roboscriptorium.config import Settings
from roboscriptorium.files import write_atomic
from roboscriptorium.trustdata import SPECS, rows_of, seats, trainable, usable, weighed

SETTINGS = Settings.from_env()
READINGS, SEATS = weighed(SETTINGS), seats(SETTINGS)
SEEDS = 5
MEMO = Path("work/probes/accent-prior.json")
ACUTE = "́"
WAYS = ("trained without the offers", "trained with them", "with them, counted apart")
APART = False


def acutes(text: str) -> int:
    return unicodedata.normalize("NFD", text).count(ACUTE)


def bare(text: str) -> str:
    return unicodedata.normalize("NFD", text).replace(ACUTE, "")


def unread(s, k: int) -> bool:
    return not any(k < len(has) and has[k] for has in s.support.values())


pair = functools.lru_cache(maxsize=None)(trust.pair)


def key(s, k: int) -> str:
    return pair(s.ours, s.others[k - 1]) + ("|unread" if APART and unread(s, k) else "")


def pairs_table(suspects, right, books):
    counts, seen_in = defaultdict(lambda: [0, 0]), defaultdict(set)
    for s, ok, book in zip(suspects, right, books, strict=True):
        for k in range(1, 1 + len(s.others)):
            counts[key(s, k)][0] += ok[k]
            counts[key(s, k)][1] += 1
            seen_in[key(s, k)].add(book)
    return {k: (a, n) for k, (a, n) in counts.items() if len(seen_in[k]) >= trust.MIN_BOOKS}


def prior(s, k, pairs):
    def look(name):
        a, n = pairs.get(name, (0, 0))
        return (a + 1) / (n + 2), float(np.log1p(n))

    if k == 0:
        rivals = [look(key(s, j)) for j in range(1, 1 + len(s.others))]
        p, n = max(rivals, key=lambda t: t[0]) if rivals else (0.5, 0.0)
        return [1 - p, n]
    return list(look(key(s, k)))


trust.pairs_table, trust.prior = pairs_table, prior


def group(r) -> str | None:
    """Which accent place a row is: its first version adding a stress accent to the
    build's, by whether a reader has it and whether the print does."""
    s = r["s"]
    for k, v in enumerate(s.others, 1):
        if acutes(v) > acutes(s.ours) and bare(v) == bare(s.ours):
            who = "only the scan's measure" if unread(s, k) else "a reader has it"
            return f"{who}, print has {'the accent' if r['right'][k] else 'none'}"
    return None


def offered(r) -> bool:
    return (group(r) or "").startswith("only")


def score(name: str) -> dict:
    global APART
    rows = books[name]
    names = [n for n in books if n != name and trainable(n)]
    sizes = [len(r["right"]) for r in rows]
    out = {}
    for way in WAYS:
        APART = way == WAYS[2]
        train = [(n, r) for n in names for r in books[n] if way != WAYS[0] or not offered(r)]
        suspects, right = [r["s"] for _, r in train], [r["right"] for _, r in train]
        owners = [n for n, _ in train]
        X, y = trust.training_matrix(suspects, right, owners, READINGS, SEATS)
        pairs = trust.pairs_table(suspects, right, owners)
        Xt = np.array([trust.features(r["s"], k, pairs, READINGS, SEATS) for r in rows for k in range(len(r["right"]))])
        p = trust.Trees(SEEDS).fit(X, y).predict_proba(Xt)[:, 1]
        c, at = Counter(), 0
        for r, n in zip(rows, sizes, strict=True):
            q = p[at : at + n] / max(p[at : at + n].sum(), 1e-9)
            at += n
            did = "asks" if q.max() < 0.9 else "right" if r["right"][int(q.argmax())] else "silent error"
            c[f"{group(r) or 'other places'}: {did}"] += 1
        out[way] = dict(c)
    return out


books: dict = {}

if __name__ == "__main__":
    # `usable` leaves out a book without data, which `rows_of` would build with the models.
    books.update({n: rows_of(n, SETTINGS) for n in SPECS if not usable(n, SETTINGS)})
    memo = json.loads(MEMO.read_text()) if MEMO.exists() else {}
    for name in books:
        if name not in memo:
            memo[name] = score(name)
            write_atomic(MEMO, json.dumps(memo))
            print(name, flush=True)
    total = {way: Counter() for way in WAYS}
    for m in memo.values():
        for way in WAYS:
            total[way].update(m[way])
    groups = sorted({k.split(": ")[0] for way in WAYS for k in total[way]})
    for g in groups:
        print(g)
        for way in WAYS:
            c = total[way]
            print(f"  {way:28} right {c[f'{g}: right']:6}  asks {c[f'{g}: asks']:5}  silent errors {c[f'{g}: silent error']:4}")
    for way in WAYS:
        c = total[way]
        print(f"{way:28} all places: asks {sum(v for k, v in c.items() if k.endswith('asks'))}, silent errors {sum(v for k, v in c.items() if k.endswith('silent error'))}")
