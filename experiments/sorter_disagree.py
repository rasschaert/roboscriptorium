"""Where two sets of line-role trees disagree, book by book, and which is right there:
each tuning book's labelled lines (`sorterdata.lines`) scored by each set's copy trained
without it, as the build keeps lines (`sorter.KEEP_BODY` for body, else the likeliest of
heading and other). Says whether a judge settling only their disagreements could take
the best of both, as the italic judge does. No models.

    uv run python experiments/sorter_disagree.py <old models dir> <new models dir>
"""

import sys
from collections import Counter
from pathlib import Path

import numpy as np

from roboscriptorium import bench, sorter
from roboscriptorium.sorterdata import lines

old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])


def calls(m, rows):
    X = sorter._matrix([r["f"] for r in rows], m.features)
    classes = list(m.model.classes_)
    p = m.model.predict_proba(X)
    body = classes.index("body")
    out = []
    for q in p:
        if q[body] >= sorter.KEEP_BODY:
            out.append("body")
        else:
            rest = [(q[i], c) for i, c in enumerate(classes) if c != "body"]
            out.append(max(rest)[1])
    return out


tot = Counter()
examples = []
print(f"{'book':34} {'lines':>6}  err old/new  apart  old right/new right/neither")
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    try:
        rows = lines(spec)
        old = calls(sorter.load(sorter.without(old_dir / "line-roles.pkl", name)), rows)
        new = calls(sorter.load(sorter.without(new_dir / "line-roles.pkl", name)), rows)
    except Exception as e:
        print(f"{name}: skipped ({e})")
        continue
    lab = [r["label"] for r in rows]
    apart = [i for i in range(len(rows)) if old[i] != new[i]]
    c = Counter(
        "old" if old[i] == lab[i] else "new" if new[i] == lab[i] else "neither" for i in apart
    )
    eo = sum(o != y for o, y in zip(old, lab)); en = sum(n != y for n, y in zip(new, lab))
    tot.update({"lines": len(rows), "old err": eo, "new err": en, "apart": len(apart), **c})
    print(f"{name[:34]:34} {len(rows):6}  {eo:4}/{en:<4}  {len(apart):5}  {c['old']:4}/{c['new']:4}/{c['neither']:4}")
    for i in apart[:2]:
        examples.append((name, rows[i]["page"], lab[i], old[i], new[i]))
print("all:", dict(tot))
print("best of both on every disagreement:", tot["old err"] - tot["new"], "errors")
for e in examples[:30]:
    print("  ", e)
