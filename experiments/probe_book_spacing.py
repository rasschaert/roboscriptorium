"""The book's own spacing of a repeated form as arbiter columns (the user's review of
Andere levens, 2026-11-14: "M.H." or "M. H.", which its text layer prints 5 and 11 times).
For a place whose versions differ only in spaces, how often the book's layer prints each
form elsewhere: the version's count, the layer's, their difference (log); blank for other
places. Two arbiters on the held-out folds of `probe_book_vocab.py`; `--control` puts
random columns in their place.

    PYTHONPATH=experiments uv run python experiments/probe_book_spacing.py [--control]
"""

import argparse
import json
import math
import re
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
from probe_book_vocab import READINGS, SEATS, SETTINGS, rule, silent_at
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable


def layer_text(book: str) -> str:
    pages = json.loads((Path("work") / book / "stages" / "text-layer.json").read_text())["pages"]
    return " ".join(line["text"] for page in pages for line in page["lines"])


def columns(s, k: int, text: str | None, control: bool) -> list[float]:
    versions = [s.ours, *s.others]
    if len({v.replace(" ", "") for v in versions}) != 1:
        return [math.nan] * 3
    if control:
        rng = np.random.default_rng(zlib.crc32(f"{versions[0]}|{versions[k]}|{k}".encode()))
        return list(rng.uniform(0, 4, 3))
    if text is None:
        return [math.nan] * 3
    count = lambda v: math.log1p(len(re.findall(re.escape(v.strip()), text)))  # noqa: E731
    mine, layer = count(versions[k]), count(versions[0])
    return [mine, layer, mine - layer]


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
    texts = {n: layer_text(n) for n in names}
    books = {n: rows_of(n, SETTINGS) for n in names}
    spaced = sum(
        len({v.replace(" ", "") for v in [r["s"].ours, *r["s"].others]}) == 1
        for rows in books.values() for r in rows
    )  # fmt: skip
    print(f"places differing only in spaces: {spaced}", flush=True)
    tot, changed = Counter(), []
    for name, rows in books.items():
        silent, asked = rule(rows)
        train_rows = [r for n in books if n != name and trainable(n) for r in books[n]]
        pa = scored(train_rows, rows, False, texts, a.control)
        pb = scored(train_rows, rows, True, texts, a.control)
        for lab, n in (("rule's", asked), ("none", 0), ("half", asked // 2)):
            tot[f"today@{lab}"] += silent_at(rows, pa, n)
            tot[f"+spacing@{lab}"] += silent_at(rows, pb, n)
        target = silent_at(rows, pa, asked)
        for tag, p in (("today", pa), ("+spacing", pb)):
            tot[f"{tag} questions"] += next(
                n for n in range(len(rows) + 1) if silent_at(rows, p, n) <= target
            )
        for r, x, y_ in zip(rows, pa, pb, strict=True):
            if int(x.argmax()) != int(y_.argmax()):
                v = [r["s"].ours, *r["s"].others]
                changed.append((name, v, v[int(x.argmax())], v[int(y_.argmax())], r["right"][int(y_.argmax())]))
    print("totals:", dict(tot))
    fixed = [c for c in changed if c[4]]
    print(f"best version changed on {len(changed)} suspects: right now on {len(fixed)}, wrong now on {len(changed) - len(fixed)}")
    for c in changed[:40]:
        print(f"  {'FIXED' if c[4] else 'BROKE'} {c[0][:16]:16} {c[1]}  {c[2]!r} → {c[3]!r}")


if __name__ == "__main__":
    main()
