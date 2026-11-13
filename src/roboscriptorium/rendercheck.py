"""Render and compare: a judge that knows no language. Each version of a suspect is drawn
in the book's typeface, at the book's size, and laid over the scan's ink; the version
that fits best gets the vote; how well it fits and its margin over the next make its
confidence (`sureness`).

The typeface is found from the scan (`match`): words of the text layer are cut out along
their ink, drawn in every font of a library, and the fonts ranked by how well the
drawings lie over the ink; the best few are then ranked again by the judge's own fit on
plain words, which tells apart faces whose word shapes tie. The library is a folder of
OpenType and TrueType files (`Settings.fonts`), out of git.

The judge (`Judge`) answers the vision judges' question (`ocrcheck._decide`) from the
suspect's page and box alone, so it sits beside them as one more vote for the arbiter.
"""

import json
import math
import random
import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pymupdf
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import fftconvolve

from roboscriptorium import pdf as pdflayer
from roboscriptorium.clients.decide import Answer
from roboscriptorium.files import write_atomic
from roboscriptorium.pdf import PageText

# The judges' names among the second vision judges (`ROBO_ALARM_MODEL=…,render`): the
# whole place's fit, and the two best-fitting versions compared where they differ.
MODEL = "render"
DIFFER = "render-differ"
MODELS = (MODEL, DIFFER)
# The cached match's format.
VERSION = 2
# How a place is cut and drawn: part of the judge's answers' cache key.
FITS = 7
DPI = 400
# The size, in pixels an em, that drawings are made at before scaling to the scan.
RENDER_PX = 96
WORDS = 240
FIRST_PASS = 40
KEPT = 40
# The best text cuts of the word-shape ranking, which the judge's own fit chooses among.
NEAR = 5
# Plain words of the layer that choice is made on.
SETTLE_WORDS = 150
STRETCHES = (0.92, 0.96, 1.0, 1.04, 1.08)
# Ink spread: a drawing's strokes thinned or thickened by this many scan pixels.
SPREADS = (-3, 0, 3, 5)
# A blank this wide, in line heights, parts a word from its neighbour.
WORD_GAP = 0.2
# Ink no wider and hardly taller than this, in line heights, is a dot.
DOT = 0.16
# An ellipsis set with its dots apart: the blank between two dots, in ems.
DOT_GAPS = (0.08, 0.16, 0.26, 0.4)
# A closing quote set over the stop before it, as some books kern it: how far left, in ems.
KERNS = (-0.12, -0.22, -0.32)
# Small capitals drawn as capitals at this share of their size.
SMALL_CAPS = (0.74, 0.82)
# An ordinal's ending set as a superscript ("14ᵉ"): its share of the size, and how far
# up, in ems.
SUPERSCRIPT = ((0.6, 0.3), (0.7, 0.25))
# How sure a pick is: a logistic model of whether it is the print, from the best version's
# fit and the logarithm of its margin over the next (intercept, fit, log margin), fitted
# on labelled places by `experiments/render_confidence.py`.
SURENESS = (-1.007, 6.903, 0.718)
# Which of two versions is the print, from where their drawings differ: a logistic model
# of the first's less the second's share of drawing without ink under it and of ink it
# doesn't draw (no intercept: the order means nothing), fitted on labelled places by
# `experiments/probe_render_difference.py --fit`.
DIFFERENCE = (-5.061, -19.857)
# Drawings differ where their darkness is this far apart (of 255).
APART = 64
# A place this many times taller than the book's lines is set in display type (a chapter
# heading), which the judge, drawing at the text's size, can't compare.
DISPLAY = 1.3
_NOT_TEXT = re.compile(r"Bold|Black|Semibold|Demi|Italic|Heavy", re.I)
_PLAIN = re.compile(r"regular|roman", re.I)
_STOP_QUOTE = re.compile(r"([.,…])([’”'\"])")
_CAPITALS = re.compile(r"[A-ZÀ-Þ]{2,}")
_DOTS = re.compile(r"\.\.\.|…")
_ORDINAL = re.compile(r"(?<=\d)(?:e|de|ste)\b")
_BLUR = ImageFilter.GaussianBlur(1.5)


