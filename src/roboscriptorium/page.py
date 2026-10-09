"""What a page's layout says about its lines, without any model.

Shared by the line-role rules (roles.py), the review flags (flags.py) and reflow:
page geometry, the lines at the page's edges, text repeated across pages
(running heads), sunk chapter openings, printed page numbers, heading labels and
numerals, and lines the OCR read from a drawing or a smudge.
"""

import itertools
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
# Lines whose letters and digits differ by at most one edit per this many count as the
# same text when looking for repeats across pages: enough for OCR noise ("MONEV"),
# not for headings that share words ("THE FIFTH CHAPTER", "THE SIXTH CHAPTER").
REPEAT_LETTERS_PER_EDIT = 10
# A page whose text starts this much lower (as a share of page height) than most
# pages' does is sunk: a chapter opening.
SUNK_PAGE_DROP = 0.08
# A line of running text is at least this share of the page's usual line width.
TEXT_LINE_WIDTH = 0.8
# A page's first line stands alone when the next starts more than this many line
# pitches below it.
SET_APART_PITCHES = 1.8
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


# How the OCR layer misreads the digits of a page number ("Il" for "11").
_DIGIT_MISREADS = str.maketrans("IlOo", "1100")


def reads_as_folio(word: str, folio: int | None) -> bool:
    """Whether `word` is the page's printed number. With `folio` unknown, any number is.

    A folio of two digits or more may have one digit misread ("28" on page 23); a
    chapter number rarely has as many digits and all but one in common.
    """
    word = word.strip(".,")
    if folio is None:
        return word.isdigit()
    word = word.translate(_DIGIT_MISREADS)
    if not word.isdigit():
        return False
    printed = str(folio)
    if word == printed:
        return True
    return (
        len(printed) >= 2
        and len(word) == len(printed)
        and sum(a != b for a, b in zip(word, printed, strict=True)) == 1
    )


def without_folio(text: str, folio: int | None) -> str:
    """The line without the page number `folio` at either end ("Animal Language II")."""
    words = text.split()
    while words and reads_as_folio(words[-1], folio):
        words.pop()
    while words and reads_as_folio(words[0], folio):
        words.pop(0)
    return " ".join(words)


def title_key(text: str, folio: int | None = None) -> str:
    """Letters and digits of a line without its page number `folio` at either end.

    Digits stay: "CHAPTER XL1I." is not "CHAPTER XLI.", "CHAPTER 2" not "CHAPTER 3".
    """
    return re.sub(r"[^A-Z0-9]", "", without_folio(text, folio).upper())


def label_number(text: str) -> str:
    """The number after a heading label ("CHAPTER 12", "Hoofdstuk 3"), or ""."""
    words = [w.strip(".,»«*:") for w in text.upper().split()]
    for word, nxt in itertools.pairwise(words):
        if word in NUMBERED_WORDS and nxt.isdigit():
            return nxt
    return ""


def sunk_pages(pages: list[PageText]) -> set[int]:
    """Pages whose first line, or whose running text, starts well below the usual place.

    A chapter label can sit at the usual height above a sunk opening ("EEN").
    """
    sunk: set[int] = set()
    for top in (_first_line_top, _text_top):
        tops = {p.number: t for p in pages if (t := top(p)) is not None}
        if tops:
            usual = statistics.median(tops.values())
            sunk |= {n for n, t in tops.items() if t > usual + SUNK_PAGE_DROP}
    return sunk


def _first_line_top(page: PageText) -> float | None:
    return page.lines[0].y0 / page.height if page.lines else None


def _text_top(page: PageText) -> float | None:
    """Where the first line of near full width starts, as a share of the page height."""
    if not page.lines:
        return None
    full, _ = geometry(page)
    wide = next((ln for ln in page.lines if ln.x1 - ln.x0 >= TEXT_LINE_WIDTH * full), None)
    return wide.y0 / page.height if wide else None


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


def folio(page_number: int, offset: int | None) -> int | None:
    """The number printed on a page, given the book's `page_offset`."""
    return None if offset is None else page_number - offset


class Repeats:
    """How often each page-edge line's text recurs at the edge of other pages.

    A line's letters and digits, without its page number, match within a small edit
    budget, to absorb OCR noise in running heads, but a trailing Roman numeral and a
    heading label's number must match exactly: "CHAPTER II." and "CHAPTER III.",
    "CHAPTER 2" and "CHAPTER 3" are different texts.
    """

    def __init__(self, pages: list[PageText]):
        self._offset = page_offset(pages)
        self._pages: dict[tuple[str, str, str], set[int]] = defaultdict(set)
        for page in pages:
            for i in edge_lines(page):
                key = self._key(page.lines[i].text, page.number)
                if key[0]:
                    self._pages[key].add(page.number)

    def _key(self, text: str, page_number: int) -> tuple[str, str, str]:
        text = without_folio(text, folio(page_number, self._offset))
        return title_key(text), numeral(text), label_number(text)

    def other_pages(self, text: str, page_number: int) -> int:
        key, *numbers = self._key(text, page_number)
        if len(key) < 4:
            return 0
        pages: set[int] = set()
        for (other, *other_numbers), found in self._pages.items():
            if other_numbers == numbers and (
                other == key
                or Levenshtein.distance(key, other) <= max(1, len(key) // REPEAT_LETTERS_PER_EDIT)
            ):
                pages |= found
        return len(pages - {page_number})


def set_apart_opening(page: PageText) -> bool:
    """The page's first line is short and stands alone: nothing below it, or a gap of
    more than a line before the next."""
    if not page.lines:
        return False
    full, _ = geometry(page)
    first = page.lines[0]
    if first.x1 - first.x0 >= TEXT_LINE_WIDTH * full:
        return False
    if len(page.lines) == 1:
        return True
    pitches = [b.y0 - a.y0 for a, b in zip(page.lines[1:], page.lines[2:], strict=False)]
    pitch = statistics.median(pitches) if pitches else first.y1 - first.y0
    return page.lines[1].y0 - first.y0 > SET_APART_PITCHES * pitch
