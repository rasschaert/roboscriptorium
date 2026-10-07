"""Read a golden book's reference chapters, and the italic marks they carry.

While a source is read, italic text is wrapped in two control characters
(`ITALIC_START`, `ITALIC_END`); the chapter files hold it as `<i>`.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

XHTML = "{http://www.w3.org/1999/xhtml}"
ITALIC_TAGS = {f"{XHTML}i", f"{XHTML}em"}
ITALIC_START, ITALIC_END = "\x01", "\x02"
_MARKS = str.maketrans("", "", ITALIC_START + ITALIC_END)


@dataclass(frozen=True)
class Chapter:
    heading: str
    paragraphs: list[str]
    # Per paragraph, the indices of its italic words in `paragraph.split()`.
    italic: list[frozenset[int]] = field(default_factory=list)


def _text(el: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def marked_text(el: ET.Element, keep=lambda child: True):
    """An element's text with its italic parts marked, leaving out children `keep` refuses."""
    if el.text:
        yield el.text
    for child in el:
        if keep(child):
            italic = child.tag in ITALIC_TAGS
            yield ITALIC_START if italic else ""
            yield from marked_text(child, keep)
            yield ITALIC_END if italic else ""
        if child.tail:
            yield child.tail


def unmarked(text: str) -> str:
    return text.translate(_MARKS)


def italic_words(marked: str) -> frozenset[int]:
    """Indices of the words of `unmarked(marked).split()` with a letter or digit in italics."""
    out, inside, k = set(), False, 0
    for token in marked.split():
        word = False
        for c in token:
            if c == ITALIC_START:
                inside = True
            elif c == ITALIC_END:
                inside = False
            else:
                word = True
                if inside and c.isalnum():
                    out.add(k)
        k += word
    return frozenset(out)


def append_marked(parent: ET.Element, marked: str) -> None:
    """Set marked text as `parent`'s content, its italic parts as `<i>` children."""
    pieces = re.split(f"([{ITALIC_START}{ITALIC_END}])", marked)
    last, italic = None, False
    for piece in pieces:
        if piece in (ITALIC_START, ITALIC_END):
            italic = piece == ITALIC_START
            if italic:
                last = ET.SubElement(parent, "i")
                last.text = ""
            continue
        if italic:
            last.text += piece
        elif last is None:
            parent.text = (parent.text or "") + piece
        else:
            last.tail = (last.tail or "") + piece


def _number(path: Path) -> int:
    return int(re.search(r"(\d+)", path.stem).group(1))


def load_chapters(text_dir: Path) -> list[Chapter]:
    chapters = []
    for path in sorted(text_dir.glob("chapter-*.xhtml"), key=_number):
        body = ET.parse(path).getroot().find(f"{XHTML}body")
        # A chapter title next to the number sits in an <hgroup> as a <p>.
        group = body.find(f".//{XHTML}hgroup")
        heading = group if group is not None else body.find(f".//{XHTML}h2")
        in_heading = set(heading.iter()) if heading is not None else set()
        marked = ["".join(marked_text(p)) for p in body.iter(f"{XHTML}p") if p not in in_heading]
        paragraphs = [re.sub(r"\s+", " ", unmarked(m)).strip() for m in marked]
        title = " ".join(_text(el) for el in heading) if group is not None else None
        chapters.append(
            Chapter(
                title or (_text(heading) if heading is not None else ""),
                paragraphs,
                [italic_words(m) for m in marked],
            )
        )
    return chapters
