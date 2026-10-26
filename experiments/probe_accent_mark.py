"""Is the mark over a suspect's letter an accent, or a speck or nothing? No models.

The arbiter's silent accent errors (2026-10-26) go both ways: specks taken for accents
(Doodskleed's "zè", "eén", Glazuur's "óp") and printed emphasis accents dropped ("ík",
"míjn"). A suspect already names the word and the letter, so unlike
`probe_accent_shape.py` only the ink above that one letter is measured.

For every settled suspect in the trust data with a version that differs from the layer's
only by a mark on one letter: the letter's place in the span's box (by its share of the
span's characters), the span rendered at 400 dpi, and the ink above the x-height within
the letter's columns. Per place: its largest mark's area, elongation, tilt, fill and
darkness, and the count of other small marks above the span's other letters (a speckled
patch). The label: whether the print has a mark on that letter. Prints each feature's AUC,
and a leave-one-book-out forest's.

    uv run python experiments/probe_accent_mark.py [out.jsonl]
"""

import glob
import io
import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy import ndimage

from roboscriptorium import trust

DPI = 400


def strip(c: str) -> str:
    return "".join(x for x in unicodedata.normalize("NFD", c) if not unicodedata.combining(x))


def marked_letter(ours: str, other: str) -> int | None:
    """The one position where the two differ only by a mark, else None."""
    if len(ours) != len(other):
        return None
    diff = [i for i, (a, b) in enumerate(zip(ours, other)) if a != b]
    if len(diff) != 1 or strip(ours[diff[0]]) != strip(other[diff[0]]):
        return None
    return diff[0]


def blobs(g: np.ndarray):
    """Ink mask, x-height top row, and the components wholly above it, small ones only."""
    ink = g < (g.mean() - 1.5 * g.std() if g.std() else 128)
    rows = ink.sum(axis=1)
    if not rows.any():
        return ink, 0, []
    core = np.nonzero(rows > rows.max() * 0.5)[0]
    top, xh = core.min(), max(1, core.max() - core.min())
    labels, _ = ndimage.label(ink)
    out = []
    for i, sl in enumerate(ndimage.find_objects(labels), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if sl[0].stop > top + 2 or h > xh or w > xh or h * w < 4:
            continue
        mask = labels[sl] == i
        ys, xs = np.nonzero(mask)
        if len(ys) < 4:
            continue
        cov = np.cov(np.vstack([xs, ys])) + np.eye(2) / 12
        vals, vecs = np.linalg.eigh(cov)
        elong = float(np.sqrt(max(vals[1], 1e-6) / max(vals[0], 1e-6)))
        vx, vy = vecs[:, 1]
        tilt = (float(np.degrees(np.arctan2(vx, -vy))) + 90) % 180 - 90
        dark = float(255 - g[sl][mask].mean())
        out.append(
            {
                "x0": sl[1].start, "x1": sl[1].stop, "area": len(ys) / xh**2,
                "elong": elong, "tilt": tilt, "fill": len(ys) / (h * w), "dark": dark,
                "gap": (top - sl[0].stop) / xh,
            }
        )  # fmt: skip
    return ink, top, out


def measure(page: pymupdf.Page, s: dict, i: int) -> dict | None:
    x0, y0, x1, y1 = s["box"]
    clip = pymupdf.Rect(x0, y0 - (y1 - y0) * 0.35, x1, y1) & page.rect
    if clip.is_empty:
        return None
    pix = page.get_pixmap(clip=clip, dpi=DPI, colorspace=pymupdf.csGRAY)
    g = np.asarray(Image.open(io.BytesIO(pix.tobytes("png"))), dtype=float)
    _, _, marks = blobs(g)
    n = len(s["ours"])
    w = g.shape[1] / n
    lo, hi = (i - 0.3) * w, (i + 1.3) * w
    here = [m for m in marks if m["x1"] > lo and m["x0"] < hi]
    elsewhere = [m for m in marks if not (m["x1"] > lo and m["x0"] < hi)]
    best = max(here, key=lambda m: m["area"]) if here else None
    f = {"marks_here": len(here), "marks_elsewhere": len(elsewhere) / n}
    for k in ("area", "elong", "tilt", "fill", "dark", "gap"):
        f[k] = best[k] if best else 0.0
    f["abs_tilt"] = abs(f["tilt"])
    return f


def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    if not len(pos) or not len(neg):
        return float("nan")
    return float(((pos[:, None] > neg[None]) + 0.5 * (pos[:, None] == neg[None])).mean())


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    rows = []
    for path in sorted(glob.glob("work/probes/ocr-trust/*.json")):
        book = Path(path).stem
        source = Path("work") / book / "source.pdf"
        if not source.exists():
            continue
        doc = pymupdf.open(source)
        for r in json.load(open(path)):
            if not r.get("settled"):
                continue
            s = r["suspect"]
            for k, v in enumerate(s["others"], 1):
                if trust.kind(s["ours"], v) != "accent":
                    continue
                i = marked_letter(s["ours"], v)
                if i is None or not (r["right"][0] or r["right"][k]):
                    continue
                layer_marked = s["ours"][i] != strip(s["ours"][i])
                f = measure(doc[s["page"] - 1], s, i)
                if f is None:
                    continue
                print_marked = layer_marked if r["right"][0] else not layer_marked
                rows.append(
                    {
                        "book": book, "page": s["page"], "ours": s["ours"], "other": v,
                        "letter": strip(s["ours"][i]).lower(), "layer_marked": layer_marked,
                        "marked": print_marked, "layer_right": r["right"][0], **f,
                    }
                )  # fmt: skip
        print(book, len(rows), file=sys.stderr)
    if out:
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    y = np.array([r["marked"] for r in rows])
    print(f"{len(rows)} places, {y.sum()} marked in print")
    feats = ["marks_here", "area", "elong", "abs_tilt", "fill", "dark", "gap", "marks_elsewhere"]
    for k in feats:
        x = np.array([r[k] for r in rows])
        print(f"{k:16} AUC {auc(x[y], x[~y]):.3f}")
