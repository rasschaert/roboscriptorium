"""How a scanned book sets its dashes and ellipses, measured on the scan: a dash's length
against the font's letters and the gaps beside it (`guess`), an ellipsis's dots and the
space before it (`measure_ellipses`), each over enough of the book's pages and cached.
`typography.py` sets the text in the style found.
"""

import json
import re
import statistics
from dataclasses import asdict, dataclass

import numpy as np
import pymupdf

from roboscriptorium import ink
from roboscriptorium.files import write_atomic
from roboscriptorium.pdf import page_words
from roboscriptorium.typography import DASHES, DashStyle, EllipsisStyle, _is_dash

VERSION = 2


DPI = 300


SCALE = DPI / 72


# An en dash is about one letter long, an em dash two.
EM_FROM = 1.6


# A gap of at most this share of the book's word space is a thin one; one under
# GLUED letters is none at all.
THIN_UNDER = 0.75


GLUED = 0.2


# Enough dashes to settle it; pages are read in order until this many are measured.
ENOUGH = 60


@dataclass(frozen=True)
class Guess:
    style: DashStyle
    dashes: int  # how many were measured
    length: float  # median length, in letters
    gap: float  # median gap beside a dash, in letters
    word_gap: float  # median gap between words, in letters

    def describe(self) -> str:
        name = {"–": "en", "—": "em"}[self.style.dash]
        return (
            f"{name} dashes, {self.style.spacing} spacing (from {self.dashes} dashes on the "
            f"scan: {self.length:.2f} letters long, gaps {self.gap:.2f} against "
            f"{self.word_gap:.2f} between words)"
        )


def guess(pdf_path, numbers: list[int], cache, pages: list | None = None) -> Guess | None:
    """The dash style the scan shows, cached; None when it has too few dashes to tell.
    Found through the PDF's own words, or on an image-only scan through its first reading's
    (`pages`' words), which are cached apart."""
    texts = {p.number: p for p in pages or []}
    source = "first reading" if any(p.words for p in texts.values()) else "pdf"
    if cache.exists():
        raw = json.loads(cache.read_text())
        same = raw.get("pages") == numbers and raw.get("words", "pdf") == source
        if raw.get("version") == VERSION and same:
            g = raw["guess"]
            return Guess(DashStyle(**g.pop("style")), **g) if g else None
    found = []
    with pymupdf.open(pdf_path) as pdf:
        for n in numbers:
            if len(found) >= ENOUGH:
                break
            page = pdf[n - 1]
            words = page_words(page, texts.get(n))
            for w in words:
                if _is_dash(w[4]) or any(c in DASHES for c in w[4]) or "--" in w[4]:
                    line = [v for v in words if v[5] == w[5] and v[6] == w[6]]
                    if (m := _measure(page, w, line)) is not None:
                        found.append(m)
    result = _decide(found)
    blob = {"version": VERSION, "pages": numbers, "words": source}
    blob["guess"] = asdict(result) if result else None
    write_atomic(cache, json.dumps(blob))
    return result


def _decide(found: list[dict]) -> Guess | None:
    if len(found) < 3:
        return None
    length = statistics.median(m["length"] for m in found)
    gaps = [g for m in found for g in (m["left"], m["right"]) if g is not None]
    word_gaps = [g for m in found for g in m["word_gaps"]]
    if not gaps or not word_gaps:
        return None
    gap, word_gap = statistics.median(gaps), statistics.median(word_gaps)
    if gap < GLUED:
        spacing = "none"
    elif gap < THIN_UNDER * word_gap:
        spacing = "thin"
    else:
        spacing = "word"
    dash = "—" if length >= EM_FROM else "–"
    return Guess(DashStyle(dash, spacing), len(found), length, gap, word_gap)


def _ink(gray: np.ndarray) -> np.ndarray:
    """Ink by Otsu's threshold on the crop, the threshold's own grey included."""
    return gray <= ink.threshold(gray)


