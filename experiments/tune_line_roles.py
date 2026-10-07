"""Regularising the line-role trees: settings scored leaving one book out, with stability.

Reads the feature sets `train_line_roles.py` cached in work/probes/line-roles/.
For each setting: role errors over all books leaving one book out, and the
spread of each book's errors when one more training book is left out too.

    uv run python experiments/tune_line_roles.py [--focus]

`--focus` runs only the best settings, with and without the layout model's features.
"""

import itertools
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

OUT = Path("work/probes/line-roles")
HELD_OUT = {"lady-into-fox", "villa-toscane", "grand-hotel-europa", "de-tuin-van-de-avondnevel"}
WITHOUT_MODEL = {"asked", "p_body"}

books = {p.stem: json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))}
names = [k for k in next(iter(books.values()))[0]["f"] if k != "pipeline"]
plain = [k for k in names if k not in WITHOUT_MODEL and not k.startswith("model_")]


def matrix(rows, cols):
    return np.array([[r["f"][k] for k in cols] for r in rows], dtype=float)


def weights(labels, how):
    counts = Counter(labels)
    if how == "none":
        return None
    power = {"balanced": 1.0, "sqrt": 0.5}[how]
    return np.array([(len(labels) / counts[y]) ** power for y in labels])


def errors(name, train_names, cols, setting):
    train = [r for n in train_names for r in books[n]]
    y = [r["label"] for r in train]
    how, leaf, depth, l2 = setting
    clf = HistGradientBoostingClassifier(
        min_samples_leaf=leaf, max_depth=depth, l2_regularization=l2, random_state=0
    )
    clf.fit(matrix(train, cols), y, sample_weight=weights(y, how))
    pred = clf.predict(matrix(books[name], cols))
    return sum(r["label"] != p for r, p in zip(books[name], pred, strict=True))


baseline = sum(
    sum(r["label"] != r["f"]["pipeline"] for r in rows) for rows in books.values()
)
print(f"roles.py: {baseline} errors over {len(books)} books")
grid = list(itertools.product(["balanced", "sqrt", "none"], [20, 80], [None, 4], [0.0, 1.0]))
feature_sets = [("+model", names), ("plain", plain)]
if "--focus" in sys.argv:
    grid = [("balanced", 20, 4, 1.0), ("sqrt", 20, 4, 1.0)]
    no_layout = [k for k in names if not k.startswith(("layout_", "page_figure"))]
    feature_sets = [("+model", names), ("+model, no layout", no_layout)]
columns = dict(feature_sets)
results = []
for cols_label, cols in feature_sets:
    for setting in grid:
        per_book = {n: errors(n, [m for m in books if m != n], cols, setting) for n in books}
        results.append((sum(per_book.values()), cols_label, setting, per_book))
        print(f"{sum(per_book.values()):5} {cols_label:18} {setting}", flush=True)

results.sort(key=lambda r: r[0])
print("\nbest settings, per book (roles.py first):")
for total, cols_label, setting, per_book in results[:4]:
    print(f"\n{total} {cols_label} {setting}")
    cols = columns[cols_label]
    for n, e in per_book.items():
        pipe = sum(r["label"] != r["f"]["pipeline"] for r in books[n])
        # Stability: also leave out each other book in turn.
        spread = [
            errors(n, [m for m in books if m not in (n, drop)], cols, setting)
            for drop in books
            if drop != n
        ]
        tag = " (held out)" if n.split("--")[0] in HELD_OUT else ""
        print(
            f"  {n[:34]:34} roles.py {pipe:4}  trees {e:4}  dropping a book: "
            f"{min(spread)}–{max(spread)} (median {statistics.median(spread)}){tag}"
        )
