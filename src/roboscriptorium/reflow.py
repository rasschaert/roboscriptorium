"""Turn positioned page lines into blocks: drop print artefacts, mark chapter
headings, undo line-end hyphenation and join paragraphs across page breaks.

Line roles come from a decision model (see roles.py). Without them, a footer
heuristic drops page numbers and the rest is treated as body text.
"""

import itertools
import re
import statistics
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from roboscriptorium.hyphens import HYPHENS, Compound, join, spellings
from roboscriptorium.ir import Block, Heading, Paragraph, SourceRef
from roboscriptorium.page import NUMBERED_WORDS, bare_numeral, digits
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.quotes import close_quotes, open_single, single_quoted
from roboscriptorium.roles import LineRole, is_body

# A paragraph-opening indent is ~10pt on the target scans; line-start jitter
# from skew stays under ~3pt.
INDENT_MIN = 5.0
# A line narrower than this (points) on a text line's row is a mark split off it.
SLIVER_WIDTH = 8.0
# A paragraph indent is at most this wide; a line starting further right is centred.
MAX_INDENT = 30.0
# A line set flush starts at most this far left of the margin: further left, the
# layer's box has slipped (De tuin's indented page tops at -1.8 to -6.6 points; Reis's
# flush ones from -1.0).
FLUSH_SLACK = 1.5
# The local left margin is the lower quartile of line starts within this many
# lines either side: it follows skew drift down the page, and stays on the
# margin even when only two lines are left and one of them is indented.
MARGIN_WINDOW = 5
# Where paragraphs aren't indented, a paragraph starts after a line that ends a
# sentence this far short of the right margin, as a share of the line width.
# Only in justified text: most of the window's lines that end mid-sentence end within
# JUSTIFIED_SLACK points of the margin.
SHORT_LINE = 0.02
JUSTIFIED_SLACK = 3.0
JUSTIFIED_SHARE = 0.6
# Lines ending mid-sentence needed to tell; the page's run stands in for a window
# with fewer.
JUSTIFIED_INNER = 3
# The page's margin, from the lines that reach the right margin (most are a paragraph's
# inner lines), takes over where the local window's lines are all indented: a run of
# one-line dialogue paragraphs. It needs this many such lines.
PAGE_MARGIN_LINES = 4
# A line further below the one before it than this many times the run's usual line
# pitch, at its top and its bottom alike, starts a paragraph: a blank line set before
# an unindented one, or letters spaced apart. Box tops alone jitter on some layers.
PARAGRAPH_GAP = 1.5
# White space of this many pitches before a paragraph is a scene break.
SCENE_GAP = 1.8
# A line of nothing but ornaments ("* * *", "⁂", "• • •") sets a scene break.
_ORNAMENT = re.compile(r"^\s*(?:[*·•⁂~#◊♦]\s*){1,}$")
SENTENCE_END = tuple(".!?:'\"’”)…")
# The footer (page number, ornaments, specks read as text) starts after a gap
# wider than this many line spacings, in the bottom fifth of the page, and holds
# only lines of at most FOOTER_MAX_CHARS characters. Line height stands in for
# the spacing when there are too few body lines to measure it.
FOOTER_ZONE = 0.8
FOOTER_GAP = 1.5
FOOTER_MAX_CHARS = 4

# Older OCR layers keep the thin space some printers set before punctuation. A dot in
# a spaced run (". . .") keeps its space: the typography stage sets the run book-wide.
_SPACE_BEFORE_PUNCTUATION = re.compile(r"(?<!\.)\s+([,;:.!?])(?=\s|$)(?!\s\.)")

# Typesetting ligatures ("ﬁ", "ﬀ") are glyphs, not letters.
_LIGATURES = str.maketrans(
    {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\ufb06": "st",
    }
)


def tidy(text: str) -> str:
    return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text.translate(_LIGATURES))


def footer_start(page: PageText) -> int:
    """Index of the first footer line, or len(lines) when there is no footer."""
    lines = page.lines
    for i in range(1, len(lines)):
        if i >= 2:
            spacing = statistics.median(b.y0 - a.y0 for a, b in itertools.pairwise(lines[:i]))
        else:
            spacing = lines[0].y1 - lines[0].y0
        if (
            lines[i].y0 > page.height * FOOTER_ZONE
            and lines[i].y0 - lines[i - 1].y0 > FOOTER_GAP * spacing
            and all(len(ln.text.replace(" ", "")) <= FOOTER_MAX_CHARS for ln in lines[i:])
        ):
            return i
    return len(lines)


