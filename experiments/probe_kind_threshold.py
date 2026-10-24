"""Would a sureness threshold per kind of question beat the one threshold? (Argon's value
of information, DeepSeek's ranking, Fable's narrowing; the checklist, "A threshold per kind
of question").

Each tuning book's settled suspects are scored by the arbiter saved without that book (as
`bench` scores it), validation books by the arbiter itself. A suspect's kind is what its
likeliest other version changes in the layer's (`trust.kind`). Replaying `trust.decide`
with a threshold per kind, a suspect is asked when it is among the page budget's least sure
and under its kind's threshold; a decided suspect whose likeliest version isn't the print is
a silent error. Per kind, the curve of questions and silent errors over thresholds; then
thresholds per kind chosen on the other tuning books (fewest silent errors at no more
questions than the one threshold there) and applied to the book left out.

    uv run python experiments/probe_kind_threshold.py
"""

import itertools
from collections import Counter
from pathlib import Path

import numpy as np

from roboscriptorium import trust
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable

GRID = (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0)
KINDS = ("accent", "space", "case", "quote", "letters")


def pages(name: str) -> int:
    """The pages the book's data was built from, which the pipeline's budget counts."""
    spec = SPECS[name]
    first, last = scoring.page_range(spec.split(":")[0]) if spec else Book.load(Path("work") / name).body_pages
    return last - first + 1


def score(name: str, rows: list[dict], path: Path) -> list[dict]:
    model = trust.load(trust.without(path, name) if trainable(name) else path)
    out = []
    for r in rows:
        s = r["s"]
        p = trust.probabilities(model, s)
        others = sorted(range(1, len(p)), key=lambda k: -p[k])
        out.append({
            "kind": trust.kind(s.ours, s.others[others[0] - 1]) if others else "letters",
            "sure": trust.sureness(model, p),
            "raw": float(p.max()),
            "unseen": trust.unseen(s),
            "wrong": not r["right"][0 if trust.unseen(s) else int(p.argmax())],
        })  # fmt: skip
    return out


def replay(items: list[dict], budget: int, below: dict[str, float]) -> tuple[int, int]:
    """(questions, silent errors) with these thresholds per kind, as `trust.decide` asks."""
    order = sorted(range(len(items)), key=lambda i: (not items[i]["unseen"], items[i]["sure"], items[i]["raw"]))
    asked = {
        i for i in order[:budget]
        if items[i]["unseen"] or items[i]["sure"] < below[items[i]["kind"]] or below[items[i]["kind"]] >= 1
    }  # fmt: skip
    return len(asked), sum(it["wrong"] for i, it in enumerate(items) if i not in asked)


def choose(books: dict[str, tuple[list, int]], base: float) -> dict[str, float]:
    """The thresholds per kind with fewest silent errors on these books at no more
    questions than `base` for every kind. Which suspects fall inside the budget doesn't
    depend on the thresholds, so each kind's questions and catches add up apart and every
    combination is counted from one table."""
    table = {k: [[0, 0] for _ in GRID] for k in KINDS}
    for items, budget in books.values():
        order = sorted(items, key=lambda it: (not it["unseen"], it["sure"], it["raw"]))
        for it in order[:budget]:
            if it["unseen"]:
                continue
            for j, g in enumerate(GRID):
                if it["sure"] < g or g >= 1:
                    table[it["kind"]][j][0] += 1
                    table[it["kind"]][j][1] += it["wrong"]
    start = tuple(GRID.index(base) for _ in KINDS)
    cap = sum(table[k][j][0] for k, j in zip(KINDS, start, strict=True))
    best = None
    for combo in itertools.product(range(len(GRID)), repeat=len(KINDS)):
        q = sum(table[k][j][0] for k, j in zip(KINDS, combo, strict=True))
        caught = sum(table[k][j][1] for k, j in zip(KINDS, combo, strict=True))
        if q <= cap and (best is None or (-caught, q) < best[0]):
            best = ((-caught, q), combo)
    return {k: GRID[j] for k, j in zip(KINDS, best[1], strict=True)}


if __name__ == "__main__":
    settings = Settings.from_env()
    path = Path(settings.ocr_trust_model)
    base = settings.ocr_ask_below
    names = [n for n in SPECS if SPECS[n] != "answers" and not usable(n, settings)]
    books = {}
    for name in names:
        rows = rows_of(name, settings)
        books[name] = (score(name, rows, path), round(settings.ocr_questions_per_page * pages(name)))
    tuning = {n: v for n, v in books.items() if trainable(n)}
    held = {n: v for n, v in books.items() if not trainable(n)}
    print(f"tuning books {len(tuning)}, validation books {len(held)}")
    counts = Counter(it["kind"] for it, _ in tuning.values() for it in it)
    print("suspects by kind:", dict(counts))

    print("\nper kind, the others at", base, "(tuning): threshold → questions / silent errors")
    for k in KINDS:
        cells = []
        for g in GRID:
            below = {**dict.fromkeys(KINDS, base), k: g}
            q = s = 0
            for it, b in tuning.values():
                dq, ds = replay(it, b, below)
                q, s = q + dq, s + ds
            cells.append(f"{g}: {q}/{s}")
        print(f"  {k:8} " + "  ".join(cells))

    one = Counter()
    per = Counter()
    for name, (it, b) in tuning.items():
        below = choose({n: v for n, v in tuning.items() if n != name}, base)
        q0, s0 = replay(it, b, dict.fromkeys(KINDS, base))
        q1, s1 = replay(it, b, below)
        one.update(questions=q0, silent=s0)
        per.update(questions=q1, silent=s1)
        if (q0, s0) != (q1, s1):
            print(f"  {name[:36]:36} one {q0}/{s0}  per kind {q1}/{s1}  {below}")
    print(f"\ntuning, each book left out: one threshold {dict(one)}, per kind {dict(per)}")
    below = choose(tuning, base)
    print("chosen on every tuning book:", below)
    one, per = Counter(), Counter()
    for it, b in held.values():
        q0, s0 = replay(it, b, dict.fromkeys(KINDS, base))
        q1, s1 = replay(it, b, below)
        one.update(questions=q0, silent=s0)
        per.update(questions=q1, silent=s1)
    print(f"validation: one threshold {dict(one)}, per kind {dict(per)}")
