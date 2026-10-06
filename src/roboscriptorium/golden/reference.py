"""Read a golden book's reference chapters (Standard Ebooks XHTML)."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

XHTML = "{http://www.w3.org/1999/xhtml}"


@dataclass(frozen=True)
class Chapter:
    heading: str
    paragraphs: list[str]


def _text(el: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


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
        paragraphs = [_text(p) for p in body.iter(f"{XHTML}p") if p not in in_heading]
        title = " ".join(_text(el) for el in heading) if group is not None else None
        chapters.append(
            Chapter(title or (_text(heading) if heading is not None else ""), paragraphs)
        )
    return chapters
