"""How often a line the line-role trees call a chapter heading is one, by how sure they
are: each tuning book's labelled lines (`sorterdata.lines`) scored by production's trees
left out of it. Says from what sureness a heading need not be asked. No models.

    uv run python experiments/heading_sureness.py
"""

import collections
from pathlib import Path

from roboscriptorium import bench, sorter
from roboscriptorium.config import Settings
from roboscriptorium.sorterdata import lines

CUTS = (0.5, 0.8, 0.9, 0.95, 0.97, 0.99)
models = Path(Settings.from_env().sorter_model)
hits = collections.Counter()
wrong = collections.defaultdict(list)
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    rows = lines(spec)
    m = sorter.load(sorter.without(models, name))
    if m is None:
        continue
    X = sorter._matrix([r["f"] for r in rows], m.features)
    classes = list(m.model.classes_)
    if "heading" not in classes:
        continue
    ph = m.model.predict_proba(X)
    for r, p in zip(rows, ph, strict=True):
        best = classes[int(p.argmax())]
        if best != "heading":
            continue
        sure = float(p.max())
        for c in CUTS:
            if sure >= c:
                hits[(c, r["label"])] += 1
        if r["label"] != "heading" and sure >= 0.9:
            wrong[name].append((r["page"], r["line"], round(sure, 3), r["label"]))
print("sureness ≥   headings  body  other   share right")
for c in CUTS:
    h, b, o = hits[(c, "heading")], hits[(c, "body")], hits[(c, "other")]
    print(f"{c:9}   {h:8} {b:5} {o:6}   {h / max(1, h + b + o):.3f}")
print("called headings at 0.9 or more that the reference doesn't hold as one:")
for name, places in wrong.items():
    print(f"  {name[:34]:34} {len(places):3}  {places[:6]}")
