"""A date line at a page's top dropped as a running head in a book that has none (Het
geluid van bananen PDF 159, 170: "Shatila, 19 augustus 1982", lost silent). Would the
line-role trees keep it if told how the book's pages open and close: the share of its
pages whose first line repeats on other pages, and whose last does? Each tuning book
scored by trees fitted on the others, with and without the two columns, as the build
keeps lines (P(body) ≥ `sorter.KEEP_BODY`): body lines lost, other lines kept. No models.

    uv run python experiments/probe_sorter_bookheads.py
"""

from collections import Counter

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import bench, sorter
from roboscriptorium.sorterdata import lines

books = {}
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    try:
        rows = lines(spec)
    except Exception:
        continue
    tops = [r["f"]["repeats"] >= 3 for r in rows if r["f"]["i_top"] == 0]
    foots = [r["f"]["repeats"] >= 3 for r in rows if r["f"]["i_bottom"] == 0]
    extra = [sum(tops) / max(1, len(tops)), sum(foots) / max(1, len(foots))]
    books[name] = (rows, extra)
    print(f"{name[:40]:40} pages opening on a repeated line {extra[0]:.2f}, closing on one {extra[1]:.2f}", flush=True)


def fit(X, labels):
    counts = Counter(labels)
    weight = {c: len(labels) / (len(counts) * n) for c, n in counts.items()}
    model = HistGradientBoostingClassifier(max_depth=4, min_samples_leaf=20, l2_regularization=1.0, random_state=0)
    return model.fit(X, labels, sample_weight=[weight[c] for c in labels])


tot = Counter()
for name, (rows, extra) in books.items():
    for label, wide in (("today", False), ("told the book", True)):
        def matrix(rs, ex):
            X = sorter._matrix([r["f"] for r in rs], sorter.FEATURES)
            return np.hstack([X, np.tile(ex, (len(rs), 1))]) if wide else X

        Xt = np.vstack([matrix(rs, ex) for n, (rs, ex) in books.items() if n != name])
        yt = [r["label"] for n, (rs, _) in books.items() if n != name for r in rs]
        model = fit(Xt, yt)
        body = list(model.classes_).index("body")
        p = model.predict_proba(matrix(rows, extra))[:, body]
        lost = sum(q < sorter.KEEP_BODY and r["label"] == "body" for q, r in zip(p, rows, strict=True))
        kept = sum(q >= sorter.KEEP_BODY and r["label"] != "body" for q, r in zip(p, rows, strict=True))
        tot[(label, "body lines lost")] += lost
        tot[(label, "other lines kept")] += kept
        if name.startswith(("het-geluid", "het-heft", "the-story")):
            print(f"  {name[:24]:24} {label:14} lost {lost}, kept {kept}", flush=True)
print(dict(tot))
