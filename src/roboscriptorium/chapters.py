"""Chapter numbers: the book's own run of numbered chapters, read where the layer can't.

Old-style figures read as letters ("Io" for 10, "SE" for 51, "zi" for 23), and a short
line read as a speck is dropped before any reader sees it. Two facts of the book settle
them. A chapter opening looks like the book's other chapter openings, so a short line
set apart atop a sunk page is a heading where most such openings carry one
(`openings`). And numbered chapters run 1, 2, 3 …, so a number read as letters, or a
heading too short to be a title, is the number its neighbours say (`numbered`).
"""

import re
import statistics
from collections import Counter
from collections.abc import Callable
from dataclasses import replace

from rapidfuzz.distance import Levenshtein

from roboscriptorium import page as P
from roboscriptorium.ir import Block, Heading, SourceRef
from roboscriptorium.pdf import PageText
from roboscriptorium.roles import LineRole, is_body
from roboscriptorium.typestyle import SAME_SIZE, Style

# A chapter number is at most this many characters as read ("I2", "17.", "#7").
NUMBER_CHARS = 3
# The book's set-apart sunk openings carry a heading on at least this share of them.
OPENINGS_WITH_HEADING = 2 / 3
# At least this many such openings, so the share is the book's habit.
MIN_OPENINGS = 5
# At least this many headings, and half of them following the one before, make a run.
MIN_NUMBERED = 5
RULE = "book-openings"
# A dropped number filling a gap in the run of headings (`run_gaps`) is at most this far
# past the run's last number: two chapters in a row the layer lost, then this one.
RUN_GAP = 3
RUN_RULE = "chapter-run"
OFF_RUN_RULE = "off-run"
# The share of a run's numbered headings that must stand centred for an off-centre one
# off the run to be taken for a speck.
CENTRED_SHARE = 0.8

# How the layer misreads old-style figures: a 1 as I or l, a 0 as o, a 5 as S, a 2 as Z.
_MISREADS = str.maketrans("IilOoSsZz", "111005522")


def openings(pages: list[PageText], roles: dict[SourceRef, LineRole]) -> dict[SourceRef, LineRole]:
    """`roles` with a short line set apart atop a sunk page made a chapter heading, where
    most of the book's set-apart sunk openings start on one; a title of words too, where
    most of those headings are words, even one the trees took for body (Reis om mijn
    schedel's "Een gebaar in het vensterglas", 0.60). Returns a new dict."""
    sunk = P.sunk_pages(pages)
    apart = [p for p in pages if p.number in sunk and P.set_apart_opening(p)]
    if len(apart) < MIN_OPENINGS:
        return roles
    headed = [p for p in apart if _role(roles, p) == "chapter_heading"]
    if len(headed) < OPENINGS_WITH_HEADING * len(apart):
        return roles
    titled = sum(1 for p in headed if len(p.lines[0].text.strip()) > NUMBER_CHARS)
    words = titled > len(headed) / 2
    out = dict(roles)
    for p in apart:
        ref = SourceRef(p.number, 0)
        role = roles.get(ref)
        if role is None or role.role == "chapter_heading" or is_body(role) and not words:
            continue
        line = p.lines[0]
        text = line.text.strip()
        # A speck in a corner reads as "-" or "." and stands aside; a number is centred.
        full, _ = P.geometry(p)
        if (
            (len(text) <= NUMBER_CHARS or words)
            and any(c.isalnum() for c in text)
            and P.centred_on_page(line, p, full)
        ):
            out[ref] = LineRole("chapter_heading", role.confidence, 0.0, RULE)
    return out


