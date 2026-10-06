"""Decide what each doubtful line on a page is: body text or a print artefact.

Lines in the middle of the text block, flush with the margin, are body text and
aren't asked about. Lines near the top or bottom of the page, and short centred
lines anywhere, go to a decision model with their position and neighbours.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboscriptorium.clients import ollaya
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.ir import SourceRef
from roboscriptorium.page import (
    Repeats,
    bare_numeral,
    centred_on_page,
    edge_lines,
    garbled,
    geometry,
    labelled,
    page_offset,
    printed_page_number,
    sunk_pages,
    title_key,
)
from roboscriptorium.pdf import PageText

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
# A chapter heading appears once. The model gives this count little weight, so a
# "heading" whose text recurs on at least this many other pages is a running head.
HEADING_MAX_REPEATS = 3
# A line the model calls something other than body is still kept as body when
# P(body) is at least this; losing text is worse than keeping a stray line.
KEEP_BODY_AT = 0.5
# The first lines of a sunk page are asked about, and a bare Roman numeral among
# them is the chapter heading.
SUNK_HEADING_LINES = 3
# A subtitle under a chapter heading has at least this many letters or digits ("i"
# is a speck, "12" a page number, "1945" a subtitle).
SUBTITLE_MIN_CHARS = 4
# A bare number opening a page is a section number unless it is within this much
# of the page's printed number (allowing for OCR misreading a digit).
PAGE_NUMBER_SLACK = 10
# A "heading" that repeats an earlier heading line of at least this many letters is
# a running head.
RUNNING_TITLE_MIN_LETTERS = 6


@dataclass(frozen=True)
class LineRole:
    role: str
    confidence: float
    p_body: float
    # The rule that set this role instead of the model's answer ("" for the model's own).
    rule: str = ""


def candidates(page: PageText, sunk: bool = False) -> list[int]:
    """The lines worth asking the model about: page edges, centred, garbled and labelled lines."""
    n = len(page.lines)
    if n == 0:
        return []
    full, _ = geometry(page)
    edge = set(edge_lines(page))
    if sunk:
        edge |= set(range(min(SUNK_HEADING_LINES, n)))
    centred = {i for i, ln in enumerate(page.lines) if centred_on_page(ln, page, full)}
    noisy = {i for i, ln in enumerate(page.lines) if garbled(ln)}
    labels = {i for i, ln in enumerate(page.lines) if labelled(ln, full)}
    return sorted(edge | centred | noisy | labels)


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


def state(page: PageText, i: int, repeats: Repeats) -> dict[str, Any]:
    lines = page.lines
    line = lines[i]
    full, left = geometry(page)
    if centred_on_page(line, page, full):
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
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # cut off by an interrupted run
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
    sunk = sunk_pages(pages)
    offset = page_offset(pages)
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
                role = LineRole("running_head", role.confidence, role.p_body, "repeated-heading")
            # The model reads a bare "V" as a page number; its place on the page says heading.
            if page.number in sunk and i < SUNK_HEADING_LINES and bare_numeral(page.lines[i].text):
                role = LineRole("chapter_heading", role.confidence, 0.0, "sunk-numeral")
            page_roles[i] = role
        for i, role in page_roles.items():
            text = page.lines[i].text
            if role.role == "chapter_heading":
                key = title_key(text)
                if printed_page_number(text, page, offset):
                    page_roles[i] = LineRole(
                        "running_head", role.confidence, role.p_body, "printed-page-number"
                    )
                elif len(key) >= RUNNING_TITLE_MIN_LETTERS and key in heading_lines:
                    page_roles[i] = LineRole(
                        "running_head", role.confidence, role.p_body, "repeated-title"
                    )
            elif _section_number(page, i, offset, page_roles):
                page_roles[i] = LineRole("chapter_heading", role.confidence, 0.0, "section-number")
            elif not _is_body(role) and _finishes_sentence(page, i, page_roles):
                page_roles[i] = LineRole("body", role.confidence, 1.0, "finishes-sentence")
        _subtitles(page, page_roles, offset)
        heading_lines |= {
            title_key(page.lines[i].text)
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
            and not printed_page_number(page.lines[i].text, page, offset)
        ):
            page_roles[i] = LineRole("chapter_heading", role.confidence, 0.0, "subtitle")
