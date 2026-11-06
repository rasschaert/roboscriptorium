"""Lost lines inside a text block: slots about one line pitch tall between two text-layer
lines (a line with no letter or digit, "€", counted as none) that hold ink. For the
lost-text errors of the latest tuning and validation benches, is such a slot there, and how
many slots hold ink otherwise?

    uv run python experiments/probe_ink_slots.py [book …]

No models: the cached text layers, the scans and the benches' error lists. Writes every
slot to work/probes/ink-slots/<book>.jsonl.
"""

import json
import statistics
import sys
import tomllib
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import bench

RUNS = ["tuning-20261105T081806-2929d12-dirty", "validation-20261105T082120-2929d12-dirty"]
OUT = Path("work/probes/ink-slots")
DPI = 150
LOW, HIGH = 1.6, 2.5  # the gap between the two lines' tops, in line pitches
# Ink is this much darker than the strip's paper (its median: a slot is mostly paper).
DARK = 60


def junk(text: str) -> bool:
    return not any(c.isalnum() for c in text)


def pages_of(spec: str) -> tuple[str, range]:
    name, *rest = spec.split(":")
    if rest and rest[0]:
        a, b = map(int, rest[0].split("-"))
    else:
        a, b = tomllib.loads(Path(f"work/{name}/book.toml").read_text())["body_pages"]
    return name, range(a, b + 1)


def ink(doc: pymupdf.Document, number: int, x0: float, y0: float, x1: float, y1: float):
    """Dark pixels and the rows they span in a strip of the page, at `DPI`."""
    page = doc[number - 1]
    clip = pymupdf.Rect(x0, y0, x1, y1) & page.rect
    if clip.is_empty or clip.height < 1:
        return 0, 0
    pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, : pix.width]
    dark = img < np.median(img) - DARK
    rows = np.flatnonzero(dark.sum(axis=1) >= 2)
    return int(dark.sum()), int(rows[-1] - rows[0] + 1) if rows.size else 0


lost = {}
for run in RUNS:
    for line in open(f"work/bench/{run}.errors.jsonl"):
        r = json.loads(line)
        if not r["got"].strip() and r["want"].strip():
            lost.setdefault(r["book"], []).append(r)

specs = bench.SETS["tuning"] + bench.SETS["validation"]
OUT.mkdir(parents=True, exist_ok=True)
total = {"slots": 0, "inked": 0, "pages": 0, "lost": 0, "lost_on_inked_page": 0}
for spec in specs:
    name, pages = pages_of(spec)
    if sys.argv[1:] and name not in sys.argv[1:]:
        continue
    layer = json.loads(Path(f"work/{name}/stages/textlayer.json").read_text())["pages"]
    by_number = {p["number"]: p for p in layer if p["number"] in pages}
    rows = []
    with pymupdf.open(f"work/{name}/source.pdf") as doc:
        for number, page in sorted(by_number.items()):
            lines = [ln for ln in page["lines"] if not junk(ln["text"])]
            if len(lines) < 5:
                continue
            heights = statistics.median(ln["y1"] - ln["y0"] for ln in lines)
            pitch = statistics.median(
                b["y0"] - a["y0"] for a, b in zip(lines, lines[1:]) if b["y0"] > a["y0"]
            )
            left = min(ln["x0"] for ln in lines)
            right = max(ln["x1"] for ln in lines)
            for a, b in zip(lines, lines[1:]):
                step = b["y0"] - a["y0"]
                if not LOW * pitch <= step <= HIGH * pitch:
                    continue
                # The strip between the two lines, a little in from each.
                y0, y1 = a["y1"] + 0.15 * heights, b["y0"] - 0.15 * heights
                if y1 - y0 < 0.5 * heights:
                    continue
                dark, span = ink(doc, number, left, y0, right, y1)
                rows.append(
                    {
                        "page": number,
                        "above": a["text"],
                        "below": b["text"],
                        "step": round(step / pitch, 2),
                        "dark": dark,
                        "span": round(span / (DPI / 72) / heights, 2),
                    }
                )
    book_lost = [r for r in lost.get(name, []) if r["page"] in by_number]
    inked = [r for r in rows if r["dark"] >= 20 and r["span"] >= 0.5]
    hit = [r for r in book_lost if any(s["page"] == r["page"] for s in inked)]
    (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(
        f"{name[:30]:30} pages {len(by_number):4}  slots {len(rows):4}  inked {len(inked):3}  "
        f"lost {len(book_lost):2}, on a page with an inked slot {len(hit):2}",
        flush=True,
    )
    for r in book_lost:
        mark = "*" if r in hit else " "
        print(f"   {mark} p{r['page']} {r['want'][:60]!r}")
    total["slots"] += len(rows)
    total["inked"] += len(inked)
    total["pages"] += len(by_number)
    total["lost"] += len(book_lost)
    total["lost_on_inked_page"] += len(hit)
print(total)
