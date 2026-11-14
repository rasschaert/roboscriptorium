"""Where two sets of italic trees disagree, book by book, and which is right there: each
tuning book's words (`work/probes/italic-words/`) scored by each set's copy trained
without it. Says whether a judge settling only their disagreements could take the best
of both. No models.

    uv run python experiments/italic_disagree.py <old models dir> <new models dir>
"""

import json
import sys
from pathlib import Path

import numpy as np

from roboscriptorium import bench, italics

OUT = Path("work/probes/italic-words")
old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])
tot = np.zeros(6, dtype=int)
print(f"{'book':34} {'words':>7} {'italic':>6}  err old/new  apart  old right/new right")
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    path = OUT / f"{name}.jsonl"
    if not path.exists():
        continue
    rows = [json.loads(line) for line in open(path)]
    lab = np.array([r["label"] for r in rows])
    picks = []
    for d in (old_dir, new_dir):
        trees = italics.load(italics.without(d / "italics.pkl", name))
        X = np.array([[r[k] for k in trees.features] for r in rows], dtype=float)
        picks.append(trees.model.predict_proba(X)[:, 1] >= italics.ITALIC_P)
    old, new = picks
    apart = old != new
    row = [len(rows), int(lab.sum()), int((old != lab).sum()), int((new != lab).sum()),
           int(apart.sum()), int((old[apart] == lab[apart]).sum())]  # fmt: skip
    tot += row
    print(f"{name[:34]:34} {row[0]:7} {row[1]:6}  {row[2]:5}/{row[3]:<5} {row[4]:5}  "
          f"{row[5]:5}/{row[4] - row[5]:<5}")  # fmt: skip
print(f"{'all':34} {tot[0]:7} {tot[1]:6}  {tot[2]:5}/{tot[3]:<5} {tot[4]:5}  {tot[5]:5}/{tot[4] - tot[5]:<5}")
print(f"best of both on every disagreement: {tot[2] - tot[5] if False else tot[2] - (tot[4] - tot[5]) - 0} errors "
      f"(old {tot[2]}, new {tot[3]})")
