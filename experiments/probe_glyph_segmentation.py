"""Stage 0 of the per-book alphabet idea: can a line crop be cut into one blob per glyph?

For each control line of the frozen reader set (its text is known), threshold the crop, label its
connected components, and compare their number with the number the text should give: one per
letter or digit or stop, two for i, j, !, ?, :, ;, = and the like, and for a letter carrying an
accent whose mark stands apart (assumed here: accented letters give two). Touching letters
(rn, cl, ri, ft) give fewer, a speck or the page edge more. No models.

    uv run python experiments/probe_glyph_segmentation.py
"""

import json
import unicodedata
from collections import Counter
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path("work/tryout/reader-v3")
TWO = set("ij!?:;=")


def expected(text: str) -> int:
    n = 0
    for ch in text:
        if ch.isspace():
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        n += 2 if ch in TWO or len(decomposed) > 1 else 1
    return n


def blobs(png: bytes) -> int:
    grey = np.asarray(Image.open(BytesIO(png)).convert("L"), dtype=float)
    ink = grey < (grey.min() + grey.max()) / 2
    labelled, count = ndimage.label(ink, structure=np.ones((3, 3)))
    sizes = ndimage.sum(ink, labelled, range(1, count + 1))
    height = grey.shape[0]
    # A blob touching the crop's top or bottom edge is a neighbouring line's ascender or
    # descender; specks of a few pixels are scan noise, not marks.
    edge = set(np.unique(labelled[0])) | set(np.unique(labelled[-1]))
    return sum(
        1
        for k, s in enumerate(sizes, 1)
        if k not in edge and s >= max(4, 0.0006 * height * height)
    )


if __name__ == "__main__":
    import hashlib

    items = json.loads((ROOT / "items.json").read_text())["items"]
    off = Counter()
    for item in items:
        if item["stratum"] != "control":
            continue
        crop = ROOT / "crops" / f"{hashlib.sha256(item['id'].encode()).hexdigest()[:16]}.png"
        off[blobs(crop.read_bytes()) - expected(item["truth"])] += 1
    total = sum(off.values())
    print(f"{total} control lines; blobs minus expected:")
    for d in sorted(off):
        if abs(d) <= 6:
            print(f"  {d:+d}: {off[d]:4}  {off[d] / total:5.1%}")
    exact = off[0]
    near = sum(off[d] for d in (-1, 0, 1))
    print(f"exact {exact / total:.1%}, within one {near / total:.1%}")
