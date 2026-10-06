"""Regions of a page a human should look at: what isn't plain running text.

The pipeline is weakest where a page departs from the text block: headings,
inscriptions and signs set apart, captions, lines the role model dropped or kept
without being sure, and OCR read from a drawing. Consecutive flagged lines with
the same treatment form one region.

With layout regions from the page image (layout.py), pictures become regions
too, captions and titles are marked on their lines, and text the text layer
lacks (a region with no lines in it) becomes a region of its own: a box on the
page rather than a run of lines. A caption printed sideways (found with the page
turned, or read by the text layer as a column of scraps) is one region, and the
rest of its page is left to the picture.
"""

import hashlib
import statistics
from dataclasses import dataclass, replace

from roboscriptorium import roles as R
from roboscriptorium.ir import SourceRef
from roboscriptorium.layout import Region
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
    "picture": "a picture (the layout model)",
    "caption": "a caption (the layout model)",
    "layout-title": "a title to the layout model, but not a heading here",
    "missing-text": "text the layout model sees, but the text layer lacks",
    "rotated": "text printed sideways",
}
# A page's text is sideways when most of its lines are scraps of this many
# characters or fewer, stacked in one column this narrow (in points).
SIDEWAYS_MAX_CHARS = 3
SIDEWAYS_SHARE = 0.8
SIDEWAYS_COLUMN = 15
# Room around sideways text, along its column, so the crop holds whole words.
SIDEWAYS_PAD = 60
# A speck: a dropped line of at most this many characters, under this share of
# the page's usual line height (a stroke of a quote mark, a dot of ink).
SPECK_MAX_CHARS = 2
SPECK_HEIGHT = 0.5
# Layout regions below this confidence are ignored when they hold no text-layer line.
MISSING_TEXT_CONFIDENCE = 0.5


@dataclass(frozen=True)
class Flag:
    key: str
    page: int
    first: int
    last: int
    text: str  # the lines as the text layer reads them, one per line
    treatment: str  # "text", "heading", "dropped", or "missing" (nothing in the book)
    reasons: list[str]
    # A layout region on the page, in PDF points; then first..last are the lines in
    # it, or last < first (= where text would be inserted) when it has none.
    box: tuple[float, float, float, float] | None = None


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


def _speck(page: PageText, i: int) -> bool:
    line = page.lines[i]
    usual = statistics.median(ln.y1 - ln.y0 for ln in page.lines)
    return (
        len(line.text.replace(" ", "")) <= SPECK_MAX_CHARS
        and line.y1 - line.y0 < SPECK_HEIGHT * usual
    )


def _reasons(
    page: PageText, i: int, role: LineRole | None, furniture: _Furniture, layout: list[str]
) -> list[str]:
    n = len(page.lines)
    edge = i < R.EDGE_LINES_TOP or i >= n - R.EDGE_LINES_BOTTOM
    how = treatment(role)
    reasons = [r for r in layout if not (r == "layout-title" and how == "heading")]
    if how == "heading":
        reasons.append("heading")
    elif how == "dropped":
        if (edge and furniture(page, i) or _speck(page, i)) and not reasons:
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


