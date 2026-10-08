"""Learned trust for the OCR check: how likely each version of a suspect is what the scan prints.

A model trained on golden books' suspects (each version labelled from the aligned
printed truth) scores each version from what the judges picked and how sure they
were, which second readings read it, whether the word list knows it, what kind
of difference it is, and a prior for the exact substitution it makes (`pair`: a
scan's errors are a few signatures, '|' for 'I' or a lost '’', nearly deterministic
across books). A book's suspects are then ranked by how sure the model is of
its best version: the least sure are asked, up to a budget of questions, and the
rest take their best version.
"""

import difflib
import hashlib
import math
import pickle
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from roboscriptorium.ocrcheck import Suspect, _typographic

MODEL_VERSION = 3
# The length of `features`; a saved model of another width can't score them.
FEATURES = 23
# A substitution's prior counts only when the training books that show it number this
# many: one book's reference conventions must not teach every other book.
MIN_BOOKS = 2
READINGS = ("glm", "tess", "qwen")
QUOTES = "'\"‘’“”"

# Per substitution (`pair`): how often the version making it was the print, and how
# often it was seen, over the training suspects.
Pairs = dict[str, tuple[int, int]]


@dataclass
class Trust:
    """The trees and the substitution priors they were trained with."""

    model: object
    pairs: Pairs


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _letters(text: str) -> str:
    return "".join(c for c in text if c.isalnum())


def pair(ours: str, other: str) -> str:
    """The substitution between the layer's version and another: each differing stretch,
    from → to ("'|'→'I'", "''→'’'"); "=" when they are the same."""
    sm = difflib.SequenceMatcher(None, ours, other, autojunk=False)
    parts = [
        f"{ours[i1:i2]!r}→{other[j1:j2]!r}"
        for tag, i1, i2, j1, j2 in sm.get_opcodes()
        if tag != "equal"
    ]
    return "|".join(parts) or "="


def pairs_table(suspects: list[Suspect], right: list[list[bool]], books: list[str]) -> Pairs:
    """The substitution priors from labelled suspects (`books` names each one's book),
    pairs seen in fewer than `MIN_BOOKS` books left out."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    seen_in: dict[str, set[str]] = defaultdict(set)
    for s, ok, book in zip(suspects, right, books, strict=True):
        for k, v in enumerate(s.others, 1):
            key = pair(s.ours, v)
            counts[key][0] += ok[k]
            counts[key][1] += 1
            seen_in[key].add(book)
    return {k: (a, n) for k, (a, n) in counts.items() if len(seen_in[k]) >= MIN_BOOKS}


def prior(s: Suspect, k: int, pairs: Pairs) -> list[float]:
    """Version k's prior: how often its substitution was the print (Laplace-smoothed,
    0.5 unseen) and log(1 + times seen). The layer's own version gets its strongest
    rival's prior, inverted."""

    def look(key: str) -> tuple[float, float]:
        a, n = pairs.get(key, (0, 0))
        return (a + 1) / (n + 2), math.log1p(n)

    if k == 0:
        rivals = [look(pair(s.ours, v)) for v in s.others]
        p, n = max(rivals, key=lambda t: t[0]) if rivals else (0.5, 0.0)
        return [1 - p, n]
    return list(look(pair(s.ours, s.others[k - 1])))


def features(s: Suspect, k: int, pairs: Pairs | None = None) -> list[float]:
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
    return f + prior(s, k, pairs or {})


def probabilities(trust: Trust, s: Suspect) -> np.ndarray:
    """Each version's probability of being what the scan prints, summing to one."""
    n = 1 + len(s.others)
    X = np.array([features(s, k, trust.pairs) for k in range(n)])
    p = trust.model.predict_proba(X)[:, 1]
    return p / max(p.sum(), 1e-9)


def training_matrix(
    suspects: list[Suspect], right: list[list[bool]], pairs: Pairs
) -> tuple[np.ndarray, np.ndarray]:
    """Feature rows and labels for every version of the training suspects. Each suspect
    is scored with its own labels left out of `pairs`: counted in, the prior repeats the
    label and the trees learn to lean on it."""
    counts = {k: list(v) for k, v in pairs.items()}
    X, y = [], []
    for s, ok in zip(suspects, right, strict=True):
        own = [(pair(s.ours, v), ok[k]) for k, v in enumerate(s.others, 1)]
        for key, hit in own:
            if key in counts:
                counts[key][0] -= hit
                counts[key][1] -= 1
        table = {k: (a, n) for k, (a, n) in counts.items()}
        for k, hit in enumerate(ok):
            X.append(features(s, k, table))
            y.append(int(hit))
        for key, hit in own:
            if key in counts:
                counts[key][0] += hit
                counts[key][1] += 1
    return np.array(X), np.array(y)


def train(
    suspects: list[Suspect], right: list[list[bool]], books: list[str] | None = None
) -> Trust:
    """Trees over the labelled suspects, with the substitution priors from the same
    (`books` names each suspect's book; without it no pair reaches `MIN_BOOKS`)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    pairs = pairs_table(suspects, right, books or [""] * len(suspects))
    X, y = training_matrix(suspects, right, pairs)
    model = HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )
    return Trust(model.fit(X, y), pairs)


def save(trust: Trust, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        pickle.dumps({"version": MODEL_VERSION, "model": trust.model, "pairs": trust.pairs})
    )


class Mismatch(RuntimeError):
    """The saved model was trained on other features than these."""


def load(path: Path) -> Trust | None:
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
    return Trust(model, blob.get("pairs", {}))


def without(path: Path, book: str) -> Path:
    """Where the model trained without `book`'s suspects is kept, beside `path`."""
    return path.with_name(f"{path.stem}-without-{book}{path.suffix}")


def fingerprint(path: Path) -> str:
    """A short hash of the saved model's file, to record which model decided."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def decide(suspects: list[Suspect], trust: Trust, questions: int) -> list[Suspect]:
    """Copies of the suspects with the model's choices: the `questions` it is least sure
    of go to review, the others take their most likely version."""
    scored = [(probabilities(trust, s), s) for s in suspects]
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
