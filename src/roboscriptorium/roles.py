"""Decide what each doubtful line on a page is: body text or a print artefact.

Lines in the middle of the text block, flush with the margin, are body text and
aren't asked about. Lines near the top or bottom of the page, and short centred
lines anywhere, go to a decision model with their position and neighbours.
"""

import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rapidfuzz.distance import Levenshtein

from roboscriptorium.clients import ollaya
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText

ROLES = {
    "body": "Part of the running text of the book: prose or dialogue, including the short "
    "last line of a paragraph",
    "running_head": "The book or chapter title repeated at the top of most pages, often with "
    "a page number at one end",
    "page_number": "A page number on its own",
    "chapter_heading": "A chapter or part heading such as 'CHAPTER XII.', which appears only "
    "once, where that chapter begins",
    "artifact": "Not part of the book's text: a library or digitisation stamp, a printer's "
    "signature mark at the bottom of a page, or scanning noise",
}
QUESTIONS = {
    "role": ollaya.choice(
        "This is one line of text extracted from a scanned page of a printed book. What is it?",
        ROLES,
    )
}
# Lines whose letters differ by at most one edit per this many letters count as the
# same text when looking for repeats across pages: enough for OCR noise ("MONEV"),
# not for headings that share words ("THE FIFTH CHAPTER", "THE SIXTH CHAPTER").
REPEAT_LETTERS_PER_EDIT = 10
# A chapter heading appears once. The model gives this count little weight, so a
# "heading" whose text recurs on at least this many other pages is a running head.
HEADING_MAX_REPEATS = 3
# A line the model calls something other than body is still kept as body when
# P(body) is at least this; losing text is worse than keeping a stray line.
KEEP_BODY_AT = 0.5
# A page whose text starts this much lower (as a share of page height) than most
# pages' does is sunk: a chapter opening.
SUNK_PAGE_DROP = 0.08
# The first lines of a sunk page are asked about, and a bare Roman numeral among
# them is the chapter heading.
SUNK_HEADING_LINES = 3
# A subtitle under a chapter heading has at least this many letters or digits ("i"
# is a speck, "12" a page number, "1945" a subtitle).
SUBTITLE_MIN_CHARS = 4
# A page offset counts only when this many pages, and this share of the numbers
# found at page edges, agree on it.
PAGE_OFFSET_MIN_PAGES = 3
PAGE_OFFSET_MIN_SHARE = 0.25
# A bare number opening a page is a section number unless it is within this much
# of the page's printed number (allowing for OCR misreading a digit).
PAGE_NUMBER_SLACK = 10
# A "heading" that repeats an earlier heading line of at least this many letters is
# a running head.
RUNNING_TITLE_MIN_LETTERS = 6
# Lines where fewer than this share of tokens look like words are asked about too.
GARBLED_MAX_WORDLIKE = 0.5
# Lines this close to the top or bottom of the page are asked about.
EDGE_LINES_TOP = 2
EDGE_LINES_BOTTOM = 3
# A line is centred when its midpoint is this close to the page's (as a share of
# page width) and it is shorter than CENTRED_MAX_WIDTH of a full line.
CENTRED_TOLERANCE = 0.08
CENTRED_MAX_WIDTH = 0.8


@dataclass(frozen=True)
class LineRole:
    role: str
    confidence: float
    p_body: float


def _geometry(page: PageText) -> tuple[float, float]:
    """Typical full line width and left margin."""
    full = statistics.median(ln.x1 - ln.x0 for ln in page.lines) or 1.0
    left = statistics.median(ln.x0 for ln in page.lines)
    return full, left


