"""A book's dash and ellipsis style, measured on the scan or set in book.toml, and written
into every dash and ellipsis.

OCR layers write every dash as an em dash and space it at random, so how a book
prints its dashes is a decision for the whole book, not per line. On the page
image each dash's stroke is a run of columns whose ink is a thin band around
mid-height: about one letter long for an en dash, two for an em dash. The blank
columns either side, against the gaps between words on the same crops, tell
glued from thin from word-spaced dashes.

The output then sets every dash between words that way: a no-break space before
it (narrow for thin gaps) and a breaking one after it. Number ranges (1914–1918)
and hyphens are left alone.

Ellipses are a book-wide choice too: the glyph, three dots or spaced dots, with or
without a space before. OCR layers merge spaced dots and drop the gap before them,
but hardly ever invent gaps (Dutch books with tight dots: at most 1% of their runs
read spaced), so the runs that kept their gaps are the evidence in the layer. A layer
that drops every gap says nothing, so the gaps are measured on the scan as well: three
dots are short runs of ink near the baseline, and the blanks before and between them,
against the word gaps on the same line, tell a spaced ellipsis from a tight one.
"""

import re
from dataclasses import dataclass, replace

from roboscriptorium.ir import Block, Paragraph

DASHES = "—–"
SPACES = {"none": ("", ""), "thin": (" ", " "), "word": (" ", " ")}


@dataclass(frozen=True)
class DashStyle:
    dash: str  # "–" or "—"
    spacing: str  # "none", "thin" or "word"


def _is_dash(text: str) -> bool:
    return any(c in DASHES for c in text) or text in ("-", "--")


# A dash with whatever spacing the layer gave it, all of it; `_kept` says which stay as read.
_DASH = re.compile(r"\s*(?:[—–]|--)\s*|(?<=\S) +- +(?=\S)")


def _kept(text: str, m: re.Match) -> bool:
    """Whether a dash is part of a number rather than between words: a range, digits on
    both sides however spaced (1914–1918, 1914 – 1918), or a dash glued to a digit (–5)."""
    prev = text[m.start() - 1] if m.start() > 0 else ""
    nxt = text[m.end()] if m.end() < len(text) else ""
    found = m.group()
    glued_left = prev.isdigit() and not found[0].isspace()
    glued_right = nxt.isdigit() and not found[-1].isspace()
    return (prev.isdigit() and nxt.isdigit()) or glued_left or glued_right


def styled(text: str, style: DashStyle) -> tuple[str, list[int]]:
    """The text with every dash between words set in the book's style, and where each of
    the old text's characters went in it.

    Before a closing quote or punctuation, and at a paragraph's start or end, a dash
    takes only the space on its open side.
    """
    before, after = SPACES[style.spacing]
    out, where, pos = [], [], 0
    for m in _DASH.finditer(text):
        if _kept(text, m):
            continue
        for c in text[pos : m.start()]:
            where.append(len("".join(out)))
            out.append(c)
        prev = text[m.start() - 1] if m.start() > 0 else ""
        nxt = text[m.end()] if m.end() < len(text) else ""
        lead = before if prev and prev not in "‘“'\"([" else ""
        trail = after if nxt and nxt not in "’”'\".,;:!?)]…" else ""
        at = len("".join(out)) + len(lead)
        where += [at] * (m.end() - m.start())
        out.append(lead + style.dash + trail)
        pos = m.end()
    for c in text[pos:]:
        where.append(len("".join(out)))
        out.append(c)
    return "".join(out), where


@dataclass(frozen=True)
class EllipsisStyle:
    dots: str  # "…", "..." or ". . ."
    space_before: bool


# Spaced reads are rare noise in a tightly set book, common in a spaced one.
SPACED_FROM = 0.25
# Fewer ellipses than this in the layer leave the book's style unknown.
FEW = 10
# The glyph, or three dots with at most one space between each, with the space before it;
# not part of four dots.
_RUN = re.compile(r"(?<![.…\s])(\s*)(?<![.…] )(…|\.(?: ?\.){2})(?! ?[.…])")
# What opens a quotation or aside: an ellipsis after it takes no space.
_OPENING = "‘“'\"([—–-"


def guess_ellipsis(lines: list[str]) -> EllipsisStyle | None:
    """How the layer's lines set their ellipses, by majority; None when there are too few."""
    runs = []
    for line in lines:
        for m in _RUN.finditer(line):
            if m.start() == 0 or line[m.start() - 1] in _OPENING:
                continue
            runs.append((m.group(2), bool(m.group(1))))
    if len(runs) < FEW:
        return None
    glyphs = [r for r in runs if r[0] == "…"]
    dots = [r for r in runs if r[0] != "…"]
    spaced = [r for r in dots if r[0] == ". . ."]
    if len(glyphs) > len(dots):
        form, votes = "…", glyphs
    elif len(spaced) >= SPACED_FROM * len(dots):
        form, votes = ". . .", spaced
    else:
        form, votes = "...", dots
    return EllipsisStyle(form, 2 * sum(sp for _, sp in votes) > len(votes))