def _measure(page: pymupdf.Page, word: tuple, line: list[tuple]) -> dict | None:
    """One dash's length and the blank either side, and the word gaps around it, in letters."""
    x0, y0, x1, y1, text = word[:5]
    letters = [w for w in line if w[4].isalpha() and len(w[4]) >= 3]
    if not letters:
        return None
    char_w = statistics.median((w[2] - w[0]) / len(w[4]) for w in letters)
    at = next((i for i, c in enumerate(text) if c in DASHES + "-"), 0)
    expect = x0 + (x1 - x0) * (at + 0.5) / len(text)
    # The line's height, not the dash's own box: a first reading's box hugs the stroke.
    top, bottom = min(w[1] for w in line), max(w[3] for w in line)
    clip = pymupdf.Rect(expect - 8 * char_w, top, expect + 8 * char_w, bottom)
    pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=pymupdf.csGRAY)
    dark = _ink(np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width))
    h, rows = dark.shape[0], np.arange(dark.shape[0])
    thin, empty = [], []
    for c in range(dark.shape[1]):
        col = rows[dark[:, c]]
        empty.append(len(col) == 0)
        thin.append(
            len(col) > 0 and col[-1] - col[0] <= 0.15 * h and 0.3 * h <= col.mean() <= 0.8 * h
        )
    unit = char_w * SCALE
    strokes = [r for r in _runs(thin) if r[1] - r[0] >= 0.25 * unit]
    if not strokes:
        return None
    centre = (expect - clip.x0) * SCALE
    a, b = min(strokes, key=lambda r: abs((r[0] + r[1]) / 2 - centre))
    blanks = _runs(empty)
    left = next((r for r in blanks if r[1] == a), None)
    right = next((r for r in blanks if r[0] == b), None)
    # Word gaps: the blank run at each boundary between two of the layer's words in the crop.
    word_gaps = []
    for v, w in zip(line, line[1:], strict=False):
        if not v[4].strip(DASHES + "-") or not w[4].strip(DASHES + "-"):
            continue
        at = ((v[2] + w[0]) / 2 - clip.x0) * SCALE
        if 0 < at < len(empty):
            near = [r for r in blanks if r[0] - unit / 2 <= at <= r[1] + unit / 2]
            near = [r for r in near if 0 < r[0] and r[1] < len(empty)]
            if near:
                r = min(near, key=lambda r: abs((r[0] + r[1]) / 2 - at))
                word_gaps.append((r[1] - r[0]) / unit)
    return {
        "length": (b - a) / unit,
        "left": _gap(left, a, len(empty), unit),
        "right": _gap(right, b, len(empty), unit),
        "word_gaps": word_gaps,
    }


def _crop_ink(page: pymupdf.Page, clip: pymupdf.Rect) -> np.ndarray:
    pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=pymupdf.csGRAY)
    return _ink(np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width))


def _gap(run, edge: int, width: int, unit: float) -> float | None:
    """A blank run beside the stroke, in letters: 0 when ink touches it, None at the crop's edge."""
    if run is None:
        return 0.0
    if run[0] == 0 or run[1] == width:
        return None
    return (run[1] - run[0]) / unit


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    out, start = [], None
    for i, f in enumerate([*flags, False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i))
            start = None
    return out


# Measured on the golden scans (decisions.md 2026-10-13): the blank before an ellipsis's
# first dot is at most 0.62 of the word gap where the print sets no space, at least 0.86
# where it does; dots are 0.28–0.63 letters apart when tight, 0.91–1.21 when spaced.
SPACE_BEFORE_FROM = 0.75


SPACED_DOTS_FROM = 0.75


# Ellipses measured to settle it, and the fewest that say anything.
ELLIPSES_ENOUGH = 60


ELLIPSES_FEW = 3


ELLIPSIS_VERSION = 1


# An ellipsis in a word of the layer: the glyph, or three dots with at most a space between.
_IN_WORD = re.compile(r"…|\.\s?\.\s?\.")


@dataclass(frozen=True)
class EllipsisMeasure:
    ellipses: int  # how many were measured
    before: float  # median blank before the first dot, in letters
    between: float  # median blank between dots, in letters
    word_gap: float  # median gap between words on their lines, in letters

    @property
    def space_before(self) -> bool:
        return self.before >= SPACE_BEFORE_FROM * self.word_gap

    @property
    def spaced(self) -> bool:
        return self.between >= SPACED_DOTS_FROM

    def describe(self) -> str:
        return (
            f"{'spaced' if self.spaced else 'tight'} dots, "
            f"{'a' if self.space_before else 'no'} space before (from {self.ellipses} "
            f"ellipses on the scan: {self.before:.2f} letters before, {self.between:.2f} "
            f"between dots, against {self.word_gap:.2f} between words)"
        )


