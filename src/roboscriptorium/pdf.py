"""Read a PDF's existing text layer as positioned lines, and render page images."""

import json
import subprocess
import threading
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import pymupdf

from roboscriptorium import ocr
from roboscriptorium.files import write_atomic

# A fragment belongs to a visual line when it overlaps the line's vertical span by
# at least this share of its own height. OCR layers box each word separately, and
# the tops of one line's words differ by several points with ascenders and skew.
SAME_LINE_OVERLAP = 0.5
# A line's first glyph this many times taller than the rest is a large initial
# (a drop cap): its height says nothing about which printed line the text is on.
INITIAL_HEIGHT = 1.6
# PyMuPDF isn't thread-safe. A program that uses it from several threads (the
# review server) holds this lock around every use.
PDF_LOCK = threading.Lock()
# Bumped whenever line extraction changes, so cached text layers are rebuilt.
TEXT_LAYER_VERSION = 5
# Ligatures a font may put in the Unicode private-use area, where the text layer
# then holds a code that means nothing outside that font.
PRIVATE_LIGATURES = {"ff", "fi", "fl", "ffi", "ffl", "fj", "ft", "st", "ct", "Th", "ch", "ck", "tt"}
# Zoom for reading a word with such a glyph: born-digital text renders cleanly.
PRIVATE_READ_ZOOM = 6


@dataclass(frozen=True)
class Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    # Set on lines a human typed in, whose paragraph breaks are known.
    starts_paragraph: bool | None = None
    # The line begins with a decorated initial letter (a drop cap) a human supplied.
    initial: bool = False
    # On a corrected copy of a page: the line's index in the text layer. A line a
    # human typed in has the index of the line it was inserted before.
    source: int | None = None


@dataclass(frozen=True)
class PageText:
    number: int  # 1-based
    width: float
    height: float
    lines: list[Line]


def _visual_lines(
    fragments: list[Line], cores: list[tuple[float, float]] | None = None
) -> list[Line]:
    """Merge fragments that share a baseline, ordered top to bottom.

    `cores` is each fragment's vertical span without a large initial, which is what
    decides its line; the lines' boxes still hold the whole fragments.
    """
    if cores is None:
        cores = [(f.y0, f.y1) for f in fragments]
    merged: list[list[tuple[Line, tuple[float, float]]]] = []
    order = sorted(zip(fragments, cores, strict=True), key=lambda fc: (sum(fc[1]) / 2, fc[0].x0))
    for frag, (y0, y1) in order:
        if merged:
            top = min(c[0] for _, c in merged[-1])
            bottom = max(c[1] for _, c in merged[-1])
            overlap = min(bottom, y1) - max(top, y0)
            if overlap >= SAME_LINE_OVERLAP * (y1 - y0):
                merged[-1].append((frag, (y0, y1)))
                continue
        merged.append([(frag, (y0, y1))])
    lines = []
    for members in merged:
        group = sorted((f for f, _ in members), key=lambda f: f.x0)
        lines.append(
            Line(
                text=" ".join(f.text for f in group),
                x0=group[0].x0,
                y0=min(f.y0 for f in group),
                x1=group[-1].x1,
                y1=max(f.y1 for f in group),
            )
        )
    return lines


def line_words(page_words: list, page: PageText) -> list[list]:
    """The text layer's words per line, left to right.

    A word goes to the line whose vertical centre is nearest among those whose box
    holds its centre: some OCR layers give lines boxes far taller than the print,
    so neighbouring lines' boxes overlap.
    """
    out = [[] for _ in page.lines]
    for w in page_words:
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        holding = [k for k, ln in enumerate(page.lines) if _holds(ln, cx, cy)]
        if holding:
            k = min(holding, key=lambda k: abs((page.lines[k].y0 + page.lines[k].y1) / 2 - cy))
            out[k].append(w)
    return [sorted(ws, key=lambda w: w[0]) for ws in out]


def _holds(line, cx: float, cy: float) -> bool:
    return line.x0 - 3 <= cx <= line.x1 + 3 and line.y0 - 2 <= cy <= line.y1 + 2


