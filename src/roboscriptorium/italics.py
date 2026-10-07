"""Italic words, from the slant of their strokes on the page image.

Each text-layer word is cropped from the page image and its ink (above the
baseline: a y's descender leans like italic) is sheared by a range of angles.
The angle at which the strokes line up most sharply is the word's slant; italic
type leans about 10–15°, roman stands upright. Ink is what is darker than the
page's own threshold (Otsu), so pale scans count their grey strokes. No model.

Only words with an upright stem to measure are: two stems, or one in a word
without diagonal letters. A word of round and diagonal letters ("zo", "ze")
leans like italic whatever its type. An unmeasured word between two italic
words is italic ("I can talk").
"""

import json
import re
from dataclasses import replace
from pathlib import Path

import numpy as np
import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium.files import write_atomic
from roboscriptorium.ir import Block, Paragraph, SourceRef
from roboscriptorium.pdf import PageText, line_words, spells

VERSION = 7
DPI = 300
ANGLES = np.arange(-25, 26, 1)
ITALIC_AT = 8  # degrees of slant
# Upright stems per letter, in roman and italic alike.
STEMS = {c: 1 for c in "bdfijklpqrtBDEFIJKLPRT"} | {c: 2 for c in "hnuHNU"} | {"m": 3, "M": 2}
DIAGONALS = set("kvwxyzAKVWXYZ")


def ink_threshold(gray: np.ndarray) -> int:
    """The grey level that best splits a page into ink and paper (Otsu)."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    levels = np.arange(256)
    weight = np.cumsum(hist)
    mean = np.cumsum(hist * levels)
    total, total_mean = weight[-1], mean[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (total_mean * weight - mean * total) ** 2 / (weight * (total - weight))
    return int(np.nanargmax(between[:-1]))


def slant(gray: np.ndarray, threshold: int = 128) -> float:
    """The shear angle (degrees, leaning right) that makes a word's strokes most upright.

    Ink is darker than `threshold`.
    """
    ink = gray < threshold
    rows = ink.sum(axis=1)
    if rows.max(initial=0) == 0:
        return float("nan")
    baseline = int(np.nonzero(rows >= 0.4 * rows.max())[0].max())
    ys, xs = np.nonzero(ink[: baseline + 1])
    if len(xs) < 30:
        return float("nan")
    ys = ys.max() - ys
    best, best_score = float("nan"), -1.0
    for a in ANGLES:
        sheared = xs - ys * np.tan(np.radians(a))
        hist = np.bincount(np.round(sheared - sheared.min()).astype(int)).astype(float)
        if (score := float((hist**2).sum())) > best_score:
            best, best_score = float(a), score
    return best


def detect(pdf: Path, pages: list[PageText], cache: Path) -> dict[SourceRef, frozenset[int]]:
    """Per text-layer line, the indices of its italic words in `line.text.split(" ")`.

    Only lines whose text-layer words spell the line are measured. Cached per page.
    """
    done: dict[str, dict[str, list[int]]] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == VERSION:
            done = raw["pages"]
    todo = [p for p in pages if str(p.number) not in done]
    if todo:
        with pymupdf.open(pdf) as doc:
            for page in todo:
                done[str(page.number)] = _page(doc[page.number - 1], page)
        write_atomic(cache, json.dumps({"version": VERSION, "pages": done}))
    return {
        SourceRef(p.number, int(k)): frozenset(v)
        for p in pages
        for k, v in done[str(p.number)].items()
    }


def _page(pdf_page: pymupdf.Page, page: PageText) -> dict[str, list[int]]:
    pix = pdf_page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    scale = DPI / 72
    threshold = ink_threshold(img)
    out = {}
    for k, (line, words) in enumerate(
        zip(page.lines, line_words(pdf_page.get_text("words"), page), strict=True)
    ):
        if not words or not spells(words, line.text):
            continue
        leaning = []
        for w in words:
            if not _measurable(w[4]):
                leaning.append(None)
                continue
            x0, y0, x1, y1 = (int(v * scale) for v in w[:4])
            leaning.append(slant(img[max(0, y0) : y1, max(0, x0) : x1], threshold) >= ITALIC_AT)
        if italic := _fill(leaning):
            out[str(k)] = italic
    return out


def _measurable(word: str) -> bool:
    stems = sum(STEMS.get(c, 0) for c in word)
    return stems >= 2 or (stems == 1 and not DIAGONALS & set(word))


def _fill(leaning: list[bool | None]) -> list[int]:
    """Italic word indices; an unmeasured word between two italic ones is italic."""
    out = []
    for i, v in enumerate(leaning):
        if v:
            out.append(i)
        elif v is None:
            before = next((x for x in reversed(leaning[:i]) if x is not None), False)
            after = next((x for x in leaning[i + 1 :] if x is not None), False)
            if before and after:
                out.append(i)
    return out


def _key(word: str) -> str:
    return re.sub(r"\W+", "", word.lower())


def mark(
    blocks: list[Block], pages: list[PageText], italic: dict[SourceRef, frozenset[int]]
) -> list[Block]:
    """Copies of the blocks whose paragraphs carry their italic words.

    `pages` is the text layer the italics were measured on. A paragraph's words
    are aligned with its source lines' words, so OCR fixes, joined hyphenations
    and typed corrections don't shift the marks.
    """
    lines = {(p.number, k): ln for p in pages for k, ln in enumerate(p.lines)}
    out = []
    for block in blocks:
        if not isinstance(block, Paragraph) or not any(s in italic for s in block.sources):
            out.append(block)
            continue
        source: list[tuple[str, bool]] = []
        for ref in block.sources:
            if (line := lines.get((ref.page, ref.line))) is None:
                continue
            marks = italic.get(ref, frozenset())
            source += [(w, i in marks) for i, w in enumerate(line.text.split(" "))]
        words = block.text.split()
        found = set()
        for op in Levenshtein.opcodes([_key(w) for w, _ in source], [_key(w) for w in words]):
            if op.tag == "insert":
                continue
            flags = [f for _, f in source[op.src_start : op.src_end]]
            if op.tag == "equal":
                found |= {op.dest_start + k for k, f in enumerate(flags) if f}
            elif op.tag == "replace" and 2 * sum(flags) > len(flags):
                found |= set(range(op.dest_start, op.dest_end))
        out.append(replace(block, italic=tuple(sorted(found))) if found else block)
    return out
