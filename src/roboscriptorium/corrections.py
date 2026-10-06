"""A human's answers about flagged regions, applied on the next build.

Each answer says what a region is: running text, a heading, something to drop
(page furniture, scan noise), or an image; optionally with the text as printed.
Answers live in `work/<book>/review/regions.jsonl`; the latest per region wins.
They are keyed on the region's page and text layer, so an answer stops applying
when the text layer under it changes.
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from roboscriptorium.flags import Flag, region_key
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole

ACTIONS = {
    "text": "Running text",
    "heading": "Heading",
    "drop": "Not part of the book (page furniture, noise)",
    "image": "An image or decoration",
}
_ROLE = {
    "text": LineRole("body", 1.0, 1.0),
    "heading": LineRole("chapter_heading", 1.0, 0.0),
    "drop": LineRole("artifact", 1.0, 0.0),
    "image": LineRole("artifact", 1.0, 0.0),
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


class Corrections:
    def __init__(self, path: Path):
        self.path = path
        self.by_key: dict[str, Correction] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                c = Correction(**json.loads(line))
                self.by_key[c.key] = c

    def record(self, flag: Flag, action: str, text: str | None) -> Correction:
        if action not in ACTIONS:
            raise KeyError(action)
        c = Correction(
            flag.key,
            flag.page,
            flag.first,
            flag.last,
            flag.text,
            action,
            text if text and text != flag.text else None,
            datetime.now(UTC).isoformat(timespec="seconds"),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
        self.by_key[c.key] = c
        return c


def apply(pages: list[PageText], roles: dict[SourceRef, LineRole], corrections: Corrections) -> int:
    """Override roles (and text) where a human answered; returns how many applied."""
    by_number = {p.number: p for p in pages}
    applied = 0
    for c in corrections.by_key.values():
        page = by_number.get(c.page)
        if page is None or c.last >= len(page.lines):
            continue
        lines = page.lines[c.first : c.last + 1]
        if region_key(c.page, "\n".join(ln.text for ln in lines)) != c.key:
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
    return applied
