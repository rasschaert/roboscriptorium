"""Probe: printed lines the OCR layer lacks, found by the layout model and read by glm-ocr.

A candidate is a layout region (not a figure, not turned) with no text-layer line
inside it and at most about one line tall. With --read, glm-ocr reads each one.

    uv run python experiments/probe_missing_lines.py work/<book> [--read]
"""

import json
import sys
from pathlib import Path
from statistics import median

import pymupdf

from roboscriptorium import ocrcheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.flags import _inside
from roboscriptorium.layout import Region
from roboscriptorium.pdf import cached_text_layer

book = Book.load(Path(sys.argv[1]))
first, last = book.body_pages
pages = [p for p in cached_text_layer(book.source, book.stages / "textlayer.json")
         if first <= p.number <= last]
raw = json.loads((book.stages / "layout.json").read_text())["pages"]
height = median(ln.y1 - ln.y0 for p in pages for ln in p.lines)
found = []
for p in pages:
    for r in raw.get(str(p.number), []):
        region = Region(r["label"], r["confidence"], r["x0"], r["y0"], r["x1"], r["y1"], r["turned"])
        if region.label == "figure" or region.turned:
            continue
        if region.y1 - region.y0 > 1.8 * height:
            continue
        if any(_inside(ln, region) for ln in p.lines):
            continue
        found.append((p.number, region))
print(f"{len(found)} candidates on {len({n for n, _ in found})} pages; median line height {height:.1f}")
settings = Settings.from_env()
with pymupdf.open(book.source) as doc:
    for n, r in found:
        reading = ""
        if "--read" in sys.argv:
            png = ocrcheck._line_crop(doc, n, (r.x0, r.y0, r.x1, r.y1))
            reading = ocrcheck.read_line(png, settings.ocr_model, settings.ollama_url)
        print(f"p{n} {r.label} {r.confidence:.2f} {r.x0:.0f},{r.y0:.0f},{r.x1:.0f},{r.y1:.0f} {reading!r}")
