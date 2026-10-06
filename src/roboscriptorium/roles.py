"""Decide what each doubtful line on a page is: body text or a print artefact.

Lines in the middle of the text block, flush with the margin, are body text and
aren't asked about. Lines near the top or bottom of the page, and short centred
lines anywhere, go to a decision model with their position and neighbours.
"""

import hashlib
import json
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

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
# Lines whose letters match at least this closely (0–100) count as the same text
# when looking for repeats across pages.
REPEAT_SIMILARITY = 85
# A chapter heading appears once. The model gives this count little weight, so a
# "heading" whose text recurs on at least this many other pages is a running head.
HEADING_MAX_REPEATS = 5
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


def candidates(page: PageText) -> list[int]:
    n = len(page.lines)
    if n == 0:
        return []
    full, _ = _geometry(page)
    edge = set(range(min(EDGE_LINES_TOP, n))) | set(range(max(0, n - EDGE_LINES_BOTTOM), n))
    centred = {i for i, ln in enumerate(page.lines) if _centred(ln, page, full)}
    return sorted(edge | centred)


def _letters(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())


def _numeral(text: str) -> str:
    """A trailing Roman numeral, as in "CHAPTER XII.", or ""."""
    words = re.sub(r"[^A-Za-z\s]", " ", text).split()
    return words[-1].upper() if words and re.fullmatch(r"[IVXLC]+", words[-1].upper()) else ""


class Repeats:
    """How often each page-edge line's text recurs at the edge of other pages.

    Letters match fuzzily, to absorb OCR noise in running heads, but a trailing Roman
    numeral must match exactly: "CHAPTER II." and "CHAPTER III." are different texts.
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
                other == key or fuzz.ratio(key, other) >= REPEAT_SIMILARITY
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
    for page in pages:
        for i in candidates(page):
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
            roles[SourceRef(page.number, i)] = role
    return roles
