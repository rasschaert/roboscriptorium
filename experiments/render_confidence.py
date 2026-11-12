"""Render and compare: how sure is the judge of a pick? A logistic model of whether the
pick is the print, from how well the best version lies over the ink (its fit) and its
margin over the next, fitted on the labelled places of `probe_face_by_places.py` (each
book in its five best faces, so a typeface that suits a book poorly is among them).
Prints each signal's AUC with each book left out in turn, the calibration, and the
coefficients for `rendercheck.SURENESS`. No models.

    uv run python experiments/render_confidence.py
"""

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

PLACES = Path("work/probes/face-by-places")


def signals(fit, margin):
    return np.c_[fit, np.log(np.asarray(margin) + 1e-3)]


rows, right, book = [], [], []
for at, path in enumerate(sorted(PLACES.glob("*.json"))):
    data = json.loads(path.read_text())
    for face in data["faces"]:
        for pick, row in zip(face["picks"], data["rows"]):
            if pick is not None:
                rows.append((pick["fit"], pick["margin"]))
                right.append(pick["pick"] == row["right"])
                book.append(at)
rows, right, book = np.array(rows), np.array(right), np.array(book)
X = signals(rows[:, 0], rows[:, 1])
print(f"{len(right)} picks over {len(set(book))} books, {right.mean():.1%} the print")
for name, cols in (("margin", [1]), ("fit", [0]), ("both", [0, 1])):
    sure = np.zeros(len(right))
    for b in np.unique(book):
        model = LogisticRegression(max_iter=1000).fit(X[book != b][:, cols], right[book != b])
        sure[book == b] = model.predict_proba(X[book == b][:, cols])[:, 1]
    print(f"{name:7} AUC {roc_auc_score(right, sure):.3f}")
for low, high in ((0, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.01)):
    at = (sure >= low) & (sure < high)
    print(f"  sure {low:.2f}–{high:.2f}: {at.sum():6} picks, {right[at].mean():.1%} the print")
model = LogisticRegression(max_iter=1000).fit(X, right)
print("SURENESS = (intercept, fit, log margin) =",
      tuple(round(float(v), 3) for v in (model.intercept_[0], *model.coef_[0])))
