"""Does ink that no text-layer line covers mark a page that lost text?

For the pages holding a whole-line lost-text error (any bench log with causes) and a
random sample of the other pages of the same books, count the dark pixels outside every
layer line's box (padded) and outside the page's outer margin, and report where the lost
pages rank. A dot line at a line's start ("... Ik heb"), a dateline, a lost sentence all
leave such ink; a page number or running head is a layer line, so it covers itself.

    uv run python experiments/probe_uncovered_ink.py [out.jsonl]

No models: the cached text layers, the scans and the benches' error lists.
"""

import json
import random
import sys
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from probe_gap_ink import layer, positives  # noqa: E402

PAD = 4.0
EDGE = 0.04
DARK = 110
SAMPLE = 120


def uncovered(page_pix: np.ndarray, lines: list[dict], zoom: float) -> tuple[int, int]:
    """(dark pixels outside the lines and the edge, the largest run of dark rows there)."""
    mask = np.zeros(page_pix.shape, dtype=bool)
    for ln in lines:
        mask[
            max(0, int((ln["y0"] - PAD) * zoom)) : int((ln["y1"] + PAD) * zoom),
            max(0, int((ln["x0"] - PAD) * zoom)) : int((ln["x1"] + PAD) * zoom),
        ] = True
    h, w = page_pix.shape
    mask[: int(h * EDGE)] = mask[-int(h * EDGE) :] = True
    mask[:, : int(w * EDGE)] = mask[:, -int(w * EDGE) :] = True
    dark = (page_pix < DARK) & ~mask
    return int(dark.sum()), int((dark.sum(axis=1) > 0).sum())


def main() -> None:
    random.seed(1)
    pos = positives()
    rows = []
    for book in sorted({r["book"] for r in pos}):
        pages = layer(book)
        marked = {r["page"] for r in pos if r["book"] == book}
        others = [n for n in pages if n not in marked and len(pages[n]["lines"]) > 3]
        chosen = [n for n in marked if n in pages] + random.sample(others, min(SAMPLE, len(others)))
        doc = pymupdf.open(Path("work") / book / "source.pdf")
        for n in chosen:
            p = doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csGRAY)
            pix = np.frombuffer(p.samples, dtype=np.uint8).reshape(p.height, p.width)
            ink, rowsn = uncovered(pix, pages[n]["lines"], 1.0)
            rows.append({"book": book, "page": n, "lost": n in marked, "ink": ink, "rows": rowsn})
        print(book, "done", flush=True)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text("".join(json.dumps(r) + "\n" for r in rows))
    lost = [r for r in rows if r["lost"]]
    rest = [r for r in rows if not r["lost"]]
    print(f"{len(lost)} pages with a loss, {len(rest)} others")
    for t in (50, 100, 200, 400, 800, 1600):
        c = sum(r["ink"] >= t for r in lost)
        f = sum(r["ink"] >= t for r in rest)
        print(f"uncovered ink >= {t:5}: lost pages {c:3}/{len(lost)}  other pages {f:4}/{len(rest)} ({f / len(rest):.0%})")


main()