def _core(line: dict) -> tuple[float, float]:
    """A text-layer line's vertical span, leaving out a large initial it opens with."""
    spans = [s for s in line["spans"] if s["text"].strip()]
    if len(spans) > 1:
        first = spans[0]["bbox"][3] - spans[0]["bbox"][1]
        rest = max(s["bbox"][3] - s["bbox"][1] for s in spans[1:])
        if first > INITIAL_HEIGHT * rest:
            return min(s["bbox"][1] for s in spans[1:]), max(s["bbox"][3] for s in spans[1:])
    return line["bbox"][1], line["bbox"][3]


def read_text_layer(pdf: Path) -> list[PageText]:
    pages = []
    with pymupdf.open(pdf) as doc:
        for index, page in enumerate(doc):
            fragments, cores = [], []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if text:
                        fragments.append(Line(text, *line["bbox"]))
                        cores.append(_core(line))
            lines = _visual_lines(fragments, cores)
            pages.append(PageText(index + 1, page.rect.width, page.rect.height, lines))
        spelled = str.maketrans(_private_ligatures(doc))
    for page in pages:
        page.lines[:] = [replace(ln, text=ln.text.translate(spelled)) for ln in page.lines]
    return pages


def spells(words: list, text: str) -> bool:
    """Whether the text layer's words (as `get_text("words")` gives them) spell `text`.

    A word's private-use glyphs are left out of the comparison: the line's text
    has them spelled out ("\ue050anks" is "Thanks").
    """
    tokens = text.split(" ")
    return len(words) == len(tokens) and all(
        w[4] == t or "".join(c for c in w[4] if not _private(c)) in t
        for w, t in zip(words, tokens, strict=True)
    )


def _private(ch: str) -> bool:
    return 0xE000 <= ord(ch) <= 0xF8FF


def ligature_read(word: str, glyph: str, reading: str) -> str | None:
    """The ligature `glyph` spells in `word`, given an OCR reading of the word."""
    before, _, after = word.partition(glyph)
    if not (reading.startswith(before) and reading.endswith(after)):
        return None
    letters = reading[len(before) : len(reading) - len(after)]
    return letters if letters in PRIVATE_LIGATURES else None


def _private_ligatures(doc: pymupdf.Document) -> dict[str, str]:
    """The letters each private-use glyph stands for, by reading the words that hold it.

    Tesseract reads the rendered word; what it reads between the known letters
    either side must be a ligature. Each glyph takes the majority over its words;
    a glyph no reading explains is left as it is.
    """
    votes: dict[str, Counter] = defaultdict(Counter)
    for page in doc:
        for x0, y0, x1, y1, word, *_ in page.get_text("words"):
            glyphs = [c for c in word if _private(c)]
            if len(glyphs) != 1:
                continue
            clip = pymupdf.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
            zoom = pymupdf.Matrix(PRIVATE_READ_ZOOM, PRIVATE_READ_ZOOM)
            try:
                reading = ocr.tesseract(
                    page.get_pixmap(matrix=zoom, clip=clip).tobytes("png"), "eng"
                )
            except (OSError, subprocess.SubprocessError):
                return {}
            if letters := ligature_read(word, glyphs[0], reading):
                votes[glyphs[0]][letters] += 1
    return {glyph: counts.most_common(1)[0][0] for glyph, counts in votes.items()}


def cached_text_layer(pdf: Path, cache: Path) -> list[PageText]:
    if cache.exists():
        raw = json.loads(cache.read_text())
        if isinstance(raw, dict) and raw.get("version") == TEXT_LAYER_VERSION:
            return [
                PageText(p["number"], p["width"], p["height"], [Line(**ln) for ln in p["lines"]])
                for p in raw["pages"]
            ]
    pages = read_text_layer(pdf)
    blob = {"version": TEXT_LAYER_VERSION, "pages": [asdict(p) for p in pages]}
    write_atomic(cache, json.dumps(blob, ensure_ascii=False, indent=1))
    return pages


def render_jpeg(pdf: Path, page_number: int, dpi: int = 150) -> bytes:
    with pymupdf.open(pdf) as doc:
        return doc[page_number - 1].get_pixmap(dpi=dpi).tobytes("jpeg")


def render_png(pdf: Path, page_number: int, max_pixels: int = 900_000) -> bytes:
    """Render a page as PNG, scaled to fit within max_pixels."""
    with pymupdf.open(pdf) as doc:
        page = doc[page_number - 1]
        zoom = (max_pixels / (page.rect.width * page.rect.height)) ** 0.5
        return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