def other_figures(path: Path) -> list[dict[int, int]]:
    """The font's figures other than its default ones (old-style, or lining where the
    default is old-style), each set as a translation of the digits to the code points
    the font keeps them at. Only sets the font gives code points (Adobe's fonts do, in
    the private-use area) can be drawn: the drawing library applies no font features."""
    try:
        font = TTFont(path, lazy=True)
        gsub, cmap = font["GSUB"].table, font.getBestCmap()
    except Exception:  # noqa: BLE001  (a font without the table, or one fontTools can't read)
        return []
    codes = {name: code for code, name in cmap.items()}
    digits = {cmap[ord(d)]: ord(d) for d in "0123456789" if ord(d) in cmap}
    sets = []
    for tag in ("onum", "lnum"):
        figures = {}
        for record in gsub.FeatureList.FeatureRecord:
            if record.FeatureTag != tag:
                continue
            for index in record.Feature.LookupListIndex:
                for sub in gsub.LookupList.Lookup[index].SubTable:
                    mapping = getattr(getattr(sub, "ExtSubTable", sub), "mapping", {})
                    for plain, other in mapping.items():
                        if plain in digits and other in codes:
                            figures[digits[plain]] = codes[other]
        if len(figures) == 10 and figures not in sets:
            sets.append(figures)
    return sets


class Face:
    """A font, drawn at any size. `load(px)` gives it at `px` pixels an em; `figures`
    are its other sets of digits (`other_figures`)."""

    def __init__(self, load, figures: list[dict[int, int]] = ()):
        self._load = load
        self._cuts: dict[int, ImageFont.FreeTypeFont] = {}
        self.figures = list(figures)

    @classmethod
    def from_file(cls, path: Path) -> "Face":
        return cls(lambda px: ImageFont.truetype(str(path), px), other_figures(path))

    def at(self, scale: float = 1.0) -> ImageFont.FreeTypeFont:
        px = round(RENDER_PX * scale)
        if px not in self._cuts:
            self._cuts[px] = self._load(px)
        return self._cuts[px]


@dataclass(frozen=True)
class Match:
    """A book's typeface: the library's file, how well it fits the scan's words (0–1), the
    ink spread it fits at, and the book's type size in scan pixels an em."""

    file: str
    name: str
    fit: float
    spread: int
    size: float

    @property
    def fingerprint(self) -> str:
        return f"{FITS}:{self.file}:{self.spread}:{self.size:.1f}"


def _levelled(grey: np.ndarray) -> np.ndarray | None:
    """Darkness (0–1, paper 0, the darkest ink 1); None when the image holds no ink."""
    paper, dark = np.percentile(grey, 20), grey.max()
    if dark - paper < 0.25:
        return None
    return np.clip((grey - paper) / (dark - paper), 0, 1).astype(np.float32)


def _trimmed(grey: np.ndarray) -> np.ndarray | None:
    mask = grey > 0.5
    if mask.sum() < 20:
        return None
    rows, cols = np.where(mask.any(1))[0], np.where(mask.any(0))[0]
    return grey[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def _darkness(image: Image.Image) -> np.ndarray:
    return 1.0 - np.asarray(image.convert("L"), dtype=np.float32) / 255.0


def _picture(ink: np.ndarray) -> Image.Image:
    return Image.fromarray((ink * 255).astype(np.uint8))


def _clip_ink(page: pymupdf.Page, clip: pymupdf.Rect) -> np.ndarray | None:
    pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=pymupdf.csGRAY)
    grey = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    return _levelled(1.0 - grey / 255.0)


def word_ink(page: pymupdf.Page, word: tuple) -> np.ndarray | None:
    """A layer word's ink, trimmed to it: its box grown to the blank columns and rows
    around its ink, since layer boxes cut through letters or stop short of them."""
    high = word[3] - word[1]
    clip = pymupdf.Rect(
        word[0] - high * 1.5, word[1] - high * 0.3, word[2] + high * 1.5, word[3] + high * 0.3
    )
    clip &= page.rect
    grey = _clip_ink(page, clip)
    if grey is None:
        return None
    scale, inset = DPI / 72, high * 0.25
    left, right = round((word[0] - clip.x0) * scale), round((word[2] - clip.x0) * scale)
    top = round((word[1] + inset - clip.y0) * scale)
    bottom = round((word[3] - inset - clip.y0) * scale)
    mask = grey > 0.5
    height = bottom - top
    rows = mask[:, left:right].any(1)
    while top > 0 and rows[top - 1]:
        top -= 1
    while bottom < len(rows) and rows[bottom]:
        bottom += 1
    cols = mask[top:bottom].any(0)
    gap = max(3, round(height * 0.16))
    while left > 0 and cols[max(0, left - gap) : left].any():
        left -= 1
    while right < len(cols) and cols[right : right + gap].any():
        right += 1
    if left == 0 or right == len(cols):
        return None
    return _trimmed(grey[top:bottom, left:right])


