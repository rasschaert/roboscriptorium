"""Printed lines the text layer lacks, read from the page image.

OCR layers drop short lines: a bare chapter number ("3"), a page number, a line
of dialogue ("'Ja.'"), and now and then a block's first or last line. The layout model
still sees a region there. A region about one line tall that no text-layer line falls
in, or the strip of a text region above its first layer line or below its last, is
read by the OCR model, and the
reading goes into a copy of the page as a line of its own, in reading order, so
roles, rules and reflow treat it like any other line. Readings are cached in
`stages/missing-lines.json`.

Figures and captions are left to the figures stage, and regions a human
answered in the review keep the human's text.
"""

import unicodedata
from dataclasses import replace
from pathlib import Path
from statistics import median

import pymupdf

from roboscriptorium import chapters, readers
from roboscriptorium.files import read_cache, write_cache
from roboscriptorium.layout import Region
from roboscriptorium.page import sunk_pages
from roboscriptorium.pdf import Line, PageText

VERSION = 1
MAX_HEIGHT = 1.8  # times the book's median line height
# Above a sunk page's text, where a chapter opens, a drawn number may stand taller
# (Artemis sets each in a circle about four lines high).
OPENING_MAX_HEIGHT = 5.0
SKIPPED = {"figure", "figure_caption"}
# A text region's strip above its first layer line or below its last, at least this
# many line heights tall, is a line the layer lacks.
EDGE_GAP = 1.5
# A read line overlapping a layer line down by this share of its height is that line
# (Hoe wij verdwijnen's, Goede dochter's and Vals alarm's short replies overlap 0.35–0.38;
# lines a pitch apart don't overlap).
SAME_LINE = 0.3
# Where the spotter marks a box above the text of this many sunk pages at one place, the
# same place on a sunk page it marked nothing at is read too (`openings`).
OPENING_PLACES = 3
# A placed box holds print where this share of its pixels is dark (a blank opening's paper
# reads 0.0, Het schaduwhuis' narrowest chapter number "1" 0.05) and a run of inked rows
# spans this share of its height (a figure most of it; a speck, Doodskleed's on PDF 18,
# a fifth).
INK = 0.02
INK_SPAN = 0.4
INK_DPI = 150
# A placed box's confidence: the spotter gives none of its own boxes 0.
PLACED = 0.0
# A layer line this short, reading as no number, above a sunk page's text is a drawing
# misread ("ae", "/" for Artemis' circled numbers), not a line of text.
JUNK_CHARS = 3


def _inside(line: Line, box) -> bool:
    cx, cy = (line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2
    return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]


def _overlap(a: Region, b: Region) -> bool:
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    smaller = min((a.x1 - a.x0) * (a.y1 - a.y0), (b.x1 - b.x0) * (b.y1 - b.y0))
    return w > 0 and h > 0 and w * h >= 0.5 * smaller


def candidates(
    pages: list[PageText],
    regions: dict[int, list[Region]],
    answered: dict[int, list[tuple[float, float, float, float]]],
) -> list[tuple[int, Region]]:
    """Line-sized regions holding no text-layer line and not part of one, one per spot
    (the surest); above the text of a sunk page, or on a page the layer holds nothing of,
    regions up to a few lines tall, where the layer's junk in a drawing (`_junk`) counts
    as no line; and a text region's strip above its first layer line or below its last
    (`edges`).

    `answered` holds, per page, the boxes of regions a human typed text for.
    """
    heights = [ln.y1 - ln.y0 for p in pages for ln in p.lines]
    if not heights:
        return []
    tallest = MAX_HEIGHT * median(heights)
    opening = OPENING_MAX_HEIGHT * median(heights)
    sunk = sunk_pages(pages)
    found = []
    for page in pages:
        # Above a sunk page's text the layer's junk in a drawing is no line (`_junk`).
        top = min((ln.y0 for ln in page.lines), default=0.0)
        if page.number in sunk:
            top = next((ln.y0 for ln in page.lines if not _junk(ln)), top)
        figures = [r for r in regions.get(page.number, []) if r.label == "figure"]
        kept: list[Region] = []
        for r in sorted(regions.get(page.number, []), key=lambda r: -r.confidence):
            box = (r.x0, r.y0, r.x1, r.y1)
            centre = Line("", *box)
            above = page.number in sunk and r.y1 <= top
            lines = [ln for ln in page.lines if not (above and _junk(ln))]
            if (
                r.label in SKIPPED
                or r.turned
                or r.y1 - r.y0 > tallest
                and not (above and r.y1 - r.y0 <= opening)
                # A page the layer has nothing of may set its title in display type
                # (Pieter Daens' "Onze doden" under "BOEK VIJF").
                and not (not page.lines and r.y1 - r.y0 <= opening)
                or any(_inside(ln, box) for ln in lines)
                or any(_inside(centre, (ln.x0, ln.y0, ln.x1, ln.y1)) for ln in lines)
                or any(_inside(centre, (f.x0, f.y0, f.x1, f.y1)) for f in figures)
                or any(_inside(centre, b) for b in answered.get(page.number, []))
                or any(_overlap(r, k) for k in kept)
            ):
                continue
            kept.append(r)
        found += [(page.number, r) for r in kept]
        found += [
            (page.number, e)
            for e in edges(page, regions.get(page.number, []), median(heights))
            if not any(_overlap(e, k) for k in kept)
            and not any(
                _inside(Line("", e.x0, e.y0, e.x1, e.y1), b) for b in answered.get(page.number, [])
            )
        ]
    return found


