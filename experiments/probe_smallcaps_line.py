"""Small capitals told by the line's own x-height: on places whose versions differ only in
case and whose letters, in lower case, stand on the x-height alone (a c e m n o r s u v w
x z, with marks and stops between), the height of the place's ink from its line's
baseline, over that line's x-height (where the line's ink is densest). Lower case should
stand near 1, small capitals higher, full capitals higher still. No models.

    uv run python experiments/probe_smallcaps_line.py [book …]

Prints, by what the print has, the measured ratios; writes
work/probes/smallcaps-line/rows.json.
"""

import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import rendercheck as R
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium import pdf as pdflayer

OUT = Path("work/probes/smallcaps-line")
TRUST = Path("work/probes/ocr-trust")
LOW = re.compile(r"^[acemnorsuvwxz.\-’'!?:]+$")


def band(profile: np.ndarray) -> tuple[int, int] | None:
    """The rows of the line's lower-case body: around the densest row, while a row holds
    at least half its ink."""
    if profile.max() <= 0:
        return None
    peak = int(profile.argmax())
    top, bottom = peak, peak
    while top > 0 and profile[top - 1] >= profile[peak] * 0.5:
        top -= 1
    while bottom < len(profile) - 1 and profile[bottom + 1] >= profile[peak] * 0.5:
        bottom += 1
    return top, bottom


def book(name: str) -> list[dict]:
    d = Path("work") / name
    rows = json.loads((TRUST / f"{name}.json").read_text())
    pages = {p.number: p for p in cached_text_layer(d / "source.pdf", d / "stages/textlayer.json")}
    out = []
    with pymupdf.open(d / "source.pdf") as doc:
        for r in rows:
            s = r["suspect"]
            versions = [s["ours"], *s["others"]]
            right = r.get("right") or []
            if len({v.casefold() for v in versions}) != 1 or len(set(versions)) < 2:
                continue
            if sum(right) != 1 or not LOW.match(versions[0].casefold()):
                continue
            page = doc[s["page"] - 1]
            words = pdflayer.page_words(page, pages.get(s["page"]))
            bx0, by0, bx1, by1 = s["box"]
            mid = (by0 + by1) / 2
            line = [w for w in words if w[1] <= mid <= w[3]]
            span = [w for w in line if bx0 - 1 <= (w[0] + w[2]) / 2 <= bx1 + 1]
            if len(line) < 4 or not span:
                continue
            x0, x1 = min(w[0] for w in line), max(w[2] for w in line)
            y0, y1 = min(w[1] for w in line), max(w[3] for w in line)
            clip = pymupdf.Rect(x0, y0, x1, y1) & page.rect
            with pdflayer.PDF_LOCK:
                grey = R._clip_ink(page, clip)
            if grey is None:
                continue
            ink = grey > 0.5
            body = band(ink.sum(1).astype(float))
            if body is None:
                continue
            xheight = body[1] - body[0] + 1
            scale = R.DPI / 72
            c0 = round((min(w[0] for w in span) - clip.x0) * scale)
            c1 = round((max(w[2] for w in span) - clip.x0) * scale)
            rows_inked = np.where(ink[: body[1] + 1, c0:c1].any(1))[0]
            if not len(rows_inked) or xheight < 6:
                continue
            ratio = (body[1] - rows_inked[0] + 1) / xheight
            printed = versions[right.index(True)]
            out.append(
                {
                    "book": name,
                    "page": s["page"],
                    "versions": versions,
                    "print": printed,
                    "capitals": printed.casefold() != printed,
                    "ratio": round(float(ratio), 3),
                }
            )
    return out


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.stem for p in TRUST.glob("*.json"))
    names = [n for n in names if (Path("work") / n / "source.pdf").exists()]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as pool:
        for found in pool.map(book, names):
            rows += found
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    for caps in (False, True):
        rs = sorted(r["ratio"] for r in rows if r["capitals"] == caps)
        if rs:
            q = np.percentile(rs, [5, 25, 50, 75, 95])
            print(f"print {'with capitals' if caps else 'lower case  '}: n={len(rs):4}  "
                  f"5/25/50/75/95% {' '.join(f'{x:.2f}' for x in q)}")
    for cut in (1.05, 1.1, 1.15, 1.2):
        caps_above = sum(r["ratio"] >= cut for r in rows if r["capitals"])
        low_above = sum(r["ratio"] >= cut for r in rows if not r["capitals"])
        print(f"  at {cut}: capitals above {caps_above}, lower case above {low_above}")
