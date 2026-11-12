"""Render and compare: a judge that knows no language. Each version of a suspect is drawn
in the book's typeface, at the book's size, and laid over the scan's ink; the version
that fits best gets the vote, and the margin over the next is its confidence.

The typeface is found from the scan (`match`): words of the text layer are cut out along
their ink, drawn in every font of a library, and the fonts ranked by how well the
drawings lie over the ink. The library is a folder of OpenType and TrueType files
(`Settings.fonts`), out of git.

The judge (`Judge`) answers the vision judges' question (`ocrcheck._decide`) from the
suspect's page and box alone, so it sits beside them as one more vote for the arbiter.
"""

import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import fftconvolve

from roboscriptorium import pdf as pdflayer
from roboscriptorium.clients.decide import Answer
from roboscriptorium.files import write_atomic
from roboscriptorium.pdf import PageText

# The judge's name among the second vision judges (`ROBO_ALARM_MODEL=…,render`).
MODEL = "render"
# The cached match's format, and part of the judge's answers' cache key.
VERSION = 1
DPI = 400
# The size, in pixels an em, that drawings are made at before scaling to the scan.
RENDER_PX = 96
WORDS = 240
FIRST_PASS = 40
KEPT = 40
STRETCHES = (0.92, 0.96, 1.0, 1.04, 1.08)
# Ink spread: a drawing's strokes thinned or thickened by this many scan pixels.
SPREADS = (-3, 0, 3, 5)
# A blank this wide, in line heights, parts a word from its neighbour.
WORD_GAP = 0.2
# A closing quote set over the stop before it, as some books kern it: how far left, in ems.
KERNS = (-0.12, -0.22, -0.32)
# Small capitals drawn as capitals at this share of their size.
SMALL_CAPS = (0.74, 0.82)
# A margin this wide between the best fit and the next is a confidence of 1.
SURE_MARGIN = 0.25
_NOT_TEXT = re.compile(r"Bold|Black|Semibold|Demi|Italic|Heavy", re.I)
_PLAIN = re.compile(r"regular|roman", re.I)
_STOP_QUOTE = re.compile(r"([.,…])([’”'\"])")
_CAPITALS = re.compile(r"[A-ZÀ-Þ]{2,}")
_BLUR = ImageFilter.GaussianBlur(1.5)


class Face:
    """A font, drawn at any size. `load(px)` gives it at `px` pixels an em."""

    def __init__(self, load):
        self._load = load
        self._cuts: dict[int, ImageFont.FreeTypeFont] = {}

    @classmethod
    def from_file(cls, path: Path) -> "Face":
        return cls(lambda px: ImageFont.truetype(str(path), px))

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
        return f"{VERSION}:{self.file}:{self.spread}:{self.size:.1f}"


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


def text_cut(ranked: list[dict]) -> dict:
    """Of fonts ranked by fit, the best that is a text cut: neither bold nor italic by its
    name, or regular by its file's."""
    for entry in ranked:
        if not _NOT_TEXT.search(entry["name"]) or _PLAIN.search(Path(entry["file"]).stem):
            return entry
    return ranked[0]


def em_size(words: list[tuple[str, np.ndarray]], font: ImageFont.FreeTypeFont) -> float:
    """The book's type size in scan pixels an em: what the font must be drawn at."""
    ratios = [
        ink.shape[0] / glyphs.shape[0]
        for word, ink in words
        if (glyphs := drawn(font, word)) is not None
    ]
    return RENDER_PX * float(np.median(ratios))


def match(pdf: Path, pages: list[PageText], library: Path, cache: Path | None = None) -> Match:
    """The book's typeface among the library's fonts, by the scan's words on `pages`:
    every font on a few words, then the best on all of them. A match
    in `cache` is kept whatever pages it was made from: a book is set in one typeface,
    and a slice of it must be judged as the whole is."""
    key = {"version": VERSION}
    if cache is not None and cache.exists():
        held = json.loads(cache.read_text())
        if held.get("key") == key and (library / held["match"]["file"]).exists():
            return Match(**held["match"])
    fonts = library_fonts(library)
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
    entry = text_cut(ranked)
    found = Match(
        entry["file"],
        entry["name"],
        round(entry["fit"], 4),
        entry["spread"],
        round(em_size(words[:80], fonts[entry["file"]]), 2),
    )
    if cache is not None:
        write_atomic(cache, json.dumps({"key": key, "match": asdict(found)}, indent=1))
    return found


