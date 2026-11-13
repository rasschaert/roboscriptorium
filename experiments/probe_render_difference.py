"""Render and compare: does judging only where two versions' drawings differ tell them
apart better than the whole strip's fit (the checklist, "More tactics")? A comma against
a stop changes little of a word's ink, so the whole-strip fit hardly moves. Here each
of two versions is laid where it fits best, and the two are compared with the scan only
on the pixels where their drawings disagree. On a sample of the trust data's labelled
two-version places, by kind of difference. No models.

    uv run python experiments/probe_render_difference.py <book> [more …]
    uv run python experiments/probe_render_difference.py --report

Writes work/probes/render-difference/<book>.json.
"""

import json
import random
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from PIL import ImageFilter
from scipy.signal import fftconvolve

from roboscriptorium import ocr, pdf, rendercheck, trustdata
from roboscriptorium.book import Book
from roboscriptorium.rendercheck import RENDER_PX, STRETCHES, _picture, _spread

OUT = Path("work/probes/render-difference")
PLACES = 600
BLUR = ImageFilter.GaussianBlur(1.5)


def kind(a: str, b: str) -> str:
    def bare(s):
        return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))

    def letters(s):
        return "".join(c for c in s if c.isalnum())

    if a.replace(" ", "") == b.replace(" ", ""):
        return "space"
    if bare(a) == bare(b):
        return "accent"
    if a.lower() == b.lower():
        return "case"
    if letters(a) == letters(b):
        return "punctuation"
    return "letters"


def _canvas(ink, pad):
    strip = np.asarray(_picture(ink).filter(BLUR), np.float32)
    return np.pad(strip, ((pad[0], pad[0]), (pad[1], pad[1]))), float((strip * strip).sum())


def placed(face, spread, size, ink, version, pad, anchor=None):
    """The version's best-fitting drawing on the strip's canvas (padded by `pad`): its
    fit, the drawing laid on the canvas, and where (top, left, width, stretch). With
    `anchor` (stretch, top, left or None, right or None) it is laid at that stretch
    within a few pixels of that corner, so two versions sharing a start or an end lie
    letter on letter."""
    canvas, energy = _canvas(ink, pad)
    best = (0.0, None, None)
    slack = max(2, round(size * 0.06))
    for glyphs in rendercheck.drawings(face, version):
        high = max(4, round(glyphs.shape[0] * size / RENDER_PX))
        for stretch in STRETCHES if anchor is None else (anchor[0],):
            wide = max(4, round(glyphs.shape[1] * size / RENDER_PX * stretch))
            if high > canvas.shape[0] or wide > canvas.shape[1]:
                continue
            sized = _spread(_picture(glyphs).resize((wide, high)), spread)
            mine = np.asarray(sized.filter(BLUR), np.float32)
            over = fftconvolve(canvas, mine[::-1, ::-1], mode="valid")
            if anchor is not None:
                _, top, left, right = anchor
                x0 = left if left is not None else right - wide
                window = np.full_like(over, -np.inf)
                ys = slice(max(0, top - 3 * slack), top + 3 * slack + 1)
                xs = slice(max(0, x0 - slack), x0 + slack + 1)
                window[ys, xs] = over[ys, xs]
                over = window
                if not np.isfinite(over).any():
                    continue
            y, x = np.unravel_index(over.argmax(), over.shape)
            fit = float(over[y, x]) / (energy * float((mine * mine).sum())) ** 0.5
            if fit > best[0]:
                laid = np.zeros_like(canvas)
                laid[y : y + high, x : x + wide] = mine
                best = (fit, laid, (int(y), int(x), wide, stretch))
    return canvas, best


def _shared(a: str, b: str) -> tuple[int, int]:
    """How many characters two versions share at their start and at their end."""
    start = next(
        (i for i, (x, y) in enumerate(zip(a, b, strict=False)) if x != y), min(len(a), len(b))
    )
    end = next(
        (i for i, (x, y) in enumerate(zip(a[::-1], b[::-1], strict=False)) if x != y),
        min(len(a), len(b)),
    )
    return start, end


