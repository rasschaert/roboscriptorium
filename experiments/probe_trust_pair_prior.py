"""Trust with a substitution-pair prior, scored leaving one book out, against trust as it is.

The prior for a version: how often, in the training books, a version that differs from
the layer's by exactly this substitution (from → to, e.g. '' → '’', '|' → 'I', 'é' → 'ë')
was the print, Laplace-smoothed, with how often the pair was seen (log). The layer's own
version gets its strongest rival's prior, inverted. A pair counts only when seen in at
least `--min-books` training books (default 2), so one book's reference conventions can't
teach every other book. Training rows are scored with their own label left out of the
table (a leaked label made the model trust the prior too much and did worse).

Per book, as `train_ocr_trust.py` prints: silent errors (the chosen version wrong) at the
fixed rule's own number of questions, and at budgets of 0, 0.25, 0.5 and 1 question per
page, for the trees as they are and with the prior. Then the prior's stability with one
more training book left out, and, with `--two-pass`, a second pass where the asked
suspects' labels (the reviewer's answers) give a per-book posterior per pair that
rescores the unasked ones.

    PYTHONPATH=experiments uv run python experiments/probe_trust_pair_prior.py [--min-books N] [--two-pass] [--per-book PAIR]

`--per-book PAIR` prints one pair's split per book (e.g. "''→'.'"), to see whether a
single book dominates it.
"""

import difflib
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from ocr_trust_data import OUT, SPECS, load, suspect
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.book import Book
from roboscriptorium.cli import _range

HELD_OUT = {
    "lady-into-fox",
    "grand-hotel-europa",
    "de-tuin-van-de-avondnevel",
    "de-eerlijke-vinder",
    "youre-never-weird-on-the-internet",
}
READINGS = {"glm", "tess", "qwen"}
BUDGETS = (0.0, 0.25, 0.5, 1.0)

args = sys.argv[1:]
MIN_BOOKS = int(args[args.index("--min-books") + 1]) if "--min-books" in args else 2
TWO_PASS = "--two-pass" in args
PER_BOOK = args[args.index("--per-book") + 1] if "--per-book" in args else ""


def pair(ours: str, other: str) -> str:
    """The substitution between two versions of a span: each differing stretch, from → to."""
    sm = difflib.SequenceMatcher(None, ours, other, autojunk=False)
    parts = [
        f"{ours[i1:i2]!r}→{other[j1:j2]!r}"
        for tag, i1, i2, j1, j2 in sm.get_opcodes()
        if tag != "equal"
    ]
    return "|".join(parts) or "="


def make():
    return HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )


def rows_of(name: str) -> list[dict]:
    rows = [r for r in load(name) if r["settled"]]
    for r in rows:
        r["s"] = suspect(r)
        r["book"] = name
    return rows


def usable(name: str) -> bool:
    if not (OUT / f"{name}.json").exists():
        return False
    rows = load(name)
    return bool(rows) and READINGS <= set(rows[0]["suspect"]["support"])


def trainable(name: str) -> bool:
    return name.split("--")[0] not in HELD_OUT


def pages_of(name: str) -> int:
    spec = SPECS[name]
    ranged = spec and spec != "answers"
    first, last = (
        _range(spec.split(":")[0]) if ranged else Book.load(Path("work") / name).body_pages
    )
    return last - first + 1