def scan_words(pdf: Path, pages: list[PageText], count: int) -> list[tuple[str, np.ndarray]]:
    """Plain lower-case words of five letters or more, with their ink, from up to twelve
    of `pages`, away from their ends where there are enough. An image-only page's words
    are its first reading's."""
    rng = random.Random(0)
    inner = pages[2:-2] or pages
    sample = rng.sample(inner, min(12, len(inner)))
    found = []
    with pdflayer.PDF_LOCK, pymupdf.open(pdf) as doc:
        for text in sample:
            page = doc[text.number - 1]
            words = [
                w
                for w in pdflayer.page_words(page, text)
                if len(w[4]) >= 5 and w[4].isalpha() and w[4].islower() and w[4].isascii()
            ]
            for w in rng.sample(words, min(len(words), count // len(sample) + 4)):
                cut = word_ink(page, w)
                if cut is not None and cut.shape[0] > 20:
                    found.append((w[4], cut))
    rng.shuffle(found)
    return found[:count]


def drawn(font: ImageFont.FreeTypeFont, word: str) -> np.ndarray | None:
    """A word's ink as the font draws it, trimmed to it."""
    box = font.getbbox(word)
    if box[2] - box[0] < 4:
        return None
    image = Image.new("L", (box[2] - box[0] + 8, RENDER_PX * 2), 255)
    ImageDraw.Draw(image).text((4 - box[0], RENDER_PX // 3), word, font=font, fill=0)
    grey = _levelled(_darkness(image))
    return None if grey is None else _trimmed(grey)


def _spread(image: Image.Image, spread: int) -> Image.Image:
    if spread > 0:
        return image.filter(ImageFilter.MaxFilter(spread))
    if spread < 0:
        return image.filter(ImageFilter.MinFilter(-spread))
    return image


def word_fit(scan: np.ndarray, glyphs: np.ndarray, stretch: float, spread: int = 0) -> float:
    """How well a drawn word lies over the scan's, 0–1: their correlation with the
    drawing scaled to the scan word's height, both blurred a little, left edges together."""
    h = scan.shape[0]
    w = max(2, round(glyphs.shape[1] * h / glyphs.shape[0] * stretch))
    sized = _spread(_picture(glyphs).resize((w, h), Image.BILINEAR), spread)
    mine = np.asarray(sized.filter(_BLUR), dtype=np.float32)
    theirs = np.asarray(_picture(scan).filter(_BLUR), dtype=np.float32)
    width = max(w, theirs.shape[1])
    a, b = np.zeros((h, width), np.float32), np.zeros((h, width), np.float32)
    a[:, :w], b[:, : theirs.shape[1]] = mine, theirs
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))


def _score(font, words, stretches, spreads) -> tuple[float, int]:
    """The font's mean fit over the words at its best stretch and spread, and that spread."""
    best = (0.0, 0)
    pictures = [(scan, drawn(font, word)) for word, scan in words]
    for stretch in stretches:
        for spread in spreads:
            fits = [word_fit(s, g, stretch, spread) if g is not None else 0.0 for s, g in pictures]
            best = max(best, (float(np.mean(fits)), spread))
    return best


def library_fonts(library: Path) -> dict[str, ImageFont.FreeTypeFont]:
    """The library's fonts that draw Latin letters of their own (no symbol or fallback
    face), by their path within it."""
    fonts = {}
    for path in sorted(library.rglob("*")):
        if path.suffix.lower() not in (".otf", ".ttf"):
            continue
        try:
            font = ImageFont.truetype(str(path), RENDER_PX)
            shapes = {font.getmask(c).getbbox() for c in "aegkmx"}
        except Exception:  # noqa: BLE001  (a file FreeType cannot read is no font)
            continue
        if len(shapes) >= 5 and None not in shapes:
            fonts[str(path.relative_to(library))] = font
    return fonts


def _is_text(entry: dict) -> bool:
    return not _NOT_TEXT.search(entry["name"]) or bool(_PLAIN.search(Path(entry["file"]).stem))


def text_cut(ranked: list[dict]) -> dict:
    """Of fonts ranked by fit, the best that is a text cut: neither bold nor italic by its
    name, or regular by its file's."""
    return next((entry for entry in ranked if _is_text(entry)), ranked[0])


def near_ties(ranked: list[dict], count: int = NEAR) -> list[dict]:
    """The best `count` text cuts of fonts ranked by fit, best first; the best font alone
    where none is a text cut."""
    return [entry for entry in ranked if _is_text(entry)][:count] or ranked[:1]


def word_strips(pdf: Path, pages: list[PageText], count: int) -> list[tuple[str, np.ndarray]]:
    """Plain words of four letters or more from up to fifteen of `pages`, each with its
    ink as the judge cuts a place (`place_ink`)."""
    rng = random.Random(1)
    found = []
    with pdflayer.PDF_LOCK, pymupdf.open(pdf) as doc:
        sample = rng.sample(pages, min(15, len(pages)))
        for text in sample:
            page = doc[text.number - 1]
            words = [
                w for w in pdflayer.page_words(page, text) if len(w[4]) >= 4 and w[4].isalpha()
            ]
            for w in rng.sample(words, min(len(words), count // len(sample) + 4)):
                ink = place_ink(page, w[:4], text)
                if ink is not None:
                    found.append((w[4], ink))
    rng.shuffle(found)
    return found[:count]


def place_fit(
    face: "Face", spread: int, size: float, strips: list[tuple[str, np.ndarray]]
) -> float:
    """How well a face draws the book's plain words, as the judge fits a version (`fits`):
    the mean over `strips`, 0 without any."""
    if not strips:
        return 0.0
    return float(np.mean([fits(face, spread, size, ink, [word])[0] for word, ink in strips]))


def em_size(words: list[tuple[str, np.ndarray]], font: ImageFont.FreeTypeFont) -> float:
    """The book's type size in scan pixels an em: what the font must be drawn at."""
    ratios = [
        ink.shape[0] / glyphs.shape[0]
        for word, ink in words
        if (glyphs := drawn(font, word)) is not None
    ]
    return RENDER_PX * float(np.median(ratios))


def match(
    pdf: Path,
    pages: list[PageText],
    library: Path,
    cache: Path | None = None,
    typeface: str | None = None,
) -> Match:
    """The book's typeface among the library's fonts, by the scan's words on `pages`:
    every font on a few words, the best on all of them, and of those the best few text
    cuts on how the judge itself fits plain words (`place_fit`). `typeface`, a font file
    in the library (book.toml's key), is taken instead of a choice. A match in `cache`
    is kept whatever pages it was made from: a book is set in one typeface, and a slice
    of it must be judged as the whole is."""
    key = {"version": VERSION, "typeface": typeface}
    if cache is not None and cache.exists():
        held = json.loads(cache.read_text())
        if held.get("key") == key and (library / held["match"]["file"]).exists():
            return Match(**held["match"])
    if typeface is not None and not (library / typeface).is_file():
        raise ValueError(f"book.toml's typeface {typeface!r} is no file in {library}")
    fonts = (
        library_fonts(library)
        if typeface is None
        else {typeface: ImageFont.truetype(str(library / typeface), RENDER_PX)}
    )
    words = scan_words(pdf, pages, WORDS)
    if not fonts or not words:
        raise ValueError(
            f"no typeface to match: {len(fonts)} fonts in {library}, {len(words)} words"
        )
    quick = sorted(
        (
            (_score(f, words[:FIRST_PASS], (1.0, 0.94, 1.06), (0, 3))[0], n)
            for n, f in fonts.items()
        ),
        reverse=True,
    )
    ranked = []
    for _, name in quick[:KEPT]:
        fit, spread = _score(fonts[name], words, STRETCHES, SPREADS)
        ranked.append(
            {"file": name, "name": " ".join(fonts[name].getname()), "fit": fit, "spread": spread}
        )
    ranked.sort(key=lambda e: -e["fit"])
    near = near_ties(ranked)
    strips = word_strips(pdf, pages, SETTLE_WORDS) if len(near) > 1 else []
    for entry in near:
        entry["size"] = em_size(words[:80], fonts[entry["file"]])
        entry["place_fit"] = place_fit(
            Face.from_file(library / entry["file"]), entry["spread"], entry["size"], strips
        )
    # `max` keeps the first of equals: the better word shapes.
    entry = max(near, key=lambda e: e["place_fit"])
    found = Match(
        entry["file"],
        entry["name"],
        round(entry["fit"], 4),
        entry["spread"],
        round(entry["size"], 2),
    )
    if cache is not None:
        tried = [
            {"file": e["file"], "name": e["name"], "fit": round(e["fit"], 4),
             "place_fit": round(e["place_fit"], 4)}
            for e in near
        ]  # fmt: skip
        write_atomic(
            cache, json.dumps({"key": key, "match": asdict(found), "near": tried}, indent=1)
        )
    return found


def near(cache: Path) -> list[dict]:
    """The faces a cached match chose among, best word shapes first: each its file, name,
    word fit and the judge's fit on plain words."""
    return json.loads(cache.read_text()).get("near", []) if cache.exists() else []


def place_ink(page: pymupdf.Page, box, text: PageText | None = None) -> np.ndarray | None:
    """The ink at a suspect's box, as a strip of its line (0–1, not trimmed): everything
    between the blank before the layer's words there and the blank after them, so a mark
    the layer missed beside a word is in it and its neighbours' letters aren't. Where a
    line is set too tight for such a blank, the strip ends at the widest blank before
    the layer's next word. On an image-only page the words are its first reading's
    (`text`). None where there are no words."""
    bx0, by0, bx1, by1 = box
    words = pdflayer.page_words(page, text)
    span = [
        w
        for w in words
        if bx0 - 1 <= (w[0] + w[2]) / 2 <= bx1 + 1 and by0 <= (w[1] + w[3]) / 2 <= by1
    ]
    if not span:
        return None
    x0, y0 = min(w[0] for w in span), min(w[1] for w in span)
    x1, y1 = max(w[2] for w in span), max(w[3] for w in span)
    high = y1 - y0
    clip = pymupdf.Rect(x0 - high * 4, y0 - high * 0.3, x1 + high * 4, y1 + high * 0.3)
    clip &= page.rect
    grey = _clip_ink(page, clip)
    if grey is None:
        return None
    scale = DPI / 72
    left, right = round((x0 - clip.x0) * scale), round((x1 - clip.x0) * scale)
    mask = grey > 0.5
    cols = mask.any(0)
    gap = max(4, round(high * scale * WORD_GAP))
    dot = max(3, round(high * scale * DOT))

    def is_dot(c0: int, c1: int) -> bool:
        rows = np.where(mask[:, c0:c1].any(1))[0]
        return 0 < c1 - c0 <= dot and len(rows) > 0 and rows[-1] - rows[0] < dot * 1.5

    # Outward from just inside the span's box to the first blank as wide as a word space,
    # and on through an ellipsis's dots, which stand as far apart as narrow word spaces.
    a = min(left + gap, right)
    while True:
        while a > 0 and cols[max(0, a - gap) : a].any():
            a -= 1
        e = a
        while e > 0 and not cols[e - 1]:
            e -= 1
        f = e
        while f > 0 and cols[f - 1]:
            f -= 1
        if not (e > 0 and a - e < 2 * gap and is_dot(f, e)):
            break
        a = f
    b = max(right - gap, left)
    while True:
        while b < len(cols) and cols[b : b + gap].any():
            b += 1
        e = b
        while e < len(cols) and not cols[e]:
            e += 1
        f = e
        while f < len(cols) and cols[f]:
            f += 1
        if not (e < len(cols) and e - b < 2 * gap and is_dot(e, f)):
            break
        b = f
    # How far the strip may reach: a third into the layer's words either side on the
    # line; a mark the layer holds apart (an ellipsis's dot) is no word.
    line = [w for w in words if y0 <= (w[1] + w[3]) / 2 <= y1 and any(c.isalnum() for c in w[4])]
    before = max((w for w in line if w[2] <= x0 + 1), key=lambda w: w[2], default=None)
    after = min((w for w in line if w[0] >= x1 - 1), key=lambda w: w[0], default=None)
    low = round((before[2] - (before[2] - before[0]) / 3 - clip.x0) * scale) if before else 0
    top = round((after[0] + (after[2] - after[0]) / 3 - clip.x0) * scale) if after else len(cols)
    low, top = max(low, 0), min(top, len(cols))
    lead = trail = gap
    if a <= low:
        blank = _widest_blank(cols, low, min(left + gap, right))
        if blank is None:
            return None
        a, lead = blank[1], min(gap, blank[1] - blank[0])
    if b >= top:
        blank = _widest_blank(cols, max(right - gap, left), top)
        if blank is None:
            return None
        b, trail = blank[0], min(gap, blank[1] - blank[0])
    if b - a < 6:
        return None
    return grey[:, max(0, a - lead) : b + trail]


def _widest_blank(cols: np.ndarray, start: int, end: int) -> tuple[int, int] | None:
    """The widest run of columns without ink in `start`–`end`, as (first, past the last)."""
    best, at = None, start
    while at < end:
        if cols[at]:
            at += 1
            continue
        stop = at
        while stop < end and not cols[stop]:
            stop += 1
        if best is None or stop - at > best[1] - best[0]:
            best = (at, stop)
        at = stop
    return best


def _pieces(face: Face, pieces: list[tuple]) -> np.ndarray | None:
    """Pieces of text drawn in a row: each (text, scale, shift before it in ems), and
    how far above the baseline in ems where it is a superscript."""
    width = int(sum(face.at(p[1]).getlength(p[0]) for p in pieces)) + RENDER_PX
    image = Image.new("L", (width, RENDER_PX * 2), 255)
    draw, x = ImageDraw.Draw(image), RENDER_PX // 4
    for text, scale, shift, *rise in pieces:
        cut = face.at(scale)
        x += shift * RENDER_PX
        up = rise[0] * RENDER_PX if rise else 0
        draw.text((x, RENDER_PX * 1.3 - up), text, font=cut, fill=0, anchor="ls")
        x += cut.getlength(text)
    grey = _levelled(_darkness(image))
    return None if grey is None else _trimmed(grey)


def drawings(face: Face, version: str) -> list[np.ndarray]:
    """The ways a book may set a version: as the font spaces it; with a closing quote
    kerned over the stop before it; with an ellipsis's dots apart; with a run of
    capitals as small capitals; with an ordinal's ending as a superscript; each of these in
    font's other figures where the version has digits."""
    ways = [[(version, 1.0, 0.0)]]
    if m := _STOP_QUOTE.search(version):
        for kern in KERNS:
            ways.append([(version[: m.end(1)], 1.0, 0.0), (version[m.end(1) :], 1.0, kern)])
    if m := _DOTS.search(version):
        for gap in DOT_GAPS:
            ways.append(
                [
                    (version[: m.start()], 1.0, 0.0),
                    (".", 1.0, 0.0),
                    (".", 1.0, gap),
                    (".", 1.0, gap),
                    (version[m.end() :], 1.0, gap / 2),
                ]
            )
    if _CAPITALS.search(version):
        for small in SMALL_CAPS:
            way, at = [], 0
            for m in _CAPITALS.finditer(version):
                if m.start() > at:
                    way.append((version[at : m.start()], 1.0, 0.0))
                way.append((m.group(), small, 0.0))
                at = m.end()
            if at < len(version):
                way.append((version[at:], 1.0, 0.0))
            ways.append(way)
    if m := _ORDINAL.search(version):
        for small, rise in SUPERSCRIPT:
            ways.append(
                [
                    (version[: m.start()], 1.0, 0.0),
                    (m.group(), small, 0.0, rise),
                    (version[m.end() :], 1.0, 0.0),
                ]
            )
    if any(c.isdigit() for c in version):
        ways += [
            [(piece[0].translate(figures), *piece[1:]) for piece in way]
            for figures in face.figures
            for way in list(ways)
        ]
    return [g for g in (_pieces(face, way) for way in ways) if g is not None]


def fits(face: Face, spread: int, size: float, ink: np.ndarray, versions: list[str]) -> list[float]:
    """Per version, how well its drawing at the book's size lies over the strip's ink:
    the cosine of the two at the best position and stretch, so ink the drawing lacks
    and ink it adds both count against it."""
    strip = np.asarray(_picture(ink).filter(_BLUR), np.float32)
    energy = float((strip * strip).sum())
    out = []
    for version in versions:
        best = 0.0
        for glyphs in drawings(face, version) if version.strip() and energy else []:
            high = max(4, round(glyphs.shape[0] * size / RENDER_PX))
            for stretch in STRETCHES:
                wide = max(4, round(glyphs.shape[1] * size / RENDER_PX * stretch))
                sized = _spread(_picture(glyphs).resize((wide, high)), spread)
                mine = np.asarray(sized.filter(_BLUR), np.float32)
                pad_y = max(6, high - strip.shape[0] + 6)
                pad_x = max(6, wide - strip.shape[1] + 6)
                canvas = np.pad(strip, ((pad_y, pad_y), (pad_x, pad_x)))
                over = fftconvolve(canvas, mine[::-1, ::-1], mode="valid")
                best = max(best, float(over.max()) / (energy * float((mine * mine).sum())) ** 0.5)
        out.append(best)
    return out


def _laid(face: Face, spread: int, size: float, canvas, energy, version, anchor=None):
    """The version's best-fitting drawing on the padded strip `canvas`: its fit, the
    drawing laid there, and where (top, left, width, stretch). With `anchor` (stretch,
    top, left or None, right or None) it is laid at that stretch within a few pixels of
    that corner, so two versions sharing a start or an end lie letter on letter."""
    best = (0.0, None, None)
    slack = max(2, round(size * 0.06))
    for glyphs in drawings(face, version):
        high = max(4, round(glyphs.shape[0] * size / RENDER_PX))
        for stretch in STRETCHES if anchor is None else (anchor[0],):
            wide = max(4, round(glyphs.shape[1] * size / RENDER_PX * stretch))
            if high > canvas.shape[0] or wide > canvas.shape[1]:
                continue
            sized = _spread(_picture(glyphs).resize((wide, high)), spread)
            mine = np.asarray(sized.filter(_BLUR), np.float32)
            over = fftconvolve(canvas, mine[::-1, ::-1], mode="valid")
            if anchor is not None:
                _, top, left, right = anchor
                x0 = left if left is not None else right - wide
                ys = slice(max(0, top - 3 * slack), top + 3 * slack + 1)
                xs = slice(max(0, x0 - slack), max(0, x0 + slack + 1))
                window = np.full_like(over, -np.inf)
                window[ys, xs] = over[ys, xs]
                over = window
                if not np.isfinite(over).any():
                    continue
            y, x = np.unravel_index(over.argmax(), over.shape)
            fit = float(over[y, x]) / (energy * float((mine * mine).sum()) + 1e-6) ** 0.5
            if fit > best[0]:
                laid = np.zeros_like(canvas)
                laid[y : y + high, x : x + wide] = mine
                best = (fit, laid, (int(y), int(x), wide, stretch))
    return best


def _shared(a: str, b: str) -> tuple[int, int]:
    """How many characters two versions share at their start and at their end."""
    limit = min(len(a), len(b))
    start = next((i for i in range(limit) if a[i] != b[i]), limit)
    end = next((i for i in range(limit) if a[-1 - i] != b[-1 - i]), limit)
    return start, end


def difference(
    face: Face, spread: int, size: float, ink: np.ndarray, first: str, second: str
) -> tuple[float, float] | None:
    """Two versions compared with the scan only where their drawings differ: the
    first's less the second's share, on those pixels, of drawing without ink under it
    and of ink it doesn't draw. Each is laid where it fits best and the other letter on
    letter with it (anchored on their shared start or end); the better-fitting of the
    two layings counts. None where nothing differs or a version can't be laid."""
    strip = np.asarray(_picture(ink).filter(_BLUR), np.float32)
    pad = (round(size * 1.2), round(size * 3))
    canvas = np.pad(strip, ((pad[0], pad[0]), (pad[1], pad[1])))
    energy = float((strip * strip).sum())
    start, end = _shared(first, second)
    best = None
    for versions, sign in (((first, second), 1), ((second, first), -1)):
        fit, a, at = _laid(face, spread, size, canvas, energy, versions[0])
        if a is None:
            continue
        y, x, wide, stretch = at
        anchor = (stretch, y, x, None) if start >= end else (stretch, y, None, x + wide)
        _, b, _ = _laid(face, spread, size, canvas, energy, versions[1], anchor)
        if b is None:
            continue
        differ = np.abs(a - b) > APART
        n = int(differ.sum())
        if not n:
            continue
        bare = [float((np.clip(d - canvas, 0, None) * differ).sum()) / n / 255 for d in (a, b)]
        undrawn = [float((np.clip(canvas - d, 0, None) * differ).sum()) / n / 255 for d in (a, b)]
        if best is None or fit > best[0]:
            best = (fit, sign * (bare[0] - bare[1]), sign * (undrawn[0] - undrawn[1]))
    return None if best is None else best[1:]


def sureness(fit: float, margin: float) -> float:
    """The probability that the best-fitting version is the print (`SURENESS`): low
    where even it lies poorly over the ink (a typeface that doesn't suit the book, a
    place cut wrong) or the next version fits nearly as well."""
    intercept, by_fit, by_margin = SURENESS
    return 1 / (1 + math.exp(-(intercept + by_fit * fit + by_margin * math.log(margin + 1e-3))))


class Judge:
    """The fit as a second vision judge (`ocrcheck._decide`'s `alarms`): asked the vision
    judges' question, it answers with the option whose version fits the scan best, from
    the suspect's page and box in the question's state. It takes no crop. Where the
    layer has no words at the box, or the box is taller than a line of the text
    (`DISPLAY`: a heading in display type), it answers "neither", which is no vote."""

    model = MODEL

    def __init__(self, pdf: Path, face: Face, found: Match, pages: list[PageText] = ()):
        self._pdf, self._face, self._match = pdf, face, found
        self._texts = {p.number: p for p in pages}
        heights = [ln.y1 - ln.y0 for p in pages for ln in p.lines if ln.text.strip()]
        self._line = statistics.median(heights) if heights else None
        # Part of each answer's cache key: another typeface or size is another judge.
        self.fingerprint = found.fingerprint

    def decide(self, state: dict, questions: dict, image_png: bytes | None = None) -> dict:
        versions = state["readings"]
        letters = [c for c in questions["reading"]["criteria"] if c != "neither"]
        high = state["box"][3] - state["box"][1]
        if self._line is not None and high > DISPLAY * self._line:
            return {"reading": Answer("choice", "neither", 0.0, {})}
        with pdflayer.PDF_LOCK, pymupdf.open(self._pdf) as doc:
            ink = place_ink(doc[state["page"] - 1], state["box"], self._texts.get(state["page"]))
        if ink is None:
            # "neither" is no pick; an empty value would read as the first version.
            return {"reading": Answer("choice", "neither", 0.0, {})}
        scores = fits(self._face, self._match.spread, self._match.size, ink, versions)
        order = sorted(range(len(versions)), key=lambda i: -scores[i])
        sure = sureness(scores[order[0]], scores[order[0]] - scores[order[1]])
        return {"reading": Answer("choice", letters[order[0]], sure, {})}


class Differ(Judge):
    """The second judge of the two: of the two versions that fit the place best, the
    one the scan agrees with where their drawings differ (`difference`), a comma against
    a stop being a few pixels of a word's ink. No vote where `Judge` has none, or
    nothing differs."""

    model = DIFFER

    def decide(self, state: dict, questions: dict, image_png: bytes | None = None) -> dict:
        none = {"reading": Answer("choice", "neither", 0.0, {})}
        versions = state["readings"]
        letters = [c for c in questions["reading"]["criteria"] if c != "neither"]
        high = state["box"][3] - state["box"][1]
        if self._line is not None and high > DISPLAY * self._line:
            return none
        with pdflayer.PDF_LOCK, pymupdf.open(self._pdf) as doc:
            ink = place_ink(doc[state["page"] - 1], state["box"], self._texts.get(state["page"]))
        if ink is None:
            return none
        spread, size = self._match.spread, self._match.size
        scores = fits(self._face, spread, size, ink, versions)
        a, b = sorted(range(len(versions)), key=lambda i: -scores[i])[:2]
        if not scores[b]:
            return none
        told = difference(self._face, spread, size, ink, versions[a], versions[b])
        if told is None:
            return none
        by_bare, by_undrawn = DIFFERENCE
        first = 1 / (1 + math.exp(-(by_bare * told[0] + by_undrawn * told[1])))
        pick, sure = (a, first) if first >= 0.5 else (b, 1 - first)
        return {"reading": Answer("choice", letters[pick], sure, {})}


def judge(
    pdf: Path,
    pages: list[PageText],
    library: Path,
    cache: Path,
    typeface: str | None = None,
    model: str = MODEL,
) -> Judge:
    """The judge `model` for a book, its typeface matched from `pages` (and kept in
    `cache`), or `typeface` where book.toml names one."""
    if not library.is_dir():
        raise ValueError(f"the judge {model!r} draws with the fonts in {library}: no such folder")
    found = match(pdf, pages, library, cache, typeface)
    kind = Differ if model == DIFFER else Judge
    return kind(pdf, Face.from_file(library / found.file), found, pages)
