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
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from rapidfuzz.distance import Levenshtein

from roboscriptorium.evaluate import normalise
from roboscriptorium.files import write_atomic
from roboscriptorium.ocrcheck import Suspect, _typographic
from roboscriptorium.reflow import _SPACE_BEFORE_PUNCTUATION

MODEL_VERSION = 6
# A substitution's prior counts only when the training books that show it number this
# many: one book's reference conventions must not teach every other book.
MIN_BOOKS = 2
# How many golden suspects one of a book's own answered suspects counts as in its
# substitution table (`with_answers`).
ANSWER_WEIGHT = 3
READINGS = ("glm", "tess", "qwen")
# The page readers' readings (`pagereader.py`), when a build makes them.
PAGE_READINGS = ("glm-page", "qwen-page")


def width(readings: tuple[str, ...] = READINGS) -> int:
    """The length of `features` over these readings; a saved model of another width
    can't score them."""
    return 23 + len(readings)


FEATURES = width()
QUOTES = "'\"‘’“”"

# Per substitution (`pair`): how often the version making it was the print, and how
# often it was seen, over the training suspects.
Pairs = dict[str, tuple[int, int]]


@dataclass
class Trust:
    """The trees, the substitution priors they were trained with, and the calibration of
    their sureness: how often a suspect's likeliest version was right, by how sure the
    trees were, on books they weren't trained on (isotonic; None leaves it raw)."""

    model: object
    pairs: Pairs
    calibration: object | None = None
    # The readings whose support it was trained on, in feature order.
    readings: tuple[str, ...] = READINGS


def sureness(trust: Trust, p: np.ndarray) -> float:
    """The chance that the likeliest of these version probabilities is the print."""
    if trust.calibration is None:
        return float(p.max())
    return float(trust.calibration.predict([p.max()])[0])


def calibrate(sure: list[float], right: list[bool]):
    """An isotonic map from the trees' sureness to how often they were right."""
    from sklearn.isotonic import IsotonicRegression

    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    return iso.fit(np.array(sure), np.array(right, dtype=float))


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


def fold(text: str) -> str:
    """Text compared as the score compares it (`evaluate.normalise`: quote and dash
    glyphs, ellipses, spaced dots), with what reflow sets anyway folded too: a break
    hyphen, spaces before punctuation. A space beside a quote mark stays: no stage
    removes it, so the score counts it ("geweest. ‘" is not "geweest.’")."""
    return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", normalise(text.replace("¬", "-")))


