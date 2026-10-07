"""Footnotes the reference keeps apart: the scan's footnote lines, left out of a score.

The pipeline doesn't place footnotes yet, so a scan's footnote lines end up in the
running text. A golden book whose reference has notes (`notes.txt`) is scored
without them: a line is a note's when its words occur in a note, in order, and a
short line right after one on the same page is its last line ("(vert.)").
"""

from dataclasses import replace
from pathlib import Path

from rapidfuzz import fuzz

from roboscriptorium.evaluate import normalise
from roboscriptorium.ir import Document, Paragraph, SourceRef
from roboscriptorium.pdf import PageText

# A line must be this long to be matched on its own, and match a note this closely.
MIN_CHARS = 15
MATCH = 90


def load(path: Path) -> list[str]:
    return [n for n in path.read_text().splitlines() if n.strip()] if path.exists() else []


def note_lines(pages: list[PageText], notes: list[str]) -> set[SourceRef]:
    """The lines of `pages` that print one of the notes."""
    texts = [normalise(n) for n in notes]
    found = set()
    for page in pages:
        previous = False
        for i, line in enumerate(page.lines):
            text = normalise(line.text)
            if len(text) >= MIN_CHARS:
                previous = any(fuzz.partial_ratio(text, n) >= MATCH for n in texts)
            else:
                previous = previous and bool(text)
            if previous:
                found.add(SourceRef(page.number, i))
    return found


def without(doc: Document, lines: set[SourceRef], pages: dict[int, PageText]) -> Document:
    """A copy of `doc` without the words that came from `lines`.

    A paragraph's words are spread over its source lines in proportion to their
    word counts, as `disagreements` does; italic marks follow their words.
    """
    if not lines:
        return doc
    blocks = []
    for block in doc.blocks:
        if not isinstance(block, Paragraph) or not lines & set(block.sources):
            blocks.append(block)
            continue
        words = block.text.split()
        owners = _owners(block, len(words), pages)
        keep = [k for k, ref in enumerate(owners) if ref not in lines]
        if not keep:
            continue
        index = {k: n for n, k in enumerate(keep)}
        blocks.append(
            replace(
                block,
                text=" ".join(words[k] for k in keep),
                sources=[s for s in block.sources if s not in lines],
                italic=tuple(index[k] for k in block.italic if k in index),
            )
        )
    return replace(doc, blocks=blocks)


def _owners(p: Paragraph, n: int, pages: dict[int, PageText]) -> list[SourceRef]:
    counts = [max(1, len(pages[s.page].lines[s.line].text.split())) for s in p.sources]
    scale = sum(counts) / max(1, n)
    bounds, total = [], 0
    for c in counts:
        total += c
        bounds.append(total)
    out, k = [], 0
    for i in range(n):
        while k < len(bounds) - 1 and i * scale >= bounds[k]:
            k += 1
        out.append(p.sources[k])
    return out