def indented(lines: list[Line]) -> list[bool]:
    """Whether each line starts a paragraph: right of the left margin, below a gap, or
    after a sentence's short last line in justified text.

    The margin is the lower quartile of line starts within a window, which follows skew
    down the page, or the page's own margin where that is further left (`_page_margin`)
    and the line before doesn't reach the right margin: in a run of short dialogue
    paragraphs every line in the window is indented. After a full line the window's
    margin holds, so an indented block (a hanging list, a sidebar) isn't split up.
    """
    page = _page_margin(lines)
    pitch = _pitch(lines)
    flags = []
    for i, line in enumerate(lines):
        window = lines[max(0, i - MARGIN_WINDOW) : i + MARGIN_WINDOW + 1]
        starts = sorted(ln.x0 for ln in window)
        margin = starts[len(starts) // 4]
        if page is not None and not (i and _full(lines, i - 1, page.right)):
            margin = min(margin, page.at((line.y0 + line.y1) / 2))
        if line.starts_paragraph is not None:
            flags.append(line.starts_paragraph)
        else:
            flags.append(
                line.x0 - margin > INDENT_MIN
                or (i > 0 and _spaced(lines[i - 1], line, pitch))
                or _after_short_line(lines, i, margin)
            )
    return flags


@dataclass(frozen=True)
class _Margin:
    base: float
    slope: float  # points right per point down: the page's skew
    right: float  # where full lines end

    def at(self, y: float) -> float:
        return self.base + self.slope * y


def _page_margin(lines: list[Line]) -> _Margin | None:
    """The left margin of the run's lines that reach the right margin, following the skew
    their right ends show; None with too few such lines (ragged right, a short run)."""
    # The right margin: the furthest right that enough lines end at, as dialogue may
    # make up most of the run.
    reached = [
        ln.x1
        for ln in lines
        if sum(abs(o.x1 - ln.x1) < JUSTIFIED_SLACK for o in lines) >= PAGE_MARGIN_LINES
    ]
    if not reached:
        return None
    right = max(reached)
    full = [ln for ln in lines if abs(right - ln.x1) < JUSTIFIED_SLACK]
    mid = [(ln.y0 + ln.y1) / 2 for ln in full]
    slopes = [
        (b.x1 - a.x1) / (yb - ya)
        for (a, ya), (b, yb) in itertools.combinations(zip(full, mid, strict=True), 2)
        if abs(yb - ya) > 1
    ]
    slope = statistics.median(slopes) if slopes else 0.0
    starts = sorted(ln.x0 - slope * y for ln, y in zip(full, mid, strict=True))
    return _Margin(starts[len(starts) // 4], slope, right)


def _full(lines: list[Line], k: int, right: float) -> bool:
    """Whether line k reaches a right margin: the page's, or the one it shares with a line
    beside it (an indented block's)."""
    x1 = lines[k].x1
    beside = [lines[j].x1 for j in (k - 1, k + 1) if 0 <= j < len(lines)]
    return right - x1 < JUSTIFIED_SLACK or any(abs(x - x1) < JUSTIFIED_SLACK for x in beside)


def _pitch(lines: list[Line]) -> float | None:
    pitches = [b.y0 - a.y0 for a, b in itertools.pairwise(lines)]
    return statistics.median(pitches) if len(pitches) >= 3 else None


def _spaced(above: Line, line: Line, pitch: float | None, times: float = PARAGRAPH_GAP) -> bool:
    """White space of `times` pitches between two lines, after one that ends in
    punctuation: below a line stopping mid-word or mid-sentence ("be-"), the gap is a line
    the layer lost."""
    end = above.text.rstrip()[-1:]
    return (
        pitch is not None
        and bool(end)
        and not end.isalnum()
        and end not in HYPHENS
        and min(line.y0 - above.y0, line.y1 - above.y1) > times * pitch
    )


def _after_short_line(lines: list[Line], i: int, margin: float) -> bool:
    return i > 0 and _short_end(lines, i - 1, margin) and _may_open(lines[i])


def _short_end(lines: list[Line], k: int, margin: float) -> bool:
    """Whether line k ends a sentence short of the right margin in justified text."""
    window = lines[max(0, k + 1 - MARGIN_WINDOW) : k + MARGIN_WINDOW + 2]
    # Lines that stop mid-sentence show whether the text is justified: dialogue's
    # short last lines don't count against it.
    inner = [ln for ln in window if not ln.text.rstrip().endswith(SENTENCE_END)]
    if len(inner) < JUSTIFIED_INNER:
        inner = [ln for ln in lines if not ln.text.rstrip().endswith(SENTENCE_END)]
    if len(inner) < JUSTIFIED_INNER:
        return False
    ends = sorted(ln.x1 for ln in inner)
    right = ends[len(ends) // 2]
    justified = sum(abs(right - ln.x1) < JUSTIFIED_SLACK for ln in inner)
    return (
        justified >= JUSTIFIED_SHARE * len(inner)
        and right - lines[k].x1 > SHORT_LINE * (right - margin)
        and lines[k].text.rstrip().endswith(SENTENCE_END)
    )


def _broken_word(text: str, line: Line) -> bool:
    """Whether `line` continues a word `text` broke with a hyphen: no paragraph starts there,
    however the line is set (beside a picture or an initial its margin moves)."""
    return (
        text.endswith(HYPHENS) and len(text) > 1 and text[-2].isalpha() and line.text[:1].islower()
    )


def _flush_where_paragraphs_indent(lines: list[Line], k: int) -> bool:
    """Whether line k sits on the run's left margin while the run indents its paragraphs
    (a line starts an indent's width right of the margin; a centred one, further right,
    doesn't count). A box left of the margin is the layer's slip, not a flush line."""
    starts = sorted(ln.x0 for ln in lines)
    margin = starts[len(starts) // 4]
    return -FLUSH_SLACK <= lines[k].x0 - margin <= INDENT_MIN and any(
        INDENT_MIN < ln.x0 - margin < MAX_INDENT for ln in lines
    )


def _sliver(lines: list[Line], i: int) -> bool:
    """Whether line i is a mark or two, narrower than `SLIVER_WIDTH`, sharing a row with
    the line before or after it: they overlap over most of the shorter one's height. A
    picture's garbled reading, wide, isn't one."""
    line = lines[i]
    if (
        line.x1 - line.x0 >= SLIVER_WIDTH
        or len(line.text.split()) != 1
        or len(line.text.strip()) > 2
    ):
        return False
    for j in (i - 1, i + 1):
        if 0 <= j < len(lines):
            other = lines[j]
            overlap = min(line.y1, other.y1) - max(line.y0, other.y0)
            if overlap > 0.5 * min(line.y1 - line.y0, other.y1 - other.y0):
                return True
    return False


def _may_open(line: Line) -> bool:
    """Whether a line can start a paragraph: not in lower case or on punctuation."""
    text = line.text.lstrip()
    return not text[:1].islower() and not text.startswith(tuple(".,;:!?"))


def _role(roles: dict[SourceRef, LineRole] | None, ref: SourceRef) -> str:
    r = roles.get(ref) if roles is not None else None
    return "body" if is_body(r) else r.role


def reflow(
    pages: list[PageText],
    roles: dict[SourceRef, LineRole] | None = None,
    known: Callable[[str], bool] | None = None,
    compound: Compound | None = None,
) -> list[Block]:
    """Lines into blocks. `known` says whether the language's word list has a word
    (`Lexicon.knows`), and `compound` whether an undecided hyphen is the word's own:
    evidence for the hyphens at line ends (`join`)."""
    seen = spellings(pages)
    blocks: list[Block] = []
    opening = True
    # Whether a scene break waits for the next paragraph.
    scene = [False]
    # Whether the last run of body lines ended on a sentence's short last line.
    short_end = [False]
    for page in pages:
        lines = page.lines if roles is not None else page.lines[: footer_start(page)]
        kept = []
        for index, line in enumerate(lines):
            role = _role(roles, SourceRef(page.number, index))
            # The IR points at the line's index on the page before answers, also on a
            # corrected copy (`Line.source`).
            ref = SourceRef(page.number, index if line.source is None else line.source, line.typed)
            if role == "body":
                kept.append((ref, line))
                continue
            if role == "artifact" and _sliver(lines, index):
                # A sliver the layer split off a text line (a closing quote): dropped, it
                # shouldn't cut the run its row belongs to.
                continue
            # Indents are measured within each run of body lines.
            opening = _add_body(blocks, kept, opening, seen, known, scene, short_end, compound)
            kept = []
            if _ornament(line):
                scene[0] = True
                continue
            if role == "epigraph":
                # A motto's line, each its own paragraph, set apart (`epigraphs.py`).
                blocks.append(Paragraph(line.text, [ref], opening=True, epigraph=True))
                opening = True
                continue
            if role == "chapter_heading":
                previous = blocks[-1] if blocks else None
                if _continues(previous, line, page.number):
                    # A heading set over several lines, like "CHAPTER" above "I."
                    # A numeral read with "l" or "1" for "I" ("Ill.") keeps its full stop.
                    numeral = bare_numeral(line.text)
                    text = numeral + line.text.strip()[len(numeral) :] if numeral else line.text
                    previous.text += f" {text}"
                    previous.sources.append(ref)
                    if _labels(previous.parts[-1]) and not numeral:
                        previous.parts.append(text)
                    else:
                        previous.parts[-1] += f" {text}"
                else:
                    text = bare_numeral(line.text) or line.text
                    blocks.append(Heading(text, [ref], [text]))
                opening = True
        opening = _add_body(blocks, kept, opening, seen, known, scene, short_end, compound)
    for block in blocks:
        block.text = tidy(block.text)
        if isinstance(block, Paragraph):
            block.text = close_quotes(block.text)
        if isinstance(block, Heading):
            block.parts = [tidy(p) for p in block.parts]
    if single_quoted(blocks):
        for block in blocks:
            if isinstance(block, Paragraph):
                block.text = open_single(block.text)
    return blocks


def _labels(text: str) -> bool:
    """Whether a heading line is a label like "THE FIRST CHAPTER" or "CHAPTER XII."."""
    return bool(NUMBERED_WORDS & {w.strip(".,") for w in text.upper().split()})


def _continues(previous: Block | None, line: Line, page: int) -> bool:
    """Whether a heading line belongs to the heading just before it."""
    if not isinstance(previous, Heading) or previous.sources[-1].page != page:
        return False
    if bare_numeral(line.text) or digits(line.text.strip().rstrip(".")):
        # "The Nature of a Crime" above "I" is the book's title, then chapter I; a number
        # under "CHAPTER 2" is the chapter's first section. Only a bare label takes it.
        words = previous.text.upper().split()
        return bool(words) and words[-1].strip(".") in NUMBERED_WORDS
    # "THE FIRST CHAPTER" under the book's title starts a heading of its own.
    return not _labels(line.text)


def _ornament(line: Line) -> bool:
    """A line of ornaments marking a scene break: "⁂", or three marks at least ("* * *";
    one or two are a speck)."""
    marks = line.text.replace(" ", "")
    return bool(_ORNAMENT.match(line.text)) and (len(marks) >= 3 or marks == "⁂")


def _add_body(
    blocks: list[Block],
    kept: list[tuple[SourceRef, Line]],
    opening: bool,
    seen: Counter,
    known: Callable[[str], bool] | None,
    scene: list[bool] | None = None,
    short_end: list[bool] | None = None,
    compound: Compound | None = None,
) -> bool:
    """Append a run of body lines to `blocks`; whether the next block still opens a section.

    `scene` holds whether a scene break waits for the next paragraph: an ornament line
    sets it, and white space of `SCENE_GAP` pitches after a sentence is one too, as is a
    page that opens flush left after a finished paragraph where paragraphs indent.
    `short_end` holds whether the last run ended on a sentence's short last line, which
    starts a paragraph at the top of the next page as it does within a page."""
    scene = scene if scene is not None else [False]
    short_end = short_end if short_end is not None else [False]
    lines = [ln for _, ln in kept]
    flags = indented(lines)
    pitch = _pitch(lines)
    for k, ((ref, line), starts_paragraph) in enumerate(zip(kept, flags, strict=True)):
        if _ornament(line):
            scene[0] = True
            continue
        if k and pitch is not None and _spaced(lines[k - 1], line, pitch, SCENE_GAP):
            scene[0] = True
        current = blocks[-1] if blocks else None
        if (
            k == 0
            and short_end[0]
            and line.starts_paragraph is not False
            and _may_open(line)
            and isinstance(current, Paragraph)
            and current.sources
            and current.sources[-1].page != ref.page
            and _flush_where_paragraphs_indent(lines, 0)
        ):
            # A page that opens flush left after a finished paragraph, in a book that
            # indents its paragraphs: a scene's first paragraph, its white space lost
            # at the foot of the page before.
            scene[0] = True
        if not isinstance(current, Paragraph) or (k == 0 and opening) or scene[0]:
            first = opening and k == 0
            blocks.append(
                Paragraph(
                    line.text,
                    [ref],
                    opening=first or scene[0],
                    initial=line.initial,
                    break_before=scene[0] and not first,
                )
            )
            scene[0] = False
        elif line.initial or (
            (
                starts_paragraph
                or (k == 0 and line.starts_paragraph is None and short_end[0] and _may_open(line))
            )
            and not _broken_word(current.text, line)
        ):
            blocks.append(Paragraph(line.text, [ref], initial=line.initial))
        else:
            current.text = join(current.text, line.text, seen, known, compound)
            current.sources.append(ref)
    if lines:
        k = len(lines) - 1
        starts = sorted(ln.x0 for ln in lines[max(0, k - MARGIN_WINDOW) :])
        short_end[0] = _short_end(lines, k, starts[len(starts) // 4])
    return opening and not kept
