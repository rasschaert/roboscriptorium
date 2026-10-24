"""Can an acute accent be told from the dot of an i by its shape on the scan? (the per-book
alphabet's first question, decisions.md 2026-10-21.) No models.

On a book that prints stress accents often, every aligned body line whose reference holds an
acute or grave vowel (`accent`) and as many with none (`plain`), seeded; each line's crop cut
as the OCR check cuts it. The small marks above the letters (connected components narrower
and shorter than a letter, wholly above the line's middle) are measured: elongation (the long
axis over the short, from second moments) and tilt. Per line its most accent-like mark; the
AUC says how well that separates accented lines from plain ones.

    uv run python experiments/probe_accent_shape.py [book]
"""

import io
import random
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from tryout import _beside_break, _shifted, slice_of  # noqa: E402

from roboscriptorium import bench, disagreements, readers  # noqa: E402
from roboscriptorium.golden import scoring  # noqa: E402
from roboscriptorium.golden.align import align  # noqa: E402
from roboscriptorium.golden.manifest import Golden  # noqa: E402
from roboscriptorium.golden.reference import load_chapters  # noqa: E402
from roboscriptorium.pdf import cached_text_layer  # noqa: E402

ACCENTED = set("áéíóúàèìòùÁÉÍÓÚ")
# Lines with quote marks or apostrophes are left out: their marks sit above the letters too.
QUOTES = set("'\"‘’“”`´")


def marks(png: bytes) -> list[tuple[float, float]]:
    """(elongation, tilt in degrees from upright) of each small mark above the letters."""
    g = np.asarray(Image.open(io.BytesIO(png)).convert("L"), dtype=float)
    ink = g < (g.mean() - 2 * g.std() if g.std() else 128)
    rows = ink.sum(axis=1)
    if not rows.any():
        return []
    core = np.nonzero(rows > rows.max() * 0.5)[0]
    top = core.min()  # the x-height band's top: the rows most letters reach
    labels, n = ndimage.label(ink)
    out = []
    for i, sl in enumerate(ndimage.find_objects(labels), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if sl[0].stop > top + 1 or h > (core.max() - top) or w > (core.max() - top) or h * w < 4:
            continue
        ys, xs = np.nonzero(labels[sl] == i)
        if len(ys) < 4:
            continue
        # A pixel's own spread (1/12 each way) keeps a one-pixel line from dividing by zero.
        cov = np.cov(np.vstack([xs, ys])) + np.eye(2) / 12
        vals, vecs = np.linalg.eigh(cov)
        elong = float(np.sqrt(max(vals[1], 1e-6) / max(vals[0], 1e-6)))
        vx, vy = vecs[:, 1]
        # Signed tilt from upright: positive leans right at the top, as an acute does.
        tilt = float(np.degrees(np.arctan2(vx, -vy)))
        tilt = (tilt + 90) % 180 - 90
        out.append((elong, tilt))
    return out


def auc(pos: list[float], neg: list[float]) -> float:
    pairs = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return pairs / max(1, len(pos) * len(neg))


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "het-schaduwhuis--ia-scan"
    spec = next(s for s in bench.SETS["tuning"] if s.startswith(name))
    book, (first, last), chapters = slice_of(spec)
    pages = [p for p in cached_text_layer(book.source, book.stages / "textlayer.json") if first <= p.number <= last]
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if chapters:
        reference = reference[chapters[0] - 1 : chapters[1]]
    reference, _ = disagreements.patch(reference, scoring.verdicts(book))
    labels = align(pages, reference)
    by = {p.number: p for p in pages}
    accent, plain = [], []
    for ref, lab in labels.items():
        page = by[ref.page]
        text = page.lines[ref.line].text
        if lab.role != "body" or not lab.truth or _beside_break(page.lines, ref.line) or _shifted(text, lab.truth):
            continue
        if QUOTES & set(lab.truth):
            continue
        (accent if ACCENTED & set(lab.truth) else plain).append(ref)
    rng = random.Random(0)
    plain = rng.sample(plain, min(len(plain), len(accent)))
    scores = {"accent": [], "plain": []}
    with pymupdf.open(book.source) as doc:
        for kind, refs in (("accent", accent), ("plain", plain)):
            for ref in refs:
                boxes = readers.line_boxes(doc[ref.page - 1], by[ref.page])
                png = readers._line_crop(doc, ref.page, boxes[ref.line], readers.crop_span(boxes, ref.line))
                ms = marks(png)
                # The most accent-like mark: the longest, tilted ones counting most.
                scores[kind].append(sum(1.6 <= e <= 6 and 15 <= t <= 75 for e, t in ms))
    print(f"{name}: {len(accent)} accented lines, {len(plain)} plain")
    for q in (0.1, 0.5, 0.9):
        print(f"  {q:.0%}: accent {np.quantile(scores['accent'], q):.2f}  plain {np.quantile(scores['plain'], q):.2f}")
    print(f"  AUC {auc(scores['accent'], scores['plain']):.3f}")
