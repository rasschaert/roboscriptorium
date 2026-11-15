"""Reworked dropped idea 1, without a vision model: a small model trained on the lines the
old and the grown line-role trees disagree on, from the line's own features and both sets'
probabilities, says which set to follow there. Each tuning book scored by a referee
trained on the other books' disagreements. No models.

    uv run python experiments/sorter_referee.py <old models dir> <new models dir>
"""

import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import bench, sorter
from roboscriptorium.sorterdata import lines
from sorter_disagree import calls

old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])
books = {}
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    try:
        rows = lines(spec)
        mo = sorter.load(sorter.without(old_dir / "line-roles.pkl", name))
        mn = sorter.load(sorter.without(new_dir / "line-roles.pkl", name))
    except Exception:
        continue
    old, new = calls(mo, rows), calls(mn, rows)
    po = mo.model.predict_proba(sorter._matrix([r["f"] for r in rows], mo.features))
    pn = mn.model.predict_proba(sorter._matrix([r["f"] for r in rows], mn.features))
    keys = sorted(rows[0]["f"])
    apart = []
    for i, r in enumerate(rows):
        if old[i] == new[i]:
            continue
        x = [float(r["f"].get(k, np.nan) if r["f"].get(k) is not None else np.nan) for k in keys]
        x += list(po[i]) + list(pn[i])
        apart.append((x, r["label"], old[i], new[i]))
    books[name] = apart
tot = Counter()
for name, apart in books.items():
    if not apart:
        continue
    train = [a for m, rows in books.items() if m != name for a in rows if a[1] in (a[2], a[3])]
    X = np.array([a[0] for a in train])
    y = np.array([a[1] == a[3] for a in train])  # follow the grown set
    ref = HistGradientBoostingClassifier(max_depth=3, min_samples_leaf=5, random_state=0).fit(X, y)
    follow_new = ref.predict(np.array([a[0] for a in apart]))
    for (x, lab, o, n), fn in zip(apart, follow_new, strict=True):
        tot["places"] += 1
        tot["old right"] += o == lab
        tot["new right"] += n == lab
        tot["referee right"] += (n if fn else o) == lab
    print(name, len(apart), flush=True)
print("totals:", dict(tot))
