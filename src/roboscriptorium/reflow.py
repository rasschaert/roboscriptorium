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
from roboscriptorium.roles import LineRole

# A paragraph-opening indent is ~10pt on the target scans; line-start jitter
# from skew stays under ~3pt.
INDENT_MIN = 5.0
# The local left margin is the lower quartile of line starts within this many
# lines either side: it follows skew drift down the page, and stays on the
# margin even when only two lines are left and one of them is indented.
MARGIN_WINDOW = 5
# The footer (page number, ornaments, specks read as text) starts after a gap
# wider than this many line spacings, in the bottom fifth of the page, and holds
# only lines of at most FOOTER_MAX_CHARS characters. Line height stands in for
# the spacing when there are too few body lines to measure it.
FOOTER_ZONE = 0.8
FOOTER_GAP = 1.5
FOOTER_MAX_CHARS = 4

# A line the model calls something other than body is still kept as body when
# P(body) is at least this; losing text is worse than keeping a stray line.
KEEP_BODY_AT = 0.5

HYPHENS = ("-", "\u00ad", "\u00ac")
DASHES = ("\u2014", "\u2013")
_LOWER_START = re.compile(r"^[a-zà-ÿ]")
# Older OCR layers keep the thin space some printers set before punctuation.
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,;:.!?])(?=\s|$)")


def tidy(text: str) -> str:
    return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)


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
    """Whether each line starts right of the local left margin."""
    flags = []
    for i, line in enumerate(lines):
        window = lines[max(0, i - MARGIN_WINDOW) : i + MARGIN_WINDOW + 1]
        starts = sorted(ln.x0 for ln in window)
        margin = starts[len(starts) // 4]
        flags.append(line.x0 - margin > INDENT_MIN)
    return flags


def join(text: str, nxt: str) -> str:
    """Append the next line, undoing hyphenation where the word continues."""
    if text.endswith(HYPHENS) and len(text) > 1 and text[-2].isalpha():
        # A capital after the break means a real hyphen, as in "Noord-Holland".
        return text[:-1] + nxt if _LOWER_START.match(nxt) else text + nxt
    if text.endswith(DASHES):
        return text + nxt
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
                if isinstance(previous, Heading) and previous.sources[-1].page == page.number:
                    # A heading set over several lines, like "CHAPTER" above "I."
                    previous.text += f" {line.text}"
                    previous.sources.append(ref)
                else:
                    blocks.append(Heading(line.text, [ref]))
                opening = True
        _add_body(blocks, kept, opening)
        if kept:
            opening = False
    for block in blocks:
        block.text = tidy(block.text)
    return blocks


def _add_body(blocks: list[Block], kept: list[tuple[SourceRef, Line]], opening: bool) -> None:
    flags = indented([ln for _, ln in kept])
    for k, ((ref, line), starts_paragraph) in enumerate(zip(kept, flags, strict=True)):
        current = blocks[-1] if blocks else None
        if not isinstance(current, Paragraph) or (k == 0 and opening):
            blocks.append(Paragraph(line.text, [ref], opening=opening and k == 0))
        elif starts_paragraph:
            blocks.append(Paragraph(line.text, [ref]))
        else:
            current.text = join(current.text, line.text)
            current.sources.append(ref)
