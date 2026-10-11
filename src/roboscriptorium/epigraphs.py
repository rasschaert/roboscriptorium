"""Epigraphs: a motto set on a page of its own, apart from the running text.

A page holding a few short lines (`MAX_LINES`), each starting well right of the book's
left margin (`INSET`), with no heading on it, is an epigraph: "‘It’s closing time’" over
"(Leonard Cohen, The Future)". The book's margin and full line width are read on its
full pages, since a page of two lines can't show its own. A chapter's last page of a
few short lines starts them at the margin, so it isn't one; nor are garbled lines, a
title in capitals, or a line of two words. Reflow sets the lines as
paragraphs marked `epigraph` (`ROLE`), which the EPUB sets apart as one block.
"""

import re
import statistics

from roboscriptorium import page as P
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import KEEP_BODY_AT, LineRole

# An epigraph page holds at most this many lines.
MAX_LINES = 6
# Each of its lines starts at least this share of a full line right of the margin, and
# is at most `SHORT` of a full line wide.
INSET = 0.15
SHORT = 0.75
# A page this full of lines shows the book's margin and line width.
FULL_PAGE = 10
# An epigraph holds at least this many words of two letters or more.
MIN_WORDS = 3
# The role reflow gives an epigraph's lines.
ROLE = LineRole("epigraph", 1.0, 0.0, "epigraph")
_FURNITURE = ("page_number", "running_head", "chapter_heading")


def lines(pages: list[PageText], roles: dict[SourceRef, LineRole]) -> set[SourceRef]:
    """The lines of `pages` that print an epigraph (positions in `pages`)."""
    full = [p for p in pages if len(p.lines) >= FULL_PAGE]
    if not full:
        return set()
    width = statistics.median(ln.x1 - ln.x0 for p in full for ln in p.lines)
    found = set()
    for page in pages:
        refs = [SourceRef(page.number, i) for i in range(len(page.lines))]
        kinds = [_kind(roles.get(r)) for r in refs]
        if "chapter_heading" in kinds:
            continue
        kept = [i for i, k in enumerate(kinds) if k not in _FURNITURE]
        if not kept or len(kept) > MAX_LINES:
            continue
        # The margin of the pages either side, as crops move it from page to page.
        near = [p for p in full if abs(p.number - page.number) <= 10] or full
        margin = statistics.median(ln.x0 for p in near for ln in p.lines)
        if _reads([page.lines[i] for i in kept]) and all(
            page.lines[i].x0 - margin >= INSET * width
            and page.lines[i].x1 - page.lines[i].x0 <= SHORT * width
            for i in kept
        ):
            found.update(refs[i] for i in kept)
    return found


def _reads(lines: list[Line]) -> bool:
    """Whether the lines read as a motto: `MIN_WORDS` words at least, none of the lines
    garbled (a picture or a speck read as text), and not all in capitals (a part's title
    is). Not checked against the word list: a motto is often in another language."""
    words = [w for ln in lines for w in re.findall(r"[^\W\d_]{2,}", ln.text)]
    return (
        len(words) >= MIN_WORDS
        and not any(P.garbled(ln) for ln in lines)
        and any(c.islower() for w in words for c in w)
    )


def _kind(role: LineRole | None) -> str:
    """The line's role as reflow and the furniture checks see it."""
    if role is None or role.p_body >= KEEP_BODY_AT:
        return "body"
    return role.role
