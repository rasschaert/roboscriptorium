"""Learned trust for the OCR check (`trust.py`), scored leaving one book out, against the rule.

Each version of each settled suspect (`ocr_trust_data.py`) is a row: is this what
the scan prints? Per book: the fixed rule's silent errors (applied or kept, but
wrong) and questions, and each model's silent errors at the rule's own number of
questions and at budgets of questions per page (the least sure suspects asked,
the rest taking their most likely version). Then the same for the trees with one
more training book left out, for stability.

    PYTHONPATH=experiments uv run python experiments/train_ocr_trust.py [--save]

`--save` trains on the tuning books (never the held-out ones) and writes the model
the pipeline uses (ROBO_OCR_TRUST=1); with a copy trained without each tuning book,
which `roboscriptorium bench` scores that book with.
"""

import sys
from collections import Counter
from pathlib import Path

import numpy as np
from ocr_trust_data import SPECS, load, suspect
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from roboscriptorium import trust
from roboscriptorium.book import Book
from roboscriptorium.cli import _range
from roboscriptorium.config import Settings

HELD_OUT = {"lady-into-fox", "grand-hotel-europa", "de-tuin-van-de-avondnevel", "de-eerlijke-vinder", "youre-never-weird-on-the-internet"}
BUDGETS = (0.0, 0.25, 0.5, 1.0)
MODELS = {
    "logistic": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "trees": lambda: HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    ),
}


def rows_of(name: str) -> list[dict]:
    rows = [r for r in load(name) if r["settled"]]
    for r in rows:
        r["s"] = suspect(r)
    return rows


def matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, list[int]]:
    X, y, owner = [], [], []
    for i, r in enumerate(rows):
        for k, ok in enumerate(r["right"]):
            X.append(trust.features(r["s"], k))
            y.append(int(ok))
            owner.append(i)
    return np.array(X), np.array(y), owner


def per_suspect(rows, probs, owner) -> list[np.ndarray]:
    out = [[] for _ in rows]
    for p, i in zip(probs, owner, strict=True):
        out[i].append(p)
    return [np.array(p) / max(sum(p), 1e-9) for p in out]


def silent_at(rows, ps, n: int) -> int:
    """Silent errors when the n least sure suspects are asked and the rest take their best."""
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
    return sum(wrong for _, wrong in order[n:])


def rule(rows) -> tuple[int, int]:
    silent = asked = 0
    for r in rows:
        s = r["s"]
        if s.choice == "review":
            asked += 1
        else:
            k = 0 if s.choice == "ours" else 1 + s.others.index(s.chosen)
            silent += not r["right"][k]
    return silent, asked


def pages_of(name: str) -> int:
    spec = SPECS[name]
    ranged = spec and spec != "answers"
    first, last = _range(spec.split(":")[0]) if ranged else Book.load(Path("work") / name).body_pages
    return last - first + 1


def scored(make, train_names, rows):
    X, y, _ = matrix([r for n in train_names for r in books[n]])
    Xt, _, owner = matrix(rows)
    return per_suspect(rows, make().fit(X, y).predict_proba(Xt)[:, 1], owner)


books = {name: rows_of(name) for name in SPECS}
if "--save" in sys.argv:
    # The model the pipeline uses, and one without each tuning book, which `bench`
    # scores that book with.
    tuning = [n for n in books if n.split("--")[0] not in HELD_OUT and n != "stella"]
    path = Path(Settings.from_env().ocr_trust_model)
    for without in [None, *tuning]:
        every = [
            r
            for name, rows in books.items()
            if name != without and name.split("--")[0] not in HELD_OUT
            for r in rows
        ]
        model = trust.train([r["s"] for r in every], [r["right"] for r in every])
        out = trust.without(path, without) if without else path
        trust.save(model, out)
        print(f"trained on {len(every)} suspects, without {without}: {out}")
    sys.exit()

totals: Counter = Counter()
print(f"{'book':30} {'pages':>5} {'rule silent/asked':>18}  "
      + "  ".join(f"{m}: silent at rule's questions (budget 0/.25/.5/1)" for m in MODELS))  # fmt: skip
for name, rows in books.items():
    silent, asked = rule(rows)
    totals["rule silent"] += silent
    totals["rule asked"] += asked
    pages = pages_of(name)
    cells = []
    for label, make in MODELS.items():
        ps = scored(make, [n for n in books if n != name], rows)
        same = silent_at(rows, ps, asked)
        curve = [silent_at(rows, ps, int(b * pages)) for b in BUDGETS]
        totals[label] += same
        cells.append(f"{same:3} ({'/'.join(map(str, curve))})")
    tag = " held out" if name.split("--")[0] in HELD_OUT else ""
    print(f"{name[:30]:30} {pages:5} {silent:8}/{asked:<9}  " + "  ".join(cells) + tag)
print("\ntotals:", dict(totals))

print("\nstability (trees, silent at the rule's questions, one more training book left out):")
for name, rows in books.items():
    asked = rule(rows)[1]
    spread = [
        silent_at(rows, scored(MODELS["trees"], [n for n in books if n not in (name, drop)], rows), asked)
        for drop in books
        if drop != name
    ]
    print(f"  {name[:34]:34} {min(spread)}–{max(spread)}")
