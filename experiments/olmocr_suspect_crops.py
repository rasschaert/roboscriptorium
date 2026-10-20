"""Crops of the lines the OCR check flagged on the golden books, as the line readers see
them, for a second opinion from another reader (`mlx_read_crops.py`).

    uv run python experiments/olmocr_suspect_crops.py [book …]

Warm builds of each book (`ocr_trust=False`, as `trustdata.build`), then one crop for each
line a trust-data row names, in work/probes/olmocr-suspects/<book>/<page>_<line>.png.
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

import pymupdf

from roboscriptorium import pipeline, readers
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.trustdata import OUT, SPECS

ROOT = Path("work/probes/olmocr-suspects")

if __name__ == "__main__":
    for name in sys.argv[1:] or list(SPECS):
        path = OUT / f"{name}.json"
        if not path.exists():
            continue
        wanted = {(r["suspect"]["page"], r["suspect"]["line"]) for r in json.loads(path.read_text())}
        spec = SPECS[name]
        pages_arg = (spec.split(":") + [""])[0] if spec and spec != "answers" else ""
        book = Book.load(Path("work") / name)
        settings = replace(Settings.from_env(), ocr_trust=False)
        stages = pipeline.run(book, pages=scoring.page_range(pages_arg or None), settings=settings)
        out = ROOT / name
        out.mkdir(parents=True, exist_ok=True)
        made = 0
        with pymupdf.open(book.source) as doc:
            for page in stages.pages:
                todo = [k for (p, k) in wanted if p == page.number and k < len(page.lines)]
                if not todo:
                    continue
                boxes = readers.line_boxes(doc[page.number - 1], page)
                for k in todo:
                    target = out / f"{page.number}_{k}.png"
                    if target.exists():
                        continue
                    span = readers.crop_span(boxes, k)
                    target.write_bytes(readers._line_crop(doc, page.number, boxes[k], span))
                    made += 1
        print(f"{name[:36]:36} {len(wanted):5} lines, {made} new crops", flush=True)