def rows_from(suspects: list, truths: dict[tuple, str]) -> list[dict]:
    """Each suspect with a true line, its versions labelled by which comes closest to it."""
    rows = []
    for s in suspects:
        if (truth := truths.get((s.page, s.line, s.start))) is None:
            continue
        versions = [s.ours, *s.others]
        lines = [s.original[: s.start] + v + s.original[s.end :] for v in versions]
        distance = [Levenshtein.distance(fold(line), fold(truth)) for line in lines]
        best = min(distance)
        right = [d == best for d in distance]
        rows.append(
            {
                "suspect": asdict(s),
                "truth": truth,
                "right": right,
                "settled": right.count(True) == 1 and best <= max(2, len(s.ours) // 3),
            }
        )
    return rows


def with_answers(trust: Trust, rows: list[dict], weight: int = ANSWER_WEIGHT) -> Trust:
    """The arbiter with a book's answered suspects (`rows_from`, settled ones) counted
    `weight` times each in its substitution table: a book repeats its own substitutions
    ("we" → "wc", a stress accent), and its reviewer's answers say how they go there."""
    pairs = dict(trust.pairs)
    for r in rows:
        if not r["settled"]:
            continue
        ours = r["suspect"]["ours"]
        for k, v in enumerate(r["suspect"]["others"], 1):
            key = pair(ours, v)
            a, n = pairs.get(key, (0, 0))
            pairs[key] = (a + weight * int(r["right"][k]), n + weight)
    return replace(trust, pairs=pairs)


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


def features(
    s: Suspect, k: int, pairs: Pairs | None = None, readings: tuple[str, ...] = READINGS
) -> list[float]:
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
        *(float(s.support.get(r, ())[k]) if s.support.get(r) else 0.0 for r in readings),
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
    judges = s.judged_by[:3]
    for model in judges + [""] * (3 - len(judges)):
        picked = s.votes.get(model) == v
        c = s.confidence.get(model, 0.0)
        f += [float(picked), c if picked else -c, float(s.votes.get(model) == "")]
        picks.append(picked)
    # Whether the vision and the text judge both pick it.
    f.append(float(all(picks[:2])))
    return f + prior(s, k, pairs or {})


def probabilities(trust: Trust, s: Suspect) -> np.ndarray:
    """Each version's probability of being what the scan prints, summing to one."""
    n = 1 + len(s.others)
    X = np.array([features(s, k, trust.pairs, trust.readings) for k in range(n)])
    p = trust.model.predict_proba(X)[:, 1]
    return p / max(p.sum(), 1e-9)


def training_matrix(
    suspects: list[Suspect],
    right: list[list[bool]],
    books: list[str],
    readings: tuple[str, ...] = READINGS,
) -> tuple[np.ndarray, np.ndarray]:
    """Feature rows and labels for every version of the training suspects. Each book's
    suspects get their priors from the other training books only, as a scored book's
    come from books it isn't in: with its own book's suspects counted in (or only its
    own label left out), a signature common in that book looked surer in training
    than it is on a new book."""
    X, y = [], []
    for book in dict.fromkeys(books):
        others = [i for i, b in enumerate(books) if b != book]
        table = pairs_table(
            [suspects[i] for i in others], [right[i] for i in others], [books[i] for i in others]
        )
        for s, ok, b in zip(suspects, right, books, strict=True):
            if b != book:
                continue
            for k, hit in enumerate(ok):
                X.append(features(s, k, table, readings))
                y.append(int(hit))
    return np.array(X), np.array(y)


def train(
    suspects: list[Suspect],
    right: list[list[bool]],
    books: list[str] | None = None,
    readings: tuple[str, ...] = READINGS,
) -> Trust:
    """Trees over the labelled suspects, with the substitution priors from the same
    (`books` names each suspect's book; without it no pair reaches `MIN_BOOKS`), weighing
    the support of these `readings`."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    books = books or [""] * len(suspects)
    X, y = training_matrix(suspects, right, books, readings)
    pairs = pairs_table(suspects, right, books)
    model = HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )
    return Trust(model.fit(X, y), pairs, readings=readings)


def save(trust: Trust, path: Path) -> None:
    blob = {
        "version": MODEL_VERSION,
        "model": trust.model,
        "pairs": trust.pairs,
        "calibration": trust.calibration,
        "readings": trust.readings,
    }
    write_atomic(path, pickle.dumps(blob))


class Mismatch(RuntimeError):
    """The saved model was trained on other features than these."""


def load(path: Path) -> Trust | None:
    """The saved model, or None when there is no file. A model of another version or
    feature width raises `Mismatch`: it has to be retrained, not silently skipped."""
    if not path.exists():
        return None
    blob = pickle.loads(path.read_bytes())
    model = blob["model"]
    readings = tuple(blob.get("readings", READINGS))
    if blob.get("version") != MODEL_VERSION or model.n_features_in_ != width(readings):
        raise Mismatch(
            f"The trust model {path} is version {blob.get('version')} with "
            f"{model.n_features_in_} features; this code needs version {MODEL_VERSION} with "
            f"{width(readings)}. Retrain it (experiments/train_ocr_trust.py --save) or set "
            "ROBO_OCR_TRUST=0 for the fixed rule."
        )
    return Trust(model, blob.get("pairs", {}), blob.get("calibration"), readings)


def without(path: Path, book: str) -> Path:
    """Where the model trained without `book`'s suspects is kept, beside `path`."""
    return path.with_name(f"{path.stem}-without-{book}{path.suffix}")


def fingerprint(path: Path) -> str:
    """A short hash of the saved model's file, to record which model decided."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def unseen(s: Suspect) -> bool:
    """Whether the vision judge saw none of the versions: the
    readings missed the print (a crop of another line, a misread line). The layer was
    right on 17 of 23 such suspects in the trust data, too few for the trees to learn."""
    judges = s.judged_by
    return bool(judges) and s.votes.get(judges[0]) == ""


def decide(
    suspects: list[Suspect], trust: Trust, questions: int, below: float = 1.0
) -> list[Suspect]:
    """Copies of the suspects with the model's choices: the `questions` it is least sure
    of go to review, unless their likeliest version is right with a chance of `below` or
    more (`sureness`); the others
    take their most likely version. A suspect whose versions the vision judge saw none of
    (`unseen`) is asked first and never takes another reading's version."""
    scored = [(probabilities(trust, s), s) for s in suspects]
    sure = [sureness(trust, p) for p, _ in scored]
    # Calibration is a step function: the raw sureness orders a step's suspects.
    order = sorted(
        range(len(scored)),
        key=lambda i: (not unseen(scored[i][1]), sure[i], scored[i][0].max()),
    )
    # A calibrated sureness can be exactly 1.0, which `below` = 1.0 must still ask.
    asked = {i for i in order[:questions] if unseen(scored[i][1]) or sure[i] < below or below >= 1}
    out = []
    for i, (p, s) in enumerate(scored):
        best = int(p.argmax())
        if i in asked:
            out.append(replace(s, choice="review", chosen=None))
        elif best == 0 or unseen(s):
            out.append(replace(s, choice="ours", chosen=None))
        else:
            out.append(replace(s, choice="other", chosen=s.others[best - 1]))
    return out
