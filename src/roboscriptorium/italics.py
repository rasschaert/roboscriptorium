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

A word's slant counts from its page's upright words, so a page scanned askew leans
none of its words. A word leaning alone, among upright neighbours, and measured on fewer
than LONE_STEMS stems needs LONE_AT: "op" or "een" reads a few degrees off.
"""

import re
import statistics
from dataclasses import replace
from pathlib import Path

import numpy as np
import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium import ink
from roboscriptorium.files import read_cache, write_cache
from roboscriptorium.ir import Block, Paragraph, SourceRef
from roboscriptorium.pdf import PageText, line_words, lines_digest, page_words, spells

VERSION = 9
DPI = 300
ANGLES = np.arange(-25, 26, 1)
ITALIC_AT = 8  # degrees of slant
# A page's upright is the median slant of its words below ITALIC_AT, when it has this many
# and they are this share of its measured words: on a page set in italic, those few are
# italic words read a little upright.
UPRIGHT_MIN = 10
UPRIGHT_SHARE = 0.6
# A word with no leaning neighbour and fewer stems than this is italic from LONE_AT. Read
# by eye: Hoe wij verdwijnen's upright "op", "een", "goed" lean 9–11° from their page's
# upright, Artemis' "good", "of", "faced" 8–9°, while its "quite", "some", "anyone",
# "not" (three stems or more) lean 8–11° in italic.
LONE_STEMS = 3
LONE_AT = 12
# Upright stems per letter, in roman and italic alike.
STEMS = {c: 1 for c in "bdfijklpqrtBDEFIJKLPRT"} | {c: 2 for c in "hnuHNU"} | {"m": 3, "M": 2}
DIAGONALS = set("kvwxyzAKVWXYZ")


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

    Only lines whose text-layer words spell the line are measured. Each word's slant is
    cached per page, with the page's lines, so a page whose lines change is measured
    again; the cut is drawn over all of `pages`.
    """
    raw = read_cache(cache, VERSION)
    done: dict[str, dict] = raw["pages"] if raw else {}
    todo = [p for p in pages if done.get(str(p.number), {}).get("lines") != lines_digest(p)]
    if todo:
        with pymupdf.open(pdf) as doc:
            for page in todo:
                done[str(page.number)] = {
                    "lines": lines_digest(page),
                    "slants": _page(doc[page.number - 1], page),
                }
        write_cache(cache, VERSION, {"pages": done})
    slants = {
        SourceRef(p.number, int(k)): _leaning(v, _upright(done[str(p.number)]["slants"]))
        for p in pages
        for k, v in done[str(p.number)]["slants"].items()
    }
    out = {}
    text = {
        SourceRef(p.number, k): ln.text.split(" ") for p in pages for k, ln in enumerate(p.lines)
    }
    for ref, line in slants.items():
        above = slants.get(SourceRef(ref.page, ref.line - 1), [])
        below = slants.get(SourceRef(ref.page, ref.line + 1), [])
        edges = (_last(above), _last(below[::-1]))
        stems = [_stems(w) for w in text[ref]]
        if italic := _fill(_italic(line, stems, edges)):
            out[ref] = frozenset(italic)
    return out


def _last(line: list[float | None]) -> float | None:
    return next((a for a in reversed(line) if a is not None), None)


def _page(pdf_page: pymupdf.Page, page: PageText) -> dict[str, list[float | None]]:
    """Per measured line, each word's slant in degrees (None where it can't be measured)."""
    pix = pdf_page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    scale = DPI / 72
    threshold = ink.threshold(img)
    out = {}
    for k, (line, words) in enumerate(
        zip(page.lines, line_words(page_words(pdf_page, page), page), strict=True)
    ):
        if not words or not spells(words, line.text):
            continue
        found: list[float | None] = []
        for w in words:
            if not _measurable(w[4]):
                found.append(None)
                continue
            x0, y0, x1, y1 = (int(v * scale) for v in w[:4])
            a = slant(img[max(0, y0) : y1, max(0, x0) : x1], threshold)
            found.append(None if np.isnan(a) else a)
        out[str(k)] = found
    return out


def _upright(lines: dict[str, list[float | None]]) -> float:
    """The page's upright slant: the median of its words that don't lean like italic."""
    measured = [a for line in lines.values() for a in line if a is not None]
    roman = [a for a in measured if abs(a) < ITALIC_AT]
    if len(roman) < UPRIGHT_MIN or len(roman) < UPRIGHT_SHARE * len(measured):
        return 0.0
    return statistics.median(roman)


def _leaning(line: list[float | None], upright: float) -> list[float | None]:
    return [None if a is None else a - upright for a in line]


def _italic(
    line: list[float | None], stems: list[int], edges: tuple[float | None, float | None]
) -> list[bool | None]:
    """Each word leaning like italic; one with no leaning measured neighbour and fewer than
    LONE_STEMS `stems` needs LONE_AT.

    `edges` are the measured words before the line's first and after its last (the line
    above's last, the line below's first), so a run carried over a line end keeps them.
    """
    measured = [i for i, a in enumerate(line) if a is not None]
    out: list[bool | None] = [None] * len(line)
    for n, i in enumerate(measured):
        beside = [line[j] for j in measured[max(0, n - 1) : n] + measured[n + 1 : n + 2]]
        if n == 0 and edges[0] is not None:
            beside.append(edges[0])
        if n == len(measured) - 1 and edges[1] is not None:
            beside.append(edges[1])
        a = line[i]
        alone = not any(b >= ITALIC_AT for b in beside)
        few = i >= len(stems) or stems[i] < LONE_STEMS
        out[i] = a >= (LONE_AT if alone and few else ITALIC_AT)
    return out


def _stems(word: str) -> int:
    return sum(STEMS.get(c, 0) for c in word)


def _measurable(word: str) -> bool:
    stems = _stems(word)
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


# A motto or dedication is set in one type: at most this many of its words measured
# otherwise than all the rest take the rest's type ("Voor", too round to measure, among
# italic words; "Zwart", whose Z and w lean, among upright ones).
APART_ODD = 1


def uniform(blocks: list[Block]) -> list[Block]:
    """Copies of the blocks with each motto's or dedication's lines set in one type, where
    all but `APART_ODD` of their words are."""
    out = list(blocks)
    k = 0
    while k < len(out):
        kind = _apart(out[k])
        if kind is None:
            k += 1
            continue
        end = k
        while end < len(out) and _apart(out[end]) == kind:
            end += 1
        group = out[k:end]
        words = sum(len(b.text.split()) for b in group)
        italic = sum(len(b.italic) for b in group)
        if words > APART_ODD and 0 < words - italic <= APART_ODD:
            out[k:end] = [replace(b, italic=tuple(range(len(b.text.split())))) for b in group]
        elif words > APART_ODD and 0 < italic <= APART_ODD:
            out[k:end] = [replace(b, italic=()) for b in group]
        k = end
    return out


def _apart(block: Block) -> str | None:
    if isinstance(block, Paragraph) and (block.epigraph or block.dedication):
        return "epigraph" if block.epigraph else "dedication"
    return None


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
            # A typed line has no ink measured: its words stay upright, not its neighbour's.
            if ref.typed or (line := lines.get((ref.page, ref.line))) is None:
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