def run_gaps(
    pages: list[PageText],
    roles: dict[SourceRef, LineRole],
    reread: Callable[[set[SourceRef]], dict[SourceRef, str]] | None = None,
) -> dict[SourceRef, LineRole]:
    """`roles` with a dropped line made a chapter heading where it fills a gap in the book's
    run of numbered headings: in reading order it reads a number past the run so far (by
    at most `RUN_GAP`; before the run's first number, within `RUN_GAP` below it) and short
    of the next heading's, centred, not the page's printed number, and not a page's first
    or last line, where page numbers stand, unless it opens a sunk page. Monterosso's
    chapters set mid-page between white lines ("4" between "3" and "5") are dropped as
    specks by the trees. A line of at most `NUMBER_CHARS` characters that reads as no
    number ("Kil" for 11, "e," for 2) is read again by `reread`, only where the run has a
    gap, and counts by that reading. Needs `MIN_NUMBERED` numbered headings. Returns a new
    dict."""
    offset = P.page_offset(pages)
    sunk = P.sunk_pages(pages)
    order = [(p, i) for p in pages for i in range(len(p.lines))]
    anchors = [
        (k, v)
        for k, (p, i) in enumerate(order)
        if (r := roles.get(SourceRef(p.number, i))) is not None
        and r.role == "chapter_heading"
        and (v := value(p.lines[i].text)) is not None
    ]
    if len(anchors) < MIN_NUMBERED:
        return roles

    def placed(p: PageText, i: int) -> bool:
        role = roles.get(SourceRef(p.number, i))
        if role is None or is_body(role) or role.role == "chapter_heading":
            return False
        edge = i in (0, len(p.lines) - 1) and not (i == 0 and p.number in sunk)
        full, _ = P.geometry(p)
        return (
            not edge
            and not P.printed_page_number(p.lines[i].text.strip(), p, offset)
            and P.centred_on_page(p.lines[i], p, full)
        )

    # Where the kept headings may leave a number out: before the run's first one above 1,
    # between two more than one apart, and after the last.
    in_gap, before, after = set(), None, iter(anchors + [(len(order), None)])
    upcoming = next(after)
    for k in range(len(order)):
        while upcoming[0] < k:
            before, upcoming = upcoming[1], next(after)
        if upcoming[0] == k:
            continue
        if upcoming[1] is None or upcoming[1] - (before or 0) > 1:
            in_gap.add(k)
    misread = {
        SourceRef(p.number, i)
        for k, (p, i) in enumerate(order)
        if k in in_gap
        and value(p.lines[i].text) is None
        and len(p.lines[i].text.strip()) <= NUMBER_CHARS
        and placed(p, i)
    }
    second = reread(misread) if reread is not None and misread else {}

    out = dict(roles)
    run = None  # the last number of the run, in reading order
    nxt = iter(anchors + [(len(order), None)])
    upcoming = next(nxt)
    for k, (p, i) in enumerate(order):
        while upcoming[0] < k:
            upcoming = next(nxt)
        ref = SourceRef(p.number, i)
        if upcoming[0] == k:
            run = upcoming[1]
            continue
        v = value(p.lines[i].text)
        if v is None and ref in second:
            v = value(second[ref])
        if v is None or not placed(p, i):
            continue
        after_run = run < v <= run + RUN_GAP if run is not None else False
        below_first = run is None and upcoming[1] is not None and upcoming[1] - RUN_GAP <= v
        if (after_run or below_first) and (upcoming[1] is None or v < upcoming[1]):
            out[ref] = LineRole("chapter_heading", roles[ref].confidence, 0.0, RUN_RULE)
            run = v
    return out


def off_run(pages: list[PageText], roles: dict[SourceRef, LineRole]) -> dict[SourceRef, LineRole]:
    """`roles` with a heading dropped that reads as a number off the book's run (not between
    its neighbours' numbers) and stands unlike the run's headings, off the middle where at
    least `CENTRED_SHARE` of them are centred: Doodskleed's specks above a page's first
    line read "7" between chapters 3 and 4. A misread number set like the others stays
    (Monterosso's centred "5" for 15), as does an off-centre one the run expects there.
    Needs `MIN_NUMBERED` numbered headings. Returns a new dict."""
    numbered_lines = [
        (SourceRef(p.number, i), v, P.centred_on_page(line, p, P.geometry(p)[0]))
        for p in pages
        for i, line in enumerate(p.lines)
        if (r := roles.get(SourceRef(p.number, i))) is not None
        and r.role == "chapter_heading"
        and len(line.text.strip()) <= NUMBER_CHARS
        and (v := value(line.text)) is not None
    ]
    if len(numbered_lines) < MIN_NUMBERED:
        return roles
    if sum(c for _, _, c in numbered_lines) < CENTRED_SHARE * len(numbered_lines):
        return roles
    out = dict(roles)
    for k, (ref, v, centred) in enumerate(numbered_lines):
        before = numbered_lines[k - 1][1] if k > 0 else None
        after = numbered_lines[k + 1][1] if k + 1 < len(numbered_lines) else None
        fits = (before is None or v > before) and (after is None or v < after)
        if not centred and not fits:
            role = roles[ref]
            out[ref] = LineRole("artifact", role.confidence, role.p_body, OFF_RUN_RULE)
    return out


