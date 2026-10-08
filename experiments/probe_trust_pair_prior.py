"""Trust with its substitution-pair prior against trust without it, leaving one book out.

The prior (`trust.pairs_table`, `trust.prior`): how often, in the training books, a
version differing from the layer's by exactly this substitution ('' → '’', '|' → 'I',
'é' → 'ë') was the print. A pair counts when seen in at least `trust.MIN_BOOKS`
training books (`--min-books` overrides), and a training book's suspects get their priors
from the other training books only (`trust.training_matrix`), as a scored book's do.

Per book, as `train_ocr_trust.py` prints: silent errors (the chosen version wrong) at the
fixed rule's own number of questions and at budgets of 0, 0.25, 0.5 and 1 question per
page, for the trees without the prior (an empty table) and with it. Then the prior's
stability with one more training book left out, and, with `--two-pass`, a second pass
where the asked suspects' labels (the reviewer's answers) give a per-book posterior per
pair that rescores the unasked ones.

    PYTHONPATH=experiments uv run python experiments/probe_trust_pair_prior.py [--min-books N] [--two-pass] [--per-book PAIR]

`--per-book PAIR` prints one pair's split per book (e.g. "''→'.'"), to see whether a
single book dominates it.
"""

import sys
from collections import Counter
from pathlib import Path

import numpy as np
from ocr_trust_data import OUT, SPECS, load, suspect
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.book import Book
from roboscriptorium.cli import _range

HELD_OUT = {"lady-into-fox", "grand-hotel-europa", "de-tuin-van-de-avondnevel", "de-eerlijke-vinder", "youre-never-weird-on-the-internet"}
READINGS = {"glm", "tess", "qwen"}
BUDGETS = (0.0, 0.25, 0.5, 1.0)

args = sys.argv[1:]
if "--min-books" in args:
    trust.MIN_BOOKS = int(args[args.index("--min-books") + 1])
TWO_PASS = "--two-pass" in args
PER_BOOK = args[args.index("--per-book") + 1] if "--per-book" in args else ""


def make():
    return HistGradientBoostingClassifier(max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0)


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
    first, last = _range(spec.split(":")[0]) if ranged else Book.load(Path("work") / name).body_pages
    return last - first + 1


def per_suspect(rows, probs, owner) -> list[np.ndarray]:
    out = [[] for _ in rows]
    for p, i in zip(probs, owner, strict=True):
        out[i].append(p)
    return [np.array(p) / max(sum(p), 1e-9) for p in out]


def scored(train: list[dict], rows: list[dict], with_prior: bool) -> list[np.ndarray]:
    suspects, right = [r["s"] for r in train], [r["right"] for r in train]
    pairs = trust.pairs_table(suspects, right, [r["book"] for r in train]) if with_prior else {}
    X, y = (
        trust.training_matrix(suspects, right, [r["book"] for r in train])
        if with_prior
        else trust.training_matrix(suspects, right, [""] * len(train))
    )
    Xt, owner = [], []
    for i, r in enumerate(rows):
        for k in range(len(r["right"])):
            Xt.append(trust.features(r["s"], k, pairs))
            owner.append(i)
    return per_suspect(rows, make().fit(X, y).predict_proba(np.array(Xt))[:, 1], owner)


def silent_at(rows, ps, n: int) -> int:
    """Silent errors when the n least sure suspects are asked and the rest take their best."""
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
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
print(f"a pair counts when seen in ≥ {trust.MIN_BOOKS} training books; a training book's priors come from the other books\n")

if PER_BOOK:
    print(f"pair {PER_BOOK} per book (other version the print / seen):")
    for name, rows in books.items():
        a = n = 0
        for r in rows:
            for k, v in enumerate(r["s"].others, 1):
                if trust.pair(r["s"].ours, v) == PER_BOOK:
                    a += r["right"][k]
                    n += 1
        if n:
            print(f"  {name[:34]:34} {a:4}/{n:<4}")
    print()

print(f"{'book':34} {'pages':>5} {'rule s/a':>9}   {'trees: at rule q (0/.25/.5/1)':>30}   {'+prior: same':>30}")
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

print("\nstability (+prior, silent at the rule's questions, one more training book left out): min–max")
for name, rows in books.items():
    asked = rule(rows)[1]
    spread = [
        silent_at(rows, scored([r for n in books if n not in (name, drop) and trainable(n) for r in books[n]], rows, True), asked)
        for drop in books
        if drop != name and trainable(drop)
    ]
    print(f"  {name[:34]:34} {min(spread)}–{max(spread)}")

if TWO_PASS:
    print(
        "\ntwo passes (+prior): the asked suspects' labels give a per-book posterior per pair, "
        "which rescores the unasked. Silent at .25/.5/1 per page: one pass → two"
    )

    def posterior(s, k: int, answered: dict) -> float:
        def look(key: str) -> float:
            a, n = answered.get(key, (0, 0))
            return (a + 1) / (n + 2)

        if k == 0:
            return 1 - max((look(trust.pair(s.ours, v)) for v in s.others), default=0.5)
        return look(trust.pair(s.ours, s.others[k - 1]))

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
                    a, n = answered.get(key := trust.pair(s.ours, v), (0, 0))
                    answered[key] = (a + rows[i]["right"][k], n + 1)
            two = 0
            for i in rest:
                s = rows[i]["s"]
                p = np.array([ps[i][k] * posterior(s, k, answered) for k in range(len(ps[i]))])
                two += not rows[i]["right"][int(p.argmax())]
            twos.append(two)
        one_total += ones
        two_total += twos
        print(f"  {name[:34]:34} {'/'.join(f'{c:3}' for c in ones)} → {'/'.join(f'{c:3}' for c in twos)}")
    print(f"  {'all':34} {'/'.join(f'{int(c):3}' for c in one_total)} → {'/'.join(f'{int(c):3}' for c in two_total)}")
