"""A book's dash and ellipsis style, measured on the scan or set in book.toml, and written
into every dash and ellipsis.

OCR layers write every dash as an em dash and space it at random, so how a book
prints its dashes is a decision for the whole book, not per line. On the page
image each dash's stroke is a run of columns whose ink is a thin band around
mid-height: about one letter long for an en dash, two for an em dash. The blank
columns either side, against the gaps between words on the same crops, tell
glued from thin from word-spaced dashes.

The output then sets every dash between words that way: a no-break space before
it (narrow for thin gaps) and a breaking one after it. Number ranges (1914–1918)
and hyphens are left alone.

Ellipses are a book-wide choice too: the glyph, three dots or spaced dots, with or
without a space before. OCR layers merge spaced dots and drop the gap before them,
but hardly ever invent gaps (Dutch books with tight dots: at most 1% of their runs
read spaced), so the runs that kept their gaps are the evidence.
"""

import json
import re
import statistics
from dataclasses import asdict, dataclass, replace

import numpy as np
import pymupdf

from roboscriptorium.files import write_atomic
from roboscriptorium.ir import Block, Paragraph

VERSION = 1
DPI = 300
SCALE = DPI / 72
DASHES = "—–"
# An en dash is about one letter long, an em dash two.
EM_FROM = 1.6
# A gap of at most this share of the book's word space is a thin one; one under
# GLUED letters is none at all.
THIN_UNDER = 0.75
GLUED = 0.2
# Enough dashes to settle it; pages are read in order until this many are measured.
ENOUGH = 60
SPACES = {"none": ("", ""), "thin": (" ", " "), "word": (" ", " ")}


@dataclass(frozen=True)
class DashStyle:
    dash: str  # "–" or "—"
    spacing: str  # "none", "thin" or "word"


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


def guess(pdf_path, numbers: list[int], cache) -> Guess | None:
    """The dash style the scan shows, cached; None when it has too few dashes to tell."""
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == VERSION and raw.get("pages") == numbers:
            g = raw["guess"]
            return Guess(DashStyle(**g.pop("style")), **g) if g else None
    found = []
    with pymupdf.open(pdf_path) as pdf:
        for n in numbers:
            if len(found) >= ENOUGH:
                break
            page = pdf[n - 1]
            words = page.get_text("words")
            for w in words:
                if _is_dash(w[4]) or any(c in DASHES for c in w[4]) or "--" in w[4]:
                    line = [v for v in words if v[5] == w[5] and v[6] == w[6]]
                    if (m := _measure(page, w, line)) is not None:
                        found.append(m)
    result = _decide(found)
    blob = {"version": VERSION, "pages": numbers, "guess": asdict(result) if result else None}
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
    """Ink by Otsu's threshold on the crop."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    levels = np.arange(256)
    w0 = np.cumsum(hist)
    w1 = gray.size - w0
    m0 = np.cumsum(hist * levels) / np.maximum(w0, 1)
    m1 = ((hist * levels).sum() - np.cumsum(hist * levels)) / np.maximum(w1, 1)
    return gray <= int(np.argmax(w0 * w1 * (m0 - m1) ** 2))


def _measure(page: pymupdf.Page, word: tuple, line: list[tuple]) -> dict | None:
    """One dash's length and the blank either side, and the word gaps around it, in letters."""
    x0, y0, x1, y1, text = word[:5]
    letters = [w for w in line if w[4].isalpha() and len(w[4]) >= 3]
    if not letters:
        return None
    char_w = statistics.median((w[2] - w[0]) / len(w[4]) for w in letters)
    at = next((i for i, c in enumerate(text) if c in DASHES + "-"), 0)
    expect = x0 + (x1 - x0) * (at + 0.5) / len(text)
    clip = pymupdf.Rect(expect - 8 * char_w, y0, expect + 8 * char_w, y1)
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


def _gap(run, edge: int, width: int, unit: float) -> float | None:
    """A blank run beside the stroke, in letters: 0 when ink touches it, None at the crop's edge."""
    if run is None:
        return 0.0
    if run[0] == 0 or run[1] == width:
        return None
    return (run[1] - run[0]) / unit


def _is_dash(text: str) -> bool:
    return any(c in DASHES for c in text) or text in ("-", "--")


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    out, start = [], None
    for i, f in enumerate([*flags, False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i))
            start = None
    return out


# A dash between words, with whatever spacing the layer gave it; not inside a number range.
_DASH = re.compile(r"(?<![\d])\s*(?:[—–]|--)\s*(?![\d])|(?<=\S) +- +(?=\S)")


