"""Learned trust for the OCR check, scored leaving one book out, against SURE/SURE_ALONE.

Each version of each settled suspect (`ocr_trust_data.py`) is a row: is this what
the scan prints? A model gives each version a probability; per suspect they are
normalised. A version is applied (or the layer kept) without asking when its
probability clears a threshold chosen on the *training* books for PRECISION;
everything else is a question, most uncertain first.

Per book: silent errors (applied or kept, but wrong) and questions, for the fixed
rule and for each model, and silent errors when only a budget of questions per
page may be asked (the rest take the most likely version).

    uv run python experiments/train_ocr_trust.py
"""

import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
from ocr_trust_data import SPECS, load
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from roboscriptorium.book import Book
from roboscriptorium.cli import _range

HELD_OUT = {"lady-into-fox", "grand-hotel-europa", "de-tuin-van-de-avondnevel"}
PRECISION = 0.99
BUDGETS = (0.0, 0.25, 0.5, 1.0)
CLEF, WINNOW = "clef:27b", "winnow:e4b"
QUOTES = "'\"‘’“”"


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def kind(ours: str, v: str) -> dict[str, float]:
    strip = str.maketrans("", "", QUOTES)
    letters = lambda t: "".join(c for c in t if c.isalnum())  # noqa: E731
    return {
        "same": float(v == ours),
        "word_break": float(v.replace(" ", "") == ours.replace(" ", "") and v != ours),
        "quotes_only": float(v.translate(strip) == ours.translate(strip) and v != ours),
        "punct_only": float(letters(v) == letters(ours) and v != ours),
        "accent_only": float(_plain(v) == _plain(ours) and v != ours),
        "case_only": float(v.lower() == ours.lower() and v != ours),
        "longer": float(len(v) - len(ours)),
    }


def features(r: dict, k: int) -> dict[str, float]:
    v, ours = r["versions"][k], r["versions"][0]
    votes, conf = r["votes"], r["confidence"]
    known = r["known"][k]
    others_known = [x for i, x in enumerate(r["known"]) if i != k]
    f = {
        "is_ours": float(k == 0),
        "versions": float(len(r["versions"])),
        "typographic": float(r["typographic"]),
        "glm": float(r["glm"][k]),
        "tess": float(r["tess"][k]),
        "known": {True: 1.0, False: 0.0, None: 0.5}[known],
        "only_known": float(known is True and all(x is False for x in others_known)),
        "dutch": float(any(c in "ëéïĳ" for c in r["original"]) or " de " in r["original"]),
        **kind(ours, v),
    }
    for model, name in ((CLEF, "clef"), (WINNOW, "winnow")):
        picked = votes.get(model) == v
        c = conf.get(model, 0.0)
        f[f"{name}_pick"] = float(picked)
        f[f"{name}_conf"] = c if picked else -c
        f[f"{name}_none"] = float(votes.get(model) == "")
    f["both"] = f["clef_pick"] * f["winnow_pick"]
    return f


def rows_of(name: str) -> list[dict]:
    return [r for r in load(name) if r["settled"]]


def matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, list[int]]:
    X, y, owner = [], [], []
    for i, r in enumerate(rows):
        for k in range(len(r["versions"])):
            X.append(list(features(r, k).values()))
            y.append(int(r["right"][k]))
            owner.append(i)
    return np.array(X), np.array(y), owner


def per_suspect(rows, probs, owner) -> list[np.ndarray]:
    out = [[] for _ in rows]
    for p, i in zip(probs, owner, strict=True):
        out[i].append(p)
    return [np.array(p) / max(sum(p), 1e-9) for p in out]


def threshold(rows, ps) -> float:
    """The lowest probability at which acting on the best version is right ≥ PRECISION."""
    pairs = sorted(((p.max(), r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True)),
                   reverse=True)  # fmt: skip
    best, right = 1.01, 0
    for n, (p, ok) in enumerate(pairs, 1):
        right += ok
        if right / n >= PRECISION:
            best = p
    return best


def at_questions(rows, ps, n: int) -> int:
    """Silent errors when the n most uncertain suspects are asked and the rest take their best."""
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
    return sum(wrong for _, wrong in order[n:])


