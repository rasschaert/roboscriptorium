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
from dataclasses import dataclass, field, replace

from roboscriptorium import page as P
from roboscriptorium import roles as R
from roboscriptorium.ir import SourceRef
from roboscriptorium.layout import Region
from roboscriptorium.ocrcheck import Doubt
from roboscriptorium.pdf import PageText
from roboscriptorium.quotes import KINDS
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
    "ocr-doubt": "two OCR readings differ, and the models weren't sure which is right",
    "quotes": "its paragraph's quote marks don't pair up: one may be lost or misread",
    "washed-out": "the scan is too faint to read: the text layer here is guesswork",
    "lost-line": "white space inside a sentence: the text layer may have lost a line",
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
# A gap between two running-text lines this many times the page's line pitch, below a
# line stopping mid-word or mid-sentence, is a line the text layer lost.
LOST_LINE_GAP = 1.5
# The line below such a gap is running text: this long, opening with a letter, a digit or
# a quote mark.
LOST_LINE_MIN_CHARS = 10
QUOTES = "‘’“”'\"„"
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
    # When OCR readings of a line differ: the region as each reads it, the text
    # layer's first, each with the models that picked it ({"text", "votes"}).
    readings: list[dict] = field(default_factory=list)
    # For a question about one place in a line: that place, as a span of line `first`
    # as the text layer reads it. An answer then changes only that span.
    span: tuple[int, int] | None = None
    # For a break hyphen: the next line's first word, which the readings end with.
    joined: str = ""


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
    return P.centred_in_text(page, i, CENTRED_BALANCE)


@dataclass(frozen=True)
class _Furniture:
    """What recurs at page edges: running heads and printed page numbers."""

    repeats: P.Repeats
    offset: int | None

    def __call__(self, page: PageText, i: int) -> bool:
        text = page.lines[i].text
        if P.printed_page_number(text, page, self.offset):
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
    edge = i < P.EDGE_LINES_TOP or i >= n - P.EDGE_LINES_BOTTOM
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
        if P.garbled(page.lines[i]):
            reasons.append("garbled")
        if _centred(page, i):
            reasons.append("centred")
        if _set_apart(page, i):
            reasons.append("set-apart")
    return reasons


def _doubt(page: PageText, d: Doubt, roles: dict[SourceRef, LineRole]) -> Flag:
    """The question about one place in a line: its readings as whole lines, its crop the place."""
    return Flag(
        region_key(page.number, f"{d.original}\n{d.start}:{d.end}"),
        page.number,
        d.line,
        d.line,
        d.original,
        treatment(roles.get(SourceRef(page.number, d.line))),
        ["ocr-doubt"],
        d.box,
        [{"text": text, "votes": list(votes)} for text, votes in d.readings],
        (d.start, d.end),
        d.joined,
    )


def _region(
    page: PageText,
    run: list[tuple[int, str, list[str]]],
    proposed: dict[SourceRef, dict[str, str]],
) -> Flag:
    """A run of flagged lines; with `proposed` lines in it (other readings by kind,
    `quotes.readings`), the region as the text layer reads it and as each kind reads it
    are its readings: a line without a kind reads as the OCR check left it, else the
    layer."""
    first, last = run[0][0], run[-1][0]
    text = "\n".join(page.lines[k].text for k in range(first, last + 1))
    reasons = list(dict.fromkeys(r for _, _, rs in run for r in rs))
    flag = Flag(region_key(page.number, text), page.number, first, last, text, run[0][1], reasons)
    refs = [SourceRef(page.number, k) for k in range(first, last + 1)]
    if any(r in proposed for r in refs):
        readings = [{"text": text, "votes": []}]
        for kind in KINDS:
            if not any(kind in proposed.get(r, {}) for r in refs):
                continue
            other = "\n".join(
                proposed.get(r, {}).get(kind)
                or proposed.get(r, {}).get("OCR check")
                or page.lines[r.line].text
                for r in refs
            )
            same = next((g for g in readings if g["text"] == other), None)
            if same is None:
                readings.append({"text": other, "votes": [kind]})
            else:
                same["votes"].append(kind)
        flag = replace(flag, readings=readings)
    return flag


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


