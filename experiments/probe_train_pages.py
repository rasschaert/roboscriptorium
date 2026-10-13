"""Does the arbiter learn more from more pages a book? Trained on each book's first N pages only.

Every tuning book's suspects are cut to those on its first N slice pages, the trees are
trained on the cut books but one, and the left-out book is scored on all its suspects,
as `train_ocr_trust.py` scores them (silent errors at the rule's own number of questions,
and at budgets of questions a page). A book shorter than N gives all it has, so N past the
longest slice is the whole data.

    PYTHONPATH=experiments uv run python experiments/probe_train_pages.py [N ...]

No models; about a minute an N.
"""

import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from ocr_trust_data import SPECS, load, suspect
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import bench, trust
from roboscriptorium.book import Book
from roboscriptorium.cli import _range
from roboscriptorium.config import Settings

HELD_OUT = {spec.split("--")[0] for spec in bench.SETS["validation"] + bench.SETS["test"]}
BUDGETS = (0.0, 0.25, 0.5, 1.0)
_SETTINGS = Settings.from_env()
JUDGES = {_SETTINGS.judge_model, _SETTINGS.check_model, _SETTINGS.alarm_model, "word list"} - {""}


def first_page(name: str) -> tuple[int, int]:
    spec = SPECS[name]
    if spec and spec != "answers":
        return _range(spec.split(":")[0])
    return Book.load(Path("work") / name).body_pages


def rows_of(name: str) -> list[dict]:
    rows = [r for r in load(name) if r["settled"]]
    for r in rows:
        s = suspect(r)
        r["s"] = replace(
            s,
            votes={m: v for m, v in s.votes.items() if m in JUDGES},
            judges=tuple(m for m in s.judges if m in JUDGES),
            confidence={m: c for m, c in s.confidence.items() if m in JUDGES},
        )
    return rows


def scored(train: dict[str, list[dict]], rows: list[dict]):
    suspects = [r["s"] for rs in train.values() for r in rs]
    right = [r["right"] for rs in train.values() for r in rs]
    names = [n for n, rs in train.items() for _ in rs]
    pairs = trust.pairs_table(suspects, right, names)
    X, y = trust.training_matrix(suspects, right, names)
    model = HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    ).fit(X, y)
    out = []
    for r in rows:
        p = model.predict_proba([trust.features(r["s"], k, pairs) for k in range(len(r["right"]))])[:, 1]
        out.append(p / max(p.sum(), 1e-9))
    return out


def silent_at(rows, ps, n: int) -> int:
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
    return sum(wrong for _, wrong in order[n:])


def asked_by_rule(rows) -> int:
    return sum(r["s"].choice == "review" for r in rows)


names = [
    n for n in SPECS
    if n != "stella" and n.split("--")[0] not in HELD_OUT
    and (Path("work/probes/ocr-trust") / f"{n}.json").exists()
]
books = {n: rows_of(n) for n in names}
span = {n: first_page(n) for n in names}
sizes = [int(a) for a in sys.argv[1:]] or [10, 20, 45, 1000]

print(f"{len(names)} tuning books with data; pages a slice: "
      + ", ".join(f"{n.split('--')[0]} {b - a + 1}" for n, (a, b) in span.items()))
for size in sizes:
    cut = {n: [r for r in rs if r["s"].page < span[n][0] + size] for n, rs in books.items()}
    totals: Counter = Counter()
    line = []
    for name, rows in books.items():
        pages = span[name][1] - span[name][0] + 1
        ps = scored({n: rs for n, rs in cut.items() if n != name}, rows)
        totals["rule"] += silent_at(rows, ps, asked_by_rule(rows))
        for b in BUDGETS:
            totals[b] += silent_at(rows, ps, int(b * pages))
        line.append(f"{name.split('--')[0][:12]} {silent_at(rows, ps, pages)}")
    trained = sum(len(rs) for rs in cut.values())
    print(f"\nfirst {size} pages: {trained} suspects to train on")
    print("  silent errors over all books, at the rule's questions:", totals["rule"],
          "| at 0/.25/.5/1 a page:", "/".join(str(totals[b]) for b in BUDGETS))
    print("  per book at 1 a page:", ", ".join(line))
