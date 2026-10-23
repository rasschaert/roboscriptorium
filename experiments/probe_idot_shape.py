"""Is the mark over an accented i different in shape from the book's own i-dots? No models.

    uv run python experiments/probe_idot_shape.py

Per book, the reference is the control lines of the frozen reader set (clean lines, known text):
every small blob standing just above a narrow upright one (an i or j and its dot) gives a mark
with an area, an aspect (height over width), a fill, a tilt (the angle of its long axis) and a
sideways offset from the stem. The test lines are the unasked set's: the six real stress-accent
errors (the accent is printed, the reader wrote a plain i) and the clean control lines. Each line
is scored by its oddest mark, the largest standardised distance from the book's own marks.
Reported: how the six accented lines rank among all test lines (an AUC) and their scores.
"""

import hashlib
import json
from collections import defaultdict
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

READER = Path("work/tryout/reader-v3")
UNASKED = Path("work/probes/unasked-set")
RUN = "tuning-20261020T182636-f38e636-dirty"


def real_lines() -> set[str]:
    """The ids (book:page:line) of the lines holding a stress-accent error that no question was asked
    about and the layer kept: the accent is printed and the readers wrote a plain letter."""
    rows = [json.loads(x) for x in Path(f"work/bench/{RUN}.errors.jsonl").read_text().splitlines()]
    return {
        f"{r['book']}:{r['page']}:{r['lines'][0]}"
        for r in rows
        if r["cause"] == "stress accent" and not r["asked"] and r["layer"] == "kept" and r["lines"]
        and r["lines"][0] == r["lines"][1] and "i" in r["want"].lower().replace("í", "i")
    }


def marks(png: bytes) -> list[list[float]]:
    grey = np.asarray(Image.open(BytesIO(png)).convert("L"), dtype=float)
    ink = grey < (grey.min() + grey.max()) / 2
    lab, n = ndimage.label(ink, structure=np.ones((3, 3)))
    boxes = ndimage.find_objects(lab)
    areas = ndimage.sum(ink, lab, range(1, n + 1))
    height = grey.shape[0]
    blobs = []
    for k, (s, a) in enumerate(zip(boxes, areas)):
        top, bottom, left, right = s[0].start, s[0].stop, s[1].start, s[1].stop
        if top == 0 or bottom == height or a < 4:
            continue  # touching the crop's edge: a neighbour line's
        blobs.append({"k": k + 1, "t": top, "b": bottom, "l": left, "r": right, "a": a})
    out = []
    for m in blobs:
        mh, mw = m["b"] - m["t"], m["r"] - m["l"]
        stems = [
            s for s in blobs
            if s["t"] >= m["b"] - 1 and s["t"] - m["b"] <= 1.2 * max(mh, 3)
            and min(s["r"], m["r"]) - max(s["l"], m["l"]) >= 0.4 * mw
            and (s["r"] - s["l"]) <= 0.6 * (s["b"] - s["t"]) and s["a"] > 2.5 * m["a"]
        ]
        if not stems:
            continue
        s = min(stems, key=lambda s: s["t"])
        ys, xs = np.nonzero(lab[m["t"]:m["b"], m["l"]:m["r"]] == m["k"])
        cov = np.cov(np.vstack([xs, ys])) if len(xs) > 2 else np.eye(2)
        tilt = 0.5 * np.arctan2(2 * cov[0, 1], cov[0, 0] - cov[1, 1])
        sh = s["b"] - s["t"]
        out.append([
            m["a"] / sh**2, mh / max(mw, 1), m["a"] / max(mh * mw, 1), np.cos(2 * tilt), np.sin(2 * tilt),
            ((m["l"] + m["r"]) / 2 - (s["l"] + s["r"]) / 2) / max(s["r"] - s["l"], 1),
        ])
    return out


def crop(root: Path, item: dict) -> bytes:
    return (root / "crops" / f"{hashlib.sha256(item['id'].encode()).hexdigest()[:16]}.png").read_bytes()


if __name__ == "__main__":
    reference = defaultdict(list)
    for item in json.loads((READER / "items.json").read_text())["items"]:
        if item["stratum"] == "control":
            reference[item["book"]] += marks(crop(READER, item))
    stats = {b: (np.mean(m, 0), np.std(m, 0) + 1e-6) for b, m in reference.items() if len(m) >= 20}
    print({b[:18]: len(m) for b, m in reference.items()})
    real = real_lines()
    scored = []
    for item in json.loads((UNASKED / "items.json").read_text())["items"]:
        book = item["book"]
        if book not in stats:
            continue
        found = marks(crop(UNASKED, item))
        if not found:
            continue
        mean, std = stats[book]
        score = max(float(np.abs((np.array(f) - mean) / std).max()) for f in found)
        scored.append((score, item["id"] in real, item["id"]))
    scored.sort(reverse=True)
    pos = [s for s in scored if s[1]]
    neg = [s for s in scored if not s[1]]
    auc = np.mean([(p[0] > n[0]) + 0.5 * (p[0] == n[0]) for p in pos for n in neg]) if pos and neg else float("nan")
    print(f"{len(scored)} test lines with a mark over a stem; the {len(pos)} accented ones against {len(neg)} others: AUC {auc:.2f}")
    for p in pos:
        rank = 1 + sum(n[0] > p[0] for n in neg)
        print(f"  {p[2]:50} score {p[0]:5.1f}  rank {rank} of {len(neg) + 1}")
