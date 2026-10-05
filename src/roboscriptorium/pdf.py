"""Read a PDF's existing text layer as positioned lines, and render page images."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

# Fragments whose tops differ by less than this (in points) are one visual line.
SAME_LINE_TOLERANCE = 3.0


@dataclass(frozen=True)
class Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class PageText:
    number: int  # 1-based
    width: float
    height: float
    lines: list[Line]


def _visual_lines(fragments: list[Line]) -> list[Line]:
    """Merge fragments that share a baseline, ordered top to bottom."""
    merged: list[list[Line]] = []
    for frag in sorted(fragments, key=lambda f: (f.y0, f.x0)):
        if merged and abs(frag.y0 - merged[-1][0].y0) < SAME_LINE_TOLERANCE:
            merged[-1].append(frag)
        else:
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
        return [
            PageText(p["number"], p["width"], p["height"], [Line(**ln) for ln in p["lines"]])
            for p in raw
        ]
    pages = read_text_layer(pdf)
    cache.write_text(json.dumps([asdict(p) for p in pages], ensure_ascii=False, indent=1))
    return pages


def render_jpeg(pdf: Path, page_number: int, dpi: int = 150) -> bytes:
    with pymupdf.open(pdf) as doc:
        return doc[page_number - 1].get_pixmap(dpi=dpi).tobytes("jpeg")