def _inside(line, region: Region) -> bool:
    cx, cy = (line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2
    return region.x0 <= cx <= region.x1 and region.y0 <= cy <= region.y1


def _box_flag(page: PageText, region: Region, inside: list[int], reason: str) -> Flag:
    box = (region.x0, region.y0, region.x1, region.y1)
    if inside:
        first, last = inside[0], inside[-1]
        text = "\n".join(page.lines[k].text for k in range(first, last + 1))
        how = "dropped"
    else:
        first = sum(1 for ln in page.lines if (ln.y0 + ln.y1) / 2 < region.y0)
        last, text, how = first - 1, "", "missing"
    label = f"{region.label} {box[0]:.0f},{box[1]:.0f},{box[2]:.0f},{box[3]:.0f}\n{text}"
    return Flag(region_key(page.number, label), page.number, first, last, text, how, [reason], box)


def _layout(
    page: PageText, regions: list[Region]
) -> tuple[dict[int, list[str]], set[int], list[Flag]]:
    """Reasons per line, the lines inside pictures, and regions of their own."""
    reasons: dict[int, list[str]] = {}
    in_pictures: set[int] = set()
    flags = []
    missing: list[Region] = []
    for region in regions:
        inside = [i for i, ln in enumerate(page.lines) if _inside(ln, region)]
        if region.label == "figure":
            in_pictures |= set(inside)
            flags.append(_box_flag(page, region, inside, "picture"))
        elif region.turned:
            flags.append(_box_flag(page, region, inside, "rotated"))
        elif region.label in ("figure_caption", "title") and inside:
            reason = "caption" if region.label == "figure_caption" else "layout-title"
            for i in inside:
                reasons.setdefault(i, []).append(reason)
        elif (
            region.label in ("figure_caption", "title", "plain text")
            and not inside
            and region.confidence >= MISSING_TEXT_CONFIDENCE
        ):
            missing.append(region)
    if missing:
        # One region per page: a page the text layer skipped has many text blocks.
        union = Region(
            "missing text",
            min(r.confidence for r in missing),
            min(r.x0 for r in missing),
            min(r.y0 for r in missing),
            max(r.x1 for r in missing),
            max(r.y1 for r in missing),
        )
        flags.append(_box_flag(page, union, [], "missing-text"))
    return reasons, in_pictures, flags


def sideways(page: PageText) -> bool:
    """Text printed turned (a landscape plate's caption): the layer reads a column of scraps."""
    lines = page.lines
    if len(lines) < 4:
        return False
    scraps = sum(len(ln.text.replace(" ", "")) <= SIDEWAYS_MAX_CHARS for ln in lines)
    centres = [(ln.x0 + ln.x1) / 2 for ln in lines]
    return scraps >= SIDEWAYS_SHARE * len(lines) and max(centres) - min(centres) <= SIDEWAYS_COLUMN


def _sideways_flag(page: PageText, roles: dict[SourceRef, LineRole]) -> Flag:
    lines = page.lines
    box = (
        min(ln.x0 for ln in lines) - 4,
        max(0.0, min(ln.y0 for ln in lines) - SIDEWAYS_PAD),
        max(ln.x1 for ln in lines) + 4,
        min(page.height, max(ln.y1 for ln in lines) + SIDEWAYS_PAD),
    )
    text = "\n".join(ln.text for ln in lines)
    flag = Flag(
        region_key(page.number, text), page.number, 0, len(lines) - 1, text, "", ["rotated"], box
    )
    return replace(flag, treatment=_treatment_of(page, flag, roles))


def _treatment_of(page: PageText, flag: Flag, roles: dict[SourceRef, LineRole]) -> str:
    kinds = {
        treatment(roles.get(SourceRef(page.number, i))) for i in range(flag.first, flag.last + 1)
    }
    return "text" if "text" in kinds else "heading" if "heading" in kinds else "dropped"


def find(
    pages: list[PageText],
    roles: dict[SourceRef, LineRole],
    layout: dict[int, list[Region]] | None = None,
) -> list[Flag]:
    flags: list[Flag] = []
    furniture = _Furniture(R.Repeats(pages), R._page_offset(pages))
    for page in pages:
        regions = (layout or {}).get(page.number, [])
        line_reasons, in_pictures, boxes = _layout(page, regions)
        if any(r.turned for r in regions) or sideways(page):
            if not any(r.turned for r in regions):
                boxes = [f for f in boxes if "picture" in f.reasons] + [_sideways_flag(page, roles)]
            flags += [
                replace(f, treatment=_treatment_of(page, f, roles)) if f.last >= f.first else f
                for f in boxes
            ]
            continue
        page_flags: list[Flag] = []
        run: list[tuple[int, str, list[str]]] = []
        for i in range(len(page.lines)):
            role = roles.get(SourceRef(page.number, i))
            reasons = (
                []
                if i in in_pictures
                else _reasons(page, i, role, furniture, line_reasons.get(i, []))
            )
            how = treatment(role)
            if reasons and run and run[-1][0] == i - 1 and run[-1][1] == how:
                run.append((i, how, reasons))
                continue
            if run:
                page_flags.append(_region(page, run))
            run = [(i, how, reasons)] if reasons else []
        if run:
            page_flags.append(_region(page, run))
        boxes = [
            replace(f, treatment=_treatment_of(page, f, roles)) if f.last >= f.first else f
            for f in boxes
        ]
        flags += sorted(page_flags + boxes, key=lambda f: (f.first, f.last))
    return flags
