"""Can a classifier on a blob's size, shape and place tell a speck from print? Trained on the
boxes the user drew (`speck_boxes_from_screenshot.py`), scored leaving one page out.

    uv run python experiments/probe_speck_blobs.py

For each labelled page: ink components at 300 dpi (small and medium ones: a speck can be bigger than
a stop), each with its area, height, width, fill, darkness, its place against the text layer's
lines (inside a line's box, its distance to the nearest line, its height against that line's
x-height band) and how isolated it is. A blob is a speck where its centre falls inside a drawn
box; the rest of the page's blobs are print or specks nobody marked. No models.
"""

import json
from io import BytesIO
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy import ndimage
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium.pdf import cached_text_layer

DPI = 300
K = DPI / 72
SPECKS = Path("work/probes/specks")


def blobs(book: str, page: int, boxes: list[list[float]]) -> tuple[np.ndarray, np.ndarray, list[tuple]]:
    root = Path("work") / book
    layer = {p.number: p for p in cached_text_layer(root / "source.pdf", root / "stages" / "textlayer.json")}[page]
    with pymupdf.open(root / "source.pdf") as doc:
        png = doc[page - 1].get_pixmap(dpi=DPI).tobytes("png")
    grey = np.asarray(Image.open(BytesIO(png)).convert("L"), dtype=float)
    ink = grey < (np.percentile(grey, 2) + np.percentile(grey, 60)) / 2
    labelled, n = ndimage.label(ink, structure=np.ones((3, 3)))
    areas = ndimage.sum(ink, labelled, range(1, n + 1))
    lines = [(ln.x0, ln.y0, ln.x1, ln.y1) for ln in layer.lines]
    heights = [b - a for _, a, _, b in lines]
    body = float(np.median(heights)) if heights else 10.0
    centres = []
    rows = []
    for k, s in enumerate(ndimage.find_objects(labelled)):
        area = areas[k]
        h, w = (s[0].stop - s[0].start) / K, (s[1].stop - s[1].start) / K
        if area < 4 or max(h, w) > 2.5 * body:
            continue
        cx, cy = (s[1].start + s[1].stop) / 2 / K, (s[0].start + s[0].stop) / 2 / K
        inside = [ln for ln in lines if ln[0] - 2 <= cx <= ln[2] + 2 and ln[1] - 2 <= cy <= ln[3] + 2]
        gap = min((abs(cy - (ln[1] + ln[3]) / 2) for ln in lines), default=999.0)
        if inside:
            ln = min(inside, key=lambda ln: abs(cy - (ln[1] + ln[3]) / 2))
            rel = (cy - ln[1]) / max(1.0, ln[3] - ln[1])
        else:
            rel = -1.0
        fill = area / max(1.0, (s[0].stop - s[0].start) * (s[1].stop - s[1].start))
        dark = float(grey[s][labelled[s] == k + 1].mean())
        rows.append([area, h / body, w / body, h / max(w, 1e-3), fill, dark, float(bool(inside)), gap / body, rel, cx / layer.width, cy / layer.height])
        centres.append((cx, cy))
    y = np.array([any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes) for cx, cy in centres], dtype=int)
    return np.array(rows), y, centres


if __name__ == "__main__":
    data = {}
    for f in sorted(SPECKS.glob("boxes-*.json")):
        book = f.stem.removeprefix("boxes-")
        for page, boxes in json.loads(f.read_text()).items():
            data[(book, int(page))] = blobs(book, int(page), boxes)
    for held, (X, y, _) in data.items():
        train = [d for k, d in data.items() if k != held]
        model = HistGradientBoostingClassifier(max_depth=3, min_samples_leaf=5, random_state=0).fit(
            np.vstack([t[0] for t in train]), np.concatenate([t[1] for t in train])
        )
        p = model.predict_proba(X)[:, 1]
        order = np.argsort(-p)
        top = y[order[: max(1, int(y.sum()))]].sum()
        print(
            f"{held[0][:22]} PDF page {held[1]}: {len(y)} blobs, {int(y.sum())} in boxes; "
            f"of the {int(y.sum())} surest, {int(top)} are in boxes; "
            f"flagged above 0.5: {int((p > 0.5).sum())} ({int(y[p > 0.5].sum())} in boxes)"
        )
