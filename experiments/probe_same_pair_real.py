"""What weighing the same pair elsewhere does to a book with no reference: its built
places (`stages/ocr-check.json`) scored by trees trained on every tuning book, with the
arbiter's inputs as they are and with the two more (`probe_same_pair_arbiter.py`). Counts
the places under each sureness, and lists the places asked today at a pair the book
raises three times or more, with what each arbiter makes of them, for a check by eye.
Rows to work/probes/same-pair-real/<book>.jsonl. No models.

    PYTHONPATH=experiments uv run python experiments/probe_same_pair_real.py <book> [<book> …]
"""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

import probe_same_pair_arbiter as probe
from roboscriptorium import trust
from roboscriptorium.trustdata import SPECS, rows_of, suspect, trainable, usable

OUT = Path("work/probes/same-pair-real")
OUT.mkdir(parents=True, exist_ok=True)
names = [n for n in SPECS if trainable(n) and not usable(n, probe.SETTINGS) and n not in sys.argv[1:]]
data = {n: rows_of(n, probe.SETTINGS) for n in names}
train = [r for n in names for r in data[n]]
suspects, right = [r["s"] for r in train], [r["right"] for r in train]
owners = [n for n in names for _ in data[n]]
X, y = trust.training_matrix(suspects, right, owners, probe.READINGS, probe.SEATS)
pairs = trust.pairs_table(suspects, right, owners)
more = np.vstack([probe.columns(data[n]) for n in names])
plain = trust.Trees(probe.SEEDS).fit(X, y)
paired = trust.Trees(probe.SEEDS).fit(np.hstack([X, more]), y)

for book in sys.argv[1:]:
    rows = [{"s": suspect({"suspect": d})} for d in json.loads((Path("work") / book / "stages/ocr-check.json").read_text())]
    rows = [r for r in rows if r["s"].votes]
    Xt = np.array([trust.features(r["s"], k, pairs, probe.READINGS, probe.SEATS) for r in rows for k in range(1 + len(r["s"].others))])
    cells = probe.elsewhere(rows)
    both = []
    for model, A in ((plain, Xt), (paired, np.hstack([Xt, probe.columns(rows)]))):
        p, ps, at = model.predict_proba(A)[:, 1], [], 0
        for r in rows:
            n = 1 + len(r["s"].others)
            ps.append(p[at : at + n] / max(p[at : at + n].sum(), 1e-9))
            at += n
        both.append(ps)
    asked = sum(r["s"].choice == "review" for r in rows)
    print(f"{book}: {len(rows)} judged places, {asked} asked in its build")
    for cut in (0.7, 0.8, 0.9, 0.95):
        print(f"  under {cut} sure: {sum(q.max() < cut for q in both[0])} → {sum(q.max() < cut for q in both[1])}")
    moved = Counter()
    with (OUT / f"{book}.jsonl").open("w") as out:
        for r, c, a, b in zip(rows, cells, *both, strict=True):
            s = r["s"]
            if not any(n >= 2 for _, n in c[1:]):
                continue
            versions = [s.ours, *s.others]
            row = {
                "page": s.page, "line": s.line, "box": list(s.box), "text": s.original, "versions": versions,
                "asked": s.choice == "review", "elsewhere": c,
                "as it is": [versions[int(a.argmax())], round(float(a.max()), 3)],
                "with the pair": [versions[int(b.argmax())], round(float(b.max()), 3)],
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            if s.choice == "review":
                moved["asked at a pair raised often"] += 1
                moved["of those, now 0.9 sure or more"] += b.max() >= 0.9
                moved["of those, pick changed"] += int(a.argmax()) != int(b.argmax())
            else:
                moved["not asked, pick changed"] += int(a.argmax()) != int(b.argmax())
                moved["not asked, now under 0.9"] += a.max() >= 0.9 > b.max()
    for k, v in moved.items():
        print(f"  {k}: {int(v)}")