def title_lines(
    pages: list[PageText],
    roles: dict[SourceRef, LineRole],
    styles: dict[SourceRef, Style],
) -> dict[SourceRef, LineRole]:
    """`roles` with a dropped line under a heading made a heading, where the book sets a
    heading's second line in the same type elsewhere: "Meervoudig stemrecht" under "BOEK
    TWEE" as "De cijnskiezers" under "BOEK EEN", Dolittle's "A MESSAGE FROM AFRICA" under
    "THE FOURTH CHAPTER" as "PUDDLEBY" under the first. Or where such dropped lines, of at
    most `LABEL_WORDS` words, recur in one type under `RECUR` headings or more: Het
    schaduwhuis' narrator, "ALEX" or "RENEE" under each chapter number; then the same
    words opening a page with no heading are one too (a chapter whose number the layer
    lacks). Only lines above the page's running text, of `SUBTITLE_LETTERS` letters or
    more (a speck "i" is no subtitle). On a page with no running text, a part page, a line
    of words right under a heading and set larger than the text is part of it ("Stof"
    under "Boek 3"): a motto is set small, a page number has no letters. Returns a new
    dict."""

    def heading(ref: SourceRef) -> bool:
        return (role := roles.get(ref)) is not None and role.role == "chapter_heading"

    def alike(a: Style, b: Style) -> bool:
        return (
            a.size is not None
            and b.size is not None
            and max(a.size, b.size) <= SAME_SIZE * min(a.size, b.size)
            and a.capitals == b.capitals
        )

    seconds = [
        styles[r]
        for p in pages
        for i in range(1, len(p.lines))
        if heading(r := SourceRef(p.number, i))
        and heading(SourceRef(p.number, i - 1))
        and r in styles
    ]
    dropped: list[tuple[SourceRef, Style, str]] = []  # under a heading, above the text
    for p in pages:
        above = False  # a heading above, and no running text yet
        for i, line in enumerate(p.lines):
            ref = SourceRef(p.number, i)
            role, style = roles.get(ref), styles.get(ref)
            if heading(ref):
                above = True
                continue
            if is_body(role):
                break
            # Dropped as furniture of any kind: the trees call such a line an artifact, a
            # running head or a page number.
            if not above or role is None or style is None or style.size is None:
                continue
            letters = sum(c.isalpha() for c in line.text)
            if letters >= SUBTITLE_LETTERS and not P.garbled(line):
                dropped.append((ref, style, line.text.strip()))
    labels = [
        (ref, style, text)
        for ref, style, text in dropped
        if len(text.split()) <= LABEL_WORDS
        and sum(alike(style, s) for _, s, t in dropped if len(t.split()) <= LABEL_WORDS) >= RECUR
    ]
    out = dict(roles)
    for ref, style, _ in dropped:
        if any(alike(style, s) for s in seconds):
            out[ref] = LineRole("chapter_heading", roles[ref].confidence, 0.0, "subtitle-alike")
    for ref, _, _ in labels:
        out[ref] = LineRole("chapter_heading", roles[ref].confidence, 0.0, "label-recurs")
    for p in pages:
        if any(is_body(roles.get(SourceRef(p.number, i))) for i in range(len(p.lines))):
            continue
        for i in range(1, len(p.lines)):
            ref, line = SourceRef(p.number, i), p.lines[i]
            role, style = out.get(ref), styles.get(ref)
            above = out.get(SourceRef(p.number, i - 1))
            if (
                above is not None
                and above.role == "chapter_heading"
                and role is not None
                and role.role != "chapter_heading"
                and style is not None
                and style.size is not None
                and style.size >= SAME_SIZE
                and sum(c.isalpha() for c in line.text) >= PART_TITLE_LETTERS
                and len(line.text.split()) <= LABEL_WORDS
                and not P.garbled(line)
            ):
                out[ref] = LineRole("chapter_heading", role.confidence, 0.0, "part-page")
    words = {text for _, _, text in labels}
    for p in pages:
        if not p.lines or any(heading(SourceRef(p.number, i)) for i in range(len(p.lines))):
            continue
        ref = SourceRef(p.number, 0)
        role, style = roles.get(ref), styles.get(ref)
        if (
            role is not None
            and not is_body(role)
            and style is not None
            and p.lines[0].text.strip() in words
            and any(alike(style, s) for _, s, _ in labels)
        ):
            out[ref] = LineRole("chapter_heading", role.confidence, 0.0, "label-recurs")
    return out


# A heading line at least this share of the page's full line runs as wide as text; so
# does one ending within `FLUSH` of a full line of the text's right edge, as beside a
# drawn initial ("UEEN ERMINTRUDE had" by its "Q").
RUNS_WIDE = 0.8
FLUSH = 0.03
_RUNS_ON = re.compile(r"[^\W\d_,;:-]$|[,;:-]$")


