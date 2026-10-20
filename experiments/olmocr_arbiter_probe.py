"""Does another reader's line readings, as one more witness on the OCR check's suspects,
make the arbiter surer and righter? Leave-one-book-out, as `train_ocr_trust.py` scores it:
the suspects the trees would take silently and get wrong, at the fixed rule's number of
questions, with and without the reader's support as a feature.

    PYTHONPATH=experiments uv run python experiments/olmocr_arbiter_probe.py <label>

Needs `olmocr_suspect_crops.py` and `mlx_read_crops.py <model> <label>` run first. The
reader makes no suspects of its own here: it only says which version it reads.
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.config import Settings
from roboscriptorium.ocrcheck import supports
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable, weighed

ROOT = Path("work/probes/olmocr-suspects")
label = sys.argv[1]
settings = Settings.from_env()
BASE = weighed(settings)
WITH = (*BASE, label)


def make():
    return HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )


def with_support(name: str, rows: list[dict]) -> list[dict]:
    path = ROOT / name / f"{label}.json"
    read = json.loads(path.read_text()) if path.exists() else {}
    out = []
    for r in rows:
        s = r["s"]
        line = read.get(f"{s.page}_{s.line}", "")
        curly = sum(s.original.count(c) for c in "‘’“”") > sum(s.original.count(c) for c in "'\"")
        got = supports(s.original, line, s.start, s.end, [s.ours, *s.others], curly)
        out.append({**r, "s": replace(s, support={**s.support, label: got})})
    return out


def scored(train_names, rows, books, readings):
    train = [r for n in train_names for r in books[n]]
    suspects, right = [r["s"] for r in train], [r["right"] for r in train]
    names = [n for n in train_names for _ in books[n]]
    pairs = trust.pairs_table(suspects, right, names)
    X, y = trust.training_matrix(suspects, right, names, readings)
    Xt, owner = [], []
    for i, r in enumerate(rows):
        for k in range(len(r["right"])):
            Xt.append(trust.features(r["s"], k, pairs, readings))
            owner.append(i)
    p = make().fit(X, y).predict_proba(np.array(Xt))[:, 1]
    out = [[] for _ in rows]
    for q, i in zip(p, owner, strict=True):
        out[i].append(q)
    return [np.array(q) / max(sum(q), 1e-9) for q in out]


def silent_at(rows, ps, n: int) -> int:
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
    return sum(wrong for _, wrong in order[n:])


def asked(rows) -> int:
    return sum(r["s"].choice == "review" for r in rows)


if __name__ == "__main__":
    names = [n for n in SPECS if not usable(n, settings)]
    books = {n: with_support(n, rows_of(n, settings)) for n in names}
    have = [n for n in books if (ROOT / n / f"{label}.json").exists()]
    print(f"{len(have)} of {len(books)} books have {label} readings")
    total = {"without": 0, "with": 0}
    for name in have:
        train = [n for n in have if n != name and trainable(n)]
        rows = books[name]
        n_ask = asked(rows)
        a = silent_at(rows, scored(train, rows, books, BASE), n_ask)
        b = silent_at(rows, scored(train, rows, books, WITH), n_ask)
        total["without"] += a
        total["with"] += b
        print(f"{name[:40]:40} suspects {len(rows):5}  silent errors {a:3} -> {b:3}")
    print("totals", total)
