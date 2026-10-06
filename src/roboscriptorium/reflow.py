"""Turn positioned page lines into blocks: drop print artefacts, mark chapter
headings, undo line-end hyphenation and join paragraphs across page breaks.

Line roles come from a decision model (see roles.py). Without them, a footer
heuristic drops page numbers and the rest is treated as body text.
"""

import itertools
import re
import statistics

from roboscriptorium.ir import Block, Heading, Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import KEEP_BODY_AT, NUMBERED_WORDS, LineRole, bare_numeral

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
_LOWER_START = re.compile(r"^[a-zà-ÿ]")
# Older OCR layers keep the thin space some printers set before punctuation.
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,;:.!?])(?=\s|$)")

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
    """Whether each line starts a paragraph: right of the local left margin, or after
    a sentence's short last line in justified text."""
    flags = []
    for i, line in enumerate(lines):
        window = lines[max(0, i - MARGIN_WINDOW) : i + MARGIN_WINDOW + 1]
        starts = sorted(ln.x0 for ln in window)
        margin = starts[len(starts) // 4]
        if line.starts_paragraph is not None:
            flags.append(line.starts_paragraph)
        else:
            flags.append(line.x0 - margin > INDENT_MIN or _after_short_line(lines, i, margin))
    return flags


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


def join(text: str, nxt: str) -> str:
    """Append the next line, undoing hyphenation where the word continues."""
    if text.endswith(HYPHENS) and len(text) > 1 and text[-2].isalpha():
        # A real hyphen: a capital after the break ("Noord-Holland"), or a compound
        # that has hyphens elsewhere ("Mens-erger-je-niet", "glas-in-lood").
        last, first = text.split()[-1][:-1], nxt.split()[0] if nxt.split() else ""
        if not _LOWER_START.match(nxt) or "-" in last or "-" in first:
            return text + nxt
        return text[:-1] + nxt
    if text.endswith(DASHES):
        # A spaced dash ("ziet – hoe") keeps its spaces; a closed one ("alles—en") doesn't.
        return f"{text} {nxt}" if text[:-1].endswith(" ") else text + nxt
    return f"{text} {nxt}"


def _role(roles: dict[SourceRef, LineRole] | None, ref: SourceRef) -> str:
    if roles is None or (r := roles.get(ref)) is None or r.p_body >= KEEP_BODY_AT:
        return "body"
    return r.role


def reflow(pages: list[PageText], roles: dict[SourceRef, LineRole] | None = None) -> list[Block]:
    blocks: list[Block] = []
    opening = True
    for page in pages:
        lines = page.lines if roles is not None else page.lines[: footer_start(page)]
        kept = []
        for index, line in enumerate(lines):
            ref = SourceRef(page.number, index)
            role = _role(roles, ref)
            if role == "body":
                kept.append((ref, line))
                continue
            # Indents are measured within each run of body lines.
            _add_body(blocks, kept, opening)
            if kept:
                opening = False
            kept = []
            if role == "chapter_heading":
                previous = blocks[-1] if blocks else None
                if _continues(previous, line, page.number):
                    # A heading set over several lines, like "CHAPTER" above "I."
                    previous.text += f" {line.text}"
                    previous.sources.append(ref)
                    if _labels(previous.parts[-1]) and not bare_numeral(line.text):
                        previous.parts.append(line.text)
                    else:
                        previous.parts[-1] += f" {line.text}"
                else:
                    text = bare_numeral(line.text) or line.text
                    blocks.append(Heading(text, [ref], [text]))
                opening = True
        _add_body(blocks, kept, opening)
        if kept:
            opening = False
    for block in blocks:
        block.text = tidy(block.text)
        if isinstance(block, Paragraph):
            block.text = close_quotes(block.text)
        if isinstance(block, Heading):
            block.parts = [tidy(p) for p in block.parts]
    return blocks


def close_quotes(text: str) -> str:
    """Mend a closing double quote that an old OCR layer read as a single one.

    Only in straight-quoted text: a `'` that ends a word while a `"` is open and
    no `'` is, closes the `"` ("asleep in his chair'" → "asleep in his chair\"").
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
            elif double:
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
    if bare_numeral(line.text):
        # "The Nature of a Crime" above "I" is the book's title, then chapter I.
        words = previous.text.upper().split()
        return bool(words) and words[-1].strip(".") in NUMBERED_WORDS
    # "THE FIRST CHAPTER" under the book's title starts a heading of its own.
    return not _labels(line.text)


def _add_body(blocks: list[Block], kept: list[tuple[SourceRef, Line]], opening: bool) -> None:
    flags = indented([ln for _, ln in kept])
    for k, ((ref, line), starts_paragraph) in enumerate(zip(kept, flags, strict=True)):
        current = blocks[-1] if blocks else None
        if not isinstance(current, Paragraph) or (k == 0 and opening):
            blocks.append(
                Paragraph(line.text, [ref], opening=opening and k == 0, initial=line.initial)
            )
        elif starts_paragraph or line.initial:
            blocks.append(Paragraph(line.text, [ref], initial=line.initial))
        else:
            current.text = join(current.text, line.text)
            current.sources.append(ref)
