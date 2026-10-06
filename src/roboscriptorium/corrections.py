"""A human's answers about flagged regions, applied on the next build.

Each answer says what a region is: running text, a heading, something to drop
(page furniture, scan noise), an image, a decorated initial or a caption;
optionally with the text as printed, and for a region shown on its side the
turn that makes it upright. A caption stays out of the running text; its text
waits for its picture.
Answers live in `work/<book>/review/regions.jsonl`; the latest per region wins.
They are keyed on the region's page and text layer, so an answer stops applying
when the text layer under it changes. Text given for a region the text layer has
no lines for is inserted as a new line where the region sits.

Answers apply to a copy of the pages: the text layer itself stays as it was, for
the review and its keys, and each copied line keeps its text-layer index.
"""

import functools
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from roboscriptorium import reflow
from roboscriptorium.flags import Flag
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole

ACTIONS = {
    "text": "Running text",
    "heading": "Heading",
    "drop": "Not part of the book (page furniture, noise)",
    "image": "An image or decoration",
    "initial": "A decorated initial letter",
    "caption": "A caption (kept with its picture)",
}
_ROLE = {
    "text": LineRole("body", 1.0, 1.0),
    "heading": LineRole("chapter_heading", 1.0, 0.0),
    "drop": LineRole("artifact", 1.0, 0.0),
    "image": LineRole("artifact", 1.0, 0.0),
    "initial": LineRole("artifact", 1.0, 0.0),
    "caption": LineRole("artifact", 1.0, 0.0),
}


@dataclass(frozen=True)
class Correction:
    key: str
    page: int
    first: int
    last: int
    original: str
    action: str
    text: str | None  # the region as printed, when the text layer misreads it
    at: str
    box: tuple[float, float, float, float] | None = None
    turn: int = 0  # degrees clockwise that make the region upright


class Corrections:
    def __init__(self, path: Path):
        self.path = path
        self.by_key: dict[str, Correction] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                raw = json.loads(line)
                if raw.get("box"):
                    raw["box"] = tuple(raw["box"])
                c = Correction(**raw)
                self.by_key[c.key] = c

    def record(self, flag: Flag, action: str, text: str | None, turn: int = 0) -> Correction:
        if action not in ACTIONS:
            raise KeyError(action)
        if turn not in (0, 90, 180, 270):
            raise KeyError(f"turn {turn}")
        c = Correction(
            flag.key,
            flag.page,
            flag.first,
            flag.last,
            flag.text,
            action,
            text if text and text != flag.text else None,
            datetime.now(UTC).isoformat(timespec="seconds"),
            flag.box,
            turn,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
        self.by_key[c.key] = c
        return c


def lines_beside(page: PageText, box: tuple[float, float, float, float]) -> list[int]:
    """The lines a drawn initial stands beside, or else the first line below it."""
    _, y0, x1, y1 = box
    beside = [
        i for i, ln in enumerate(page.lines) if y0 <= (ln.y0 + ln.y1) / 2 <= y1 and ln.x0 >= x1 - 2
    ]
    return beside or [i for i, ln in enumerate(page.lines) if ln.y0 >= y1][:1]


def _set_initial(page: PageText, c: Correction) -> None:
    """Put a drawn initial's letter back in front of the text beside it ("O" + "NCE")."""
    beside = lines_beside(page, c.box)
    if not beside:
        return
    line = page.lines[beside[0]]
    page.lines[beside[0]] = replace(line, text=c.text.strip() + line.text, initial=True)
    # The other lines beside the drawing are indented by it, not new paragraphs.
    for i in beside[1:]:
        page.lines[i] = replace(page.lines[i], starts_paragraph=False)


def _join_lines(text: str) -> str:
    """One paragraph from typed lines, undoing line-end hyphens as reflow does."""
    lines = [" ".join(ln.split()) for ln in text.splitlines() if ln.strip()]
    return functools.reduce(reflow.join, lines) if lines else ""


def _insert(
    page: PageText, index: int, line: Line, role: LineRole, roles: dict[SourceRef, LineRole]
) -> None:
    """Insert a line into a page, shifting the roles of the lines below it."""
    below = sorted(
        (ref for ref in roles if ref.page == page.number and ref.line >= index),
        key=lambda r: -r.line,
    )
    for ref in below:
        roles[SourceRef(ref.page, ref.line + 1)] = roles.pop(ref)
    page.lines.insert(index, line)
    roles[SourceRef(page.number, index)] = role


def apply(
    pages: list[PageText], roles: dict[SourceRef, LineRole], corrections: Corrections
) -> tuple[list[PageText], dict[SourceRef, LineRole], int]:
    """Copies of the pages and roles with the answers applied, and how many applied.

    The copies' roles are keyed on line positions in the copied pages.
    """
    pages = [
        replace(p, lines=[replace(ln, source=i) for i, ln in enumerate(p.lines)]) for p in pages
    ]
    roles = dict(roles)
    by_number = {p.number: p for p in pages}
    applied = 0
    insertions = []
    initials = []
    for c in corrections.by_key.values():
        page = by_number.get(c.page)
        if page is None or c.last >= len(page.lines):
            continue
        if c.action == "initial" and c.box and c.text:
            initials.append((page, c))
        if c.last < c.first:
            if c.text and c.box and c.action in ("text", "heading"):
                insertions.append((page, c))
            if c.text and c.box and c.action in ("text", "heading", "initial", "caption"):
                applied += 1
            continue
        lines = page.lines[c.first : c.last + 1]
        if "\n".join(ln.text for ln in lines) != c.original:
            continue
        for i in range(c.first, c.last + 1):
            roles[SourceRef(c.page, i)] = _ROLE[c.action]
        if c.text is not None and c.action in ("text", "heading"):
            first = page.lines[c.first]
            page.lines[c.first] = Line(
                " ".join(c.text.split()), first.x0, first.y0, first.x1, first.y1
            )
            for i in range(c.first + 1, c.last + 1):
                roles[SourceRef(c.page, i)] = _ROLE["drop"]
        applied += 1
    for page, c in initials:
        _set_initial(page, c)
    # Bottom up, so each insertion leaves the indices above it alone.
    for page, c in sorted(insertions, key=lambda pc: (pc[0].number, -pc[1].first)):
        # A blank line in the human's text separates paragraphs.
        paragraphs = [_join_lines(p) for p in re.split(r"\n\s*\n", c.text) if p.strip()]
        for k, text in reversed(list(enumerate(paragraphs))):
            source = min(c.first, len(page.lines) - 1) if page.lines else None
            _insert(
                page,
                c.first,
                Line(text, *c.box, starts_paragraph=k > 0 or None, source=source),
                _ROLE[c.action],
                roles,
            )
    return pages, roles, applied