def table(train: list[dict]) -> dict[str, list[int]]:
    """Per pair: [times the other version was the print, times seen], over the training
    rows, pairs seen in fewer than MIN_BOOKS books left out."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    seen_in: dict[str, set] = defaultdict(set)
    for r in train:
        s = r["s"]
        for k, v in enumerate(s.others, 1):
            key = pair(s.ours, v)
            counts[key][0] += r["right"][k]
            counts[key][1] += 1
            seen_in[key].add(r["book"])
    return {key: c for key, c in counts.items() if len(seen_in[key]) >= MIN_BOOKS}


def prior(s, k: int, counts: dict) -> list[float]:
    """The prior features of version k: P(the print) and log(1 + times seen)."""

    def look(key: str) -> tuple[float, float]:
        a, n = counts.get(key, (0, 0))
        return (a + 1) / (n + 2), math.log1p(max(0, n))

    if k == 0:
        rivals = [look(pair(s.ours, v)) for v in s.others]
        p, n = max(rivals, key=lambda t: t[0]) if rivals else (0.5, 0.0)
        return [1 - p, n]
    return list(look(pair(s.ours, s.others[k - 1])))


def matrix(rows: list[dict], counts: dict | None, training: bool = False):
    """Feature rows per version; with `counts`, the prior features appended. A training
    row is scored with its own labels left out of the table."""
    X, y, owner = [], [], []
    for i, r in enumerate(rows):
        s = r["s"]
        if counts is not None and training:
            for k, v in enumerate(s.others, 1):
                if (key := pair(s.ours, v)) in counts:
                    counts[key][0] -= r["right"][k]
                    counts[key][1] -= 1
        for k, ok in enumerate(r["right"]):
            f = trust.features(s, k)
            if counts is not None:
                f = f + prior(s, k, counts)
            X.append(f)
            y.append(int(ok))
            owner.append(i)
        if counts is not None and training:
            for k, v in enumerate(s.others, 1):
                if (key := pair(s.ours, v)) in counts:
                    counts[key][0] += r["right"][k]
                    counts[key][1] += 1
    return np.array(X), np.array(y), owner


def per_suspect(rows, probs, owner) -> list[np.ndarray]:
    out = [[] for _ in rows]
    for p, i in zip(probs, owner, strict=True):
        out[i].append(p)
    return [np.array(p) / max(sum(p), 1e-9) for p in out]


def scored(train: list[dict], rows: list[dict], with_prior: bool) -> list[np.ndarray]:
    counts = table(train) if with_prior else None
    X, y, _ = matrix(train, counts, training=True)
    Xt, _, owner = matrix(rows, counts)
    return per_suspect(rows, make().fit(X, y).predict_proba(Xt)[:, 1], owner)


def silent_at(rows, ps, n: int) -> int:
    """Silent errors when the n least sure suspects are asked and the rest take their best."""
    order = sorted(
        (p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True)
    )
    return sum(wrong for _, wrong in order[n:])


def rule(rows) -> tuple[int, int]:
    silent = asked = 0
    for r in rows:
        s = r["s"]
        if s.choice == "review":
            asked += 1
        else:
            k = 0 if s.choice == "ours" else 1 + s.others.index(s.chosen)
            silent += not r["right"][k]
    return silent, asked


books = {name: rows_of(name) for name in SPECS if usable(name)}
print("books:", ", ".join(f"{n} {len(r)}" for n, r in books.items()))
print(f"a pair counts when seen in ≥ {MIN_BOOKS} training books\n")

if PER_BOOK:
    print(f"pair {PER_BOOK} per book (other version the print / seen):")
    for name, rows in books.items():
        a = n = 0
        for r in rows:
            for k, v in enumerate(r["s"].others, 1):
                if pair(r["s"].ours, v) == PER_BOOK:
                    a += r["right"][k]
                    n += 1
        if n:
            print(f"  {name[:34]:34} {a:4}/{n:<4}")
    print()

print(
    f"{'book':34} {'pages':>5} {'rule s/a':>9}   {'trees: at rule q (0/.25/.5/1)':>30}   {'+prior: same':>30}"
)
totals: Counter = Counter()
curves = {"trees": np.zeros(len(BUDGETS)), "prior": np.zeros(len(BUDGETS))}
for name, rows in books.items():
    train = [r for n in books if n != name and trainable(n) for r in books[n]]
    silent, asked = rule(rows)
    pages = pages_of(name)
    totals["rule"] += silent
    cells = []
    for label, with_prior in (("trees", False), ("prior", True)):
        ps = scored(train, rows, with_prior)
        same = silent_at(rows, ps, asked)
        curve = [silent_at(rows, ps, int(b * pages)) for b in BUDGETS]
        totals[label] += same
        curves[label] += np.array(curve)
        cells.append(f"{same:3} ({'/'.join(f'{c:3}' for c in curve)})")
    tag = " held out" if not trainable(name) else ""
    print(f"{name[:34]:34} {pages:5} {silent:4}/{asked:<4}   {cells[0]:>30}   {cells[1]:>30}{tag}")
print("\nsilent at the rule's questions:", dict(totals))
print(
    f"silent at budgets {'/'.join(map(str, BUDGETS))} per page, all books: "
    f"trees {curves['trees'].astype(int).tolist()}, +prior {curves['prior'].astype(int).tolist()}"
)

print(
    "\nstability (+prior, silent at the rule's questions, one more training book left out): min–max"
)
for name, rows in books.items():
    asked = rule(rows)[1]
    spread = [
        silent_at(
            rows,
            scored(
                [r for n in books if n not in (name, drop) and trainable(n) for r in books[n]],
                rows,
                True,
            ),
            asked,
        )
        for drop in books
        if drop != name and trainable(drop)
    ]
    print(f"  {name[:34]:34} {min(spread)}–{max(spread)}")

if TWO_PASS:
    print(
        f"\ntwo passes (+prior): the asked suspects' labels give a per-book posterior per pair, "
        "which rescores the unasked. Silent at .25/.5/1 per page: one pass → two"
    )

    def posterior(s, k: int, answered: dict) -> float:
        def look(key: str) -> float:
            a, n = answered.get(key, (0, 0))
            return (a + 1) / (n + 2)

        if k == 0:
            return 1 - max((look(pair(s.ours, v)) for v in s.others), default=0.5)
        return look(pair(s.ours, s.others[k - 1]))

    one_total = np.zeros(3)
    two_total = np.zeros(3)
    for name, rows in books.items():
        train = [r for n in books if n != name and trainable(n) for r in books[n]]
        ps = scored(train, rows, True)
        pages = pages_of(name)
        ones, twos = [], []
        for b in (0.25, 0.5, 1.0):
            order = sorted(range(len(rows)), key=lambda i: ps[i].max())
            asked, rest = order[: int(b * pages)], order[int(b * pages) :]
            ones.append(sum(not rows[i]["right"][int(ps[i].argmax())] for i in rest))
            answered: dict[str, tuple[int, int]] = {}
            for i in asked:
                s = rows[i]["s"]
                for k, v in enumerate(s.others, 1):
                    a, n = answered.get(key := pair(s.ours, v), (0, 0))
                    answered[key] = (a + rows[i]["right"][k], n + 1)
            two = 0
            for i in rest:
                s = rows[i]["s"]
                p = np.array([ps[i][k] * posterior(s, k, answered) for k in range(len(ps[i]))])
                two += not rows[i]["right"][int(p.argmax())]
            twos.append(two)
        one_total += ones
        two_total += twos
        print(
            f"  {name[:34]:34} {'/'.join(f'{c:3}' for c in ones)} → {'/'.join(f'{c:3}' for c in twos)}"
        )
    print(
        f"  {'all':34} {'/'.join(f'{int(c):3}' for c in one_total)} → {'/'.join(f'{int(c):3}' for c in two_total)}"
    )
