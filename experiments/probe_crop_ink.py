"""Whether the OCR check's line crops fit the ink: no models.

For each line on a book's first pages, the page image's ink rows within the line's
width give its own band of ink (the rows connected to its box's middle) and any other
ink. Against the crop (`ocrcheck.crop_span`) it counts crops holding ink of another
line (separated from the line's own by an empty row), crops cutting the line's own ink
off (its band reaching past the crop's top or bottom), and lines whose band touches
the next one with no empty row between (where no crop can separate them by rows).

    uv run python experiments/probe_crop_ink.py [pages per book]
"""

import sys
import tomllib
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import ocrcheck, pdf

PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 12
DPI = 150
SCALE = DPI / 72
INK = 128  # grey level below which a pixel is ink
ROW_INK = 2  # dark pixels that make a row inked
SLACK = 0.5  # points of own ink past the crop that count as cut


def bands(rows: np.ndarray) -> list[tuple[int, int]]:
    """Runs of inked rows, as (first, last) row indices."""
    out, start = [], None
    for i, inked in enumerate(rows):
        if inked and start is None:
            start = i
        elif not inked and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(rows) - 1))
    return out


print(f"{'book':40} {'lines':>5} {'other ink':>9} {'pt med/p90/max':>15}  {'own cut':>8} {'pt med/p90/max':>15}")
for d in sorted(Path("work").glob("*--*")):
    toml, layer = d / "book.toml", d / "stages" / "textlayer.json"
    if "calibre" in d.name or not toml.exists() or not layer.exists():
        continue
    first, last = tomllib.loads(toml.read_text())["body_pages"]
    pages = [p for p in pdf.cached_text_layer(d / "source.pdf", layer) if first <= p.number <= last]
    pages = [p for p in pages if p.lines][:PAGES]
    n = other = cut = touching = 0
    intrusion, lost = [], []  # points of other ink inside crops, of own ink outside them
    with pymupdf.open(d / "source.pdf") as doc:
        for p in pages:
            page = doc[p.number - 1]
            pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
            img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride)[:, : pix.width]
            boxes = ocrcheck.line_boxes(page, p)
            for k, line in enumerate(p.lines):
                if not line.text.strip():
                    continue
                x0, y0, x1, y1 = boxes[k]
                top, bottom = ocrcheck.crop_span(boxes, k)
                c0, c1 = int(x0 * SCALE), int(x1 * SCALE) + 1
                # Rows from a little above the crop to a little below, so a cut band shows.
                r0, r1 = max(0, int((top - 8) * SCALE)), min(img.shape[0], int((bottom + 8) * SCALE) + 1)
                inked = (img[r0:r1, c0:c1] < INK).sum(axis=1) >= ROW_INK
                runs = bands(inked)
                # Ink centred inside the line's box is its own (letters, dots, accents, quote
                # marks above them); ink centred outside it is another line's.
                def centre(run):
                    return (r0 + (run[0] + run[1] + 1) / 2) / SCALE
                own = [run for run in runs if y0 <= centre(run) <= y1]
                if not own:
                    continue
                n += 1
                own_top = (r0 + min(r[0] for r in own)) / SCALE
                own_bottom = (r0 + max(r[1] for r in own) + 1) / SCALE
                outside = max(0.0, top - own_top) + max(0.0, own_bottom - bottom)
                if outside > SLACK:
                    cut += 1
                    lost.append(outside)
                t, b = top * SCALE - r0, bottom * SCALE - r0
                inside = [
                    (min(run[1] + 1, b) - max(run[0], t)) / SCALE
                    for run in runs
                    if run not in own and run[1] >= t and run[0] <= b
                ]
                if inside:
                    other += 1
                    intrusion.append(sum(inside))
                # Its ink runs on into a neighbour's: no empty row between the two lines.
                if any(run not in own and (run[0] <= own[0][0] - 1 <= run[1] or run[0] <= own[-1][1] + 1 <= run[1]) for run in runs) or (
                    len(own) == 1 and not (y0 <= centre(own[0]) <= y1)
                ):
                    touching += 1
    def spread(v):
        return f"{np.median(v):4.1f}/{np.percentile(v, 90):4.1f}/{max(v):4.1f}" if v else "   -/   -/   -"
    print(f"{d.name[:40]:40} {n:5} {other:5} {other / max(1, n):3.0%} {spread(intrusion)}  "
          f"{cut:4} {cut / max(1, n):3.0%} {spread(lost)}")
