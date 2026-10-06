"""Regions of a page a human should look at: what isn't plain running text.

The pipeline is weakest where a page departs from the text block: headings,
inscriptions and signs set apart, captions, lines the role model dropped or kept
without being sure, and OCR read from a drawing. Consecutive flagged lines with
the same treatment form one region.
"""

import hashlib
import statistics
from dataclasses import dataclass

from roboscriptorium import roles as R
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PageText
from roboscriptorium.roles import KEEP_BODY_AT, LineRole

# A dropped line the model gave at least this P(body) is worth a look; running
# heads and page numbers score far below it.
DROPPED_DOUBT = 0.1
# A line is centred when its left and right insets differ by less than this share
# of a full line, and the left inset is at least that much too.
CENTRED_BALANCE = 0.05
# A line is set apart when the gaps above and below it are both this many times the
# page's usual line spacing.
SET_APART_GAP = 1.8

REASONS = {
    "heading": "a heading",
    "dropped-mid-page": "dropped, though not at the page's edge",
    "dropped-unsure": "dropped, but the model wasn't sure",
    "kept-unsure": "kept as text, but the model thought it might not be",
    "garbled": "kept as text, but it looks garbled",
    "centred": "centred, unlike running text",
    "set-apart": "set apart by white space",
}


@dataclass(frozen=True)
class Flag:
    key: str
    page: int
    first: int
    last: int
    text: str  # the lines as the text layer reads them, one per line
    treatment: str  # "text", "heading" or "dropped"
    reasons: list[str]


def region_key(page: int, text: str) -> str:
    return f"p{page}-" + hashlib.sha1(f"{page}\n{text}".encode()).hexdigest()[:10]


def treatment(role: LineRole | None) -> str:
    if role is None or role.p_body >= KEEP_BODY_AT:
        return "text"
    return "heading" if role.role == "chapter_heading" else "dropped"


def _set_apart(page: PageText, i: int) -> bool:
    lines = page.lines
    if len(lines) < 4 or i in (0, len(lines) - 1):
        return False
    spacing = statistics.median(b.y0 - a.y0 for a, b in zip(lines, lines[1:], strict=False))
    above = lines[i].y0 - lines[i - 1].y0
    below = lines[i + 1].y0 - lines[i].y0
    return spacing > 0 and min(above, below) >= SET_APART_GAP * spacing


def _centred(page: PageText, i: int) -> bool:
    """Equal margins on both sides: unlike a paragraph's first or last line."""
    full, left = R._geometry(page)
    right = statistics.median(ln.x1 for ln in page.lines)
    line = page.lines[i]
    inset_left, inset_right = line.x0 - left, right - line.x1
    balance = CENTRED_BALANCE * full
    return (
        line.x1 - line.x0 < R.CENTRED_MAX_WIDTH * full
        and inset_left >= balance
        and abs(inset_left - inset_right) < balance
    )


@dataclass(frozen=True)
class _Furniture:
    """What recurs at page edges: running heads and printed page numbers."""

    repeats: R.Repeats
    offset: int | None

    def __call__(self, page: PageText, i: int) -> bool:
        text = page.lines[i].text
        if R._printed_page_number(text, page, self.offset):
            return True
        stripped = text.strip()
        if stripped.isdigit() and self.offset is not None:
            return abs(int(stripped) - (page.number - self.offset)) <= R.PAGE_NUMBER_SLACK
        return self.repeats.other_pages(text, page.number) >= R.HEADING_MAX_REPEATS


def _reasons(page: PageText, i: int, role: LineRole | None, furniture: _Furniture) -> list[str]:
    n = len(page.lines)
    edge = i < R.EDGE_LINES_TOP or i >= n - R.EDGE_LINES_BOTTOM
    how = treatment(role)
    reasons = []
    if how == "heading":
        reasons.append("heading")
    elif how == "dropped":
        if edge and furniture(page, i):
            return []
        if not edge:
            reasons.append("dropped-mid-page")
        if role.p_body >= DROPPED_DOUBT:
            reasons.append("dropped-unsure")
    else:
        if role is not None and role.role != "body":
            reasons.append("kept-unsure")
        if R.garbled(page.lines[i]):
            reasons.append("garbled")
        if _centred(page, i):
            reasons.append("centred")
        if _set_apart(page, i):
            reasons.append("set-apart")
    return reasons


def _region(page: PageText, run: list[tuple[int, str, list[str]]]) -> Flag:
    first, last = run[0][0], run[-1][0]
    text = "\n".join(page.lines[k].text for k in range(first, last + 1))
    reasons = list(dict.fromkeys(r for _, _, rs in run for r in rs))
    return Flag(region_key(page.number, text), page.number, first, last, text, run[0][1], reasons)


def find(pages: list[PageText], roles: dict[SourceRef, LineRole]) -> list[Flag]:
    flags: list[Flag] = []
    furniture = _Furniture(R.Repeats(pages), R._page_offset(pages))
    for page in pages:
        run: list[tuple[int, str, list[str]]] = []
        for i in range(len(page.lines)):
            role = roles.get(SourceRef(page.number, i))
            reasons = _reasons(page, i, role, furniture)
            how = treatment(role)
            if reasons and run and run[-1][0] == i - 1 and run[-1][1] == how:
                run.append((i, how, reasons))
                continue
            if run:
                flags.append(_region(page, run))
            run = [(i, how, reasons)] if reasons else []
        if run:
            flags.append(_region(page, run))
    return flags
