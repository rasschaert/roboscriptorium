"""Places where a paragraph's quote marks don't pair up: a quote the OCR layer lost.

Curly quotes only: an opening ‘ or “ at a word's start, a closing ’ or ” at its
end. A ’ inside a word (zo’n, auto’s) or opening a Dutch article (’s avonds, ’t)
is an apostrophe. A quote left open at a paragraph's end is fine when the next
paragraph opens with the same mark, as a quotation running over paragraphs does.
"""

import re
from dataclasses import dataclass

from roboscriptorium.ir import Paragraph, SourceRef

PAIRS = {"‘": "’", "“": "”"}
_ARTICLE = re.compile(r"’(s|t|n)\b")
_SENTENCE_BEFORE = re.compile(r"[.!?…]\s+$")


@dataclass(frozen=True)
class Place:
    sources: list[SourceRef]  # the paragraph's lines around the place
    why: str  # "no opening", "no closing" or "open at end"
    excerpt: str


def marks(text: str) -> list[tuple[int, str, str]]:
    """The quote marks in `text`: (offset, mark, "open" or "close"), apostrophes left out."""
    out = []
    for i, c in enumerate(text):
        if c not in "‘’“”'":
            continue
        if c == "'":
            # A straight quote among curly ones: its place says which way it faces.
            before = text[i - 1] if i else " "
            c = "‘" if before.isspace() or i == 0 else "’"
        before = text[i - 1] if i else " "
        after = text[i + 1] if i + 1 < len(text) else " "
        if c == "’" and before.isalnum() and after.isalnum():
            continue
        if c in "‘’" and not before.isalnum() and _ARTICLE.match("’" + text[i + 1 :]):
            continue
        opening = before.isspace() or before in "(—–-[" or i == 0
        if c in "‘“" and opening:
            out.append((i, c, "open"))
        elif c in "’”" and not opening:
            out.append((i, c, "close"))
        elif c in "‘“":
            # An opening mark glued to the word before it: the layer lost a space.
            out.append((i, c, "open"))
        else:
            out.append((i, c, "close"))
    return out


def problems(text: str, continued: str = "") -> list[tuple[int, str]]:
    """Offsets in `text` where a quote mark has no partner, and what is missing.

    Quotes nest in the same mark (‘Ik zei ‘arme kerel’ in het Hongaars!’), so an
    opening mark inside an open quote is a lost closing one only where it starts
    a new sentence. `continued` is the next paragraph's first character.
    """
    found = []
    depth = dict.fromkeys(PAIRS, 0)
    for i, c, kind in marks(text):
        if kind == "open":
            if depth[c] and _SENTENCE_BEFORE.search(text, 0, i):
                found.append((i, "no closing"))
            else:
                depth[c] += 1
            continue
        opener = next(o for o, cl in PAIRS.items() if cl == c)
        if depth[opener]:
            depth[opener] -= 1
        elif c == "’" and text[i - 1 : i] in ("s", "z") and not text[i + 1 : i + 2].isalnum():
            # A plural possessive (the animals’ language, Jezus’) needs no partner.
            continue
        else:
            found.append((i, "no opening"))
    if any(depth[c] and continued != c for c in PAIRS):
        found.append((len(text) - 1, "open at end"))
    return sorted(found)


def unbalanced(paragraphs: list[Paragraph]) -> list[Place]:
    """Each place where a paragraph's quotes don't pair up, with the lines it falls on."""
    out = []
    for k, p in enumerate(paragraphs):
        if not any(c in p.text for c in "‘’“”"):
            continue
        following = paragraphs[k + 1].text[:1] if k + 1 < len(paragraphs) else ""
        for offset, why in problems(p.text, following):
            out.append(Place(_around(p, offset, why), why, _excerpt(p.text, offset)))
    return out


def _around(p: Paragraph, offset: int, why: str) -> list[SourceRef]:
    """The lines a place falls on, by its share of the paragraph's text, one either side.

    A missing opening may sit anywhere before its closing mark, back to the paragraph's start.
    """
    n = len(p.sources)
    at = min(n - 1, offset * n // max(1, len(p.text)))
    first = 0 if why == "no opening" and at <= 2 else max(0, at - 1)
    return p.sources[first : min(n, at + 2)]


def _excerpt(text: str, offset: int) -> str:
    return text[max(0, offset - 40) : offset + 40].replace("\n", " ")
