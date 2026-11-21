"""The outer mark of a nested quotation every reader drops: a doubt raised where the scan
shows three ticks.

A print opens a quotation inside a quotation with two marks ("‘“Lucy", closed "kind,”’"),
and the text layer and the readers often read the three ticks as a double mark alike, so
no difference raises it: 21 of the tuning bench's 460 silent errors (docs/decisions.md,
2026-11-15). The raised ink at a word's edge is measured on the scan, its width against
the height of the line's letters (`span`). A book's own double marks give the width a
double mark has in its typeface (`Nested.survey`, from the edges every reading sets
double); where an edge the build sets double is `RATIO` times as wide, the nested version
is offered as another version (`doubts`), which the judges and the arbiter settle like
any suspect. It decides nothing itself, and learns nothing across books: a mark's size is
the typeface's.

The widths are kept per book (`stages/quote-marks.json`).
"""

import re
import statistics
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import rendercheck
from roboscriptorium.files import code_stamp, read_cache, write_cache
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PageText, line_words, page_words

VERSION = 1
# How much wider than the book's double mark an edge's raised ink is for the nested
# version to be offered: 54 of the 74 nested marks the layer lacks in seven tuning books,
# and 131 of 5,852 double ones (`experiments/probe_nested_span.py`, 2026-11-15).
RATIO = 1.4
# Double marks a book must show for its usual width to be known, and the most measured.
FEWEST, MOST = 10, 400
SINGLE, DOUBLE = "‘’'", '“”"'
STOPS = ".,;:!?…"
_TOKEN = re.compile(r"\S+")


def _strip(page: pymupdf.Page, box) -> tuple[np.ndarray, int, float] | None:
    """The ink of the words at `box` out to the blanks around them, and on over raised
    marks beyond those blanks (quote marks a print sets off by a gap, which the layer's
    box leaves out); with the row at the middle of the line's letters and the line's
    height, both by the layer's box, in the strip's pixels."""
    x0, y0, x1, y1 = box
    high = y1 - y0
    clip = pymupdf.Rect(x0 - high * 3, y0 - high * 0.3, x1 + high * 3, y1 + high * 0.3)
    clip &= page.rect
    grey = rendercheck._clip_ink(page, clip)
    if grey is None:
        return None
    scale = rendercheck.DPI / 72
    mask = grey > 0.5
    cols = mask.any(0)
    gap = max(4, round(high * scale * rendercheck.WORD_GAP))
    middle = round((y0 + high * 0.55 - clip.y0) * scale)
    reach = high * scale * 0.6
    a, b = round((x0 - clip.x0) * scale), round((x1 - clip.x0) * scale)
    a, b = min(a + gap, b), max(b - gap, a)

    def raised(c0: int, c1: int) -> bool:
        rows = np.where(mask[:, c0:c1].any(1))[0]
        return len(rows) > 0 and rows[-1] < middle and c1 - c0 <= high * scale * 0.5

    for _ in range(4):
        while a > 0 and cols[max(0, a - gap) : a].any():
            a -= 1
        c1 = a - gap
        while c1 > 0 and not cols[c1 - 1] and a - c1 < reach:
            c1 -= 1
        c0 = c1
        while c0 > 0 and cols[c0 - 1]:
            c0 -= 1
        if not (c1 > c0 and raised(c0, c1)):
            break
        a = c0
    for _ in range(4):
        while b < len(cols) and cols[b : b + gap].any():
            b += 1
        c0 = b + gap
        while c0 < len(cols) and not cols[c0] and c0 - b < reach:
            c0 += 1
        c1 = c0
        while c1 < len(cols) and cols[c1]:
            c1 += 1
        if not (c1 > c0 and raised(c0, c1)):
            break
        b = c1
    return (grey[:, a:b], middle, high * scale) if b - a > 8 else None


def span(page: pymupdf.Page, box, opening: bool) -> float | None:
    """The width of the raised ink at the opening or closing edge of the words at `box`,
    in heights of the line: the runs of ink above the letters' middle, from the
    edge inward until a column with ink below it too. 0 where the edge has none; None
    where there is no ink to measure."""
    found = _strip(page, box)
    if found is None:
        return None
    # The line's height is the layer's box, not the word's own ink: a word without
    # ascenders ("course") is as tall as its x-height.
    ink, middle, high = found
    mask = ink > 0.5
    if mask.any(0).sum() < 4 or high < 8:
        return None
    upper, lower = mask[:middle].any(0), mask[middle:].any(0)
    if not opening:
        upper, lower = upper[::-1], lower[::-1]
    # Runs of raised ink from the edge: a run with ink below the middle in any of its
    # columns is a letter (a T's bar overhangs its stem), and ends them, as does a
    # blank wider than the marks' own gaps.
    first = last = None
    at, wide = int(np.argmax(upper | lower)), len(upper)
    while at < wide:
        if not (upper[at] or lower[at]):
            at += 1
            continue
        end = at
        while end < wide and (upper[end] or lower[end]):
            end += 1
        if lower[at:end].any() or (last is not None and at - last > high * 0.6):
            break
        first = at if first is None else first
        last = end
        at = end
    return 0.0 if first is None else (last - first) / high