def styled(text: str, style: DashStyle) -> tuple[str, list[int]]:
    """The text with every dash between words set in the book's style, and where each of
    the old text's characters went in it.

    Before a closing quote or punctuation, and at a paragraph's start or end, a dash
    takes only the space on its open side.
    """
    before, after = SPACES[style.spacing]
    out, where, pos = [], [], 0
    for m in _DASH.finditer(text):
        for c in text[pos : m.start()]:
            where.append(len("".join(out)))
            out.append(c)
        prev = text[m.start() - 1] if m.start() > 0 else ""
        nxt = text[m.end()] if m.end() < len(text) else ""
        lead = before if prev and prev not in "‘“'\"([" else ""
        trail = after if nxt and nxt not in "’”'\".,;:!?)]…" else ""
        at = len("".join(out)) + len(lead)
        where += [at] * (m.end() - m.start())
        out.append(lead + style.dash + trail)
        pos = m.end()
    for c in text[pos:]:
        where.append(len("".join(out)))
        out.append(c)
    return "".join(out), where


@dataclass(frozen=True)
class EllipsisStyle:
    dots: str  # "…", "..." or ". . ."
    space_before: bool


# Spaced reads are rare noise in a tightly set book, common in a spaced one.
SPACED_FROM = 0.25
# Fewer ellipses than this in the layer leave the book's style unknown.
FEW = 10
# The glyph, or three dots with at most one space between each, with the space before it;
# not part of four dots.
_RUN = re.compile(r"(?<![.…\s])(\s*)(?<![.…] )(…|\.(?: ?\.){2})(?! ?[.…])")
# What opens a quotation or aside: an ellipsis after it takes no space.
_OPENING = "‘“'\"([—–-"


def guess_ellipsis(lines: list[str]) -> EllipsisStyle | None:
    """How the layer's lines set their ellipses, by majority; None when there are too few."""
    runs = []
    for line in lines:
        for m in _RUN.finditer(line):
            if m.start() == 0 or line[m.start() - 1] in _OPENING:
                continue
            runs.append((m.group(2), bool(m.group(1))))
    if len(runs) < FEW:
        return None
    glyphs = [r for r in runs if r[0] == "…"]
    dots = [r for r in runs if r[0] != "…"]
    spaced = [r for r in dots if r[0] == ". . ."]
    if len(glyphs) > len(dots):
        form, votes = "…", glyphs
    elif len(spaced) >= SPACED_FROM * len(dots):
        form, votes = ". . .", spaced
    else:
        form, votes = "...", dots
    return EllipsisStyle(form, 2 * sum(sp for _, sp in votes) > len(votes))


def ellipsised(text: str, style: EllipsisStyle) -> tuple[str, list[int]]:
    """The text with every ellipsis set in the book's style, and where each of the old
    text's characters went in it.

    The space before is set only after a word or closing punctuation, as a no-break
    space, and spaced dots are held together; what follows the ellipsis is left as it is.
    Four dots (a full stop and an ellipsis) are left alone.
    """
    dots = style.dots.replace(" ", "\u00a0")
    out, where, pos = [], [], 0
    for m in _RUN.finditer(text):
        for c in text[pos : m.start()]:
            where.append(len("".join(out)))
            out.append(c)
        prev = text[m.start() - 1] if m.start() > 0 else ""
        lead = m.group(1)
        if prev and prev not in _OPENING:
            lead = "\u00a0" if style.space_before else ""
        at = len("".join(out)) + len(lead)
        where += [at] * (m.end() - m.start())
        out.append(lead + dots)
        pos = m.end()
    for c in text[pos:]:
        where.append(len("".join(out)))
        out.append(c)
    return "".join(out), where


def apply(
    blocks: list[Block], dash: DashStyle | None, ellipsis: EllipsisStyle | None = None
) -> list[Block]:
    """Copies of the paragraphs with their dashes and ellipses styled; italic marks follow
    their words."""
    out = []
    for block in blocks:
        if isinstance(block, Paragraph):
            if dash is not None and any(c in block.text for c in "—–-"):
                block = _restyled(block, styled(block.text, dash))
            if ellipsis is not None and ("…" in block.text or "." in block.text):
                block = _restyled(block, ellipsised(block.text, ellipsis))
        out.append(block)
    return out


def _restyled(block: Paragraph, change: tuple[str, list[int]]) -> Paragraph:
    text, where = change
    if text == block.text:
        return block
    new_words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    token = {i: k for k, (a, b) in enumerate(new_words) for i in range(a, b)}
    old_words = [m for m in re.finditer(r"\S+", block.text)]
    # A bare dash or dot isn't an italic word, though it came from one ("Ulysses—een").
    italic = sorted(
        t
        for t in {
            token[where[i]]
            for k in block.italic
            for i in range(*old_words[k].span())
            if where[i] in token
        }
        if any(c.isalnum() for c in text[slice(*new_words[t])])
    )
    return replace(block, text=text, italic=tuple(italic))
