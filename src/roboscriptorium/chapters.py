"""Chapter numbers: the book's own run of numbered chapters, read where the layer can't.

Old-style figures read as letters ("Io" for 10, "SE" for 51, "zi" for 23), and a short
line read as a speck is dropped before any reader sees it. Two facts of the book settle
them. A chapter opening looks like the book's other chapter openings, so a short line
set apart atop a sunk page is a heading where most such openings carry one
(`openings`). And numbered chapters run 1, 2, 3 …, so a number read as letters, or a
heading too short to be a title, is the number its neighbours say (`numbered`).
"""

from dataclasses import replace

from roboscriptorium import page as P
from roboscriptorium.ir import Block, Heading, SourceRef
from roboscriptorium.pdf import PageText
from roboscriptorium.roles import LineRole, is_body

# A chapter number is at most this many characters as read ("I2", "17.", "#7").
NUMBER_CHARS = 3
# The book's set-apart sunk openings carry a heading on at least this share of them.
OPENINGS_WITH_HEADING = 2 / 3
# At least this many such openings, so the share is the book's habit.
MIN_OPENINGS = 5
# At least this many headings, and half of them following the one before, make a run.
MIN_NUMBERED = 5
RULE = "book-openings"

# How the layer misreads old-style figures: a 1 as I or l, a 0 as o, a 5 as S, a 2 as Z.
_MISREADS = str.maketrans("IilOoSsZz", "111005522")


def openings(pages: list[PageText], roles: dict[SourceRef, LineRole]) -> dict[SourceRef, LineRole]:
    """`roles` with a short line set apart atop a sunk page made a chapter heading, where
    most of the book's set-apart sunk openings start on one. Returns a new dict."""
    sunk = P.sunk_pages(pages)
    apart = [p for p in pages if p.number in sunk and P.set_apart_opening(p)]
    if len(apart) < MIN_OPENINGS:
        return roles
    headed = [p for p in apart if _role(roles, p) == "chapter_heading"]
    if len(headed) < OPENINGS_WITH_HEADING * len(apart):
        return roles
    out = dict(roles)
    for p in apart:
        ref = SourceRef(p.number, 0)
        role = roles.get(ref)
        if role is None or is_body(role) or role.role == "chapter_heading":
            continue
        if len(p.lines[0].text.strip()) <= NUMBER_CHARS:
            out[ref] = LineRole("chapter_heading", role.confidence, 0.0, RULE)
    return out


def _role(roles: dict[SourceRef, LineRole], page: PageText) -> str:
    role = roles.get(SourceRef(page.number, 0))
    return role.role if role is not None else "body"


def value(text: str) -> int | None:
    """The chapter number `text` reads as, its old-style look-alikes folded, or None."""
    t = text.strip().rstrip(".").translate(_MISREADS)
    return int(t) if 0 < len(t) <= NUMBER_CHARS and t.isascii() and t.isdigit() else None


def numbered(blocks: list[Block]) -> list[Block]:
    """The blocks with each heading of a numbered run set to its number: a look-alike
    folded ("Io" → "10") where it fits the run, and a short heading that doesn't read as
    a number ("SE", "zi") where both its neighbours agree on it. Headings with a title
    of words are left out of the run. Returns a new list."""
    at = [
        i
        for i, b in enumerate(blocks)
        if isinstance(b, Heading) and len(b.text.strip()) <= NUMBER_CHARS
    ]
    read = [value(blocks[i].text) for i in at]
    following = sum(1 for a, b in zip(read, read[1:], strict=False) if a is not None and b == a + 1)
    if len(at) < MIN_NUMBERED or following < len(at) / 2:
        return blocks
    out = list(blocks)
    settled: list[int | None] = []
    for k, i in enumerate(at):
        before = settled[k - 1] if k else None
        after = read[k + 1] if k + 1 < len(read) else None
        if before is not None:
            expected = before + 1
        elif after is not None:
            expected = after - 1
        else:
            expected = None
        number = read[k]
        if expected is not None and number != expected:
            # A reading off the run stands unless both neighbours say otherwise.
            agreed = before is not None and after == expected + 1
            number = expected if agreed or number is None and after is None else number
        settled.append(number)
        if number is not None and str(number) != blocks[i].text:
            out[i] = replace(blocks[i], text=str(number), parts=[str(number)])
    return out