def local_errors(face, found, ink, versions, pad):
    """Each version's squared error against the scan on the pixels where the two
    drawings differ, the second laid letter on letter with the first's best fit and the
    other way round, the better-fitting anchor kept; and how many pixels differ."""
    start, end = _shared(*versions)
    out = None
    for first in (0, 1):
        canvas, (fit, a, at) = placed(face, found.spread, found.size, ink, versions[first], pad)
        if a is None:
            continue
        y, x, wide, stretch = at
        anchor = (stretch, y, x, None) if start >= end else (stretch, y, None, x + wide)
        _, (_, b, _) = placed(face, found.spread, found.size, ink, versions[1 - first], pad, anchor)
        if b is None:
            continue
        differ = np.abs(a - b) > 64
        n = int(differ.sum())
        errors = [float((((d - canvas) ** 2) * differ).sum()) / max(n, 1) for d in (a, b)]
        # Per version, on those pixels: drawing without ink under it, ink it doesn't draw.
        parts = [
            (
                float((np.clip(d - canvas, 0, None) * differ).sum()) / max(n, 1) / 255,
                float((np.clip(canvas - d, 0, None) * differ).sum()) / max(n, 1) / 255,
            )
            for d in (a, b)
        ]
        if first:
            errors.reverse()
            parts.reverse()
        if out is None or fit > out[0]:
            out = (fit, errors, n, parts)
    return out


def probe(name: str) -> None:
    book = Book.load(Path("work") / name)
    layer = pdf.cached_text_layer(
        book.source, book.stages / "textlayer.json", ocr.language(book.language)
    )
    texts = {p.number: p for p in layer}
    held = json.loads((book.stages / "typeface.json").read_text())["match"]
    found = rendercheck.Match(**held)
    face = rendercheck.Face.from_file(Path("work/fonts") / found.file)
    rows = [
        r
        for r in trustdata.load(name)
        if r["settled"] and sum(r["right"]) == 1 and not r["suspect"]["others"][1:]
    ]
    rows = random.Random(0).sample(rows, min(PLACES, len(rows)))
    out = []
    with pdf.PDF_LOCK, pymupdf.open(book.source) as doc:
        for r in rows:
            s = r["suspect"]
            versions = [s["ours"], s["others"][0]]
            ink = rendercheck.place_ink(doc[s["page"] - 1], s["box"], texts.get(s["page"]))
            if ink is None or not all(v.strip() for v in versions):
                continue
            pad = (round(found.size * 1.2), round(found.size * 3))
            whole = rendercheck.fits(face, found.spread, found.size, ink, versions)
            local = local_errors(face, found, ink, versions, pad)
            if local is None:
                continue
            _, errors, n, parts = local
            out.append(
                {
                    "kind": kind(*versions),
                    "right": r["right"].index(True),
                    "fits": whole,
                    "errors": errors,
                    "pixels": n,
                    "parts": parts,
                    "longer": int(len(versions[1]) > len(versions[0])),
                    "same": len(versions[0]) == len(versions[1]),
                }
            )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(out))
    print(f"{name}: {len(out)} places", flush=True)


def report() -> None:
    by = defaultdict(lambda: [0, 0, 0, 0])
    books = {}
    for path in sorted(OUT.glob("*.json")):
        whole = local = n = 0
        for r in json.loads(path.read_text()):
            w = int(np.argmax(r["fits"])) == r["right"]
            d = (int(np.argmin(r["errors"])) if r["pixels"] else int(np.argmax(r["fits"]))) == r[
                "right"
            ]
            row = by[r["kind"]]
            row[0] += w
            row[1] += d
            row[2] += w or d
            row[3] += 1
            whole, local, n = whole + w, local + d, n + 1
        books[path.stem] = (whole / n, local / n, n)
    print("kind          places  whole strip  where they differ  either")
    for k, (w, d, e, n) in sorted(by.items(), key=lambda kv: -kv[1][3]):
        print(f"{k:12} {n:7}  {w / n:10.1%}  {d / n:16.1%}  {e / n:6.1%}")
    w, d, e, n = (sum(v[i] for v in by.values()) for i in range(4))
    print(f"{'all':12} {n:7}  {w / n:10.1%}  {d / n:16.1%}  {e / n:6.1%}")
    print("\nper book: whole strip → where they differ")
    for name, (w, d, n) in books.items():
        print(f"  {name[:42]:42} {w:.1%} → {d:.1%}  ({n})")


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        for name in sys.argv[1:]:
            probe(name)
