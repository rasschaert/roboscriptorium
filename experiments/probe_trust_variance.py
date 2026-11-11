"""How much the arbiter moves when its training data barely changes, and what steadies it.

Each tuning book's suspects are scored by an arbiter trained on the other tuning books.
Each variant is trained once on all their suspects and then again with a random 0.25%
of them left out (72 of 30,647 changed between two retrainings on 2026-11-11 and moved
the bench by fifteen unasked errors), several times. Per variant: the silent errors at the rule's number of questions and their
range over the perturbed trainings, the share of scored suspects whose pick changes,
whose place among the asked changes, and the mean move in sureness.

    uv run python experiments/probe_trust_variance.py [repeats [variants, by number]]

Each run's sureness and right picks go to work/probes/trust-variance/variant-<n>.npz
(the first row the full training), for `probe_trust_calibration.py`.

No models; about half an hour.
"""

import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.config import Settings
from roboscriptorium.trustdata import HELD_OUT, SPECS, rows_of, seats, trainable, usable, weighed

SETTINGS = Settings.from_env()
READINGS, SEATS = weighed(SETTINGS), seats(SETTINGS)
REPEATS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
DROP = 0.0025
OUT = Path("work/probes/trust-variance")
BAGS = 10


def trees(seed: int = 0, **more) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=seed, **more
    )


class Mean:
    """Several models' probabilities averaged."""

    def __init__(self, models):
        self.models = models

    def predict_proba(self, X):
        return np.mean([m.predict_proba(X) for m in self.models], axis=0)


def as_made(X, y, groups):
    return trees().fit(X, y)


def no_early_stop(X, y, groups):
    return trees(early_stopping=False).fit(X, y)


def seeds(X, y, groups):
    return Mean([trees(seed).fit(X, y) for seed in range(BAGS)])


def bags(X, y, groups):
    """Trees without early stopping on bootstrap samples of whole suspects."""
    rng = np.random.default_rng(0)
    ids = np.unique(groups)
    start = np.searchsorted(groups, ids)
    end = np.append(start[1:], len(groups))
    models = []
    for _ in range(BAGS):
        pick = rng.integers(0, len(ids), len(ids))
        rows = np.concatenate([np.arange(start[i], end[i]) for i in pick])
        models.append(trees(early_stopping=False).fit(X[rows], y[rows]))
    return Mean(models)


VARIANTS = {
    "as made (early stopping, one seed)": as_made,
    "no early stopping": no_early_stop,
    f"{BAGS} seeds averaged": seeds,
    f"{BAGS} bags of suspects, no early stopping": bags,
}


def rule(rows) -> int:
    return sum(r["s"].choice == "review" for r in rows)


def fit_and_score(make, train, names, test):
    suspects, right = [r["s"] for r in train], [r["right"] for r in train]
    pairs = trust.pairs_table(suspects, right, names)
    X, y = trust.training_matrix(suspects, right, names, READINGS, SEATS)
    # training_matrix walks the books in order, each book's suspects in theirs
    order = [i for b in dict.fromkeys(names) for i, n in enumerate(names) if n == b]
    groups = np.concatenate(
        [np.full(len(right[i]), at) for at, i in enumerate(order)]
    )
    model = make(X, y, groups)
    Xt, owner = [], []
    for i, r in enumerate(test):
        for k in range(len(r["right"])):
            Xt.append(trust.features(r["s"], k, pairs, READINGS, SEATS))
            owner.append(i)
    p = model.predict_proba(np.array(Xt))[:, 1]
    out = [[] for _ in test]
    for v, i in zip(p, owner, strict=True):
        out[i].append(v)
    return [np.array(v) / max(sum(v), 1e-9) for v in out]


def outcome(test, ps, n):
    """Per suspect: the pick, whether it is among the n least sure (asked), its sureness;
    and the silent errors."""
    sure = np.array([p.max() for p in ps])
    pick = np.array([int(p.argmax()) for p in ps])
    asked = np.zeros(len(ps), bool)
    asked[np.argsort(sure, kind="stable")[:n]] = True
    silent = sum(not r["right"][k] for r, k, a in zip(test, pick, asked, strict=True) if not a)
    return pick, asked, sure, silent


books = {n: rows_of(n, SETTINGS) for n in SPECS if not usable(n, SETTINGS)}
names = [n for n in books if trainable(n) and n.split("--")[0] not in HELD_OUT]
total = sum(len(books[n]) for n in names)
print(
    f"{total} suspects in {len(names)} books, each book scored by the others' arbiter; "
    f"{REPEATS} trainings with {DROP:.2%} of the suspects left out",
    flush=True,
)

rng = np.random.default_rng(1)
drops = [
    {n: set(np.flatnonzero(rng.random(len(books[n])) < DROP).tolist()) for n in names}
    for _ in range(REPEATS)
]


# Each run's sureness and whether its pick was right, per suspect, for the calibration.
KEPT: list[tuple[np.ndarray, np.ndarray]] = []


def run(make, drop):
    """Every book's outcome with the arbiter of the other books, `drop` left out of
    their suspects."""
    picks, asks, sures, hits, silent = [], [], [], [], 0
    for name in names:
        train, of = [], []
        for n in names:
            if n == name:
                continue
            rows = [r for i, r in enumerate(books[n]) if i not in drop.get(n, ())]
            train += rows
            of += [n] * len(rows)
        test = books[name]
        pick, ask, sure, wrong = outcome(test, fit_and_score(make, train, of, test), rule(test))
        picks.append(pick)
        asks.append(ask)
        sures.append(sure)
        hits.append(np.array([r["right"][k] for r, k in zip(test, pick, strict=True)]))
        silent += wrong
    KEPT.append((np.concatenate(sures), np.concatenate(hits)))
    return np.concatenate(picks), np.concatenate(asks), np.concatenate(sures), silent


only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
for at, (label, make) in enumerate(VARIANTS.items()):
    if only and str(at) not in only:
        continue
    KEPT.clear()
    began = time.time()
    pick0, asked0, sure0, silent0 = run(make, {})
    silents, picks, asks, moves = [], [], [], []
    for drop in drops:
        pick, ask, sure, silent = run(make, drop)
        silents.append(silent)
        picks.append(int((pick != pick0).sum()))
        asks.append(int((ask != asked0).sum()))
        moves.append(float(np.abs(sure - sure0).mean()))
    print(
        f"{label}: silent {silent0}, perturbed {min(silents)}–{max(silents)} "
        f"(sd {np.std(silents):.1f}); picks changed {np.mean(picks):.1f} "
        f"(max {max(picks)}); asked changed {np.mean(asks):.1f} (max {max(asks)}); "
        f"sureness moved {np.mean(moves):.4f}; {time.time() - began:.0f}s",
        flush=True,
    )
    np.savez(
        OUT / f"variant-{at}.npz",
        sure=np.array([k[0] for k in KEPT]),
        hit=np.array([k[1] for k in KEPT]),
    )