def _marks(token: str, opening: bool) -> str:
    """The quote marks at a token's edge ("s" single, "d" double), stops between the
    closing ones left out."""
    out = ""
    for c in token if opening else reversed(token):
        if c in SINGLE:
            out += "s"
        elif c in DOUBLE:
            out += "d"
        elif opening or c not in STOPS:
            break
    return out


def nested(token: str, opening: bool, outer: str) -> str:
    """A token that opens or closes on a double mark, with the single mark a nested
    quotation sets beside it: outside the double mark in a book whose quotations are set
    in single marks (`outer` "s": "‘“Lucy", "kind,”’"), inside it in one set in double
    marks ("“‘Lucy", "kind,’”")."""
    # A straight mark gets a straight one beside it; the build curls both later.
    straight = '"' in (token[:1] if opening else token)
    if opening:
        mark = "'" if straight else "‘"
        return mark + token if outer == "s" else token[0] + mark + token[1:]
    mark = "'" if straight else "’"
    if outer == "s":
        return token + mark
    at = max(token.rfind(c) for c in DOUBLE)
    return token[:at] + mark + token[at:]


class Nested:
    """The nested quotation marks a book's scan shows where the build sets a double mark."""

    def __init__(self, cache: Path):
        self._cache = cache
        kept = read_cache(cache, VERSION, code=code_stamp(__name__))
        self._usual: float | None = kept["usual"] if kept else None
        self._outer: str = kept["outer"] if kept else "s"
        self._surveyed: bool = bool(kept)
        self._spans: dict[str, float | None] = kept["spans"] if kept else {}
        self._new = 0

    def survey(
        self, pdf: Path, pages: list[PageText], readings: dict[str, dict[SourceRef, str]]
    ) -> None:
        """The width of the book's double marks, from up to `MOST` word edges the layer
        and every reading of the line set double, and which mark its quotations are set
        in (the commoner opening one). Kept; a book with fewer than `FEWEST` such edges
        gets no offers."""
        if self._surveyed:
            return
        widths: list[float] = []
        opens = {"s": 0, "d": 0}
        with pymupdf.open(pdf) as doc:
            for page in pages:
                if len(widths) >= MOST:
                    break
                words = None
                for k, line in enumerate(page.lines):
                    ref = SourceRef(page.number, k)
                    tokens = line.text.split()
                    for t in tokens:
                        if (m := _marks(t, True)[:1]) in opens:
                            opens[m] += 1
                    others = [r[ref].split() for r in readings.values() if ref in r]
                    if not others or any(len(o) != len(tokens) for o in others):
                        continue
                    for i in range(len(tokens)):
                        for opening in (True, False):
                            if any(_marks(v[i], opening) != "d" for v in [tokens, *others]):
                                continue
                            if words is None:
                                words = line_words(page_words(doc[page.number - 1], page), page)
                            if [w[4] for w in words[k]] != tokens:
                                continue
                            got = span(doc[page.number - 1], words[k][i][:4], opening)
                            if got:
                                widths.append(got)
        self._usual = statistics.median(widths) if len(widths) >= FEWEST else None
        self._outer = "d" if opens["d"] > opens["s"] else "s"
        self._surveyed = True
        self._new += 1

    def doubts(
        self, page: pymupdf.Page, number: int, k: int, ours: str, taken, box_of
    ) -> list[tuple[int, int, list[str]]]:
        """Tokens of a line no reading disputes (outside `taken`) that open or close on a
        double mark whose raised ink is `RATIO` times the book's double mark or wider,
        each with its nested version as its one other version. `box_of` gives a span's box
        on the page."""
        if self._usual is None:
            return []
        out = []
        for m in _TOKEN.finditer(ours):
            a0, a1 = m.start(), m.end()
            if any(t0 < a1 and a0 < t1 for t0, t1 in taken):
                continue
            for opening in (True, False):
                if _marks(m.group(), opening) != "d" or len(m.group()) < 2:
                    continue
                key = f"{number}|{k}|{a0}|{int(opening)}|{m.group()}"
                if key not in self._spans:
                    self._spans[key] = span(page, box_of(a0, a1), opening)
                    self._new += 1
                got = self._spans[key]
                if got is not None and got >= RATIO * self._usual:
                    out.append((a0, a1, [nested(m.group(), opening, self._outer)]))
                    break
        return out

    def save(self) -> None:
        if self._new:
            write_cache(
                self._cache,
                VERSION,
                {"usual": self._usual, "outer": self._outer, "spans": self._spans},
                code=code_stamp(__name__),
            )
            self._new = 0