def _junk(line: Line) -> bool:
    return len(line.text.strip()) <= JUNK_CHARS and chapters.value(line.text) is None


def _text_top(page: PageText, r: Region) -> float | None:
    """Where the page's text starts below `r`: its first line that isn't junk the layer
    read inside or above it; None when there is none."""
    return next((ln.y0 for ln in page.lines if not (ln.y0 < r.y1 and _junk(ln))), None)


def _middle(page: PageText) -> float:
    """The middle of the page's text column: of its lines near full width, else the page."""
    wide = [(ln.x0 + ln.x1) / 2 for ln in page.lines if ln.x1 - ln.x0 > 0.6 * page.width]
    return median(wide) if wide else page.width / 2


def _fitted(doc: pymupdf.Document, number: int, r: Region, floor: float) -> Region | None:
    """The box moved to the print found within half its height above or below it (never
    down to `floor`, the page's first line): the longest run of inked rows, if it spans
    `INK_SPAN` of the box's height and is dark enough (`INK`); else None (a blank place,
    a speck)."""
    h = r.y1 - r.y0
    top, bottom = r.y0 - h / 2, min(r.y1 + h / 2, floor - 1)
    pix = doc[number - 1].get_pixmap(
        clip=pymupdf.Rect(r.x0, top, r.x1, bottom), dpi=INK_DPI, colorspace=pymupdf.csGRAY
    )
    w, data = pix.width, pix.samples
    dark = [
        sum(1 for v in data[y * pix.stride : y * pix.stride + w] if v < 128)
        for y in range(pix.height)
    ]
    runs, start = [], None
    for y, d in enumerate([*dark, 0]):
        if d and start is None:
            start = y
        elif not d and start is not None:
            runs.append((start, y))
            start = None
    if not runs:
        return None
    a, b = max(runs, key=lambda run: run[1] - run[0])
    scale = (bottom - top) / pix.height
    if (b - a) * scale < INK_SPAN * h or sum(dark[a:b]) < INK * w * h / scale:
        return None
    return replace(r, y0=top + a * scale - 1, y1=min(top + b * scale + 1, floor - 1))


def openings(
    pdf: Path, pages: list[PageText], regions: dict[int, list[Region]]
) -> dict[int, list[Region]]:
    """The regions with the spotter's usual box above a sunk opening's text placed on each
    sunk opening it marked nothing at, where that place holds ink.

    A chapter number the layer lacks is read only where the spotter boxed it; on some
    openings it boxes nothing (Het schaduwhuis' chapters 1 and 4). The usual box is the
    one standing, against its page's text column, where boxes stand on `OPENING_PLACES`
    sunk pages or more; its place is their median. A blank opening (a prologue's) has no
    ink there and gets no box, nor does a speck; a box found is fitted to its ink
    (`_fitted`), as openings stand a few points apart. Short junk the layer read in the
    drawing (Artemis' circled "8" read "ae") is no first line of text (`_text_top`).
    """
    heights = [ln.y1 - ln.y0 for p in pages for ln in p.lines]
    if not heights:
        return regions
    tol = median(heights)
    numbers = sunk_pages(pages)
    sunk = [p for p in pages if p.number in numbers and p.lines]
    boxes = []  # (page, label, x0, x1 against the column's middle, y0, y1)
    for p in sunk:
        mid, top = _middle(p), p.lines[0].y0
        for r in regions.get(p.number, []):
            if r.label not in SKIPPED and not r.turned and r.y1 <= top:
                boxes.append((p.number, r.label, r.x0 - mid, r.x1 - mid, r.y0, r.y1))

    def near(a, b) -> bool:
        return (
            abs((a[2] + a[3]) - (b[2] + b[3])) / 2 <= tol
            and abs((a[4] + a[5]) - (b[4] + b[5])) / 2 <= tol
        )

    groups = [[b for b in boxes if near(a, b)] for a in boxes]
    group = max(groups, key=lambda g: len({b[0] for b in g}), default=[])
    if len({b[0] for b in group}) < OPENING_PLACES:
        return regions
    labels = [b[1] for b in group]
    label = max(set(labels), key=labels.count)
    place = [median(b[k] for b in group) for k in (2, 3, 4, 5)]
    out = dict(regions)
    with pymupdf.open(pdf) as doc:
        for p in sunk:
            mid = _middle(p)
            r = Region(label, PLACED, mid + place[0], place[2], mid + place[1], place[3])
            here = regions.get(p.number, [])
            top = _text_top(p, r)
            if top is None or r.y1 > top or any(_overlap(r, h) for h in here):
                continue
            if fitted := _fitted(doc, p.number, r, top):
                out[p.number] = [*here, fitted]
    return out