def running_text(
    pages: list[PageText], roles: dict[SourceRef, LineRole]
) -> dict[SourceRef, LineRole]:
    """`roles` with a "heading" that runs on into the next line made body: as wide as a
    line of text or flush with its right edge, ending mid-sentence, the next line body in
    lower case ("BERREN" over
    "The crowd had come to watch three men die. Most of" / "them had no idea…"). A heading
    never runs into the sentence below it. Returns a new dict."""
    out = dict(roles)
    for p in pages:
        if len(p.lines) < 2:
            continue
        full, _ = P.geometry(p)
        right = statistics.median(ln.x1 for ln in p.lines)
        for i, line in enumerate(p.lines[:-1]):
            ref, nxt = SourceRef(p.number, i), p.lines[i + 1]
            role = roles.get(ref)
            if role is None or role.role != "chapter_heading":
                continue
            below = roles.get(SourceRef(p.number, i + 1))
            if (
                (line.x1 - line.x0 >= RUNS_WIDE * full or abs(line.x1 - right) <= FLUSH * full)
                and _RUNS_ON.search(line.text.rstrip())
                and nxt.text.lstrip()[:1].islower()
                and is_body(below)
            ):
                out[ref] = LineRole("body", role.confidence, 1.0, "runs-on")
    return out


def _role(roles: dict[SourceRef, LineRole], page: PageText) -> str:
    role = roles.get(SourceRef(page.number, 0))
    return role.role if role is not None else "body"


def value(text: str) -> int | None:
    """The chapter number `text` reads as, its old-style look-alikes folded, or None."""
    t = text.strip().rstrip(".").translate(_MISREADS)
    return int(t) if 0 < len(t) <= NUMBER_CHARS and t.isascii() and t.isdigit() else None


def settled(blocks: list[Block]) -> set[SourceRef]:
    """The lines of headings their run confirms, so the review needn't ask about them
    (`blocks` after `numbered`): bare chapter numbers each one more than the one before
    or after, judged on a heading's first line ("2" of "2 ALEX"); a line whose words stand
    under `RECUR` headings' first lines or more (a narrator's "ALEX"), wherever they
    stand; titles opening on a year, at least `MIN_NUMBERED` of them, each later than the
    one before ("1885: Een ramp" after "1840-1884: Aan de Dender"); parts counted in words
    in order ("BOEK TWEE" after "BOEK EEN")."""
    headings = [b for b in blocks if isinstance(b, Heading)]
    out: set[SourceRef] = set()

    def lines(h: Heading) -> list[tuple[str, list[SourceRef]]]:
        # Each part with its own line where they pair up; a number over the lines under
        # it, which reflow sets as one part ("2 ALEX"), as its first; else the heading.
        if len(h.parts) > 1 and len(h.parts) == len(h.sources):
            return [(t, [s]) for t, s in zip(h.parts, h.sources, strict=True)]
        first, _, rest = h.text.partition(" ")
        if len(h.sources) > 1 and rest and value(first) is not None:
            return [(first, h.sources[:1]), (rest, h.sources[1:])]
        return [(h.text, list(h.sources))]

    firsts = [lines(h)[0] for h in headings]
    values = [value(t) for t, _ in firsts]
    for k, ((text, refs), v) in enumerate(zip(firsts, values, strict=True)):
        before = values[k - 1] if k else None
        after = values[k + 1] if k + 1 < len(values) else None
        if v is not None and (before == v - 1 or after == v + 1) and str(v) == text:
            out |= set(refs)
    # Recurring as a heading's second line, never its first: a label, not a running head.
    labels = Counter(t for h in headings for t, _ in lines(h)[1:])
    for h in headings:
        out |= {r for t, refs in lines(h) if labels[t] >= RECUR for r in refs}
    for key in (_year, _part):
        run = [(h, n) for h in headings if (n := key(h.text)) is not None]
        if len(run) >= MIN_NUMBERED or key is _part and len(run) >= 2:
            if all(b > a for (_, a), (_, b) in zip(run, run[1:], strict=False)):
                out |= {s for h, _ in run for s in h.sources}
    return out


_YEAR = re.compile(r"^(1[5-9]\d\d|20\d\d)\s*(?:[-–]\s*\d{4})?\s*:")
_PART = re.compile(r"^(?:boek|deel|part|book)\s+(\w+)", re.I)
_COUNT = "een twee drie vier vijf zes zeven acht negen tien".split() + (
    "one two three four five six seven eight nine ten".split()
)


def _year(text: str) -> int | None:
    """The year a title opens on ("1887-1888: ‘De Toekomst’" → 1887), or None."""
    m = _YEAR.match(text.strip())
    return int(m.group(1)) if m else None


