"""The edition's departures from its print: misprints a human chose to correct.

`work/<book>/errata.toml` lists them, each found by the page it is printed on and
the printed words themselves, never by a position:

    [[erratum]]
    page = 94
    printed = "zo,’ zeI ik"
    reads = "zo,’ zei ik"

`printed` must occur exactly once in the text of the paragraphs that page holds,
as reflowed (lines joined, line-end hyphens undone); quote glyphs, straight or
curly, match either. One that matches nothing or more than once stops the build:
add words around it until it is unique. The exception: one whose `reads` already stands
on the page is met (a reader or judge settled it that way). The review's answers keep
saying what the page prints (the readers are scored on that); an erratum changes only the text.

An edition's slip the book must not copy (a golden book's e-book numbering two chapters
5) is kept as printed instead, and the bench scores it against the print:

    [[erratum]]
    page = 53
    printed = "HOOFDSTUK 6"
    reads = "HOOFDSTUK 5"
    keep = "print"
    chapter = 6

`chapter` (the reference's chapter file) places it where the edition's words occur
more than once.
"""

import tomllib
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from pathlib import Path

from roboscriptorium.files import write_atomic
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import Block, Heading, Paragraph

# Each glyph folded to one character, so positions in the folded text are positions
# in the text.
# A hyphen, an en dash and an em dash are one glyph here too: which of them the OCR check
# kept at a word's start ("-twee" or "–twee") must not decide whether an erratum matches.
FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "„": '"', "–": "-", "—": "-"})


class Unmatched(ValueError):
    """An erratum whose printed words occur on its page not exactly once."""


# What the book keeps of an erratum: the edition's words (its correction, or its slip,
# followed all the same) or the print's (a slip the book must not copy).
EDITION, PRINT = "edition", "print"


@dataclass(frozen=True)
class Erratum:
    page: int
    printed: str
    reads: str
    keep: str = EDITION
    # The reference chapter (its file's number) the edition's words stand in, for
    # placing them there where they occur more than once.
    chapter: int | None = None


def path(root: Path) -> Path:
    return root / "errata.toml"


def load(root: Path) -> list[Erratum]:
    """A book's errata, none when it has no file."""
    file = path(root)
    if not file.exists():
        return []
    with file.open("rb") as f:
        data = tomllib.load(f)
    return [
        Erratum(e["page"], e["printed"], e["reads"], e.get("keep", EDITION), e.get("chapter"))
        for e in data.get("erratum", [])
    ]


def save(root: Path, erratum: Erratum) -> None:
    """Add an erratum to the book's file, in place of one for the same printed words on
    the same page. The file is written whole, from what it holds."""

    def quoted(text: str) -> str:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'

    kept = [e for e in load(root) if (e.page, e.printed) != (erratum.page, erratum.printed)]
    entries = [
        f"[[erratum]]\npage = {e.page}\nprinted = {quoted(e.printed)}\nreads = {quoted(e.reads)}\n"
        + (f"keep = {quoted(e.keep)}\n" if e.keep != EDITION else "")
        + (f"chapter = {e.chapter}\n" if e.chapter is not None else "")
        for e in [*kept, erratum]
    ]
    write_atomic(path(root), "\n".join(entries))


def from_line(page: int, printed: str, reads: str, lines: list[str], at: int) -> Erratum | None:
    """The erratum that turns line `at` of a page as printed into the line as it should
    read: the words that differ, with words of the line around them until they occur
    once on the page (`lines`, its lines), or None if the two lines are the same.

    A word broken across a line end is never taken in: the build finds it joined.
    """
    if printed == reads:
        return None
    head = len(_common(printed, reads))
    tail = len(_common(printed[head:][::-1], reads[head:][::-1]))
    start = printed.rfind(" ", 0, head) + 1
    end = printed.find(" ", len(printed) - tail)
    end = len(printed) if end < 0 else end
    # Whole words only; a broken word at either end of the line is out of reach.
    first = 1 if at and lines[at - 1].rstrip().endswith("-") else 0
    words = printed.split(" ")
    edges = [0]
    for w in words:
        edges.append(edges[-1] + len(w) + 1)
    lo = next(k for k in range(len(words)) if edges[k + 1] > start)
    hi = next(k for k in range(len(words)) if edges[k + 1] - 1 >= end)
    last = len(words) - (2 if printed.rstrip().endswith("-") else 1)
    page_text = " ".join(lines).translate(FOLD)

    def snippet(lo: int, hi: int) -> str:
        return " ".join(words[lo : hi + 1])

    while page_text.count(snippet(lo, hi).translate(FOLD)) > 1:
        if hi < last:
            hi += 1
        elif lo > first:
            lo -= 1
        else:
            break
    found = snippet(lo, hi)
    cut = edges[lo]
    after = len(printed) - (cut + len(found))
    return Erratum(page, found, reads[cut : len(reads) - after])


