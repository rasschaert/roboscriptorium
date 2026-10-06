"""Read a PDF's existing text layer as positioned lines, and render page images."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

# A fragment belongs to a visual line when it overlaps the line's vertical span by
# at least this share of its own height. OCR layers box each word separately, and
# the tops of one line's words differ by several points with ascenders and skew.
SAME_LINE_OVERLAP = 0.5
# Bumped whenever line extraction changes, so cached text layers are rebuilt.
TEXT_LAYER_VERSION = 2


@dataclass(frozen=True)
class Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    # Set on lines a human typed in, whose paragraph breaks are known.
    starts_paragraph: bool | None = None


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
    return pages


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
    cache.write_text(json.dumps(blob, ensure_ascii=False, indent=1))
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