def ellipsised(text: str, style: EllipsisStyle) -> tuple[str, list[int]]:
    """The text with every ellipsis set in the book's style, and where each of the old
    text's characters went in it.

    The space before is set only after a word or closing punctuation, as a no-break
    space (after "?" or "!" as the layer has it), and spaced dots are held together; what
    follows the ellipsis is left as it is.
    Four dots (a full stop and an ellipsis) are left alone.
    """
    dots = style.dots.replace(" ", "\u00a0")
    out, where, pos = [], [], 0
    for m in _RUN.finditer(text):
        for c in text[pos : m.start()]:
            where.append(len("".join(out)))
            out.append(c)
        prev = text[m.start() - 1] if m.start() > 0 else ""
        lead = m.group(1)
        if prev in "?!":
            # After a question or exclamation mark books space it their own way, mostly
            # with a space even where a word's ellipsis has none: as the layer reads it.
            lead = "\u00a0" if lead else ""
        elif prev and prev not in _OPENING:
            lead = "\u00a0" if style.space_before else ""
        at = len("".join(out)) + len(lead)
        where += [at] * (m.end() - m.start())
        out.append(lead + dots)
        pos = m.end()
    for c in text[pos:]:
        where.append(len("".join(out)))
        out.append(c)
    return "".join(out), where


_BLANK = re.compile(r"_+")


def blanked(text: str, blank: str) -> tuple[str, list[int]]:
    """The text with every printed blank, a run of underscores however many the readers
    saw, set as `blank`, and where each of the old text's characters went in it."""
    out, where, pos = [], [], 0
    for m in _BLANK.finditer(text):
        for c in text[pos : m.start()]:
            where.append(len("".join(out)))
            out.append(c)
        where += [len("".join(out))] * (m.end() - m.start())
        out.append(blank)
        pos = m.end()
    for c in text[pos:]:
        where.append(len("".join(out)))
        out.append(c)
    return "".join(out), where


def apply(
    blocks: list[Block],
    dash: DashStyle | None,
    ellipsis: EllipsisStyle | None = None,
    blank: str | None = None,
) -> list[Block]:
    """Copies of the paragraphs with their dashes, ellipses and printed blanks styled;
    italic marks follow their words. Blanks come last, so the ellipsis style leaves a
    blank set as dots as the book declares it."""
    out = []
    for block in blocks:
        if isinstance(block, Paragraph):
            if dash is not None and any(c in block.text for c in "—–-"):
                block = _restyled(block, styled(block.text, dash))
            if ellipsis is not None and ("…" in block.text or "." in block.text):
                block = _restyled(block, ellipsised(block.text, ellipsis))
            if blank is not None and "_" in block.text:
                block = _restyled(block, blanked(block.text, blank))
        out.append(block)
    return out


def _restyled(block: Paragraph, change: tuple[str, list[int]]) -> Paragraph:
    text, where = change
    if text == block.text:
        return block
    new_words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    token = {i: k for k, (a, b) in enumerate(new_words) for i in range(a, b)}
    old_words = [m.span() for m in re.finditer(r"\S+", block.text)]
    parts = {k: (a, b) for k, a, b in block.italic_parts}
    # Where the old italic characters went: a word's whole span, or its italic part.
    moved = {
        where[i]
        for k in block.italic
        for i in range(
            *(
                (old_words[k][0] + parts[k][0], old_words[k][0] + parts[k][1])
                if k in parts
                else old_words[k]
            )
        )
        if where[i] in token
    }
    italic, italic_parts = [], []
    for t in sorted({token[i] for i in moved}):
        a, b = new_words[t]
        # A bare dash or dot isn't an italic word, though it came from one.
        if not any(c.isalnum() for c in text[a:b]):
            continue
        italic.append(t)
        # A word joined to an upright one by an unspaced dash ("Ulysses—een") is italic
        # only in part: from its first italic letter to its last.
        upright = [i for i in range(a, b) if text[i].isalnum() and i not in moved]
        if upright:
            inside = [i for i in range(a, b) if i in moved and text[i].isalnum()]
            italic_parts.append((t, inside[0] - a, inside[-1] + 1 - a))
    return replace(block, text=text, italic=tuple(italic), italic_parts=tuple(italic_parts))