def from_layer(page: int, layer_line: str, reads: str, lines: list[str], at: int) -> Erratum | None:
    """The erratum that turns a text layer's line into `reads`, a wording that may begin or
    end beyond that line (a question's line takes in the words around its place): only the
    stretch the two share an anchor at both ends of is compared."""
    blocks = [
        b
        for b in SequenceMatcher(None, layer_line, reads, autojunk=False).get_matching_blocks()
        if b.size >= 3
    ]
    if not blocks:
        return None
    first, last = blocks[0], blocks[-1]
    return from_line(
        page,
        layer_line[first.a : last.a + last.size],
        reads[first.b : last.b + last.size],
        lines,
        at,
    )


def occurs_once(erratum: Erratum, lines: list[str]) -> bool:
    """Whether an erratum's printed words occur exactly once in a page's lines."""
    return " ".join(lines).translate(FOLD).count(erratum.printed.translate(FOLD)) == 1


def local(erratum: Erratum) -> bool:
    """Whether the entry changes a few characters, as a misprint does: one whose reading is
    much longer than its printed words carries words from beyond the line it was made on."""
    return abs(len(erratum.reads) - len(erratum.printed)) <= 12


def _common(a: str, b: str) -> str:
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return a[:k]


def apply(
    errata: list[Erratum], blocks: list[Block], pages: set[int], missing_ok: bool = False
) -> list[Block]:
    """Copies of the blocks with each erratum on one of `pages` applied.

    Errata on other pages are left for a build that holds them. Raises Unmatched
    for one whose printed words its page holds not exactly once; with `missing_ok`, one
    its page doesn't hold at all is left out (a golden book's build that misread those
    words: the bench counts them wrong).
    """
    out = list(blocks)
    for e in errata:
        if e.page not in pages or e.keep == PRINT:
            continue
        needle = e.printed.translate(FOLD)
        found = [
            (k, at)
            for k, b in enumerate(out)
            if isinstance(b, (Paragraph, Heading)) and any(s.page == e.page for s in b.sources)
            for at in _occurrences(b.text.translate(FOLD), needle)
        ]
        reads = e.reads.translate(FOLD)
        if not found and _occurrences(_text_of(out, e.page).translate(FOLD), reads):
            continue  # a reader or judge already settled it as the erratum would
        if not found and missing_ok:
            continue
        if len(found) != 1:
            raise Unmatched(
                f"Erratum on page {e.page}: {e.printed!r} occurs {len(found)} times on that "
                "page; it must occur once (add the words around it)."
            )
        k, at = found[0]
        b = out[k]
        b = replace(b, text=b.text[:at] + e.reads + b.text[at + len(e.printed) :])
        if isinstance(b, Heading):
            b = replace(b, parts=_parts(b.parts, needle, e, b.text))
        out[k] = b
    return out


def _parts(parts: list[str], needle: str, e: Erratum, text: str) -> list[str]:
    """A heading's parts (the lines the EPUB sets) with the erratum applied in the one
    holding its printed words; one part of the mended text where none holds them alone."""
    if not parts:
        return parts
    holding = [
        (k, at) for k, p in enumerate(parts) for at in _occurrences(p.translate(FOLD), needle)
    ]
    if len(holding) != 1:
        return [text]
    k, at = holding[0]
    out = list(parts)
    out[k] = out[k][:at] + e.reads + out[k][at + len(e.printed) :]
    return out


def _text_of(blocks: list[Block], page: int) -> str:
    return "\n".join(
        b.text
        for b in blocks
        if isinstance(b, (Paragraph, Heading)) and any(s.page == page for s in b.sources)
    )


def _occurrences(text: str, needle: str) -> list[int]:
    at, found = text.find(needle), []
    while at >= 0:
        found.append(at)
        at = text.find(needle, at + 1)
    return found


def as_printed(reference: list[Chapter], found: list[Erratum]) -> list[Chapter]:
    """The whole reference (before any slice: `chapter` counts from its first) with each
    erratum's edition words set back as printed, in a paragraph or a heading. An erratum
    whose edition words the reference holds other than once, in its `chapter` where it
    names one, is left out."""
    chapters = [replace(c, paragraphs=list(c.paragraphs), italic=list(c.italic)) for c in reference]
    for e in found:
        reads = e.reads.translate(FOLD)
        # Each place: (chapter, paragraph or -1 for the heading, offset).
        at = [
            (c, p, k)
            for c, ch in enumerate(chapters)
            for p, text in [(-1, ch.heading), *enumerate(ch.paragraphs)]
            for k in _occurrences(text.translate(FOLD), reads)
        ]
        if len(at) > 1 and e.chapter is not None:
            at = [a for a in at if a[0] == e.chapter - 1]
        if len(at) != 1:
            continue
        c, p, k = at[0]
        ch = chapters[c]
        if p < 0:
            chapters[c] = replace(
                ch, heading=ch.heading[:k] + e.printed + ch.heading[k + len(reads) :]
            )
            continue
        para = ch.paragraphs[p]
        changed = para[:k] + e.printed + para[k + len(reads) :]
        ch.paragraphs[p] = changed
        if p < len(ch.italic) and (shift := len(changed.split()) - len(para.split())):
            word = len(para[:k].split())
            ch.italic[p] = frozenset(i + shift if i > word else i for i in ch.italic[p])
    return chapters


def printed_only(found: list[Erratum]) -> list[Erratum]:
    """The errata the book keeps as printed: the reference it is scored on reads so too."""
    return [e for e in found if e.keep == PRINT]