def edges(page: PageText, regions: list[Region], height: float) -> list[Region]:
    """The strips of the text regions above their first layer line and below their
    last, where at least `EDGE_GAP` line heights are left and at most `MAX_HEIGHT`."""
    out = []
    for r in regions:
        if r.label != "plain text" or r.turned:
            continue
        inside = [ln for ln in page.lines if _inside(ln, (r.x0, r.y0, r.x1, r.y1))]
        if not inside:
            continue
        top, bottom = min(ln.y0 for ln in inside), max(ln.y1 for ln in inside)
        for y0, y1 in ((r.y0, top), (bottom, r.y1)):
            if EDGE_GAP * height <= y1 - y0 <= MAX_HEIGHT * height + height:
                out.append(replace(r, y0=y0, y1=y1))
    return out


def _key(number: int, r: Region) -> str:
    return f"{number}:{r.x0:.0f},{r.y0:.0f},{r.x1:.0f},{r.y1:.0f}"


def read(
    pdf: Path, found: list[tuple[int, Region]], model: str, ollama_url: str, cache: Path
) -> dict[str, str]:
    """The OCR model's reading of each candidate, keyed by page and box."""
    raw = read_cache(cache, VERSION, model=model)
    done: dict[str, str] = raw["lines"] if raw else {}
    todo = [(n, r) for n, r in found if _key(n, r) not in done]
    if todo:
        # Saved however the reads end, so an interrupted run keeps the ones done.
        try:
            with pymupdf.open(pdf) as doc:
                for n, r in todo:
                    png = readers._line_crop(doc, n, (r.x0, r.y0, r.x1, r.y1))
                    done[_key(n, r)] = readers.read_line(png, model, ollama_url)
        finally:
            write_cache(cache, VERSION, {"lines": done}, model=model)
    return {_key(n, r): done[_key(n, r)] for n, r in found}


def _same_line(layer: Line, read: Line) -> bool:
    """Whether a read line covers a layer line: overlapping across, and down by
    `SAME_LINE` of the read line's height or more."""
    across = min(layer.x1, read.x1) - max(layer.x0, read.x0)
    down = min(layer.y1, read.y1) - max(layer.y0, read.y0)
    return across > 0 and down >= SAME_LINE * (read.y1 - read.y0)


def _printed(text: str) -> bool:
    """Whether a reading can be printed text of a book in a Latin script: not a code fence
    the model opens on a speck ("```markdown"), nor a letter of another script ("境")."""
    if "```" in text:
        return False
    return all(not c.isalpha() or unicodedata.name(c, "").startswith("LATIN") for c in text)


def talk(found: list[tuple[int, Region]], readings: dict[str, str]) -> list[tuple[int, Region]]:
    """The candidates whose reading is the model's talk, not printed text (`_printed`): for
    another reader. glm-ocr answers "```markdown" on Artemis' circled 11; the read model
    reads it, but on a corner speck invents a sentence, so the pipeline takes its reading
    only as a number."""
    return [(n, r) for n, r in found if not _printed(readings.get(_key(n, r), ""))]


def add(
    pages: list[PageText], found: list[tuple[int, Region]], readings: dict[str, str]
) -> list[PageText]:
    """Copies of the pages with each read line in reading order (by its middle).

    A reading with no letter or digit (a smudge) is left out, and so is the model's
    talk rather than a reading (`_printed`). A read line overlapping a layer line by
    `SAME_LINE` of its height is that line, its box set too high or low by the layer (a
    short "‘Ja.’" read "qa”" seven points up): it takes the layer line's place, with the
    image's box and the model's reading, rather than standing beside it.
    """
    by_page: dict[int, list[Line]] = {}
    for n, r in found:
        text = " ".join(readings.get(_key(n, r), "").split())
        if any(c.isalnum() for c in text) and _printed(text):
            by_page.setdefault(n, []).append(Line(text, r.x0, r.y0, r.x1, r.y1))
    out = []
    for page in pages:
        if page.number not in by_page:
            out.append(page)
            continue
        lines = list(page.lines)
        for new in by_page[page.number]:
            same = next((k for k, ln in enumerate(lines) if _same_line(ln, new)), None)
            if same is not None:
                lines[same] = new
                continue
            middle = (new.y0 + new.y1) / 2
            at = sum(1 for ln in lines if (ln.y0 + ln.y1) / 2 < middle)
            lines.insert(at, new)
        out.append(replace(page, lines=lines))
    return out
