"""Bulleted lists: a line opened by a bullet becomes a list item, its bullet drawn by the
EPUB's list instead of standing in the text.

A bullet is a solid blob of ink at the middle of the letters' height, a fraction of the
line's height tall and about as wide (`bullet`); the text layer reads it as "e", "¢" or
"*", which no reader can get right because no letter is printed. Each line whose first
token is short and whose ink there is such a blob is an item; the lines after it set at
the indent of its text continue it (`survey`). A book has lists only where it prints at
least `FEWEST` bullets, so a lone speck at a line's start makes none. The bullet's shape
is the book's: a blob that fills its box is a square, else a disc (`SQUARE`).

The items are kept per book (`stages/lists.json`).
"""

import statistics
from dataclasses import replace
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import rendercheck
from roboscriptorium.files import code_stamp, read_cache, write_cache
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PageText, line_words, page_words

VERSION = 1
# A bullet's height and width, as shares of its line's strip (`rendercheck.place_ink`:
# the line and 0.3 of its height either side): Nervous System's squares are 0.19 to
# 0.2, a lower-case letter's body 0.28 and more, a full stop 0.06.
TALL = (0.1, 0.26)
# Its width against its height: a dash is several times wider than tall.
ASPECT = (0.6, 1.6)
# The share of its box it inks: a square or disc 0.75 and more, a letter under 0.55.
SOLID = 0.65
# Where its middle sits, as a share of the strip from the top: the letters' middle.
MIDDLE = (0.45, 0.72)
# A median fill this high is a square, else a disc (a disc fills pi/4 of its box).
SQUARE = 0.82
# Bullets a book must print for its lists to be taken.
FEWEST = 2
# How far a continuation line's start may lie from its item's text, in points.
ALIGN = 2.5
# The longest token that may be a misread bullet.
MARKER = 2


def bullet(ink: np.ndarray) -> float | None:
    """How much of its box a line's first mark inks, where the mark is a bullet: a solid
    blob at the letters' middle (`TALL`, `ASPECT`, `SOLID`, `MIDDLE`); None for a
    letter, a dash, a speck or blank ink."""
    mask = ink > 0.5
    cols = np.where(mask.any(0))[0]
    if len(cols) == 0:
        return None
    # The first run of inked columns: the mark, not the word after it.
    end = cols[0]
    while end + 1 < mask.shape[1] and mask[:, end + 1].any():
        end += 1
    mark = mask[:, cols[0] : end + 1]
    rows = np.where(mark.any(1))[0]
    high, wide = rows[-1] - rows[0] + 1, mark.shape[1]
    strip = mask.shape[0]
    middle = (rows[0] + rows[-1]) / 2 / strip
    fill = float(mark[rows[0] : rows[-1] + 1].mean())
    if not (TALL[0] <= high / strip <= TALL[1] and ASPECT[0] <= wide / high <= ASPECT[1]):
        return None
    if fill < SOLID or not (MIDDLE[0] <= middle <= MIDDLE[1]):
        return None
    return fill


def marker(text: str) -> str | None:
    """A line's first token, where it is short enough to be a misread bullet and text
    follows it."""
    head, _, rest = text.partition(" ")
    return head if head and len(head) <= MARKER and rest.strip() else None


class Lists:
    """A book's list items: each item's line with its bullet's token, and the lines that
    continue an item."""

    def __init__(self, cache: Path):
        self._cache = cache
        kept = read_cache(cache, VERSION, code=code_stamp(__name__))
        self.items: dict[SourceRef, str] = {}
        self.continued: set[SourceRef] = set()
        self.kind = ""
        self._done = kept is not None
        if kept:
            self._load(kept)

    def _load(self, kept: dict) -> None:
        self.items = {SourceRef(p, k): t for p, k, t in kept["items"]}
        self.continued = {SourceRef(p, k) for p, k in kept["continued"]}
        self.kind = kept["kind"]

    def survey(self, pdf: Path, pages: list[PageText]) -> None:
        """Finds the book's bullets on the scan and the lines that continue each item."""
        if self._done:
            return
        found: dict[SourceRef, tuple[str, float]] = {}
        starts: dict[SourceRef, float] = {}
        with pymupdf.open(pdf) as doc:
            for page in pages:
                words = None
                for k, line in enumerate(page.lines):
                    if (token := marker(line.text)) is None:
                        continue
                    if words is None:
                        words = line_words(page_words(doc[page.number - 1], page), page)
                    if len(words[k]) < 2 or words[k][0][4] != token:
                        continue
                    ink = rendercheck.place_ink(doc[page.number - 1], words[k][0][:4], page)
                    fill = None if ink is None else bullet(ink)
                    if fill is not None:
                        found[SourceRef(page.number, k)] = (token, fill)
                        starts[SourceRef(page.number, k)] = words[k][1][0]
        if len(found) < FEWEST:
            found = {}
        self.items = {ref: token for ref, (token, _) in found.items()}
        self.kind = (
            ("square" if statistics.median(f for _, f in found.values()) >= SQUARE else "disc")
            if found
            else ""
        )
        by_number = {p.number: p for p in pages}
        self.continued = set()
        for ref in self.items:
            lines = by_number[ref.page].lines
            k = ref.line + 1
            while (
                k < len(lines)
                and SourceRef(ref.page, k) not in self.items
                and abs(lines[k].x0 - starts[ref]) <= ALIGN
            ):
                self.continued.add(SourceRef(ref.page, k))
                k += 1
        write_cache(
            self._cache,
            VERSION,
            {
                "items": [
                    [r.page, r.line, t]
                    for r, t in sorted(self.items.items(), key=lambda e: (e[0].page, e[0].line))
                ],
                "continued": [
                    [r.page, r.line] for r in sorted(self.continued, key=lambda r: (r.page, r.line))
                ],
                "kind": self.kind,
            },
            code=code_stamp(__name__),
        )
        self._done = True

    def apply(self, pages: list[PageText]) -> list[PageText]:
        """Copies of the pages with each item's line opening a list item without its
        bullet, each line continuing an item kept in it, and the line after a list
        opening a paragraph. A line is found by its index before answers
        (`Line.source`). Where an answer or a fix already took the bullet out, the
        line's text is kept whole."""
        if not self.items:
            return pages
        out = []
        for page in pages:
            lines = list(page.lines)
            for i, line in enumerate(lines):
                ref = SourceRef(page.number, line.source if line.source is not None else i)
                if ref in self.items:
                    head, _, rest = line.text.partition(" ")
                    text = (
                        rest.lstrip()
                        if head == self.items[ref] or (head and not any(c.isalnum() for c in head))
                        else line.text
                    )
                    lines[i] = replace(line, text=text, starts_paragraph=True, item=self.kind)
                elif ref in self.continued:
                    lines[i] = replace(line, starts_paragraph=False)
                elif i and _in_list(page, i - 1, self):
                    lines[i] = replace(line, starts_paragraph=True)
            out.append(replace(page, lines=lines))
        return out

    def markers(self) -> dict[SourceRef, int]:
        """Each item's line with the end of its bullet's token in the layer's text: a
        doubt there is about no text."""
        return {ref: len(token) for ref, token in self.items.items()}


def _in_list(page: PageText, i: int, lists: Lists) -> bool:
    line = page.lines[i]
    ref = SourceRef(page.number, line.source if line.source is not None else i)
    return ref in lists.items or ref in lists.continued
