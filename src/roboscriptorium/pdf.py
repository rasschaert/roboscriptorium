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
# PyMuPDF isn't thread-safe. A program that uses it from several threads (the
# review server) holds this lock around every use.
PDF_LOCK = threading.Lock()
# Bumped whenever line extraction changes, so cached text layers are rebuilt.
TEXT_LAYER_VERSION = 4
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


def _visual_lines(fragments: list[Line]) -> list[Line]:
    """Merge fragments that share a baseline, ordered top to bottom."""
    merged: list[list[Line]] = []
    for frag in sorted(fragments, key=lambda f: ((f.y0 + f.y1) / 2, f.x0)):
        if merged:
            top = min(f.y0 for f in merged[-1])
            bottom = max(f.y1 for f in merged[-1])
            overlap = min(bottom, frag.y1) - max(top, frag.y0)
            if overlap >= SAME_LINE_OVERLAP * (frag.y1 - frag.y0):
                merged[-1].append(frag)
                continue
        merged.append([frag])
    lines = []
    for group in merged:
        group.sort(key=lambda f: f.x0)
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


def read_text_layer(pdf: Path) -> list[PageText]:
    pages = []
    with pymupdf.open(pdf) as doc:
        for index, page in enumerate(doc):
            fragments = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if text:
                        fragments.append(Line(text, *line["bbox"]))
            pages.append(
                PageText(index + 1, page.rect.width, page.rect.height, _visual_lines(fragments))
            )
        spelled = str.maketrans(_private_ligatures(doc))
    for page in pages:
        page.lines[:] = [replace(ln, text=ln.text.translate(spelled)) for ln in page.lines]
    return pages


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
