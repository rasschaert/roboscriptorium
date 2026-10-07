"""The type each line is set in, measured on the page image, relative to the body text.

A typesetter marks headings by type: larger, in capitals, bolder, spaced out;
page numbers are often smaller. Per line, each word's ink gives the height from
its tallest letters to the baseline (the type size; only words with capitals,
ascenders or digits count), its stroke width and its ink width per letter. The
book's body text is the median over its full-width lines. No model.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import numpy as np
import pymupdf

from roboscriptorium.files import write_atomic
from roboscriptorium.ir import SourceRef
from roboscriptorium.italics import ink_threshold
from roboscriptorium.page import geometry
from roboscriptorium.pdf import PageText, line_words

VERSION = 2
DPI = 300
# Letters that reach above the x-height: their tops give the type size.
TALL = re.compile(r"[A-Zbdhkl0-9À-Ý]")
# A line at least this share of the page's usual line width is running text.
BODY_WIDTH = 0.9
# A relative size that reads as larger than the body text.
LARGER = 1.2
# Two lines are set in one size when their sizes differ by at most this factor.
SAME_SIZE = 1.08


@dataclass(frozen=True)
class Style:
    """A line's type relative to the book's body text (1.0 = the same)."""

    size: float | None  # tallest letters to baseline; None without such letters
    weight: float | None  # stroke width
    pitch: float | None  # ink width per letter
    capitals: bool


def measure(pdf: Path, pages: list[PageText], cache: Path) -> dict[SourceRef, Style]:
    """Every line's style, relative to the full-width lines of `pages`.

    Raw measurements are cached per page with the page's lines, so a page whose
    lines change is measured again.
    """
    done: dict[str, dict] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == VERSION:
            done = raw["pages"]
    todo = [p for p in pages if done.get(str(p.number), {}).get("lines") != _lines(p)]
    if todo:
        with pymupdf.open(pdf) as doc:
            for page in todo:
                done[str(page.number)] = {
                    "lines": _lines(page),
                    "measured": _page(doc[page.number - 1], page),
                }
        write_atomic(cache, json.dumps({"version": VERSION, "pages": done}))

    measured = {
        SourceRef(p.number, int(k)): m
        for p in pages
        for k, m in done[str(p.number)]["measured"].items()
    }
    body = {
        SourceRef(p.number, i)
        for p in pages
        if p.lines
        for i, ln in enumerate(p.lines)
        if (ln.x1 - ln.x0) >= BODY_WIDTH * geometry(p)[0]
    }
    norm = {
        k: _median([m[k] for ref, m in measured.items() if ref in body])
        for k in ("height", "stroke", "pitch")
    }
    return {
        ref: Style(
            size=_ratio(m["height"], norm["height"]),
            weight=_ratio(m["stroke"], norm["stroke"]),
            pitch=_ratio(m["pitch"], norm["pitch"]),
            capitals=m["capitals"],
        )
        for ref, m in measured.items()
    }


def display(style: Style | None) -> bool:
    """Set apart from the body text: larger or in capitals."""
    return style is not None and style.size is not None and (style.size >= LARGER or style.capitals)


def groups(styles: dict[SourceRef, Style], places: dict[SourceRef, str]) -> list[list[SourceRef]]:
    """Lines set in one style: in one place on their pages, capitals or not, and sizes
    in a chain of steps no larger than `SAME_SIZE`. Lines without a size are left out."""
    by_kind: dict[tuple[str, bool], list[SourceRef]] = {}
    for ref, style in styles.items():
        if style.size is not None:
            by_kind.setdefault((places[ref], style.capitals), []).append(ref)
    out = []
    for refs in by_kind.values():
        refs.sort(key=lambda r: styles[r].size)
        group = [refs[0]]
        for ref in refs[1:]:
            if styles[ref].size > styles[group[-1]].size * SAME_SIZE:
                out.append(group)
                group = []
            group.append(ref)
        out.append(group)
    return out


def _ratio(value: float | None, norm: float | None) -> float | None:
    return None if value is None or not norm else round(value / norm, 2)


def _median(values: list[float | None]) -> float | None:
    values = [v for v in values if v is not None]
    return median(values) if values else None


def _lines(page: PageText) -> str:
    return hashlib.sha256("\n".join(ln.text for ln in page.lines).encode()).hexdigest()[:16]


def _page(pdf_page: pymupdf.Page, page: PageText) -> dict[str, dict]:
    if not page.lines:
        return {}
    pix = pdf_page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    scale = DPI / 72
    threshold = ink_threshold(img)
    out = {}
    for k, (line, words) in enumerate(
        zip(page.lines, line_words(pdf_page.get_text("words"), page), strict=True)
    ):
        # A line the text layer lacks (read from the scan) has only its own box.
        pieces = [(w[:4], w[4]) for w in words] or [
            ((line.x0, line.y0, line.x1, line.y1), line.text)
        ]
        inks = []
        for box, text in pieces:
            x0, y0, x1, y1 = (int(round(v * scale)) for v in box)
            crop = img[max(0, y0 - 2) : y1 + 2, max(0, x0 - 1) : x1 + 1]
            if crop.size and (ink := _ink(crop < threshold)):
                inks.append((ink, text))
        if not inks:
            continue
        letters = [c for c in line.text if c.isalpha()]
        out[str(k)] = {
            "height": _median([ink["height"] for ink, text in inks if TALL.search(text)]),
            "stroke": _median([ink["stroke"] for ink, _ in inks]),
            "pitch": sum(ink["width"] for ink, _ in inks)
            / max(1, sum(len(text.replace(" ", "")) for _, text in inks)),
            "capitals": bool(letters) and all(c.isupper() for c in letters),
        }
    return out


def _ink(ink: np.ndarray) -> dict | None:
    """Height from the topmost ink to the baseline, mean stroke width and ink width.

    The baseline is the lowest row of the dense band of ink (x-height letters),
    so descenders don't count.
    """
    rows = ink.sum(axis=1)
    if rows.max(initial=0) < 2:
        return None
    dense = np.nonzero(rows >= 0.4 * rows.max())[0]
    baseline = int(dense.max())
    top = int(np.nonzero(rows >= max(1, 0.03 * rows.max()))[0].min())
    if baseline - top < 3:
        return None
    band = ink[int(dense.min()) : baseline + 1].astype(np.int8)
    edges = np.diff(np.pad(band, ((0, 0), (1, 1))), axis=1)
    runs = np.nonzero(edges == -1)[1] - np.nonzero(edges == 1)[1]
    columns = np.nonzero(ink.any(axis=0))[0]
    return {
        "height": float(baseline - top),
        "stroke": float(runs.mean()) if runs.size else None,
        "width": float(columns[-1] - columns[0] + 1),
    }
