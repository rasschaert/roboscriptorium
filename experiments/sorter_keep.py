"""Two sets of line-role trees on the same labelled lines (`sorterdata.lines`), each tuning
book scored by its own left-out copy, as the build keeps lines: as text wherever P(body)
reaches the keep threshold (`sorter.KEEP_BODY`, 0.25). Counts body lines lost and other
lines kept, per threshold and per book. No models, about a minute; it foretold both
retrains' bench verdicts of 2026-11-05 (stray lines kept 214 → 261 and 255), so a retrain
is checked here before its bench.

    uv run python experiments/sorter_keep.py <old models dir> <new models dir>

Train the new set aside first:
`ROBO_SORTER_MODEL=<dir>/line-roles.pkl uv run python experiments/train_sorter.py --save`.
"""
import collections
import sys
from pathlib import Path

from roboscriptorium import bench, sorter
from roboscriptorium.sorterdata import lines

old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])
tuning = [s for s in bench.SETS["tuning"]]
cuts = (0.1, 0.25, 0.4, 0.5)
tot = {k: collections.Counter() for k in ("old", "new")}
for spec in tuning:
    name = spec.split(":")[0]
    rows = lines(spec)
    for which, d in (("old", old_dir), ("new", new_dir)):
        m = sorter.load(d / f"line-roles-without-{name}.pkl")
        X = sorter._matrix([r["f"] for r in rows], m.features)
        body = list(m.model.classes_).index("body")
        p = m.model.predict_proba(X)[:, body]
        for c in cuts:
            lost = sum(1 for r, q in zip(rows, p) if r["label"] == "body" and q < c)
            kept = sum(1 for r, q in zip(rows, p) if r["label"] == "other" and q >= c)
            tot[which][(c, "lost")] += lost
            tot[which][(c, "kept")] += kept
            if c == 0.25:
                tot[which][(name, "lost")] += lost
                tot[which][(name, "kept")] += kept
for c in cuts:
    print(f"P(body) >= {c}: old lost {tot['old'][(c,'lost')]:4} kept {tot['old'][(c,'kept')]:4}   new lost {tot['new'][(c,'lost')]:4} kept {tot['new'][(c,'kept')]:4}")
print("at 0.25, per book (old lost/kept → new lost/kept):")
for spec in tuning:
    n = spec.split(":")[0]
    o, w = tot["old"], tot["new"]
    if (o[(n,"lost")], o[(n,"kept")]) != (w[(n,"lost")], w[(n,"kept")]):
        print(f"  {n[:34]:34} {o[(n,'lost')]:3}/{o[(n,'kept')]:3} → {w[(n,'lost')]:3}/{w[(n,'kept')]:3}")
