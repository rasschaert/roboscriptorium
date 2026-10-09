"""Pages scanned too faint to read: the text layer there is guesswork, not a reading.

A washed-out scan (Afscheid's paper reads grey 156, its ink 149) still gets an OCR
layer, full of short scraps that pass for words, so neither the garbled-line rule nor
the word list notices. The page image does: between the paper (the page's median
grey) and the ink inside the layer's line boxes a printed page has some 60–90 grey
levels, a washed-out one under 10. Only a page whose layer holds words is measured.
At 60 dpi; cached per page in `stages/contrast.json`.
"""

import json
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium.files import write_atomic
from roboscriptorium.pdf import PageText

VERSION = 1
DPI = 60
# Grey levels between paper and ink below which a page can't be read.
FAINT_BELOW = 30
# A page's layer holds at least this many words before its faintness means lost text.
MIN_WORDS = 50


def contrast(page: pymupdf.Page, lines: list) -> float:
    """Grey levels between the paper (the page's median) and the ink (the 5th percentile
    inside the text layer's line boxes, where the ink should be)."""
    pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    grey = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
    zoom = DPI / 72
    inked = [
        grey[int(ln.y0 * zoom) : int(ln.y1 * zoom) + 1, int(ln.x0 * zoom) : int(ln.x1 * zoom) + 1]
        for ln in lines
    ]
    inked = np.concatenate([a.ravel() for a in inked if a.size])
    return float(np.percentile(grey, 50) - np.percentile(inked, 5))


def pages(pdf: Path, body: list[PageText], cache: Path) -> set[int]:
    """The numbers of the pages in `body` scanned too faint to read."""
    done: dict[str, float] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == VERSION:
            done = raw["pages"]
    worded = [p for p in body if sum(len(ln.text.split()) for ln in p.lines) >= MIN_WORDS]
    todo = [p for p in worded if str(p.number) not in done]
    if todo:
        with pymupdf.open(pdf) as doc:
            for p in todo:
                done[str(p.number)] = contrast(doc[p.number - 1], p.lines)
        write_atomic(cache, json.dumps({"version": VERSION, "pages": done}))
    return {p.number for p in worded if done[str(p.number)] < FAINT_BELOW}
