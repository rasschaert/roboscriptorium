"""How far the arbiter's asking point moves between retrainings, by calibration.

Reads what `probe_trust_variance.py` kept: per training (the full one, then each with
0.25% of the suspects left out) every tuning suspect's sureness from the other books'
arbiter and whether its pick was right. Each calibration maps sureness to the chance
of being right; a suspect under 0.9 is asked. Per calibration: the questions and the
errors left unasked for each training, and their spread.

    uv run python experiments/probe_trust_calibration.py

No models; seconds.
"""

from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

OUT = Path("work/probes/trust-variance")
BELOW = 0.9


def isotonic(sure, hit):
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(sure, hit)
    return iso.predict


def bagged(sure, hit, bags=50):
    """Isotonic maps of bootstrap samples, averaged."""
    rng = np.random.default_rng(0)
    maps = []
    for _ in range(bags):
        pick = rng.integers(0, len(sure), len(sure))
        maps.append(isotonic(sure[pick], hit[pick]))
    return lambda s: np.mean([m(s) for m in maps], axis=0)


def logit(s):
    s = np.clip(s, 1e-6, 1 - 1e-6)
    return np.log(s / (1 - s))


def platt(sure, hit):
    """A logistic curve over the sureness's log odds."""
    model = LogisticRegression(C=1e6, max_iter=1000).fit(logit(sure)[:, None], hit)
    return lambda s: model.predict_proba(logit(s)[:, None])[:, 1]


CALIBRATIONS = {"isotonic (as made)": isotonic, "50 isotonic maps averaged": bagged, "logistic": platt}

for path in sorted(OUT.glob("variant-*.npz")):
    kept = np.load(path)
    print(f"{path.name}: {len(kept['sure'])} trainings of {kept['sure'].shape[1]} suspects")
    for label, make in CALIBRATIONS.items():
        asked, unasked = [], []
        for sure, hit in zip(kept["sure"], kept["hit"].astype(float), strict=True):
            ask = make(sure, hit)(sure) < BELOW
            asked.append(int(ask.sum()))
            unasked.append(int(((hit == 0) & ~ask).sum()))
        print(
            f"  {label}: asked {asked[0]}, perturbed {min(asked[1:])}–{max(asked[1:])} "
            f"(sd {np.std(asked):.0f}); unasked errors {unasked[0]}, perturbed "
            f"{min(unasked[1:])}–{max(unasked[1:])} (sd {np.std(unasked):.1f})"
        )
