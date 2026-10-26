"""Does the ink over a suspect's letter help the arbiter? No models.

`probe_accent_mark.py` measures the mark above the one letter an accent version changes.
Here those measures (per book z-scores too) join `trust.features` for every version
that differs from the layer's by such a mark, and the trees are scored leaving one book
out as `train_ocr_trust.py` scores them: silent errors at the fixed rule's number of
questions, with and without the new features.

    uv run python experiments/probe_accent_mark_arbiter.py
"""

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from probe_accent_mark import marked_letter, measure, strip  # noqa: E402

from roboscriptorium import trust  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable, weighed  # noqa: E402

FEATS = ("marks_here", "area", "elong", "abs_tilt", "tilt", "fill", "dark", "gap", "marks_elsewhere")
SETTINGS = Settings.from_env()
READINGS = weighed(SETTINGS)
books = {n: rows_of(n, SETTINGS) for n in SPECS if not usable(n, SETTINGS)}

# Per suspect (by identity) and letter: the raw measures, then per book z-scores.
measured: dict[tuple, dict] = {}
for name, rows in books.items():
    source = Path("work") / name / "source.pdf"
    if not source.exists():
        continue
    doc = pymupdf.open(source)
    mine = []
    for r in rows:
        s = r["s"]
        for v in s.others:
            i = marked_letter(s.ours, v)
            if i is None or trust.kind(s.ours, v) != "accent":
                continue
            f = measure(doc[s.page - 1], {"box": s.box, "ours": s.ours}, i)
            if f:
                key = (id(s), i)
                measured[key] = f
                mine.append(f)
    for k in FEATS:
        x = np.array([f[k] for f in mine]) if mine else np.zeros(1)
        m, sd = x.mean(), x.std() or 1.0
        for f in mine:
            f["z_" + k] = (f[k] - m) / sd
    print(name, len(mine), file=sys.stderr)

WIDTH = 2 + 2 * len(FEATS)
plain_features = trust.features


def with_marks(s, k, pairs=None, readings=trust.READINGS):
    f = plain_features(s, k, pairs, readings)
    versions = [s.ours, *s.others]
    extra = [0.0] * WIDTH
    for v in s.others:
        i = marked_letter(s.ours, v)
        m = measured.get((id(s), i)) if i is not None else None
        if m is None:
            continue
        # Whether version k carries a mark on that letter.
        has = versions[k][i] != strip(versions[k][i]) if len(versions[k]) > i else False
        extra = [1.0, 1.0 if has else -1.0, *(m[x] for x in FEATS), *(m["z_" + x] for x in FEATS)]
        break
    return f + extra


def scored(train_names, rows):
    train = [r for n in train_names for r in books[n]]
    suspects, right = [r["s"] for r in train], [r["right"] for r in train]
    names = [n for n in train_names for _ in books[n]]
    pairs = trust.pairs_table(suspects, right, names)
    X, y = trust.training_matrix(suspects, right, names, READINGS)
    Xt, owner = [], []
    for i, r in enumerate(rows):
        for k in range(len(r["right"])):
            Xt.append(trust.features(r["s"], k, pairs, READINGS))
            owner.append(i)
    from sklearn.ensemble import HistGradientBoostingClassifier

    model = HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )
    p = model.fit(X, y).predict_proba(np.array(Xt))[:, 1]
    out = defaultdict(list)
    for q, i in zip(p, owner, strict=True):
        out[i].append(q)
    return [np.array(out[i]) / max(sum(out[i]), 1e-9) for i in range(len(rows))]


def silent_at(rows, ps, n):
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
    return [w for _, w in order[n:]]


def asked_by_rule(rows):
    return sum(r["s"].choice == "review" for r in rows)


totals = defaultdict(int)
for name, rows in books.items():
    n = asked_by_rule(rows)
    others = [b for b in books if b != name and trainable(b)]
    trust.features = plain_features
    a = sum(silent_at(rows, scored(others, rows), n))
    trust.features = with_marks
    b = sum(silent_at(rows, scored(others, rows), n))
    trust.features = plain_features
    totals["without"] += a
    totals["with"] += b
    print(f"{name[:36]:36} asked {n:4}  silent without {a:3}  with marks {b:3}")
print(dict(totals))