def outcome(rows, ps, t: float, pages: int) -> dict:
    silent = asked = 0
    order = []
    for r, p in zip(rows, ps, strict=True):
        b = int(p.argmax())
        if p.max() >= t:
            silent += not r["right"][b]
        else:
            asked += 1
            order.append((p.max(), not r["right"][b]))
    order.sort()
    curve = {}
    for budget in BUDGETS:
        n = int(budget * pages)
        curve[budget] = silent + sum(wrong for _, wrong in order[n:])
    return {"silent": silent, "asked": asked, "curve": curve}


def rule(rows) -> dict:
    silent = asked = 0
    for r in rows:
        if r["choice"] == "review":
            asked += 1
        elif r["choice"] == "ours":
            silent += not r["right"][0]
        else:
            silent += not r["right"][r["versions"].index(r["chosen"])]
    return {"silent": silent, "asked": asked}


def pages_of(name: str) -> int:
    spec = SPECS[name]
    first, last = _range(spec.split(":")[0]) if spec else Book.load(Path("work") / name).body_pages
    return last - first + 1


MODELS = {
    "logistic": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)),
    "trees": lambda: HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    ),
}

books = {name: rows_of(name) for name in SPECS}
totals: Counter = Counter()
print(f"{'book':30} {'pages':>5}  {'rule: silent/asked':>18}  "
      + "  ".join(f"{m}: silent/asked (budget 0/.25/.5/1 per page)" for m in MODELS))  # fmt: skip
def out_of_fold(make, names: list[str]) -> tuple[list[dict], list[np.ndarray]]:
    """Each training book's suspects scored by a model trained without that book."""
    rows, ps = [], []
    for name in names:
        rest = [r for other in names if other != name for r in books[other]]
        X, y, _ = matrix(rest)
        Xb, _, owner = matrix(books[name])
        rows += books[name]
        ps += per_suspect(books[name], make().fit(X, y).predict_proba(Xb)[:, 1], owner)
    return rows, ps


for name, rows in books.items():
    train = [r for other, rs in books.items() if other != name for r in rs]
    X, y, owner = matrix(train)
    Xt, _, owner_t = matrix(rows)
    pages = pages_of(name)
    fixed = rule(rows)
    totals["rule silent"] += fixed["silent"]
    totals["rule asked"] += fixed["asked"]
    cells = []
    for label, make in MODELS.items():
        model = make().fit(X, y)
        t = threshold(*out_of_fold(make, [n for n in books if n != name]))
        ps = per_suspect(rows, model.predict_proba(Xt)[:, 1], owner_t)
        o = outcome(rows, ps, t, pages)
        totals[f"{label} silent"] += o["silent"]
        totals[f"{label} asked"] += o["asked"]
        for b, n in o["curve"].items():
            totals[f"{label} at {b}"] += n
        same = at_questions(rows, ps, fixed["asked"])
        totals[f"{label} at rule's questions"] += same
        curve = "/".join(str(o["curve"][b]) for b in BUDGETS)
        cells.append(f"{same:3} at rule's questions (curve {curve})")
    tag = " held out" if name.split("--")[0] in HELD_OUT else ""
    print(f"{name[:30]:30} {pages:5}  {fixed['silent']:8}/{fixed['asked']:<9}  "
          + "  ".join(cells) + tag)  # fmt: skip
print("\ntotals:", dict(totals))


# Stability: each book scored again with one more training book left out.
print("\nstability (trees, silent at the rule's questions, one more training book left out):")
make = MODELS["trees"]
for name, rows in books.items():
    Xt, _, owner_t = matrix(rows)
    asked = rule(rows)["asked"]
    spread = []
    for drop in books:
        if drop in (name,):
            continue
        train = [r for other, rs in books.items() if other not in (name, drop) for r in rs]
        X, y, _ = matrix(train)
        ps = per_suspect(rows, make().fit(X, y).predict_proba(Xt)[:, 1], owner_t)
        spread.append(at_questions(rows, ps, asked))
    print(f"  {name[:34]:34} {min(spread)}–{max(spread)}")
