"""Line crops from the page's ink, tried against the OCR check's box crops and not
adopted (docs/decisions.md, 2026-10-08): the box crop already stops at the next
line, and the readers read no better from a crop fitted to the ink.

A line's own ink is the ink centred inside its layer box; its crop is that ink and
INK_MARGIN of paper, stopping halfway across the gap to another line's ink.
"""

import numpy as np
import pymupdf

from roboscriptorium import ocrcheck

INK_DPI = 150
INK_LEVEL = 128
INK_PIXELS = 2
INK_MARGIN = 2.0


def _runs(rows: np.ndarray) -> list[tuple[int, int]]:
    edges = np.flatnonzero(np.diff(np.concatenate(([0], rows.astype(np.int8), [0]))))
    return [(int(a), int(b) - 1) for a, b in zip(edges[::2], edges[1::2], strict=True)]


def ink_spans(pdf_page: pymupdf.Page, boxes: list) -> list[tuple[float, float]]:
    """Each line's crop top and bottom from the page's ink; the box crop where a line
    has no ink of its own in its box."""
    pix = pdf_page.get_pixmap(dpi=INK_DPI, colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride)[:, : pix.width]
    scale = INK_DPI / 72
    out = []
    for k, (x0, y0, x1, y1) in enumerate(boxes):
        em = y1 - y0
        r0, r1 = max(0, int((y0 - em) * scale)), min(img.shape[0], int((y1 + em) * scale) + 1)
        c0, c1 = max(0, int(x0 * scale)), min(img.shape[1], int(x1 * scale) + 1)
        if r1 <= r0 or c1 <= c0:
            out.append(ocrcheck.crop_span(boxes, k))
            continue
        inked = (img[r0:r1, c0:c1] < INK_LEVEL).sum(axis=1) >= INK_PIXELS
        runs = [((r0 + a) / scale, (r0 + b + 1) / scale) for a, b in _runs(inked)]
        own = [(a, b) for a, b in runs if y0 <= (a + b) / 2 <= y1]
        if not own:
            out.append(ocrcheck.crop_span(boxes, k))
            continue
        top, bottom = own[0][0], own[-1][1]
        above = [b for a, b in runs if b <= top]
        below = [a for a, b in runs if a >= bottom]
        out.append((
            max(top - INK_MARGIN, (max(above) + top) / 2 if above else -1e9),
            min(bottom + INK_MARGIN, (min(below) + bottom) / 2 if below else 1e9),
        ))  # fmt: skip
    return out


def use_ink_crops(pdf_path) -> None:
    """Make `ocrcheck.line_readings` crop from the ink: `crop_span` answers with the
    ink span of the line whose box it is given."""
    original = ocrcheck.crop_span
    spans: dict[tuple, tuple[float, float]] = {}
    seen: set[int] = set()

    def ink_crop_span(boxes, k):
        if id(boxes) not in seen:
            seen.add(id(boxes))
            page = next((n for n, bs in _pages.items() if bs is boxes), None)
            if page is not None:
                with pymupdf.open(pdf_path) as doc:
                    for box, span in zip(boxes, ink_spans(doc[page - 1], boxes), strict=True):
                        spans[tuple(box)] = span
        return spans.get(tuple(boxes[k]), original(boxes, k))

    _pages: dict[int, list] = {}
    line_boxes = ocrcheck.line_boxes

    def remembered(pdf_page, page):
        boxes = line_boxes(pdf_page, page)
        _pages[page.number] = boxes
        return boxes

    ocrcheck.line_boxes = remembered
    ocrcheck.crop_span = ink_crop_span