def measure_ellipses(pdf_path, numbers: list[int], cache) -> EllipsisMeasure | None:
    """How the scan spaces its ellipses, cached; None when too few can be measured.

    Only an ellipsis the layer reads right after a letter of the same word ("Ka...",
    "dear . . .") is measured: there the blank before it is the gap the print sets."""
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == ELLIPSIS_VERSION and raw.get("pages") == numbers:
            return EllipsisMeasure(**raw["measure"]) if raw["measure"] else None
    found, gaps = [], []
    with pymupdf.open(pdf_path) as pdf:
        for n in numbers:
            if len(found) >= ELLIPSES_ENOUGH:
                break
            page = pdf[n - 1]
            words = page_words(page)
            for w in words:
                m = _IN_WORD.search(w[4])
                if m is None or m.start() == 0 or not w[4][m.start() - 1].isalpha():
                    continue
                line = [v for v in words if v[5] == w[5] and v[6] == w[6]]
                if (r := _measure_ellipsis(page, w, m.start(), line)) is not None:
                    found.append(r)
                    gaps += _word_gaps(page, line, r["char_w"])
    result = None
    before = [r["before"] for r in found if r["before"] is not None]
    if len(found) >= ELLIPSES_FEW and before and gaps:
        result = EllipsisMeasure(
            len(found),
            statistics.median(before),
            statistics.median(g for r in found for g in r["between"]),
            statistics.median(gaps),
        )
    blob = {
        "version": ELLIPSIS_VERSION,
        "pages": numbers,
        "measure": asdict(result) if result else None,
    }
    write_atomic(cache, json.dumps(blob))
    return result


def _measure_ellipsis(page: pymupdf.Page, word: tuple, at: int, line: list[tuple]) -> dict | None:
    """The blank before an ellipsis's first dot and between its dots, in letters.

    `at` is where the ellipsis starts in the word's text. A dot is a run of inked columns
    narrower than a letter whose ink is a small spot in the line's lower half; the
    ellipsis is the run of exactly three nearest where the layer puts it."""
    x0, y0, x1, y1, text = word[:5]
    letters = [w for w in line if w[4].isalpha() and len(w[4]) >= 3]
    if not letters:
        return None
    char_w = statistics.median((w[2] - w[0]) / len(w[4]) for w in letters)
    expect = x0 + (x1 - x0) * at / len(text)
    clip = pymupdf.Rect(expect - 3 * char_w, y0, expect + 5 * char_w, y1)
    dark = _crop_ink(page, clip)
    h, rows = dark.shape[0], np.arange(dark.shape[0])
    runs = _runs([bool(dark[:, c].any()) for c in range(dark.shape[1])])
    unit = char_w * SCALE

    def dot(r: tuple[int, int]) -> bool:
        ys = rows[dark[:, r[0] : r[1]].any(axis=1)]
        return (
            len(ys) > 0
            and ys[-1] - ys[0] <= 0.22 * h
            and ys.mean() >= 0.5 * h
            and 0.08 * unit <= r[1] - r[0] <= 0.6 * unit
        )

    spots = [dot(r) for r in runs]
    threes = [
        i
        for i in range(1, len(runs) - 2)
        if all(spots[i : i + 3]) and not spots[i - 1] and (i + 3 == len(runs) or not spots[i + 3])
    ]
    if not threes:
        return None
    centre = (expect - clip.x0) * SCALE
    i = min(threes, key=lambda i: abs(runs[i][0] - centre))
    a, b, c = runs[i : i + 3]
    return {
        "before": (a[0] - runs[i - 1][1]) / unit,
        "between": [(b[0] - a[1]) / unit, (c[0] - b[1]) / unit],
        "char_w": char_w,
    }


def _word_gaps(page: pymupdf.Page, line: list[tuple], char_w: float, most: int = 3) -> list[float]:
    """The blank between neighbouring words of a line, in letters, for up to `most` pairs of
    words that end and start with a letter."""
    out = []
    for v, w in zip(line, line[1:], strict=False):
        if len(out) >= most:
            break
        if not v[4][-1:].isalpha() or not w[4][:1].isalpha():
            continue
        dark = _crop_ink(page, pymupdf.Rect(v[2] - 2 * char_w, v[1], w[0] + 2 * char_w, v[3]))
        blanks = _runs([not dark[:, c].any() for c in range(dark.shape[1])])
        inner = [r for r in blanks if 0 < r[0] and r[1] < dark.shape[1]]
        if inner:
            r = max(inner, key=lambda r: r[1] - r[0])
            out.append((r[1] - r[0]) / (char_w * SCALE))
    return out


def scanned_style(
    layer: EllipsisStyle | None, scan: EllipsisMeasure | None
) -> EllipsisStyle | None:
    """The book's ellipsis style: the scan's gaps, with the layer's choice between the glyph
    and three dots where they are tight (on paper the two look alike)."""
    if scan is None:
        return layer
    if scan.spaced:
        dots = ". . ."
    else:
        dots = layer.dots if layer is not None and layer.dots != ". . ." else "..."
    return EllipsisStyle(dots, scan.space_before)
