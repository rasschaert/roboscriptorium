"""Probe: does Qwen's line reading, as a vote, help learned trust choose? One book only.

Takes the book's settled OCR-check suspects (`ocr_trust_data.py`) and the Qwen readings
`bench_line_readings.py --extra` cached, adds whether Qwen reads each version as a
feature, and scores the trees by cross-validation over pages (5 folds), with and
without it: silent errors at budgets of questions per page.

    PYTHONPATH=experiments uv run python experiments/probe_qwen_vote.py goede-dochter--ia-scan
"""

import json
import sys
from pathlib import Path

import numpy as np
from ocr_trust_data import load, suspect
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import ocrcheck, trust

name = sys.argv[1]
model = "qwen3.8_27b-nvfp4"
qwen = json.loads((Path("work/probes/line-readings") / f"{name}--{model}.json").read_text())
rows = [r for r in load(name) if r["settled"]]
for r in rows:
    r["s"] = suspect(r)
rows = [r for r in rows if f"{r['s'].page}:{r['s'].line}" in qwen]
pages = sorted({r["s"].page for r in rows})
print(f"{len(rows)} settled suspects with a Qwen reading, {len(pages)} pages")


def feats(r, k, with_qwen):
    s = r["s"]
    f = trust.features(s, k)
    if with_qwen:
        reading = qwen[f"{s.page}:{s.line}"]
        versions = [s.ours, *s.others]
        f.append(float(ocrcheck.supports(s.original, reading, s.start, s.end, versions)[k]))
    return f


def matrix(rs, with_qwen):
    X, y, owner = [], [], []
    for i, r in enumerate(rs):
        for k, ok in enumerate(r["right"]):
            X.append(feats(r, k, with_qwen))
            y.append(int(ok))
            owner.append(i)
    return np.array(X), np.array(y), owner


def per_suspect(rs, probs, owner):
    out = [[] for _ in rs]
    for p, i in zip(probs, owner, strict=True):
        out[i].append(p)
    return [np.array(p) / max(sum(p), 1e-9) for p in out]


def silent_at(rs, ps, n):
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rs, ps, strict=True))
    return sum(wrong for _, wrong in order[n:])


def trees():
    return HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )


qwen_right = sum(
    ocrcheck.supports(r["s"].original, qwen[f"{r['s'].page}:{r['s'].line}"], r["s"].start,
                      r["s"].end, [r["s"].ours, *r["s"].others])[r["right"].index(True)]
    for r in rows
)
print(f"Qwen reads the right version of {qwen_right}/{len(rows)}")
for with_qwen in (False, True):
    ps = [None] * len(rows)
    for fold in range(5):
        test = [i for i, r in enumerate(rows) if pages.index(r["s"].page) % 5 == fold]
        train = [r for i, r in enumerate(rows) if pages.index(r["s"].page) % 5 != fold]
        X, y, _ = matrix(train, with_qwen)
        Xt, _, owner = matrix([rows[i] for i in test], with_qwen)
        got = per_suspect(test, trees().fit(X, y).predict_proba(Xt)[:, 1], owner)
        for i, p in zip(test, got, strict=True):
            ps[i] = p
    curve = [silent_at(rows, ps, int(b * len(pages))) for b in (0, 0.25, 0.5, 1.0, 2.0)]
    print(f"{'with' if with_qwen else 'without'} Qwen: silent at 0/.25/.5/1/2 questions per page: {curve}")
