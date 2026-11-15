"""The accent-zone fit (`probe_accent_fit.py`) as arbiter columns: for a candidate that
differs from another version by one letter's mark, whether it is the marked one and the
scan's cosine with the accent's shape, its ink against the accent's and the stray ink
around it; empty elsewhere. Each book scored by an arbiter trained on the others, with and
without the columns (`probe_book_vocab.py`'s harness): silent errors at the rule's
questions, at none and at half. `--control` puts random numbers in the measures' place.

    PYTHONPATH=experiments uv run python experiments/probe_accent_columns.py [--control]
"""

import json
import math
import sys
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
import probe_book_vocab as harness
from probe_accent_mark import marked_letter, strip

from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable

CONTROL = "--control" in sys.argv
KEYS = ("cosine", "mass", "stray")


def accent_features(s, k: int, index: dict) -> list[float]:
    versions = [s.ours, *s.others]
    for j in range(len(versions)):
        at = marked_letter(versions[k], versions[j]) if j != k else None
        if at is None:
            continue
        a, b = versions[k], versions[j]
        marked, plain = (a, b) if strip(a[at]) != a[at] else (b, a)
        f = index.get((s.page, marked, plain))
        if f is None:
            continue
        if CONTROL:
            rng = np.random.default_rng(zlib.crc32(f"{s.page}|{marked}|{plain}".encode()))
            return [float(marked is a), *rng.uniform(0, 1, 3)]
        return [float(marked is a), *(f[x] for x in KEYS)]
    return [math.nan] * 4


harness.vocab_features = accent_features
fit = [json.loads(line) for line in Path("work/probes/accent-fit.jsonl").read_text().splitlines()]
books = {n: rows_of(n, harness.SETTINGS) for n in SPECS if not usable(n, harness.SETTINGS)}
index = {n: {(f["page"], f["marked"], f["plain"]): f for f in fit if f["book"] == n} for n in books}
totals, changed = Counter(), []
for name, rows in books.items():
    silent, asked = harness.rule(rows)
    train_rows = [r for n in books if n != name and trainable(n) for r in books[n]]
    pa, pb = harness.scored(train_rows, rows, index, False), harness.scored(train_rows, rows, index, True)
    for label, n in (("rule's", asked), ("none", 0), ("half", asked // 2)):
        totals[f"today@{label}"] += harness.silent_at(rows, pa, n)
        totals[f"+accent@{label}"] += harness.silent_at(rows, pb, n)
    for r, x, y in zip(rows, pa, pb, strict=True):
        if int(x.argmax()) != int(y.argmax()):
            v = [r["s"].ours, *r["s"].others]
            changed.append((name, v[int(x.argmax())], v[int(y.argmax())], r["right"][int(y.argmax())]))
    print(name, flush=True)
print("totals:", dict(totals))
fixed = [c for c in changed if c[3]]
print(f"best version changed on {len(changed)} places: right now on {len(fixed)}, wrong now on {len(changed) - len(fixed)}")
for c in changed[:50]:
    print(f"  {'FIXED' if c[3] else 'BROKE'} {c[0][:16]:16} {c[1]!r} → {c[2]!r}")
