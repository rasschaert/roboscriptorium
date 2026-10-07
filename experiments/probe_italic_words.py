"""Probe: does a word's stroke slant in the scan tell italic from roman type?

Each word box from the text layer is cropped from the page image, and its ink is
sheared by a range of angles; the angle at which the strokes line up most
sharply (the column profile is most peaked) is the word's slant. No model.

Truth from the Gutenberg EPUB's <i>/<em>: each italic phrase is found, with the
words before it, in a page's text layer; its words there are italic. Words on
pages with no italic phrase are roman. Phrases that can't be placed are left
out, so a few "roman" words may be italic.

    uv run python experiments/probe_italic_words.py work/the-story-of-doctor-dolittle--stokes-1920 \
        work/.cache/gutenberg/501.epub
"""

import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium.book import Book

XHTML = "{http://www.w3.org/1999/xhtml}"
CONTEXT = 3
DPI = 300
ANGLES = np.arange(-25, 26, 1)
MIN_LETTERS = 3
REPEATS = 3  # a word seen this often has a usual slant to compare with  # shorter words have too few strokes to measure


def norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def italic_phrases(epub: Path) -> list[tuple[list[str], list[str]]]:
    """(words before, italic words) for each italic phrase in the EPUB."""
    out = []
    with zipfile.ZipFile(epub) as z:
        for name in z.namelist():
            if not name.endswith((".html", ".xhtml")):
                continue
            root = ET.fromstring(z.read(name))
            for p in root.iter(f"{XHTML}p"):
                text = ""
                for node in p.iter():
                    if node.tag in (f"{XHTML}i", f"{XHTML}em") and (node.text or "").strip():
                        italic = norm("".join(node.itertext())).split()
                        if italic:
                            out.append((norm(text).split()[-CONTEXT:], italic))
                    text += node.text or ""
                    text += node.tail or "" if node is not p else ""
    return out


def slant(gray: np.ndarray) -> tuple[float, float]:
    """The shear angle (degrees, leaning right) that makes the strokes most upright, and
    how much sharper the strokes are at that angle than upright (1 = no gain)."""
    ink = gray < 128
    # Below the baseline only descenders lie, whose long diagonal (y, g) leans like italic.
    rows = ink.sum(axis=1)
    if rows.max() == 0:
        return float("nan"), float("nan")
    baseline = int(np.nonzero(rows >= 0.4 * rows.max())[0].max())
    ink = ink[: baseline + 1]
    ys, xs = np.nonzero(ink)
    if len(xs) < 30:
        return float("nan"), float("nan")
    ys = ys.max() - ys  # height above the bottom
    scores = {}
    for a in ANGLES:
        sheared = xs - ys * np.tan(np.radians(a))
        hist = np.bincount(np.round(sheared - sheared.min()).astype(int))
        scores[float(a)] = float((hist.astype(float) ** 2).sum())
    best = max(scores, key=scores.get)
    return best, scores[best] / scores[0.0]


def main() -> None:
    book = Book.load(Path(sys.argv[1]))
    phrases = italic_phrases(Path(sys.argv[2]))
    first, last = book.body_pages
    rows = []  # (page, word, italic, slant)
    with pymupdf.open(book.source) as doc:
        pages = {}
        for n in range(first, last + 1):
            words = doc[n - 1].get_text("words")
            pages[n] = (words, [norm(w[4]) for w in words])
        italic_at: dict[int, set[int]] = {}
        for before, italic in phrases:
            seq = before + italic
            hits = []
            for n, (_, normed) in pages.items():
                flat = [(i, t) for i, w in enumerate(normed) for t in w.split()]
                tokens = [t for _, t in flat]
                for k in range(len(tokens) - len(seq) + 1):
                    if tokens[k : k + len(seq)] == seq:
                        hits.append((n, [flat[j][0] for j in range(k + len(before), k + len(seq))]))
            if len(hits) == 1:
                n, idx = hits[0]
                italic_at.setdefault(n, set()).update(idx)
        print(f"{len(phrases)} italic phrases, {sum(map(len, italic_at.values()))} italic words "
              f"placed on {len(italic_at)} pages")
        for n in sorted(pages):
            page = doc[n - 1]
            words, _ = pages[n]
            pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
            scale = DPI / 72
            top = min((w[1] for w in words), default=0)
            for i, w in enumerate(words):
                # The top line is the running head; this book sets it in italics.
                if sum(c.isalpha() for c in w[4]) < MIN_LETTERS or w[1] < top + 8:
                    continue
                x0, y0, x1, y1 = (int(v * scale) for v in w[:4])
                crop = img[max(0, y0) : y1, max(0, x0) : x1]
                rows.append((n, w[4], i in italic_at.get(n, set()), *slant(crop)))
    # Each word's usual slant: the median over its instances in the book.
    by_word: dict[str, list[float]] = {}
    for _, w, _, a, _ in rows:
        by_word.setdefault(norm(w), []).append(a)
    usual = {w: float(np.nanmedian(v)) for w, v in by_word.items() if len(v) >= REPEATS}
    for rule in ("absolute", "relative"):
        def italic_word(w, a, rule=rule):
            if rule == "relative" and norm(w) in usual:
                return a - usual[norm(w)] >= 6
            return a >= 8
        caught = sum(italic_word(w, a) for _, w, t, a, _ in rows if t)
        flagged = [(n, w, a) for n, w, t, a, _ in rows if not t and italic_word(w, a)]
        print(f"{rule}: italic caught {caught}/{sum(r[2] for r in rows)}, roman flagged "
              f"{len(flagged)}/{sum(not r[2] for r in rows)}")
        print("   ", " ".join(f"p{n}:{w}:{a:.0f}" for n, w, a in flagged))
        print("    missed:", " ".join(f"p{n}:{w}:{a:.0f}" for n, w, t, a, _ in rows
                                     if t and not italic_word(w, a)))
    italic = [(a, g) for _, _, t, a, g in rows if t]
    roman = [(a, g) for _, _, t, a, g in rows if not t]
    print(f"italic words: {len(italic)}, median slant {np.nanmedian([a for a, _ in italic]):.0f}°")
    print(f"roman words: {len(roman)}, median slant {np.nanmedian([a for a, _ in roman]):.0f}°")
    for gain in (1.0, 1.1, 1.2, 1.3, 1.5):
        caught = sum(a >= 8 and g >= gain for a, g in italic)
        flagged = sum(a >= 8 and g >= gain for a, g in roman)
        print(f"slant >= 8° and gain >= {gain}: italic caught {caught}/{len(italic)}, "
              f"roman flagged {flagged}/{len(roman)}")
    print("italic words:")
    for n, w, t, a, g in rows:
        if t:
            print(f"  p{n} {w!r} {a:.0f}° gain {g:.2f}")
    print("roman words read as slanted (>= 8°):")
    for n, w, t, a, g in [r for r in rows if not r[2] and r[3] >= 8]:
        print(f"  p{n} {w!r} {a:.0f}° gain {g:.2f}")


if __name__ == "__main__":
    main()
