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
add words around it until it is unique. The review's answers keep saying what the
page prints (the readers are scored on that); an erratum changes only the text.
"""

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

from roboscriptorium.files import write_atomic
from roboscriptorium.ir import Block, Heading, Paragraph

# Each glyph folded to one character, so positions in the folded text are positions
# in the text.
_FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "„": '"'})


class Unmatched(ValueError):
    """An erratum whose printed words occur on its page not exactly once."""


@dataclass(frozen=True)
class Erratum:
    page: int
    printed: str
    reads: str


def path(root: Path) -> Path:
    return root / "errata.toml"


def load(root: Path) -> list[Erratum]:
    """A book's errata, none when it has no file."""
    file = path(root)
    if not file.exists():
        return []
    with file.open("rb") as f:
        data = tomllib.load(f)
    return [Erratum(e["page"], e["printed"], e["reads"]) for e in data.get("erratum", [])]


def save(root: Path, erratum: Erratum) -> None:
    """Add an erratum to the book's file, in place of one for the same printed words on
    the same page. The file is written whole, from what it holds."""

    def quoted(text: str) -> str:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'

    kept = [e for e in load(root) if (e.page, e.printed) != (erratum.page, erratum.printed)]
    entries = [
        f"[[erratum]]\npage = {e.page}\nprinted = {quoted(e.printed)}\nreads = {quoted(e.reads)}\n"
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
    page_text = " ".join(lines).translate(_FOLD)

    def snippet(lo: int, hi: int) -> str:
        return " ".join(words[lo : hi + 1])

    while page_text.count(snippet(lo, hi).translate(_FOLD)) > 1:
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


def occurs_once(erratum: Erratum, lines: list[str]) -> bool:
    """Whether an erratum's printed words occur exactly once in a page's lines."""
    return " ".join(lines).translate(_FOLD).count(erratum.printed.translate(_FOLD)) == 1


def _common(a: str, b: str) -> str:
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return a[:k]


def apply(errata: list[Erratum], blocks: list[Block], pages: set[int]) -> list[Block]:
    """Copies of the blocks with each erratum on one of `pages` applied.

    Errata on other pages are left for a build that holds them. Raises Unmatched
    for one whose printed words its page holds not exactly once.
    """
    out = list(blocks)
    for e in errata:
        if e.page not in pages:
            continue
        needle = e.printed.translate(_FOLD)
        found = [
            (k, at)
            for k, b in enumerate(out)
            if isinstance(b, (Paragraph, Heading)) and any(s.page == e.page for s in b.sources)
            for at in _occurrences(b.text.translate(_FOLD), needle)
        ]
        if len(found) != 1:
            raise Unmatched(
                f"Erratum on page {e.page}: {e.printed!r} occurs {len(found)} times on that "
                "page; it must occur once (add the words around it)."
            )
        k, at = found[0]
        b = out[k]
        out[k] = replace(b, text=b.text[:at] + e.reads + b.text[at + len(e.printed) :])
    return out


def _occurrences(text: str, needle: str) -> list[int]:
    at, found = text.find(needle), []
    while at >= 0:
        found.append(at)
        at = text.find(needle, at + 1)
    return found
