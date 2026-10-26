"""What each sureness threshold for asking costs in questions and saves in silent errors,
on the tuning books' current builds. No models.

Each book's suspects as its last build cached them (`ocr-check.json`), scored by the
arbiter saved without that book (as `bench` scores it), labelled by the book's trust data
where a suspect has a settled row. Per threshold: questions (sureness below it, up to the
page budget) and silent errors (decided, labelled wrong). The book's own answers
(`trust.with_answers`, `by_book`) are left out, so the 0.8 row is near the bench's, not it.

    uv run python experiments/probe_ask_threshold.py
"""

import json
from collections import Counter
from dataclasses import fields
from pathlib import Path

import numpy as np

from roboscriptorium import bench, trust
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.ocrcheck import Suspect

BUDGET = float(__import__("os").environ.get("BUDGET", "1"))
GRID = (0.8, 0.85, 0.9, 0.95, 0.97, 0.99)
NAMES = {f.name for f in fields(Suspect)}


def as_suspect(d: dict) -> Suspect:
    d = {k: v for k, v in d.items() if k in NAMES}
    d["others"], d["box"], d["known"] = tuple(d["others"]), tuple(d["box"]), tuple(d["known"])
    d["support"] = {k: tuple(v) for k, v in d["support"].items()}
    return Suspect(**d)


path = Path(Settings.from_env().ocr_trust_model)
totals: Counter = Counter()
for spec in bench.SETS["tuning"]:
    name, pages = spec.split(":")[0], spec.split(":")[1] if ":" in spec else ""
    data = Path("work/probes/ocr-trust") / f"{name}.json"
    model = trust.load(trust.without(path, name)) or trust.load(path)
    if not data.exists():
        continue
    labels = {
        (r["suspect"]["page"], r["suspect"]["line"], r["suspect"]["start"], r["suspect"]["ours"]): r
        for r in json.loads(data.read_text())
        if r["settled"]
    }
    first, last = scoring.page_range(pages) if pages else Book.load(Path("work") / name).body_pages
    cached = [as_suspect(d) for d in json.loads((Path("work") / name / "stages/ocr-check.json").read_text())]
    cached = [s for s in cached if first <= s.page <= last]
    budget = (last - first + 1) * BUDGET
    rows = []
    for s in cached:
        r = labels.get((s.page, s.line, s.start, s.ours))
        p = trust.probabilities(model, s)
        sure = trust.sureness(model, p)
        best = int(p.argmax())
        wrong = None if r is None else not r["right"][0 if trust.unseen(s) else best]
        rows.append((trust.unseen(s), sure, float(p.max()), wrong))
    rows.sort(key=lambda t: (not t[0], t[1], t[2]))
    cells = []
    for t in GRID:
        asked = {i for i, (u, sure, _, _) in enumerate(rows[: int(budget)]) if u or sure < t}
        silent = sum(1 for i, r in enumerate(rows) if i not in asked and r[3])
        caught = sum(1 for i in asked if rows[i][3])
        totals[t, "asked"] += len(asked)
        totals[t, "silent"] += silent
        cells.append(f"{len(asked):4}/{silent:<3}")
    print(f"{name[:30]:30} pages {budget:4}  " + "  ".join(cells))
print(" " * 42 + "  ".join(f"{t:<8}" for t in GRID) + "  (questions/silent errors)")
for t in GRID:
    print(f"threshold {t}: questions {totals[t, 'asked']}, silent errors {totals[t, 'silent']}")
