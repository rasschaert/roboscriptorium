"""What a build changed against the book's previous build, for a book with no reference.

A golden book's changes are measured by the bench; a book of the user's has only its
earlier builds, kept dated in `work/<book>/epubs/`. Their headings and paragraphs, as
plain text, are lined up and every difference listed, so a rebuild that changes text in
a book already read says so (`build` prints `summary`, the places go to a file).
"""

import difflib
import html
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

_BLOCK = re.compile(r"<(h2|p)\b[^>]*>(.*?)</\1>", re.S)
_TAG = re.compile(r"<[^>]+>")


def blocks(epub: Path) -> list[tuple[str, str]]:
    """The book's headings ("h") and paragraphs ("p") in reading order, as plain text."""
    with zipfile.ZipFile(epub) as z:
        names = sorted(n for n in z.namelist() if re.search(r"text-\d+\.xhtml$", n))
        out = []
        for name in names:
            for tag, inner in _BLOCK.findall(z.read(name).decode()):
                text = " ".join(html.unescape(_TAG.sub("", inner)).split())
                if text:
                    out.append(("h" if tag == "h2" else "p", text))
    return out


@dataclass
class Changes:
    # Per kind of block ("h", "p"): how many were added, removed and changed.
    added: dict[str, int] = field(default_factory=lambda: {"h": 0, "p": 0})
    removed: dict[str, int] = field(default_factory=lambda: {"h": 0, "p": 0})
    changed: dict[str, int] = field(default_factory=lambda: {"h": 0, "p": 0})
    # Each difference as old and new text ("" where there is none).
    places: list[tuple[str, str, str]] = field(default_factory=list)


def compare(old: list[tuple[str, str]], new: list[tuple[str, str]]) -> Changes:
    """The blocks `new` adds, removes or changes against `old`. A replaced run pairs its
    blocks of the same kind one to one: a changed paragraph, not one removed and one added."""
    out = Changes()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op == "equal":
            continue
        gone, came = old[a0:a1], new[b0:b1]
        for kind in ("h", "p"):
            was = [t for k, t in gone if k == kind]
            now = [t for k, t in came if k == kind]
            for x, y in zip(was, now, strict=False):
                out.changed[kind] += 1
                out.places.append((kind, x, y))
            for x in was[len(now) :]:
                out.removed[kind] += 1
                out.places.append((kind, x, ""))
            for y in now[len(was) :]:
                out.added[kind] += 1
                out.places.append((kind, "", y))
    return out


def summary(changes: Changes) -> str:
    """One line: what changed since the last build, or that nothing did."""
    if not changes.places:
        return "since the last build: no text changed"
    parts = []
    for kind, name in (("h", "headings"), ("p", "paragraphs")):
        counts = [
            f"{n} {verb}"
            for verb, n in (
                ("changed", changes.changed[kind]),
                ("added", changes.added[kind]),
                ("removed", changes.removed[kind]),
            )
            if n
        ]
        if counts:
            parts.append(f"{name} {', '.join(counts)}")
    return "since the last build: " + "; ".join(parts)


def report(changes: Changes) -> str:
    """Every difference, old above new, for a person to check on the scan."""
    out = []
    for kind, was, now in changes.places:
        name = "heading" if kind == "h" else "paragraph"
        out.append(f"== {name}\n- {was or '(none)'}\n+ {now or '(none)'}\n")
    return "\n".join(out)


def against_last(epub: Path, folder: Path) -> tuple[Changes, Path] | None:
    """`epub` against the latest dated build in `folder`, and that build; None without one."""
    kept = sorted(folder.glob(f"{epub.stem}-*.epub"), key=lambda p: p.stat().st_mtime)
    if not kept:
        return None
    return compare(blocks(kept[-1]), blocks(epub)), kept[-1]
