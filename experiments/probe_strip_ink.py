"""Where a lost fragment sits, and how much ink a reader would have to look at to find it.

A loss between layer lines k and k+1 lies in one of three strips: right of line k (a
dropped end), the gap below it, or left of line k+1 (a dropped start, "... Ik heb"). For
the lost-text errors the error's context places (`before` ends line k, or `after` starts
line k+1), count the dark pixels in each strip; do the same for every such strip of a
sample of the other pages of those books. Prints, per strip kind and ink threshold, the
losses caught and the strips a reader would be handed per page.

    uv run python experiments/probe_strip_ink.py [out.jsonl]

No models: the cached text layers, the scans and the benches' error lists.
"""

import json
import random
import statistics
import sys
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from probe_gap_ink import layer, positives  # noqa: E402

DARK = 140
SAMPLE = 100
KINDS = ("right", "gap", "left")


def strips(lines: list[dict], k: int, left: float, right: float, h: float) -> dict[str, tuple]:
    """The three strips for a loss between lines k and k+1, as (x0, y0, x1, y1)."""
    a, b = lines[k], lines[k + 1]
    return {
        "right": (a["x1"] + 2, a["y0"], right, a["y1"]),
        "gap": (left, a["y1"] + 1, right, b["y0"] - 1),
        "left": (left, b["y0"], b["x0"] - 2, b["y1"]),
    }


def ink(pix: np.ndarray, box: tuple) -> int:
    x0, y0, x1, y1 = (max(0, int(v)) for v in box)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return 0
    return int((pix[y0:y1, x0:x1] < DARK).sum())


def place(lines: list[dict], r: dict) -> int | None:
    tail, head = r["before"].strip()[-12:], r["after"].strip()[:12]
    for k in range(len(lines) - 1):
        if tail and lines[k]["text"].strip().endswith(tail):
            return k
        if head and lines[k + 1]["text"].strip().startswith(head):
            return k
    return None


def main() -> None:
    random.seed(2)
    pos = positives()
    rows = []
    for book in sorted({r["book"] for r in pos}):
        pages = layer(book)
        doc = pymupdf.open(Path("work") / book / "source.pdf")
        marked = {r["page"] for r in pos if r["book"] == book}
        others = [n for n in pages if n not in marked and len(pages[n]["lines"]) > 4]
        for n in sorted(marked & set(pages)) + random.sample(others, min(SAMPLE, len(others))):
            lines = pages[n]["lines"]
            if len(lines) < 3:
                continue
            h = statistics.median(ln["y1"] - ln["y0"] for ln in lines)
            left, right = min(ln["x0"] for ln in lines), max(ln["x1"] for ln in lines)
            p = doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csGRAY)
            pix = np.frombuffer(p.samples, dtype=np.uint8).reshape(p.height, p.width)
            hit = {place(lines, r) for r in pos if r["book"] == book and r["page"] == n} - {None}
            for k in range(len(lines) - 1):
                if n in marked and k not in hit:
                    continue
                for kind, box in strips(lines, k, left, right, h).items():
                    rows.append(
                        {"book": book, "page": n, "k": k, "kind": kind, "lost": k in hit, "ink": ink(pix, box)}
                    )
        print(book, "done", flush=True)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text("".join(json.dumps(r) + "\n" for r in rows))
    located = {(r["book"], r["page"], r["k"]) for r in rows if r["lost"]}
    print(f"{len(located)} losses placed (of {len(pos)} errors)")
    rest_pages = len({(r["book"], r["page"]) for r in rows if not r["lost"]})
    for kind in KINDS:
        lost = [r for r in rows if r["lost"] and r["kind"] == kind]
        rest = [r for r in rows if not r["lost"] and r["kind"] == kind]
        for t in (10, 20, 40, 80):
            print(
                f"{kind:5} ink >= {t:3}: losses with ink {sum(r['ink'] >= t for r in lost):3}/{len(lost)}"
                f", other strips {sum(r['ink'] >= t for r in rest):5} ({sum(r['ink'] >= t for r in rest) / rest_pages:.2f} a page)"
            )


if __name__ == "__main__":
    main()
