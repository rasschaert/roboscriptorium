"""What a reader would notice in a built book's structure, found without a model.

A book's own logic says where its structure is off: numbered chapters run 1, 2, 3, a
chapter holds more than a line or two, and a title of words doesn't sit alone among
numbered chapters. Each place that breaks it is a `Finding`, which `build` counts and
names, so a build that looks done but isn't says so (Hoe wij verdwijnen's chapter 23 run
into 22, its dedication split over two sections, 2026-11-01).
"""

import re
from collections import Counter
from dataclasses import dataclass

from roboscriptorium import chapters, pagekinds
from roboscriptorium.ir import Block, Document, Heading, Paragraph, SourceRef

# A section of fewer words than this, not set apart as a motto or dedication, is too
# short for a chapter: a split-off line or a heading that isn't one.
SHORT_SECTION_WORDS = 20

KINDS = {
    "number-out-of-run": "a chapter number that doesn't follow the one before",
    "title-among-numbers": "a heading of words between numbered chapters",
    "short-section": f"a section of fewer than {SHORT_SECTION_WORDS} words",
}


@dataclass(frozen=True)
class Finding:
    kind: str  # a key of `KINDS`
    text: str  # the heading, or the section's first words
    where: SourceRef | None  # its first line on the scan


def findings(doc: Document) -> list[Finding]:
    """The places in `doc` where its structure breaks the book's own logic, in order."""
    return sorted(
        _numbers(doc.blocks) + _sections(doc.blocks),
        key=lambda f: (f.where.page, f.where.line) if f.where else (0, 0),
    )


def summary(found: list[Finding]) -> str:
    """One line: how many of each kind, or that none were found."""
    if not found:
        return "structure: nothing out of place"
    counts = Counter(f.kind for f in found)
    return "structure: " + ", ".join(f"{n} × {KINDS[k]}" for k, n in counts.items())


def _where(block: Block) -> SourceRef | None:
    return block.sources[0] if block.sources else None


def _numbers(blocks: list[Block]) -> list[Finding]:
    headings = [b for b in blocks if isinstance(b, Heading)]
    numbered = [(k, chapters.value(h.text)) for k, h in enumerate(headings)]
    numbered = [(k, v) for k, v in numbered if v is not None]
    pairs = list(zip(numbered, numbered[1:], strict=False))
    following = sum(1 for (_, a), (_, b) in pairs if b == a + 1)
    if len(numbered) < chapters.MIN_NUMBERED or following < len(numbered) / 2:
        return []
    # A part's title between two chapters, and the numbers starting again at 1 after it
    # ("Boek 2" over "1"), are the book's structure, not a slip.
    out = []
    for (i, a), (k, b) in pairs:
        if b == 1:
            continue
        stray = [
            h
            for h in headings[i + 1 : k]
            if chapters.value(h.text) is None
            and not re.match(pagekinds.NAMES["part-title"], h.text.strip(), re.I)
        ]
        out += [Finding("title-among-numbers", h.text, _where(h)) for h in stray]
        # A stray title filling the gap exactly is the missing number, found once; one
        # inside an unbroken run is a line taken for a heading.
        if b not in (a + 1, a + 1 + len(stray)):
            out.append(Finding("number-out-of-run", headings[k].text, _where(headings[k])))
    return out


def _sections(blocks: list[Block]) -> list[Finding]:
    out = []
    section: list[Block] = []
    for b in [*blocks, None]:
        if b is None or isinstance(b, Heading):
            text = [p for p in section if isinstance(p, Paragraph)]
            apart = all(p.epigraph or p.dedication for p in text)
            words = sum(len(p.text.split()) for p in text)
            # A heading straight over another is a part's title over its first chapter.
            if text and not apart and words < SHORT_SECTION_WORDS:
                first = section[0]
                out.append(Finding("short-section", first.text[:60], _where(first)))
            section = [b] if b is not None else []
        else:
            section.append(b)
    return out
