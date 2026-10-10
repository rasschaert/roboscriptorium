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

from roboscriptorium.ir import Block, Heading, Paragraph, SourceRef
from roboscriptorium.page import NUMBERED_WORDS, bare_numeral, digits
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import KEEP_BODY_AT, LineRole

# A paragraph-opening indent is ~10pt on the target scans; line-start jitter
# from skew stays under ~3pt.
INDENT_MIN = 5.0
# The local left margin is the lower quartile of line starts within this many
# lines either side: it follows skew drift down the page, and stays on the
# margin even when only two lines are left and one of them is indented.
MARGIN_WINDOW = 5
# Where paragraphs aren't indented, a paragraph starts after a line that ends a
# sentence this far short of the right margin, as a share of the line width.
# Only in justified text: most lines in the window end within JUSTIFIED_SLACK
# points of the margin.
SHORT_LINE = 0.05
JUSTIFIED_SLACK = 3.0
JUSTIFIED_SHARE = 0.6
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

HYPHENS = ("-", "\u00ad", "\u00ac")
DASHES = ("\u2014", "\u2013")
# What isn't part of a word, for counting spellings ("thief-taker’s," → "thief-takers").
_WORD = re.compile(r"[^\w-]")
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
    if i == 0:
        return False
    previous = lines[i - 1]
    window = lines[max(0, i - MARGIN_WINDOW) : i + MARGIN_WINDOW + 1]
    ends = sorted(ln.x1 for ln in window)
    right = ends[3 * len(ends) // 4]
    justified = sum(right - ln.x1 < JUSTIFIED_SLACK for ln in window)
    return (
        justified >= JUSTIFIED_SHARE * len(window)
        and right - previous.x1 > SHORT_LINE * (right - margin)
        and previous.text.rstrip().endswith(SENTENCE_END)
        and not lines[i].text.lstrip()[:1].islower()
        and not lines[i].text.lstrip().startswith(tuple(".,;:!?"))
    )


def spellings(pages: list[PageText]) -> Counter:
    """How often the book prints each word where no line break decides its spelling: all
    but a line's last word cut by a hyphen and the next line's first word, its rest."""
    seen: Counter = Counter()
    for page in pages:
        cut = False
        for line in page.lines:
            words = line.text.split()
            whole = words[1:] if cut else words
            cut = bool(words) and words[-1].endswith(HYPHENS)
            for word in whole[:-1] if cut else whole:
                if key := _WORD.sub("", word).lower():
                    seen[key] += 1
    return seen


def join(
    text: str, nxt: str, seen: Counter | None = None, known: Callable[[str], bool] | None = None
) -> str:
    """Append the next line, undoing hyphenation where the word continues.

    Whether a hyphen at the line's end is the word's own is settled by evidence, the
    strongest first: how the book spells the word inside lines (`seen`, from
    `spellings`: "thief-taker" elsewhere keeps it, "thieftaker" drops it); which of the
    two forms the language's word list knows (`known`, such as `Lexicon.knows`: it has
    "wc-rol" and not "wcrol"); a capital after the break ("Noord-Holland"; a word set
    in capitals isn't one); and, with a hyphen already in the word, whether the parts
    beside the break are both words ("Mens-erger-je-niet" keeps it) or one word broken
    ("Zuid-Lon-den" doesn't; without a word list the hyphen stays). Otherwise the hyphen
    was the break's.
    """
    if text.endswith(HYPHENS) and len(text) > 1 and text[-2].isalpha():
        last, first = text.split()[-1][:-1], nxt.split()[0] if nxt.split() else ""
        if _hyphen_stays(nxt, _WORD.sub("", last), _WORD.sub("", first), seen, known):
            return text.rstrip("".join(HYPHENS)) + "-" + nxt
        return text[:-1] + nxt
    if text.endswith(DASHES):
        # A spaced dash ("ziet – hoe") keeps its spaces; a closed one ("alles—en") doesn't.
        return f"{text} {nxt}" if text[:-1].endswith(" ") else text + nxt
    if text.endswith("-") and len(text) > 1 and text[-2].isdigit() and nxt[:1].isdigit():
        return text + nxt  # a number range broken at the line's end ("1914-" / "1918")
    return f"{text} {nxt}"


def _hyphen_stays(
    nxt: str, stem: str, rest: str, seen: Counter | None, known: Callable[[str], bool] | None
) -> bool:
    """Whether the hyphen between `stem` and `rest` is the word's own (see `join`)."""
    closed, hyphenated = stem + rest, f"{stem}-{rest}"
    if seen and seen[hyphenated.lower()] != seen[closed.lower()]:
        return seen[hyphenated.lower()] > seen[closed.lower()]
    if known is not None and known(hyphenated) != known(closed):
        return known(hyphenated)
    if not nxt[:1].islower():
        return not (len(rest) > 1 and rest.isupper())
    if "-" in stem or "-" in rest:
        if known is None:
            return True
        # The parts beside the break: a word of their own ("Lon" + "den") was broken
        # there; two words ("erger" + "je") were joined by the hyphen.
        before, after = stem.rsplit("-", 1)[-1], rest.split("-", 1)[0]
        if known(before + after):
            return False
        return min(len(before), len(after)) >= 3 and known(before) and known(after)
    return False


def _role(roles: dict[SourceRef, LineRole] | None, ref: SourceRef) -> str:
    if roles is None or (r := roles.get(ref)) is None or r.p_body >= KEEP_BODY_AT:
        return "body"
    return r.role


def reflow(
    pages: list[PageText],
    roles: dict[SourceRef, LineRole] | None = None,
    known: Callable[[str], bool] | None = None,
) -> list[Block]:
    """Lines into blocks. `known` says whether the language's word list has a word
    (`Lexicon.knows`), evidence for the hyphens at line ends (`join`)."""
    seen = spellings(pages)
    blocks: list[Block] = []
    opening = True
    # Whether a scene break waits for the next paragraph.
    scene = [False]
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
            # Indents are measured within each run of body lines.
            opening = _add_body(blocks, kept, opening, seen, known, scene)
            kept = []
            if _ornament(line):
                scene[0] = True
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
        opening = _add_body(blocks, kept, opening, seen, known, scene)
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


def single_quoted(blocks: list[Block]) -> bool:
    """Whether the book opens its dialogue with ‘ rather than “, as Dutch print does.

    Counted on the book's own text: an OCR layer misreads some ‘ as “, not most.
    """
    text = " ".join(b.text for b in blocks if isinstance(b, Paragraph))
    return text.count("‘") > 2 * text.count("“")


def open_single(text: str) -> str:
    """In single-quoted text, a “ that no ” closes is a ‘ the OCR layer misread.

    What closes it is the next quote mark after it, apostrophes (zo’n, ’s) aside.
    A real “ (a quote within the dialogue, a title) closes with ”, or with ’’ in
    some typesetting, so it stays.
    """
    chars = list(text)
    for i, c in enumerate(chars):
        if c != "“":
            continue
        closer = None
        for k in range(i + 1, len(chars)):
            if chars[k] not in "‘“’”":
                continue
            after = chars[k + 1] if k + 1 < len(chars) else " "
            if chars[k] == "’" and after.isalpha():
                continue
            closer = "”" if "".join(chars[k : k + 2]) == "’’" else chars[k]
            break
        if closer != "”":
            chars[i] = "‘"
    return "".join(chars)


def close_quotes(text: str) -> str:
    """Mend a closing double quote that an old OCR layer read as a single one.

    Only in straight-quoted text: a `'` while a `"` is open and no `'` is closes
    the `"`, when it follows punctuation ("before.' said he") or ends the
    paragraph ("asleep in his chair'"). After a letter and before more text it may
    be a plural possessive ("the animals' language"), so it stays.
    """
    if any(q in text for q in "“”‘’"):
        return text
    chars = list(text)
    double = single = False
    for i, c in enumerate(chars):
        before = chars[i - 1] if i else " "
        after = chars[i + 1] if i + 1 < len(chars) else " "
        if c == '"':
            double = not double
        elif c != "'" or (before.isalnum() and after.isalnum()):
            continue
        elif not before.isspace() and (after.isspace() or after in ".,;:!?—-"):
            if single:
                single = False
            elif double and (before in ".,;:!?—-" or i == len(chars) - 1):
                chars[i], double = '"', False
        elif before.isspace() or before in '"(':
            single = True
    return "".join(chars)


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
) -> bool:
    """Append a run of body lines to `blocks`; whether the next block still opens a section.

    `scene` holds whether a scene break waits for the next paragraph: an ornament line
    sets it, and white space of `SCENE_GAP` pitches after a sentence is one too."""
    scene = scene if scene is not None else [False]
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
        elif starts_paragraph or line.initial:
            blocks.append(Paragraph(line.text, [ref], initial=line.initial))
        else:
            current.text = join(current.text, line.text, seen, known)
            current.sources.append(ref)
    return opening and not kept