def place_ink(page: pymupdf.Page, box, text: PageText | None = None) -> np.ndarray | None:
    """The ink at a suspect's box, as a strip of its line (0–1, not trimmed): everything
    between the blank before the layer's words there and the blank after them, so a mark
    the layer missed beside a word is in it and its neighbours' letters aren't. On an
    image-only page the words are its first reading's (`text`). None where there are no
    words."""
    bx0, by0, bx1, by1 = box
    span = [
        w
        for w in pdflayer.page_words(page, text)
        if bx0 - 1 <= (w[0] + w[2]) / 2 <= bx1 + 1 and by0 <= (w[1] + w[3]) / 2 <= by1
    ]
    if not span:
        return None
    x0, y0 = min(w[0] for w in span), min(w[1] for w in span)
    x1, y1 = max(w[2] for w in span), max(w[3] for w in span)
    high = y1 - y0
    clip = pymupdf.Rect(x0 - high * 2.5, y0 - high * 0.3, x1 + high * 2.5, y1 + high * 0.3)
    clip &= page.rect
    grey = _clip_ink(page, clip)
    if grey is None:
        return None
    scale = DPI / 72
    left, right = round((x0 - clip.x0) * scale), round((x1 - clip.x0) * scale)
    cols = (grey > 0.5).any(0)
    gap = max(4, round(high * scale * WORD_GAP))
    # Outward from just inside the span's box to the first blank as wide as a word space.
    a = min(left + gap, right)
    while a > 0 and cols[max(0, a - gap) : a].any():
        a -= 1
    b = max(right - gap, left)
    while b < len(cols) and cols[b : b + gap].any():
        b += 1
    if a <= 0 or b >= len(cols) or b - a < 6:
        return None
    return grey[:, max(0, a - gap) : b + gap]


def _pieces(face: Face, pieces: list[tuple[str, float, float]]) -> np.ndarray | None:
    """Pieces of text drawn on one baseline: each (text, scale, shift before it in ems)."""
    width = int(sum(face.at(sc).getlength(tx) for tx, sc, _ in pieces)) + RENDER_PX
    image = Image.new("L", (width, RENDER_PX * 2), 255)
    draw, x = ImageDraw.Draw(image), RENDER_PX // 4
    for text, scale, shift in pieces:
        cut = face.at(scale)
        x += shift * RENDER_PX
        draw.text((x, RENDER_PX * 1.3), text, font=cut, fill=0, anchor="ls")
        x += cut.getlength(text)
    grey = _levelled(_darkness(image))
    return None if grey is None else _trimmed(grey)


def drawings(face: Face, version: str) -> list[np.ndarray]:
    """The ways a book may set a version: as the font spaces it; with a closing quote
    kerned over the stop before it; with a run of capitals as small capitals."""
    ways = [[(version, 1.0, 0.0)]]
    if m := _STOP_QUOTE.search(version):
        for kern in KERNS:
            ways.append([(version[: m.end(1)], 1.0, 0.0), (version[m.end(1) :], 1.0, kern)])
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


class Judge:
    """The fit as a second vision judge (`ocrcheck._decide`'s `alarms`): asked the vision
    judges' question, it answers with the option whose version fits the scan best, from
    the suspect's page and box in the question's state. It takes no crop. Where the
    layer has no words at the box it picks nothing."""

    model = MODEL

    def __init__(self, pdf: Path, face: Face, found: Match, pages: list[PageText] = ()):
        self._pdf, self._face, self._match = pdf, face, found
        self._texts = {p.number: p for p in pages}
        # Part of each answer's cache key: another typeface or size is another judge.
        self.fingerprint = found.fingerprint

    def decide(self, state: dict, questions: dict, image_png: bytes | None = None) -> dict:
        versions = state["readings"]
        letters = [c for c in questions["reading"]["criteria"] if c != "neither"]
        with pdflayer.PDF_LOCK, pymupdf.open(self._pdf) as doc:
            ink = place_ink(doc[state["page"] - 1], state["box"], self._texts.get(state["page"]))
        if ink is None:
            return {"reading": Answer("choice", "", 0.0, {})}
        scores = fits(self._face, self._match.spread, self._match.size, ink, versions)
        order = sorted(range(len(versions)), key=lambda i: -scores[i])
        margin = scores[order[0]] - scores[order[1]]
        sure = min(1.0, margin / SURE_MARGIN)
        return {"reading": Answer("choice", letters[order[0]], sure, {})}


def judge(pdf: Path, pages: list[PageText], library: Path, cache: Path) -> Judge:
    """The judge for a book, its typeface matched from `pages` (and kept in `cache`)."""
    if not library.is_dir():
        raise ValueError(f"the judge {MODEL!r} draws with the fonts in {library}: no such folder")
    found = match(pdf, pages, library, cache)
    return Judge(pdf, Face.from_file(library / found.file), found, pages)