def _lost_lines(
    page: PageText, roles: dict[SourceRef, LineRole], regions: list[Region]
) -> list[Region]:
    """The gaps where a line of running text is missing: a line's height or more of white
    space between two adjacent running-text lines, below one that stops mid-word or
    mid-sentence (a paragraph ends in punctuation), with no picture in it."""
    text = [
        treatment(roles.get(SourceRef(page.number, i))) == "text" for i in range(len(page.lines))
    ]
    pitches = [
        b.y0 - a.y0
        for k, (a, b) in enumerate(zip(page.lines, page.lines[1:], strict=False))
        if text[k] and text[k + 1]
    ]
    if len(pitches) < 3:
        return []
    pitch = statistics.median(pitches)
    pictures = [r for r in regions if r.label == "figure"]
    out = []
    for k, (a, b) in enumerate(zip(page.lines, page.lines[1:], strict=False)):
        end = a.text.rstrip()[-1:]
        if not (text[k] and text[k + 1] and end and (end.isalnum() or end in "-\u00ad\u00ac")):
            continue
        # A speck at the foot read as a scrap ("ae"), or a footnote ("*Een met was…").
        start = b.text.lstrip()[:1]
        if len(b.text.strip()) < LOST_LINE_MIN_CHARS or not (start.isalnum() or start in QUOTES):
            continue
        if min(b.y0 - a.y0, b.y1 - a.y1) <= LOST_LINE_GAP * pitch:
            continue
        if any(r.y0 < b.y0 and a.y1 < r.y1 for r in pictures):
            continue
        out.append(Region("lost line", 1.0, min(a.x0, b.x0), a.y1, max(a.x1, b.x1), b.y0))
    return out


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


def _washed_out_flag(page: PageText, roles: dict[SourceRef, LineRole]) -> Flag:
    text = "\n".join(ln.text for ln in page.lines)
    flag = Flag(
        region_key(page.number, text), page.number, 0, len(page.lines) - 1, text, "",
        ["washed-out"], (0.0, 0.0, page.width, page.height),
    )  # fmt: skip
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
    doubts: list[Doubt] | None = None,
    quotes: set[SourceRef] | None = None,
    proposed: dict[SourceRef, dict[str, str]] | None = None,
    faint: set[int] | None = None,
) -> list[Flag]:
    """Regions of the pages a human should check.

    A page in `faint` (scanned too faint to read, `faint.pages`) is one region of all its
    lines: nothing on it can be trusted, so it gets no finer questions.

    Each of the OCR check's `doubts` is a question of its own about one place in a line,
    cropped to it. `quotes` are lines where a paragraph's quote marks don't pair up
    (`quotes.unbalanced`); `proposed` are such lines as a vision model reads their marks
    (`Stages.quote_readings`), offered as a second reading.
    """
    flags: list[Flag] = []
    furniture = _Furniture(P.Repeats(pages), P.page_offset(pages))
    for page in pages:
        if page.number in (faint or set()) and page.lines:
            flags.append(_washed_out_flag(page, roles))
            continue
        regions = (layout or {}).get(page.number, [])
        line_reasons, in_pictures, boxes = _layout(page, regions)
        for i in range(len(page.lines)):
            if SourceRef(page.number, i) in (quotes or set()):
                line_reasons.setdefault(i, []).append("quotes")
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
                page_flags.append(_region(page, run, proposed or {}))
            run = [(i, how, reasons)] if reasons else []
        if run:
            page_flags.append(_region(page, run, proposed or {}))
        boxes = [
            replace(f, treatment=_treatment_of(page, f, roles)) if f.last >= f.first else f
            for f in boxes
        ]
        missing = [f.box for f in boxes if "missing-text" in f.reasons]
        boxes += [
            _box_flag(page, gap, [], "lost-line")
            for gap in _lost_lines(page, roles, regions)
            if not any(b[1] <= gap.y1 and gap.y0 <= b[3] for b in missing)
        ]
        page_flags += [_doubt(page, d, roles) for d in doubts or [] if d.page == page.number]
        flags += sorted(page_flags + boxes, key=lambda f: (f.first, f.last))
    return flags
