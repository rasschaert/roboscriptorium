"""Learned trust for the OCR check (`trust.py`), scored leaving one book out, against the rule.

Each version of each settled suspect (`ocr_trust_data.py`) is a row: is this what
the scan prints? The substitution priors (`trust.pairs_table`) come from the training
books of each fold, never from the book scored. Per book: the fixed rule's silent errors (applied or kept, but
wrong) and questions, and each model's silent errors at the rule's own number of
questions and at budgets of questions per page (the least sure suspects asked,
the rest taking their most likely version). Then the same for the trees with one
more training book left out, for stability.

    PYTHONPATH=experiments uv run python experiments/train_ocr_trust.py [--save]

`--save` trains on the tuning books (never the held-out ones) and writes the model
the pipeline uses (ROBO_OCR_TRUST=1); with a copy trained without each tuning book,
which `roboscriptorium bench` scores that book with. It refuses while a tuning book's
data is missing or stale (`--partial` saves anyway).

Only books whose data exists and was built with every current reading are used:
loading a missing one would start a cold build of it. Validation books are scored but
never trained on, here as in `--save`. Per book it also prints how often each judge
picks the labelled version: a book where winnow, which reads only the sentence, beats
clef, which reads the crop, has a reference more standard than its print.
"""

import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
from ocr_trust_data import OUT, SPECS, load, suspect
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


# The judges a build asks: votes of any other model in the data (an alarm tried and left
# off) would train the arbiter on a vote it never gets.
_SETTINGS = Settings.from_env()
JUDGES = {_SETTINGS.judge_model, _SETTINGS.check_model, _SETTINGS.alarm_model, "word list"} - {""}


def rows_of(name: str) -> list[dict]:
    rows = [r for r in load(name) if r["settled"]]
    for r in rows:
        s = suspect(r)
        r["s"] = replace(
            s,
            votes={m: v for m, v in s.votes.items() if m in JUDGES},
            confidence={m: c for m, c in s.confidence.items() if m in JUDGES},
        )
        r["book"] = name
    return rows


def matrix(rows: list[dict], pairs: trust.Pairs) -> tuple[np.ndarray, list[int]]:
    """Feature rows of the suspects to score, with the substitution priors `pairs`."""
    X, owner = [], []
    for i, r in enumerate(rows):
        for k in range(len(r["right"])):
            X.append(trust.features(r["s"], k, pairs))
            owner.append(i)
    return np.array(X), owner


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
    """`rows` scored by `make()` trained on the named books, with the substitution
    priors from those books (each training book's suspects from the other books')."""
    train = [r for n in train_names for r in books[n]]
    suspects, right = [r["s"] for r in train], [r["right"] for r in train]
    names = [n for n in train_names for _ in books[n]]
    pairs = trust.pairs_table(suspects, right, names)
    X, y = trust.training_matrix(suspects, right, names)
    Xt, owner = matrix(rows, pairs)
    return per_suspect(rows, make().fit(X, y).predict_proba(Xt)[:, 1], owner)


# Every reading the OCR check makes with these settings; data built before one of them
# lacks its support.
READINGS = {"glm", "tess"} | ({"qwen"} if _SETTINGS.read_model else set())


def usable(name: str) -> str:
    """Why a book's data can't be used, or "" when it can."""
    if not (OUT / f"{name}.json").exists():
        return "no data yet"
    rows = load(name)
    if any(not READINGS <= set(r["suspect"]["support"]) for r in rows):
        return "built before the current readings"
    # The features take the judges by position, so data without one of these settings'
    # judges would train its slot on nothing.
    judges = JUDGES - {"word list"}
    if any(not judges <= set(r["suspect"]["votes"]) for r in rows):
        return "built without one of the current judges"
    return ""


def trainable(name: str) -> bool:
    return name.split("--")[0] not in HELD_OUT


skipped = {name: why for name in SPECS if (why := usable(name))}
books = {name: rows_of(name) for name in SPECS if name not in skipped}
for name, why in skipped.items():
    print(f"skipped {name}: {why}")

print(f"\n{'book':40} {'settled':>7} {'clef':>5} {'winnow':>6}")
for name, rows in books.items():
    def right(judge: str) -> int:
        return sum(
            r["s"].votes.get(judge) in {v for v, ok in zip([r["s"].ours, *r["s"].others], r["right"], strict=True) if ok}
            for r in rows
        )
    clef, winnow = right(_SETTINGS.judge_model), right(_SETTINGS.check_model)
    flag = "  << winnow ahead: is the reference more standard than the print?" if winnow >= clef else ""
    print(f"{name[:40]:40} {len(rows):7} {clef / max(1, len(rows)):5.0%} {winnow / max(1, len(rows)):6.0%}{flag}")
print()

if "--save" in sys.argv:
    missing = [n for n in skipped if trainable(n)]
    if missing and "--partial" not in sys.argv:
        sys.exit(f"not saving: tuning data missing or stale for {', '.join(missing)} (--partial to save anyway)")
    # The model the pipeline uses, and one without each tuning book, which `bench`
    # scores that book with.
    tuning = [n for n in books if trainable(n) and n != "stella"]
    path = Path(Settings.from_env().ocr_trust_model)
    # All trained before any is written, so an interrupted run leaves no mix of old and new.
    models = []
    for without in [None, *tuning]:
        every = [
            r
            for name, rows in books.items()
            if name != without and trainable(name)
            for r in rows
        ]
        model = trust.train(
            [r["s"] for r in every], [r["right"] for r in every], [r["book"] for r in every]
        )
        models.append((trust.without(path, without) if without else path, model, len(every), without))
    for out, model, n, without in models:
        trust.save(model, out)
        print(f"trained on {n} suspects, without {without}: {out}")
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
        ps = scored(make, [n for n in books if n != name and trainable(n)], rows)
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
        silent_at(rows, scored(MODELS["trees"], [n for n in books if n not in (name, drop) and trainable(n)], rows), asked)
        for drop in books
        if drop != name and trainable(drop)
    ]
    print(f"  {name[:34]:34} {min(spread)}–{max(spread)}")