def _centred(line: Line, page: PageText, full: float) -> bool:
    mid = (line.x0 + line.x1) / 2
    return (
        abs(mid - page.width / 2) < CENTRED_TOLERANCE * page.width
        and line.x1 - line.x0 < CENTRED_MAX_WIDTH * full
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


# Words that label a heading, in capitals: "CHAPTER XII.", "DEEL TWEE". A line
# holding one always goes to the model; in reflow, a chapter number on its own
# line joins the heading above it only after one, and a line with one starts a
# new heading.
NUMBERED_WORDS = {"CHAPTER", "PART", "BOOK", "HOOFDSTUK", "DEEL", "BOEK"}


def _labelled(line: Line, full: float) -> bool:
    """A short line holding a heading label, wherever it sits ("» CHAPTER XXV.")."""
    words = {w.strip(".,»«*") for w in line.text.split()}
    return line.x1 - line.x0 < CENTRED_MAX_WIDTH * full and bool(NUMBERED_WORDS & words)


def candidates(page: PageText, sunk: bool = False) -> list[int]:
    n = len(page.lines)
    if n == 0:
        return []
    full, _ = _geometry(page)
    top = SUNK_HEADING_LINES if sunk else EDGE_LINES_TOP
    edge = set(range(min(top, n))) | set(range(max(0, n - EDGE_LINES_BOTTOM), n))
    centred = {i for i, ln in enumerate(page.lines) if _centred(ln, page, full)}
    noisy = {i for i, ln in enumerate(page.lines) if garbled(ln)}
    labelled = {i for i, ln in enumerate(page.lines) if _labelled(ln, full)}
    return sorted(edge | centred | noisy | labelled)


def _letters(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())


def _numeral(text: str) -> str:
    """A trailing Roman numeral, as in "CHAPTER XII.", or ""."""
    words = re.sub(r"[^A-Za-z\s]", " ", text).split()
    return words[-1].upper() if words and re.fullmatch(r"[IVXLC]+", words[-1].upper()) else ""


def bare_numeral(text: str) -> str:
    """The Roman numeral a line consists of ("Ill" read for "III"), or ""."""
    t = text.strip().rstrip(".")
    if not re.fullmatch(r"[IVXLC][IVXLCl1]*", t):
        return ""
    return t.replace("l", "I").replace("1", "I") if "l" in t or "1" in t else t


def _sunk_pages(pages: list[PageText]) -> set[int]:
    tops = [p.lines[0].y0 / p.height for p in pages if p.lines]
    if not tops:
        return set()
    usual = statistics.median(tops)
    return {
        p.number for p in pages if p.lines and p.lines[0].y0 / p.height > usual + SUNK_PAGE_DROP
    }


def _page_number(text: str) -> int | None:
    """A number printed at the start or end of a line, as in "Puddleby 5"."""
    words = text.split()
    for word in (words[0], words[-1]) if words else ():
        if word.isdigit():
            return int(word)
    return None


def _page_offset(pages: list[PageText]) -> int | None:
    """The usual difference between a page's place in the file and its printed number."""
    offsets = []
    for page in pages:
        n = len(page.lines)
        for i in (*range(min(EDGE_LINES_TOP, n)), *range(max(0, n - EDGE_LINES_BOTTOM), n)):
            if (number := _page_number(page.lines[i].text)) is not None:
                offsets.append(page.number - number)
    if not offsets:
        return None
    offset, count = Counter(offsets).most_common(1)[0]
    return (
        offset
        if count >= max(PAGE_OFFSET_MIN_PAGES, PAGE_OFFSET_MIN_SHARE * len(offsets))
        else None
    )


def _printed_page_number(text: str, page: PageText, offset: int | None) -> bool:
    return offset is not None and _page_number(text) == page.number - offset


def _section_number(
    page: PageText, i: int, offset: int | None, page_roles: dict[int, "LineRole"]
) -> bool:
    """A bare number opening the page, above body text, that isn't its printed page number."""
    text = page.lines[i].text.strip()
    if i != 0 or not text.isdigit() or not _is_body(page_roles.get(i + 1)):
        return False
    return offset is None or abs(int(text) - (page.number - offset)) > PAGE_NUMBER_SLACK


_OPEN_END = re.compile(r"[a-zà-ÿ,\-\u00ad\u00ac]$")
_LOWER_START = re.compile(r"^[‘’'\"“]*[a-zà-ÿ]{2,}\b")


def _finishes_sentence(page: PageText, i: int, page_roles: dict[int, "LineRole"]) -> bool:
    """A lowercase line under a body line that stops mid-sentence: "kijken." ends it."""
    if i == 0 or not _is_body(page_roles.get(i - 1)) or garbled(page.lines[i]):
        return False
    return bool(
        _OPEN_END.search(page.lines[i - 1].text.rstrip())
        and _LOWER_START.match(page.lines[i].text.strip())
    )


def _is_body(role: "LineRole | None") -> bool:
    return role is None or role.p_body >= KEEP_BODY_AT


def _title_key(text: str) -> str:
    """Letters and digits of a line without a page number at either end ("Animal Language II")."""
    words = text.split()
    while words and re.fullmatch(r"[\dIl]+", words[-1]):
        words.pop()
    while words and re.fullmatch(r"\d+", words[0]):
        words.pop(0)
    # Digits stay: "CHAPTER XL1I." is not "CHAPTER XLI.".
    return re.sub(r"[^A-Z0-9]", "", " ".join(words).upper())


class Repeats:
    """How often each page-edge line's text recurs at the edge of other pages.

    Letters match within a small edit budget, to absorb OCR noise in running heads,
    but a trailing Roman numeral must match exactly: "CHAPTER II." and "CHAPTER III."
    are different texts.
    """

    def __init__(self, pages: list[PageText]):
        self._pages: dict[tuple[str, str], set[int]] = defaultdict(set)
        for page in pages:
            n = len(page.lines)
            for i in (*range(min(EDGE_LINES_TOP, n)), *range(max(0, n - EDGE_LINES_BOTTOM), n)):
                text = page.lines[i].text
                if key := _letters(text):
                    self._pages[(key, _numeral(text))].add(page.number)

    def other_pages(self, text: str, page_number: int) -> int:
        key, numeral = _letters(text), _numeral(text)
        if len(key) < 4:
            return 0
        pages: set[int] = set()
        for (other, other_numeral), numbers in self._pages.items():
            if other_numeral == numeral and (
                other == key
                or Levenshtein.distance(key, other) <= max(1, len(key) // REPEAT_LETTERS_PER_EDIT)
            ):
                pages |= numbers
        return len(pages - {page_number})


def state(page: PageText, i: int, repeats: Repeats) -> dict[str, Any]:
    lines = page.lines
    line = lines[i]
    full, left = _geometry(page)
    if _centred(line, page, full):
        alignment = "centred"
    elif line.x0 - left > 5:
        alignment = "indented"
    else:
        alignment = "flush left"
    return {
        "line": line.text,
        "line_number": f"{i + 1} of {len(lines)}",
        "vertical_position": f"{line.y0 / page.height:.0%} down the page",
        "alignment": alignment,
        "width": f"{(line.x1 - line.x0) / full:.0%} of a full line",
        "similar_text_on_other_pages": repeats.other_pages(line.text, page.number),
        "previous_line": lines[i - 1].text if i else None,
        "next_line": lines[i + 1].text if i + 1 < len(lines) else None,
    }


class DecisionCache:
    """Answers keyed by model, questions and state, kept in a JSON lines file."""

    def __init__(self, path: Path):
        self.path = path
        self._entries: dict[str, dict] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                entry = json.loads(line)
                self._entries[entry["key"]] = entry["answer"]

    @staticmethod
    def key(model: str, questions: dict, state: dict) -> str:
        blob = json.dumps([model, questions, state], sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()

    def get(self, key: str) -> dict | None:
        return self._entries.get(key)

    def put(self, key: str, answer: dict) -> None:
        self._entries[key] = answer
        with self.path.open("a") as f:
            f.write(json.dumps({"key": key, "answer": answer}) + "\n")


def classify(
    pages: list[PageText], client: OllayaClient, cache: DecisionCache
) -> dict[SourceRef, LineRole]:
    roles = {}
    repeats = Repeats(pages)
    sunk = _sunk_pages(pages)
    offset = _page_offset(pages)
    heading_lines: set[str] = set()
    for page in pages:
        page_roles: dict[int, LineRole] = {}
        for i in candidates(page, page.number in sunk):
            st = state(page, i, repeats)
            key = DecisionCache.key(client.model, QUESTIONS, st)
            answer = cache.get(key)
            if answer is None:
                a = client.decide(st, QUESTIONS)["role"]
                answer = {
                    "role": a.value,
                    "confidence": a.confidence,
                    "p_body": a.probabilities["body"],
                }
                cache.put(key, answer)
            role = LineRole(**answer)
            if (
                role.role == "chapter_heading"
                and st["similar_text_on_other_pages"] >= HEADING_MAX_REPEATS
            ):
                role = LineRole("running_head", role.confidence, role.p_body)
            # The model reads a bare "V" as a page number; its place on the page says heading.
            if page.number in sunk and i < SUNK_HEADING_LINES and bare_numeral(page.lines[i].text):
                role = LineRole("chapter_heading", role.confidence, 0.0)
            page_roles[i] = role
        for i, role in page_roles.items():
            text = page.lines[i].text
            if role.role == "chapter_heading":
                key = _title_key(text)
                if _printed_page_number(text, page, offset) or (
                    len(key) >= RUNNING_TITLE_MIN_LETTERS and key in heading_lines
                ):
                    page_roles[i] = LineRole("running_head", role.confidence, role.p_body)
            elif _section_number(page, i, offset, page_roles):
                page_roles[i] = LineRole("chapter_heading", role.confidence, 0.0)
            elif not _is_body(role) and _finishes_sentence(page, i, page_roles):
                page_roles[i] = LineRole("body", role.confidence, 1.0)
        _subtitles(page, page_roles, offset)
        heading_lines |= {
            _title_key(page.lines[i].text)
            for i, r in page_roles.items()
            if r.role == "chapter_heading"
        }
        roles.update({SourceRef(page.number, i): r for i, r in page_roles.items()})
    return roles


def _subtitles(page: PageText, page_roles: dict[int, LineRole], offset: int | None) -> None:
    """Lines between a chapter heading and the text are its title.

    The model calls a title like "PUDDLEBY" under "THE FIRST CHAPTER" a running head
    or an artifact, which would drop it from the book.
    """
    heading = False
    for i in range(len(page.lines)):
        role = page_roles.get(i)
        if _is_body(role):
            return
        if role.role == "chapter_heading":
            heading = True
        elif (
            heading
            and len(re.sub(r"[^A-Za-z0-9]", "", page.lines[i].text)) >= SUBTITLE_MIN_CHARS
            and not _printed_page_number(page.lines[i].text, page, offset)
        ):
            page_roles[i] = LineRole("chapter_heading", role.confidence, 0.0)
