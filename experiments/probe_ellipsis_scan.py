"""How each golden book prints its ellipses, measured on the scan, against what its text
layer says (`typography.guess_ellipsis`) and what its reference sets.

For each ellipsis the layer reads ("...", "…", ". . ." in a word), the line is cropped
around it; dots are short runs of ink near the baseline. Three in a row are the ellipsis:
the blank before the first (after the letter it follows) and between them, in letters,
against the word gaps on the same line.

uv run python experiments/probe_ellipsis_scan.py [book-dir …]   (default: tuning and validation)
"""

import re
import statistics
import sys
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import bench, typography
from roboscriptorium.book import Book
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.pdf import page_words
from roboscriptorium.typography import DPI, SCALE, _ink, _runs

ENOUGH = 60
ELL = re.compile(r"…|\.\s?\.\s?\.")


def measure(page, word, line):
    x0, y0, x1, y1, text = word[:5]
    letters = [w for w in line if w[4].isalpha() and len(w[4]) >= 3]
    if not letters:
        return None
    char_w = statistics.median((w[2] - w[0]) / len(w[4]) for w in letters)
    m = ELL.search(text)
    if m is None:
        return None
    at = x0 + (x1 - x0) * m.start() / len(text)
    clip = pymupdf.Rect(at - 3 * char_w, y0, at + 5 * char_w, y1)
    pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=pymupdf.csGRAY)
    dark = _ink(np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width))
    h, rows = dark.shape[0], np.arange(dark.shape[0])
    ink = [bool(dark[:, c].any()) for c in range(dark.shape[1])]
    runs = _runs(ink)
    unit = char_w * SCALE

    def dot(r):
        cols = dark[:, r[0] : r[1]].any(axis=1)
        ys = rows[cols]
        width = r[1] - r[0]
        return (
            len(ys) > 0
            and ys[-1] - ys[0] <= 0.22 * h
            and ys.mean() >= 0.5 * h
            and 0.08 * unit <= width <= 0.6 * unit
        )

    centre = (at - clip.x0) * SCALE
    best = None
    for i in range(len(runs) - 2):
        three = runs[i : i + 3]
        if all(dot(r) for r in three) and (i + 3 == len(runs) or not dot(runs[i + 3])):
            if i > 0 and dot(runs[i - 1]):
                continue
            d = abs(three[0][0] - centre)
            if best is None or d < best[0]:
                best = (d, i)
    if best is None:
        return None
    i = best[1]
    a, b, c = runs[i : i + 3]
    before = (a[0] - runs[i - 1][1]) / unit if i > 0 else None
    return {
        "before": before,
        "between": [(b[0] - a[1]) / unit, (c[0] - b[1]) / unit],
        "char_w": char_w,
    }


def word_gaps(page, line, char_w):
    """Blank runs between the layer's word boxes on the line, in letters."""
    out = []
    for v, w in zip(line, line[1:], strict=False):
        if not v[4][-1:].isalpha() or not w[4][:1].isalpha():
            continue
        clip = pymupdf.Rect(v[2] - 2 * char_w, v[1], w[0] + 2 * char_w, v[3])
        pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=pymupdf.csGRAY)
        dark = _ink(np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width))
        blanks = [r for r in _runs([not dark[:, c].any() for c in range(dark.shape[1])])]
        inner = [r for r in blanks if 0 < r[0] and r[1] < dark.shape[1]]
        if inner:
            r = max(inner, key=lambda r: r[1] - r[0])
            out.append((r[1] - r[0]) / (char_w * SCALE))
        if len(out) >= 3:
            break
    return out


def probe(book_dir: Path, pages: tuple[int, int] | None):
    book = Book.load(book_dir)
    first, last = pages or tuple(book.body_pages)
    found, gaps, layer = [], [], []
    with pymupdf.open(book.source) as pdf:
        for n in range(first, last + 1):
            if len(found) >= ENOUGH:
                break
            page = pdf[n - 1]
            words = page_words(page)
            for w in words:
                if not ELL.search(w[4]) or not re.search(r"\w", w[4][:1] + w[4]):
                    continue
                # Only an ellipsis after a letter in the same word: "Ka...", "dear..."
                m = ELL.search(w[4])
                if m.start() == 0 or not w[4][m.start() - 1].isalpha():
                    continue
                line = [v for v in words if v[5] == w[5] and v[6] == w[6]]
                if (r := measure(page, w, line)) is None:
                    continue
                found.append(r)
                layer.append(w[4])
                gaps += word_gaps(page, line, r["char_w"])
    return book, found, gaps


def reference_style(book):
    if not book.golden:
        return "?"
    text = " ".join(
        p for ch in load_chapters(Golden.load(book.golden).text_dir) for p in ch.paragraphs
    )
    runs = re.findall(r"(\w)(\s?)(…|\.\s?\.\s?\.)", text)
    if not runs:
        return "none"
    from collections import Counter

    c = Counter((sp != "", "spaced" if " " in d or " " in d else "glyph" if d == "…" else "tight") for _, sp, d in runs)
    return ", ".join(f"{'space' if s else 'glued'}+{k} {v}" for (s, k), v in c.most_common(3))


def main():
    specs = sys.argv[1:] or [s for k in ("tuning", "validation") for s in bench.SETS[k]]
    for spec in specs:
        name, *rest = spec.split(":")
        pages = None
        if rest and rest[0]:
            a, b = rest[0].split("-")
            pages = (int(a), int(b))
        d = Path("work") / name if not name.startswith("work") else Path(name)
        book, found, gaps = probe(d, pages)
        if not found:
            print(f"{d.name[:34]:35} no ellipses measured")
            continue
        before = [m["before"] for m in found if m["before"] is not None]
        between = [g for m in found for g in m["between"]]
        print(
            f"{d.name[:34]:35} n={len(found):2}  before {statistics.median(before):.2f}"
            f" [{np.percentile(before, 25):.2f}–{np.percentile(before, 75):.2f}]"
            f"  between {statistics.median(between):.2f}"
            f"  word gap {statistics.median(gaps) if gaps else float('nan'):.2f}"
            f"  | ref {reference_style(book)}"
        )


if __name__ == "__main__":
    main()
