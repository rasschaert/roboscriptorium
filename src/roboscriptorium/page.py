"""What a page's layout says about its lines, without any model.

Shared by the line-role rules (roles.py), the review flags (flags.py) and reflow:
page geometry, the lines at the page's edges, text repeated across pages
(running heads), sunk chapter openings, printed page numbers, heading labels and
numerals, and lines the OCR read from a drawing or a smudge.
"""

import re
import statistics
from collections import Counter, defaultdict

from rapidfuzz.distance import Levenshtein

from roboscriptorium.pdf import Line, PageText

# Lines this close to the top or bottom of the page are at its edge, where page
# furniture (running heads, page numbers) sits.
EDGE_LINES_TOP = 2
EDGE_LINES_BOTTOM = 3
# A line is centred on the page when its midpoint is this close to the page's (as a
# share of page width) and it is shorter than SHORT_LINE of a full line.
CENTRED_TOLERANCE = 0.08
SHORT_LINE = 0.8
# Lines whose letters differ by at most one edit per this many letters count as the
# same text when looking for repeats across pages: enough for OCR noise ("MONEV"),
# not for headings that share words ("THE FIFTH CHAPTER", "THE SIXTH CHAPTER").
REPEAT_LETTERS_PER_EDIT = 10
# A page whose text starts this much lower (as a share of page height) than most
# pages' does is sunk: a chapter opening.
SUNK_PAGE_DROP = 0.08
# A page offset counts only when this many pages, and this share of the numbers
# found at page edges, agree on it.
PAGE_OFFSET_MIN_PAGES = 3
PAGE_OFFSET_MIN_SHARE = 0.25
# Lines where fewer than this share of tokens look like words are garbled.
GARBLED_MAX_WORDLIKE = 0.5
# Words that label a heading, in capitals: "CHAPTER XII.", "DEEL TWEE".
NUMBERED_WORDS = {"CHAPTER", "PART", "BOOK", "HOOFDSTUK", "DEEL", "BOEK"}


def geometry(page: PageText) -> tuple[float, float]:
    """Typical full line width and left margin."""
    full = statistics.median(ln.x1 - ln.x0 for ln in page.lines) or 1.0
    left = statistics.median(ln.x0 for ln in page.lines)
    return full, left


def edge_lines(page: PageText) -> list[int]:
    n = len(page.lines)
    return [*range(min(EDGE_LINES_TOP, n)), *range(max(0, n - EDGE_LINES_BOTTOM), n)]


def centred_on_page(line: Line, page: PageText, full: float) -> bool:
    """A short line near the page's middle: loose, for choosing what to ask a model about."""
    mid = (line.x0 + line.x1) / 2
    return (
        abs(mid - page.width / 2) < CENTRED_TOLERANCE * page.width
        and line.x1 - line.x0 < SHORT_LINE * full
    )


def centred_in_text(page: PageText, i: int, balance: float) -> bool:
    """Equal margins on both sides of the text block, unlike a paragraph's first or last
    line: strict, for flagging. `balance` is the slack as a share of a full line."""
    full, left = geometry(page)
    right = statistics.median(ln.x1 for ln in page.lines)
    line = page.lines[i]
    inset_left, inset_right = line.x0 - left, right - line.x1
    slack = balance * full
    return (
        line.x1 - line.x0 < SHORT_LINE * full
        and inset_left >= slack
        and abs(inset_left - inset_right) < slack
    )


_WORDLIKE = re.compile(
    r"^[\"'(“‘]*(?:[A-Za-zÀ-ÿ][a-zß-ÿ'’-]*|[A-ZÀ-Þ][A-ZÀ-Þ'’-]*)[.,;:!?\"')”’—-]*$"
)
# Dots and dashes on their own (spaced ellipses, dashes) are neither words nor noise.
_NEUTRAL = re.compile(r"^[.…—–-]+$")


