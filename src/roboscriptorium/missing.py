"""Printed lines the text layer lacks, read from the page image.

OCR layers drop short lines: a bare chapter number ("3"), a page number, a line
of dialogue ("'Ja.'"). The layout model still sees a region there. A region about
one line tall that no text-layer line falls in is read by the OCR model, and the
reading goes into a copy of the page as a line of its own, in reading order, so
roles, rules and reflow treat it like any other line. Readings are cached in
`stages/missing-lines.json`.

Figures and captions are left to the figures stage, and regions a human
answered in the review keep the human's text.
"""

import json
from dataclasses import replace
from pathlib import Path
from statistics import median

import pymupdf

from roboscriptorium import ocrcheck
from roboscriptorium.files import write_atomic
from roboscriptorium.layout import Region
from roboscriptorium.pdf import Line, PageText

VERSION = 1
MAX_HEIGHT = 1.8  # times the book's median line height
SKIPPED = {"figure", "figure_caption"}


def _inside(line: Line, box) -> bool:
    cx, cy = (line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2
    return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]


def _overlap(a: Region, b: Region) -> bool:
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    smaller = min((a.x1 - a.x0) * (a.y1 - a.y0), (b.x1 - b.x0) * (b.y1 - b.y0))
    return w > 0 and h > 0 and w * h >= 0.5 * smaller


def candidates(
    pages: list[PageText],
    regions: dict[int, list[Region]],
    answered: dict[int, list[tuple[float, float, float, float]]],
) -> list[tuple[int, Region]]:
    """Line-sized regions holding no text-layer line and not part of one, one per spot
    (the surest).

    `answered` holds, per page, the boxes of regions a human typed text for.
    """
    heights = [ln.y1 - ln.y0 for p in pages for ln in p.lines]
    if not heights:
        return []
    tallest = MAX_HEIGHT * median(heights)
    found = []
    for page in pages:
        figures = [r for r in regions.get(page.number, []) if r.label == "figure"]
        kept: list[Region] = []
        for r in sorted(regions.get(page.number, []), key=lambda r: -r.confidence):
            box = (r.x0, r.y0, r.x1, r.y1)
            centre = Line("", *box)
            if (
                r.label in SKIPPED
                or r.turned
                or r.y1 - r.y0 > tallest
                or any(_inside(ln, box) for ln in page.lines)
                or any(_inside(centre, (ln.x0, ln.y0, ln.x1, ln.y1)) for ln in page.lines)
                or any(_inside(centre, (f.x0, f.y0, f.x1, f.y1)) for f in figures)
                or any(_inside(centre, b) for b in answered.get(page.number, []))
                or any(_overlap(r, k) for k in kept)
            ):
                continue
            kept.append(r)
        found += [(page.number, r) for r in kept]
    return found


def _key(number: int, r: Region) -> str:
    return f"{number}:{r.x0:.0f},{r.y0:.0f},{r.x1:.0f},{r.y1:.0f}"


def read(
    pdf: Path, found: list[tuple[int, Region]], model: str, ollama_url: str, cache: Path
) -> dict[str, str]:
    """The OCR model's reading of each candidate, keyed by page and box."""
    done: dict[str, str] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == VERSION and raw.get("model") == model:
            done = raw["lines"]
    todo = [(n, r) for n, r in found if _key(n, r) not in done]
    if todo:
        # Saved however the reads end, so an interrupted run keeps the ones done.
        try:
            with pymupdf.open(pdf) as doc:
                for n, r in todo:
                    png = ocrcheck._line_crop(doc, n, (r.x0, r.y0, r.x1, r.y1))
                    done[_key(n, r)] = ocrcheck.read_line(png, model, ollama_url)
        finally:
            write_atomic(cache, json.dumps({"version": VERSION, "model": model, "lines": done}))
    return {_key(n, r): done[_key(n, r)] for n, r in found}


def add(
    pages: list[PageText], found: list[tuple[int, Region]], readings: dict[str, str]
) -> list[PageText]:
    """Copies of the pages with each read line in reading order (by its middle).

    A reading with no letter or digit (a smudge) is left out.
    """
    by_page: dict[int, list[Line]] = {}
    for n, r in found:
        text = " ".join(readings.get(_key(n, r), "").split())
        if any(c.isalnum() for c in text):
            by_page.setdefault(n, []).append(Line(text, r.x0, r.y0, r.x1, r.y1))
    out = []
    for page in pages:
        if page.number not in by_page:
            out.append(page)
            continue
        lines = list(page.lines)
        for new in by_page[page.number]:
            middle = (new.y0 + new.y1) / 2
            at = sum(1 for ln in lines if (ln.y0 + ln.y1) / 2 < middle)
            lines.insert(at, new)
        out.append(replace(page, lines=lines))
    return out
