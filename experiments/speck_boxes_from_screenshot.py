"""The boxes the user draws on a page in the review (the fill-page tool), read from a pasted
screenshot as positions in PDF points, for the speck labels.

    uv run python experiments/speck_boxes_from_screenshot.py <screenshot.png> <book> <pdf page>

The screenshot must show the whole page (a dark border around it is fine): the page's own area is
found as the part that isn't black and mapped onto the PDF page's size, so no scale is needed. The
boxes are the pink-red outlines. Adds them to work/probes/specks/boxes-<book>.json under the PDF page.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy import ndimage

OUT = Path("work/probes/specks")

if __name__ == "__main__":
    shot, book, page = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    im = np.asarray(Image.open(shot).convert("RGB")).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    outline = (r > 200) & (g < 120) & (50 < b) & (b < 150) & (r - g > 110)
    labelled, _ = ndimage.label(outline, structure=np.ones((3, 3)))
    boxes = [
        (s[1].start, s[0].start, s[1].stop, s[0].stop)
        for s in ndimage.find_objects(labelled)
        if s[1].stop - s[1].start > 8 and s[0].stop - s[0].start > 8
    ]
    ys, xs = np.where(im.sum(axis=2) > 60)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    with pymupdf.open(Path("work") / book / "source.pdf") as doc:
        w, h = doc[page - 1].rect.width, doc[page - 1].rect.height
    sx, sy = w / (x1 - x0), h / (y1 - y0)
    if abs((x1 - x0) / (y1 - y0) - w / h) > 0.01:
        sys.exit("the screenshot's page isn't the PDF page's shape: is the whole page in it?")
    points = [
        [round(float((a - x0) * sx), 1), round(float((b_ - y0) * sy), 1),
         round(float((c - x0) * sx), 1), round(float((d - y0) * sy), 1)]
        for a, b_, c, d in boxes
    ]
    path = OUT / f"boxes-{book}.json"
    kept = json.loads(path.read_text()) if path.exists() else {}
    kept[str(page)] = sorted(points, key=lambda p: (p[1], p[0]))
    path.write_text(json.dumps(kept))
    print(f"{len(points)} boxes on PDF page {page} of {book}")
