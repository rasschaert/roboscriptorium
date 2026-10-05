"""Turn positioned page lines into paragraphs: drop print artefacts, undo
line-end hyphenation and join paragraphs across page breaks.

Heuristic first pass. Each rule here is a candidate for an Ollaya decision once
golden pages show where it fails.
"""

import itertools
import re
import statistics

from roboscriptorium.ir import Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText

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

HYPHENS = ("-", "\u00ad", "\u00ac")
DASHES = ("\u2014", "\u2013")
_LOWER_START = re.compile(r"^[a-zà-ÿ]")


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


def reflow(pages: list[PageText]) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    for page in pages:
        body = list(enumerate(page.lines[: footer_start(page)]))
        flags = indented([ln for _, ln in body])
        for (index, line), starts_paragraph in zip(body, flags, strict=True):
            ref = SourceRef(page.number, index)
            if not paragraphs:
                paragraphs.append(Paragraph(line.text, [ref], opening=True))
            elif starts_paragraph:
                paragraphs.append(Paragraph(line.text, [ref]))
            else:
                current = paragraphs[-1]
                current.text = join(current.text, line.text)
                current.sources.append(ref)
    return paragraphs
