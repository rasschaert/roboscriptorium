"""Show-through by what it is: the other side's print, mirrored. A faint page (ink contrast
under half the book's, `probe_showthrough.py`) flipped left to right and laid over the page
before and the page after: the peak of their normalised cross-correlation, against the same
peak unflipped. Faint pages of the labelled books, by label: blank ones should match a
neighbour mirrored, washed-out text (Afscheid) shouldn't. No models.

    PYTHONPATH=experiments uv run python experiments/probe_showthrough_mirror.py
"""

import statistics
from pathlib import Path

import numpy as np
import pymupdf
from scipy import ndimage
from scipy.signal import fftconvolve
from setup_gaps import LABELS
from sklearn.metrics import roc_auc_score

from roboscriptorium import faint, pagekinds
from roboscriptorium.pdf import cached_text_layer

DPI = 50


def ink(page: pymupdf.Page) -> np.ndarray:
    """The page's ink at low resolution: darker than its surroundings, zero mean."""
    pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    grey = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w).astype(np.float32)
    high = ndimage.gaussian_filter(grey, 8) - ndimage.gaussian_filter(grey, 1)
    h, w = high.shape
    high = high[h // 12 : -h // 12, w // 12 : -w // 12]  # the scan's edges and the gutter out
    return high - high.mean()


def peak(a: np.ndarray, b: np.ndarray) -> float:
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a, b = a[:h, :w], b[:h, :w]
    over = fftconvolve(a, b[::-1, ::-1], mode="same")
    c = over[h // 2 - 15 : h // 2 + 16, w // 2 - 15 : w // 2 + 16]  # a few millimetres of slack
    return float(c.max() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))


rows = []
for name, entry in sorted(LABELS.items()):
    root = Path("work") / name
    if not (root / "source.pdf").exists():
        continue
    pages = cached_text_layer(root / "source.pdf", root / "stages" / "textlayer.json")
    labelled = {int(k): v for k, v in entry["pages"].items()}
    with pymupdf.open(root / "source.pdf") as doc:
        got = {}
        for p in pages:
            try:
                got[p.number] = faint.contrast(doc[p.number - 1], p.lines)
            except ValueError:
                pass
        body = statistics.median(got[p.number] for p in pages if p.number in got and len(p.lines) > 20)
        for p in pages:
            if p.number not in got or got[p.number] / body >= 0.5 or sum(len(ln.text.split()) for ln in p.lines) < 10:
                continue
            mine = ink(doc[p.number - 1])
            near = [ink(doc[n - 1]) for n in (p.number - 1, p.number + 1) if 1 <= n <= len(doc)]
            mirrored = max(peak(mine[:, ::-1], o) for o in near)
            plain = max(peak(mine, o) for o in near)
            label = labelled.get(p.number, "text")
            rows.append((name, p.number, label, mirrored, plain, got[p.number] / body))
    print(name, flush=True)
y = np.array([pagekinds.fate(r[2]) != "in" for r in rows])
print(f"{len(rows)} faint pages with ten words or more in the layer, {int(y.sum())} labelled out of the book")
print(f"mirrored peak AUC {roc_auc_score(y, [r[3] for r in rows]):.3f}; mirrored minus plain AUC {roc_auc_score(y, [r[3] - r[4] for r in rows]):.3f}")
for r in sorted(rows, key=lambda r: -r[3]):
    print(f"  {r[0][:30]:30} PDF {r[1]:4} {r[2]:12} mirrored {r[3]:.3f} plain {r[4]:.3f} contrast {r[5]:.2f}")
