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
read spaced), so the runs that kept their gaps are the evidence in the layer. A layer
that drops every gap says nothing, so the gaps are measured on the scan as well: three
dots are short runs of ink near the baseline, and the blanks before and between them,
against the word gaps on the same line, tell a spaced ellipsis from a tight one.
"""

import json
import re
import statistics
from dataclasses import asdict, dataclass, replace

import numpy as np
import pymupdf

from roboscriptorium.files import write_atomic
from roboscriptorium.ir import Block, Paragraph
from roboscriptorium.pdf import page_words

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
            words = page_words(page)
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


# A dash with whatever spacing the layer gave it, all of it; `_kept` says which stay as read.
_DASH = re.compile(r"\s*(?:[—–]|--)\s*|(?<=\S) +- +(?=\S)")


def _kept(text: str, m: re.Match) -> bool:
    """Whether a dash is part of a number rather than between words: a range, digits on
    both sides however spaced (1914–1918, 1914 – 1918), or a dash glued to a digit (–5)."""
    prev = text[m.start() - 1] if m.start() > 0 else ""
    nxt = text[m.end()] if m.end() < len(text) else ""
    found = m.group()
    glued_left = prev.isdigit() and not found[0].isspace()
    glued_right = nxt.isdigit() and not found[-1].isspace()
    return (prev.isdigit() and nxt.isdigit()) or glued_left or glued_right


def styled(text: str, style: DashStyle) -> tuple[str, list[int]]:
    """The text with every dash between words set in the book's style, and where each of
    the old text's characters went in it.

    Before a closing quote or punctuation, and at a paragraph's start or end, a dash
    takes only the space on its open side.
    """
    before, after = SPACES[style.spacing]
    out, where, pos = [], [], 0
    for m in _DASH.finditer(text):
        if _kept(text, m):
            continue
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
    space (after "?" or "!" as the layer has it), and spaced dots are held together; what
    follows the ellipsis is left as it is.
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
        if prev in "?!":
            # After a question or exclamation mark books space it their own way, mostly
            # with a space even where a word's ellipsis has none: as the layer reads it.
            lead = "\u00a0" if lead else ""
        elif prev and prev not in _OPENING:
            lead = "\u00a0" if style.space_before else ""
        at = len("".join(out)) + len(lead)
        where += [at] * (m.end() - m.start())
        out.append(lead + dots)
        pos = m.end()
    for c in text[pos:]:
        where.append(len("".join(out)))
        out.append(c)
    return "".join(out), where


_BLANK = re.compile(r"_+")


def blanked(text: str, blank: str) -> tuple[str, list[int]]:
    """The text with every printed blank, a run of underscores however many the readers
    saw, set as `blank`, and where each of the old text's characters went in it."""
    out, where, pos = [], [], 0
    for m in _BLANK.finditer(text):
        for c in text[pos : m.start()]:
            where.append(len("".join(out)))
            out.append(c)
        where += [len("".join(out))] * (m.end() - m.start())
        out.append(blank)
        pos = m.end()
    for c in text[pos:]:
        where.append(len("".join(out)))
        out.append(c)
    return "".join(out), where


def apply(
    blocks: list[Block],
    dash: DashStyle | None,
    ellipsis: EllipsisStyle | None = None,
    blank: str | None = None,
) -> list[Block]:
    """Copies of the paragraphs with their dashes, ellipses and printed blanks styled;
    italic marks follow their words. Blanks come last, so the ellipsis style leaves a
    blank set as dots as the book declares it."""
    out = []
    for block in blocks:
        if isinstance(block, Paragraph):
            if dash is not None and any(c in block.text for c in "—–-"):
                block = _restyled(block, styled(block.text, dash))
            if ellipsis is not None and ("…" in block.text or "." in block.text):
                block = _restyled(block, ellipsised(block.text, ellipsis))
            if blank is not None and "_" in block.text:
                block = _restyled(block, blanked(block.text, blank))
        out.append(block)
    return out


def _restyled(block: Paragraph, change: tuple[str, list[int]]) -> Paragraph:
    text, where = change
    if text == block.text:
        return block
    new_words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    token = {i: k for k, (a, b) in enumerate(new_words) for i in range(a, b)}
    old_words = [m.span() for m in re.finditer(r"\S+", block.text)]
    parts = {k: (a, b) for k, a, b in block.italic_parts}
    # Where the old italic characters went: a word's whole span, or its italic part.
    moved = {
        where[i]
        for k in block.italic
        for i in range(
            *(
                (old_words[k][0] + parts[k][0], old_words[k][0] + parts[k][1])
                if k in parts
                else old_words[k]
            )
        )
        if where[i] in token
    }
    italic, italic_parts = [], []
    for t in sorted({token[i] for i in moved}):
        a, b = new_words[t]
        # A bare dash or dot isn't an italic word, though it came from one.
        if not any(c.isalnum() for c in text[a:b]):
            continue
        italic.append(t)
        # A word joined to an upright one by an unspaced dash ("Ulysses—een") is italic
        # only in part: from its first italic letter to its last.
        upright = [i for i in range(a, b) if text[i].isalnum() and i not in moved]
        if upright:
            inside = [i for i in range(a, b) if i in moved and text[i].isalnum()]
            italic_parts.append((t, inside[0] - a, inside[-1] + 1 - a))
    return replace(block, text=text, italic=tuple(italic), italic_parts=tuple(italic_parts))