def garbled(line: Line) -> bool:
    """Text an OCR layer read from a picture or a smudge: mostly tokens that aren't words."""
    tokens = [t for t in line.text.split() if not _NEUTRAL.match(t)]
    if not tokens:
        return False
    wordlike = sum(1 for t in tokens if _WORDLIKE.match(t))
    return wordlike / len(tokens) < GARBLED_MAX_WORDLIKE


def labelled(line: Line, full: float) -> bool:
    """A short line holding a heading label, wherever it sits ("» CHAPTER XXV.")."""
    words = {w.strip(".,»«*") for w in line.text.split()}
    return line.x1 - line.x0 < SHORT_LINE * full and bool(NUMBERED_WORDS & words)


def letters(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())


def numeral(text: str) -> str:
    """A trailing Roman numeral, as in "CHAPTER XII.", or ""."""
    words = re.sub(r"[^A-Za-z\s]", " ", text).split()
    return words[-1].upper() if words and re.fullmatch(r"[IVXLC]+", words[-1].upper()) else ""


def bare_numeral(text: str) -> str:
    """The Roman numeral a line consists of ("Ill" read for "III"), or ""."""
    t = text.strip().rstrip(".")
    if not re.fullmatch(r"[IVXLC][IVXLCl1]*", t):
        return ""
    return t.replace("l", "I").replace("1", "I") if "l" in t or "1" in t else t


def title_key(text: str) -> str:
    """Letters and digits of a line without a page number at either end ("Animal Language II")."""
    words = text.split()
    while words and re.fullmatch(r"[\dIl]+", words[-1]):
        words.pop()
    while words and re.fullmatch(r"\d+", words[0]):
        words.pop(0)
    # Digits stay: "CHAPTER XL1I." is not "CHAPTER XLI.".
    return re.sub(r"[^A-Z0-9]", "", " ".join(words).upper())


def sunk_pages(pages: list[PageText]) -> set[int]:
    tops = [p.lines[0].y0 / p.height for p in pages if p.lines]
    if not tops:
        return set()
    usual = statistics.median(tops)
    return {
        p.number for p in pages if p.lines and p.lines[0].y0 / p.height > usual + SUNK_PAGE_DROP
    }


def page_number(text: str) -> int | None:
    """A number printed at the start or end of a line, as in "Puddleby 5"."""
    words = text.split()
    for word in (words[0], words[-1]) if words else ():
        if word.isdigit():
            return int(word)
    return None


def page_offset(pages: list[PageText]) -> int | None:
    """The usual difference between a page's place in the file and its printed number."""
    offsets = []
    for page in pages:
        for i in edge_lines(page):
            if (number := page_number(page.lines[i].text)) is not None:
                offsets.append(page.number - number)
    if not offsets:
        return None
    offset, count = Counter(offsets).most_common(1)[0]
    return (
        offset
        if count >= max(PAGE_OFFSET_MIN_PAGES, PAGE_OFFSET_MIN_SHARE * len(offsets))
        else None
    )


def printed_page_number(text: str, page: PageText, offset: int | None) -> bool:
    return offset is not None and page_number(text) == page.number - offset


class Repeats:
    """How often each page-edge line's text recurs at the edge of other pages.

    Letters match within a small edit budget, to absorb OCR noise in running heads,
    but a trailing Roman numeral must match exactly: "CHAPTER II." and "CHAPTER III."
    are different texts.
    """

    def __init__(self, pages: list[PageText]):
        self._pages: dict[tuple[str, str], set[int]] = defaultdict(set)
        for page in pages:
            for i in edge_lines(page):
                text = page.lines[i].text
                if key := letters(text):
                    self._pages[(key, numeral(text))].add(page.number)

    def other_pages(self, text: str, page_number: int) -> int:
        key, num = letters(text), numeral(text)
        if len(key) < 4:
            return 0
        pages: set[int] = set()
        for (other, other_numeral), numbers in self._pages.items():
            if other_numeral == num and (
                other == key
                or Levenshtein.distance(key, other) <= max(1, len(key) // REPEAT_LETTERS_PER_EDIT)
            ):
                pages |= numbers
        return len(pages - {page_number})
