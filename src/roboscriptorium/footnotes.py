"""Footnotes: the notes printed at a page's foot, kept out of the running text.

A note is a block of lines at the foot of a page, below its running text, set in type
smaller than the body's (`NOTE_SIZE`), each note opening on its mark ("*", "†", "3").
The note lines stay body for the OCR check, which reads them like any line; reflow then
leaves them out (`ROLE`), and `collect` makes each note a paragraph of its own from the
checked and answered pages. `link` finds the paragraph that carries the note's mark on
the same page; a note whose mark the layer misread stays unlinked, set after the last
paragraph of its page.
"""

import re
from collections.abc import Callable
from dataclasses import replace

from roboscriptorium.hyphens import join
from roboscriptorium.ir import Block, Note, Paragraph, SourceRef
from roboscriptorium.pdf import PageText
from roboscriptorium.roles import LineRole, is_body
from roboscriptorium.typestyle import Style

# A note's type is at most this size relative to the body's: Reis sets its notes at 0.7,
# its page numbers at 0.8 and its text at 1.0.
NOTE_SIZE = 0.78
# A note's strokes are at most this heavy relative to the body's: small type is light
# (Reis's notes 0.7–0.8), a picture or smudge read as text heavy (Afscheid's 1.6–2.6).
NOTE_WEIGHT = 1.2
# Of a note's words at least this share is in the language's word list.
WORD_SHARE = 0.5
# The role reflow gives note lines, so they leave the running text.
ROLE = LineRole("footnote", 1.0, 0.0, "footnote")
# A note's mark at the start of its first line: stars or daggers, or a number of up to
# three digits, before a space, an underscore the layer reads for one, or a capital.
_MARK = re.compile(r"^\s*([*†‡§]+|\d{1,3})(?:[\s_.)]+|(?=[A-ZÀ-Þ]))")


def _body(role: LineRole | None) -> bool:
    """Whether reflow takes the line for running text."""
    return is_body(role)


def lines(
    pages: list[PageText],
    roles: dict[SourceRef, LineRole],
    styles: dict[SourceRef, Style],
    known: Callable[[str], bool] | None = None,
) -> set[SourceRef]:
    """The lines of `pages` that print footnotes (positions in `pages`).

    On each page, the body lines below its last line in body type, when they are all in
    small type (`NOTE_SIZE`; a line without tall letters, of no measurable size, goes
    with them) and the first opens on a note mark; and there is body type above them.
    A picture or a smudge read as small type isn't a note: their strokes are heavier than
    `NOTE_WEIGHT`, and with `known` (the word list's `Lexicon.knows`) most of a note's
    words must be in it."""
    found = set()
    for page in pages:
        body = [i for i in range(len(page.lines)) if _body(roles.get(SourceRef(page.number, i)))]
        sizes = {i: _size(styles.get(SourceRef(page.number, i))) for i in body}
        weights = {i: _weight(styles.get(SourceRef(page.number, i))) for i in body}
        block = []
        for i in reversed(body):
            if sizes[i] is not None and sizes[i] >= NOTE_SIZE:
                break
            block.insert(0, i)
        if any(w is not None and w > NOTE_WEIGHT for w in (weights[i] for i in block)):
            continue
        # The block opens on a measured small line with a mark, below text in body type.
        while block and (sizes[block[0]] is None or not _MARK.match(page.lines[block[0]].text)):
            block.pop(0)
        if block and len(block) < len(body) and _words(page, block, known):
            found.update(SourceRef(page.number, i) for i in block)
    return found


def _words(page: PageText, block: list[int], known: Callable[[str], bool] | None) -> bool:
    """Whether at least `WORD_SHARE` of the block's words are in the word list."""
    if known is None:
        return True
    words = [w for i in block for w in re.findall(r"[^\W\d_]{2,}", page.lines[i].text)]
    return bool(words) and sum(known(w) or known(w.lower()) for w in words) >= WORD_SHARE * len(
        words
    )


def _size(style: Style | None) -> float | None:
    return style.size if style is not None else None


def _weight(style: Style | None) -> float | None:
    return style.weight if style is not None else None


def collect(pages: list[PageText], note_lines: set[SourceRef]) -> list[Note]:
    """The notes, in page order, from `pages` (a corrected copy: a line's original
    position is `Line.source`, or its index where that is None)."""
    notes: list[Note] = []
    for page in pages:
        for i, line in enumerate(page.lines):
            source = i if line.source is None else line.source
            # A typed line shares its `source` with the line it went before.
            ref = SourceRef(page.number, source, line.typed)
            if ref not in note_lines:
                continue
            mark = _MARK.match(line.text)
            if mark or not notes or notes[-1].paragraph.sources[-1].page != page.number:
                text = line.text[mark.end() :] if mark else line.text
                notes.append(Note(mark.group(1) if mark else "", Paragraph(text.strip(), [ref])))
            else:
                last = notes[-1].paragraph
                last.text = join(last.text, line.text.strip())
                last.sources.append(ref)
    return notes


def _mark_at(text: str, mark: str) -> re.Match | None:
    """The mark set after a word or its punctuation ("berg*.", "berg.*"), not a number
    standing on its own."""
    return re.search(rf"(?<=[^\s\d]){re.escape(mark)}(?![\w*†‡§])", text)


def link(blocks: list[Block], notes: list[Note]) -> list[Block]:
    """Copies of `blocks` whose paragraphs name the notes they carry (`Paragraph.notes`,
    indices into `notes`): the first paragraph with a line on the note's page whose text
    holds the note's mark, each mark used once; else the last paragraph on that page,
    with the note marked unlinked. `notes` are marked linked in place."""
    blocks = [replace(b, notes=list(b.notes)) if isinstance(b, Paragraph) else b for b in blocks]
    on_page: dict[int, list[int]] = {}
    for k, b in enumerate(blocks):
        if isinstance(b, Paragraph):
            for page in {s.page for s in b.sources}:
                on_page.setdefault(page, []).append(k)
    used: dict[int, int] = {}  # block → characters of its text already matched
    for n, note in enumerate(notes):
        page = note.paragraph.sources[0].page
        candidates = on_page.get(page, [])
        for k in candidates:
            text = blocks[k].text
            m = _mark_at(text[used.get(k, 0) :], note.mark) if note.mark else None
            if m:
                used[k] = used.get(k, 0) + m.end()
                blocks[k].notes.append(n)
                note.linked = True
                break
        else:
            if candidates:
                blocks[candidates[-1]].notes.append(n)
    return blocks
