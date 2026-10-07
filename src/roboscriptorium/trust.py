"""Learned trust for the OCR check: how likely each version of a suspect is what the scan prints.

A model trained on golden books' suspects (each version labelled from the aligned
printed truth) scores each version from what the judges picked and how sure they
were, which second readings read it, whether the word list knows it, and what kind
of difference it is. A book's suspects are then ranked by how sure the model is of
its best version: the least sure are asked, up to a budget of questions, and the
rest take their best version.
"""

import hashlib
import pickle
import unicodedata
from dataclasses import replace
from pathlib import Path

import numpy as np

from roboscriptorium.ocrcheck import Suspect, _typographic

MODEL_VERSION = 2
# The length of `features`; a saved model of another width can't score them.
FEATURES = 21
READINGS = ("glm", "tess", "qwen")
QUOTES = "'\"‘’“”"


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _letters(text: str) -> str:
    return "".join(c for c in text if c.isalnum())


def features(s: Suspect, k: int) -> list[float]:
    """Version k of a suspect (0 is the text layer's), as the model sees it."""
    versions = [s.ours, *s.others]
    v, ours = versions[k], s.ours
    strip = str.maketrans("", "", QUOTES)
    known = s.known[k] if s.known else None
    others_known = [x for i, x in enumerate(s.known) if i != k]
    f = [
        float(k == 0),
        float(len(versions)),
        float(_typographic(versions)),
        *(float(s.support.get(r, ())[k]) if s.support.get(r) else 0.0 for r in READINGS),
        {True: 1.0, False: 0.0, None: 0.5}[known],
        float(known is True and bool(others_known) and all(x is False for x in others_known)),
        float(v.replace(" ", "") == ours.replace(" ", "") and v != ours),
        float(v.translate(strip) == ours.translate(strip) and v != ours),
        float(_letters(v) == _letters(ours) and v != ours),
        float(_plain(v) == _plain(ours) and v != ours),
        float(v.lower() == ours.lower() and v != ours),
        float(len(v) - len(ours)),
    ]
    picks = []
    # The judges by role, as `ocrcheck` records them: the vision judge, then the text judge.
    judges = [m for m in s.votes if m != "word list"][:2]
    for model in judges + [""] * (2 - len(judges)):
        picked = s.votes.get(model) == v
        c = s.confidence.get(model, 0.0)
        f += [float(picked), c if picked else -c, float(s.votes.get(model) == "")]
        picks.append(picked)
    f.append(float(all(picks)))
    return f


def probabilities(model, s: Suspect) -> np.ndarray:
    """Each version's probability of being what the scan prints, summing to one."""
    n = 1 + len(s.others)
    p = model.predict_proba(np.array([features(s, k) for k in range(n)]))[:, 1]
    return p / max(p.sum(), 1e-9)


def train(suspects: list[Suspect], right: list[list[bool]]):
    from sklearn.ensemble import HistGradientBoostingClassifier

    X = [features(s, k) for s in suspects for k in range(1 + len(s.others))]
    y = [int(ok) for r in right for ok in r]
    model = HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )
    return model.fit(np.array(X), np.array(y))


def save(model, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps({"version": MODEL_VERSION, "model": model}))


class Mismatch(RuntimeError):
    """The saved model was trained on other features than these."""


def load(path: Path):
    """The saved model, or None when there is no file. A model of another version or
    feature width raises `Mismatch`: it has to be retrained, not silently skipped."""
    if not path.exists():
        return None
    blob = pickle.loads(path.read_bytes())
    model = blob["model"]
    if blob.get("version") != MODEL_VERSION or model.n_features_in_ != FEATURES:
        raise Mismatch(
            f"The trust model {path} is version {blob.get('version')} with "
            f"{model.n_features_in_} features; this code needs version {MODEL_VERSION} with "
            f"{FEATURES}. Retrain it (experiments/train_ocr_trust.py --save) or set "
            "ROBO_OCR_TRUST=0 for the fixed rule."
        )
    return model


def fingerprint(path: Path) -> str:
    """A short hash of the saved model's file, to record which model decided."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def decide(suspects: list[Suspect], model, questions: int) -> list[Suspect]:
    """Copies of the suspects with the model's choices: the `questions` it is least sure
    of go to review, the others take their most likely version."""
    scored = [(probabilities(model, s), s) for s in suspects]
    order = sorted(range(len(scored)), key=lambda i: scored[i][0].max())
    asked = set(order[:questions])
    out = []
    for i, (p, s) in enumerate(scored):
        best = int(p.argmax())
        if i in asked:
            out.append(replace(s, choice="review", chosen=None))
        elif best == 0:
            out.append(replace(s, choice="ours", chosen=None))
        else:
            out.append(replace(s, choice="other", chosen=s.others[best - 1]))
    return out
