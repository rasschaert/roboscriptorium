"""Whether a golden pair still measures the pipeline: its text layer against its
reference, no models. A pair whose layer is far from its reference, or whose lines
the aligner can't place, scores the edition more than the build (AGENTS.md,
"Retiring a book")."""

from collections.abc import Container
from dataclasses import dataclass
from statistics import median

from rapidfuzz.distance import Levenshtein

from roboscriptorium.evaluate import _bare_words, normalise
from roboscriptorium.golden import align
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PageText

# A book is suspect past this many times the set's median layer CER, or with more
# than this share of the lines counted unplaced.
CER_FACTOR = 3
UNPLACED_MAX = 0.05


@dataclass(frozen=True)
class Signals:
    cer: float  # placed lines, typography folded
    bare_word: float  # word edits, punctuation ignored
    unplaced: float  # share of the lines counted that the aligner can't place
    headings: int  # placed lines aligned to a reference heading


def measure(
    pages: list[PageText], reference: list[Chapter], counted: Container[SourceRef] | None = None
) -> Signals:
    """The text layer of `pages` against `reference`. Every line is aligned; only those
    in `counted` (all when None) are scored."""
    labels = align.align(pages, reference)
    dist = chars = bad = words = placed = other = headings = 0
    for p in pages:
        for k, line in enumerate(p.lines):
            ref = SourceRef(p.number, k)
            if counted is not None and ref not in counted:
                continue
            truth = labels[ref]
            if truth.role == "other":
                other += 1
                continue
            headings += truth.role == "heading"
            got, want = normalise(line.text), normalise(truth.truth)
            dist += Levenshtein.distance(got, want)
            chars += len(want)
            gw, ww = _bare_words(got), _bare_words(want)
            bad += Levenshtein.distance(gw, ww)
            words += len(ww)
            placed += 1
    return Signals(
        dist / max(1, chars), bad / max(1, words), other / max(1, placed + other), headings
    )


def suspects(books: dict[str, Signals]) -> dict[str, list[str]]:
    """Per book past a threshold, why: its CER against the set's median, or its
    unplaced share."""
    usual = median(s.cer for s in books.values()) if books else 0.0
    out = {}
    for name, s in books.items():
        why = []
        if usual and s.cer > CER_FACTOR * usual:
            why.append(f"layer CER {s.cer:.2%} > {CER_FACTOR}× the set's {usual:.2%}")
        if s.unplaced > UNPLACED_MAX:
            why.append(f"{s.unplaced:.1%} of body lines unplaced")
        if why:
            out[name] = why
    return out