def _part(text: str) -> int | None:
    """A part's count ("BOEK TWEE Meervoudig stemrecht" → 2, "Part 3" → 3), or None."""
    m = _PART.match(text.strip())
    if not m:
        return None
    word = m.group(1).lower()
    if word.isdigit():
        return int(word)
    return _COUNT.index(word) % 10 + 1 if word in _COUNT else None


def numbered(blocks: list[Block]) -> list[Block]:
    """The blocks with each heading of a numbered run set to its number: a look-alike
    folded ("Io" → "10") where it fits the run, and a short heading that doesn't read as
    a number ("SE", "zi") where both its neighbours agree on it. Headings with a title
    of words are left out of the run. Labelled numbers ("HOOFDSTUK II") run the same way,
    their label set as the book's commonest spelling of it ("Hoorpstuk 6"). Returns a new
    list."""
    out = list(blocks)
    at = [
        i
        for i, b in enumerate(blocks)
        if isinstance(b, Heading) and len(b.text.strip()) <= NUMBER_CHARS
    ]
    for i, number in zip(at, _settle([value(blocks[i].text) for i in at]), strict=True):
        if number is not None and str(number) != blocks[i].text:
            out[i] = replace(blocks[i], text=str(number), parts=[str(number)])
    labelled = [
        (i, m.group(1), m.group(2))
        for i, b in enumerate(blocks)
        if isinstance(b, Heading)
        and (m := _LABELLED.match(b.text.strip()))
        and m.group(1).lower() not in _PARTS
    ]
    if not labelled:
        return out
    common = Counter(label for _, label, _ in labelled).most_common(1)[0][0]
    alike = [(i, n) for i, label, n in labelled if _same_label(label, common)]
    for (i, _), number in zip(alike, _settle([value(n) for _, n in alike]), strict=True):
        text = f"{common} {number}" if number is not None else None
        if text is not None and text != blocks[i].text:
            out[i] = replace(blocks[i], text=text, parts=[text])
    return out


_PARTS = {"boek", "deel", "part", "book"}
# A subtitle has at least this many letters ("i", a speck under a heading, has one).
SUBTITLE_LETTERS = 4
# A heading's dropped second line recurring in one type under this many headings, of at
# most this many words, labels the book's chapters (a narrator's name, a place).
RECUR = 3
LABEL_WORDS = 4
# A part page's title under its heading has at least this many letters ("Wij"); a speck
# read as one letter has fewer.
PART_TITLE_LETTERS = 2
# A heading of a label word and a number as read ("HOOFDSTUK 11", "Hoorpstvk 13").
_LABELLED = re.compile(r"^([^\W\d_]{4,})\s+([^\s]{1,3})\.?$")
# A label at least this alike the book's commonest is that label misread ("HoOoeEpstvkK"
# 0.5, "Hoorpstuk" 0.78); another word is far below ("Proloog" 0.11).
LABEL_ALIKE = 0.5


def number_of(text: str) -> int | None:
    """A heading's chapter number, bare ("12", "Io") or after a label ("HOOFDSTUK 12"); a
    part's number ("Boek 2") is none: parts are counted apart."""
    if (n := value(text)) is not None:
        return n
    m = _LABELLED.match(text.strip())
    return value(m.group(2)) if m and m.group(1).lower() not in _PARTS else None


def _same_label(label: str, common: str) -> bool:
    return Levenshtein.normalized_similarity(label.lower(), common.lower()) >= LABEL_ALIKE


def _settle(read: list[int | None]) -> list[int | None]:
    """Each heading's number, by its run: a reading that fits stays, one off the run is
    the number both neighbours agree on. All None where the readings don't run: five or
    more, and of the neighbours both read, half following one on the other (a heading
    lost leaves a gap, not a break: Het ijzige land's lacks four)."""
    pairs = [
        (a, b) for a, b in zip(read, read[1:], strict=False) if a is not None and b is not None
    ]
    following = sum(1 for a, b in pairs if b == a + 1)
    if len(read) < MIN_NUMBERED or not pairs or following < len(pairs) / 2:
        return [None] * len(read)
    settled: list[int | None] = []
    for k, number in enumerate(read):
        before = settled[k - 1] if k else None
        after = read[k + 1] if k + 1 < len(read) else None
        if before is not None:
            expected = before + 1
        elif after is not None:
            expected = after - 1
        else:
            expected = None
        if expected is not None and number != expected:
            # A reading off the run stands unless both neighbours say otherwise.
            agreed = before is not None and after == expected + 1
            number = expected if agreed or number is None and after is None else number
        settled.append(number)
    return settled
