"""How a book prints its dashes, measured on the scan: en or em, and the gaps around them.

For each dash the text layer has (it writes every dash as an em dash), the dash's
stroke is found on the page image: a run of columns whose ink is a thin band
around mid-height, near where the layer puts the dash. Its length is compared
with the line's mean letter width (an en dash is about one letter, an em dash
about two), and the blank columns on either side with the same.

    uv run python experiments/probe_dashes.py work/stella work/reis-om-mijn-schedel--ia-scan …
"""

import statistics
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

from roboscriptorium.book import Book

DPI = 300
SCALE = DPI / 72
DASHES = "—–"


def ink(gray: np.ndarray) -> np.ndarray:
    # Otsu's threshold on the crop.
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    total, cum, mean_all = gray.size, 0.0, (hist * np.arange(256)).sum()
    best, t_best, w0 = 0.0, 128, 0.0
    for t in range(256):
        w0 += hist[t]
        if w0 == 0 or w0 == total:
            continue
        cum += t * hist[t]
        m0, m1 = cum / w0, (mean_all - cum) / (total - w0)
        between = w0 * (total - w0) * (m0 - m1) ** 2
        if between > best:
            best, t_best = between, t
    return gray <= t_best


def measure(page: pymupdf.Page, word: tuple, line_words: list[tuple]) -> dict | None:
    x0, y0, x1, y1, text = word[:5]
    letters = [w for w in line_words if w[4].isalpha() and len(w[4]) >= 3]
    if not letters:
        return None
    char_w = statistics.median((w[2] - w[0]) / len(w[4]) for w in letters)
    at = text.find(next(c for c in text if c in DASHES))
    expect = x0 + (x1 - x0) * (at + 0.5) / len(text)
    clip = pymupdf.Rect(expect - 4 * char_w, y0, expect + 4 * char_w, y1)
    pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=pymupdf.csGRAY)
    gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    dark = ink(gray)
    h = dark.shape[0]
    rows = np.arange(h)
    thin, empty = [], []
    for c in range(dark.shape[1]):
        col = rows[dark[:, c]]
        empty.append(len(col) == 0)
        thin.append(
            len(col) > 0 and col[-1] - col[0] <= 0.15 * h and 0.3 * h <= col.mean() <= 0.8 * h
        )
    # The run of thin columns nearest the expected place.
    runs, start = [], None
    for c, t in enumerate([*thin, False]):
        if t and start is None:
            start = c
        elif not t and start is not None:
            runs.append((start, c))
            start = None
    centre = (expect - clip.x0) * SCALE
    runs = [r for r in runs if r[1] - r[0] >= 0.25 * char_w * SCALE]
    if not runs:
        return None
    a, b = min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - centre))
    left = 0
    while a - left - 1 >= 0 and empty[a - left - 1]:
        left += 1
    right = 0
    while b + right < len(empty) and empty[b + right]:
        right += 1
    unit = char_w * SCALE
    return {
        "length": (b - a) / unit,
        "left": left / unit if a - left > 0 else None,
        "right": right / unit if b + right < len(empty) else None,
    }


def main(dirs: list[str]) -> None:
    for d in dirs:
        book = Book.load(Path(d))
        first, last = book.body_pages
        found = []
        with pymupdf.open(book.source) as pdf:
            for n in range(first, last + 1):
                page = pdf[n - 1]
                words = page.get_text("words")
                for w in words:
                    if any(c in DASHES for c in w[4]):
                        same_line = [v for v in words if v[5] == w[5] and v[6] == w[6]]
                        if (m := measure(page, w, same_line)) is not None:
                            found.append(m)
        if not found:
            print(f"{Path(d).name}: no dashes measured")
            continue
        lengths = [m["length"] for m in found]
        gaps = [g for m in found for g in (m["left"], m["right"]) if g is not None]
        en = sum(x < 1.5 for x in lengths)
        print(
            f"{Path(d).name[:34]:34} {len(found):4} dashes: length {statistics.median(lengths):.2f} "
            f"letters (en-like {en}, em-like {len(found) - en}); gaps median "
            f"{statistics.median(gaps):.2f}, quartiles "
            f"{np.percentile(gaps, 25):.2f}–{np.percentile(gaps, 75):.2f} letters"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
