"""How many seeds the arbiter's trees should average: steadiness, accuracy and time by number.

As `probe_trust_variance.py`: each tuning book's suspects scored by trees trained on
the other tuning books, once on all their suspects and again with a random 0.25% left
out. Twenty seeds are trained per fold; the first 1, 5, 10, 15 and all 20 are averaged.
Per number: the wrong picks, the silent errors at the rule's number of questions, the
suspects whose pick changes and whose place among the asked changes under the left-out
suspects, with the logistic calibration the questions asked under a calibrated 0.9, and
the seconds each further five seeds took to train and score.

    uv run python experiments/probe_trust_seeds.py [repeats]

No models; about half an hour.
"""

import sys
import time

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.config import Settings
from roboscriptorium.trustdata import HELD_OUT, SPECS, rows_of, seats, trainable, usable, weighed

SETTINGS = Settings.from_env()
READINGS, SEATS = weighed(SETTINGS), seats(SETTINGS)
REPEATS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
DROP = 0.0025
COUNTS = (1, 5, 10, 15, 20)

books = {n: rows_of(n, SETTINGS) for n in SPECS if not usable(n, SETTINGS)}
names = [n for n in books if trainable(n) and n.split("--")[0] not in HELD_OUT]
rng = np.random.default_rng(1)
drops = [{}] + [
    {n: set(np.flatnonzero(rng.random(len(books[n])) < DROP).tolist()) for n in names}
    for _ in range(REPEATS)
]
# Seconds spent training and scoring seeds 0-4, 5-9, 10-14 and 15-19, over every fold.
spent = [0.0] * (max(COUNTS) // 5)


def run(drop):
    """Per number of seeds: every tuning suspect's version probabilities, in order."""
    out = {k: [] for k in COUNTS}
    for name in names:
        train, of = [], []
        for n in names:
            if n == name:
                continue
            rows = [r for i, r in enumerate(books[n]) if i not in drop.get(n, ())]
            train += rows
            of += [n] * len(rows)
        suspects, right = [r["s"] for r in train], [r["right"] for r in train]
        pairs = trust.pairs_table(suspects, right, of)
        X, y = trust.training_matrix(suspects, right, of, READINGS, SEATS)
        test = books[name]
        Xt, owner = [], []
        for i, r in enumerate(test):
            for k in range(len(r["right"])):
                Xt.append(trust.features(r["s"], k, pairs, READINGS, SEATS))
                owner.append(i)
        Xt = np.array(Xt)
        each = []
        for seed in range(max(COUNTS)):
            began = time.time()
            model = HistGradientBoostingClassifier(
                max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=seed
            )
            each.append(model.fit(X, y).predict_proba(Xt)[:, 1])
            spent[seed // 5] += time.time() - began
        for k in COUNTS:
            p = np.mean(each[:k], axis=0)
            per = [[] for _ in test]
            for v, i in zip(p, owner, strict=True):
                per[i].append(v)
            out[k].append([np.array(v) / max(sum(v), 1e-9) for v in per])
    return out


def outcome(ps_by_book):
    picks, asks, sures, hits = [], [], [], []
    for name, ps in zip(names, ps_by_book, strict=True):
        test = books[name]
        n = sum(r["s"].choice == "review" for r in test)
        sure = np.array([p.max() for p in ps])
        pick = np.array([int(p.argmax()) for p in ps])
        ask = np.zeros(len(ps), bool)
        ask[np.argsort(sure, kind="stable")[:n]] = True
        picks.append(pick)
        asks.append(ask)
        sures.append(sure)
        hits.append(np.array([r["right"][k] for r, k in zip(test, pick, strict=True)]))
    return tuple(np.concatenate(v) for v in (picks, asks, sures, hits))


began = time.time()
runs = []
for at, drop in enumerate(drops):
    runs.append({k: outcome(v) for k, v in run(drop).items()})
    print(f"training {at + 1} of {len(drops)} done, {time.time() - began:.0f}s", flush=True)

total = sum(len(books[n]) for n in names)
folds = len(drops) * len(names)
print(f"{total} suspects in {len(names)} books; {REPEATS} trainings with {DROP:.2%} left out")
print(
    "seconds per training of one arbiter for each further five seeds: "
    + ", ".join(f"{s / folds:.1f}" for s in spent)
)
for k in COUNTS:
    pick0, ask0, sure0, hit0 = runs[0][k]
    silent = [int((~r[k][3] & ~r[k][1]).sum()) for r in runs]
    wrong = [int((~r[k][3]).sum()) for r in runs]
    picks = [int((r[k][0] != pick0).sum()) for r in runs[1:]]
    asks = [int((r[k][1] != ask0).sum()) for r in runs[1:]]
    moved = [float(np.abs(r[k][2] - sure0).mean()) for r in runs[1:]]
    asked = []
    for r in runs:
        curve = trust.calibrate(r[k][2].tolist(), r[k][3].tolist())
        asked.append(int((curve.predict(r[k][2]) < 0.9).sum()))
    print(
        f"{k:2} seeds: wrong picks {wrong[0]} (perturbed {min(wrong[1:])}–{max(wrong[1:])}), "
        f"silent at the rule's questions {silent[0]} (perturbed {min(silent[1:])}–"
        f"{max(silent[1:])}); picks changed {np.mean(picks):.1f} (max {max(picks)}); asked "
        f"changed {np.mean(asks):.1f} (max {max(asks)}); sureness moved {np.mean(moved):.5f}; "
        f"asked under 0.9 {asked[0]} (perturbed {min(asked[1:])}–{max(asked[1:])})"
    )
