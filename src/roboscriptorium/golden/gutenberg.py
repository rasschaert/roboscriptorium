"""Derive a golden book's reference text from a Project Gutenberg EPUB.

Gutenberg's transcriptions keep the printed edition's wording and spelling, so
the text is used as it stands. Each `h2` starts a chapter; the manifest names
the first and last chapter by the first line of their heading. Page numbers,
illustrations, captions and transcriber's notes are left out. Consecutive verse
lines become one paragraph.
"""

import hashlib
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from roboscriptorium.golden.reference import append_marked, marked_text, unmarked

XHTML = "{http://www.w3.org/1999/xhtml}"
SKIP_CLASSES = {
    "figcenter",
    "caption",
    "tnote",
    "transnote",
    "pg-boilerplate",
    "x-ebookmaker-pageno",
}
SKIP_TAGS = {f"{XHTML}{t}" for t in ("table", "img", "figure", "head")}


@dataclass
class Section:
    heading: str  # the heading's first line
    full_heading: str
    # Italic parts marked (see `reference.marked_text`).
    paragraphs: list[str] = field(default_factory=list)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _classes(el: ET.Element) -> set[str]:
    return set((el.get("class") or "").split())


def _first_line(h2: ET.Element) -> str:
    parts = [h2.text or ""]
    for child in h2.iter():
        if child is h2:
            continue
        if child.tag == f"{XHTML}br":
            break
        parts.append(child.text or "")
        if child.tail and child in list(h2):
            parts.append(child.tail)
    return _clean("".join(parts))


class _Walker:
    def __init__(self):
        self.sections: list[Section] = []
        self.notes: list[str] = []
        self._verse: list[str] = []

    def _flush_verse(self) -> None:
        if self._verse and self.sections:
            self.sections[-1].paragraphs.append(" ".join(self._verse))
        self._verse = []

    def walk(self, el: ET.Element) -> None:
        classes = _classes(el)
        if classes & {"tnote", "transnote"}:
            self.notes.append(_clean(" ".join(el.itertext())))
            return
        if el.tag in SKIP_TAGS or classes & SKIP_CLASSES:
            return
        if el.tag == f"{XHTML}h2":
            self._flush_verse()
            self.sections.append(Section(_first_line(el), _clean(" ".join(el.itertext()))))
            return
        if "verse" in classes:
            if line := _clean("".join(el.itertext())):
                self._verse.append(line)
            return
        if el.tag == f"{XHTML}p":
            self._flush_verse()
            text = _clean("".join(marked_text(el, _kept)))
            if self.sections and unmarked(text).strip():
                self.sections[-1].paragraphs.append(text)
            return
        for child in el:
            self.walk(child)


def _kept(child: ET.Element) -> bool:
    return not (child.tag in SKIP_TAGS or _classes(child) & SKIP_CLASSES)


def read_epub(epub: Path) -> tuple[list[Section], list[str]]:
    """All h2 sections of the book, in reading order, and the transcriber's notes."""
    walker = _Walker()
    with zipfile.ZipFile(epub) as z:
        names = sorted(
            (n for n in z.namelist() if re.search(r"-h-\d+\.htm\.html$", n)),
            key=lambda n: int(re.search(r"-h-(\d+)\.htm", n).group(1)),
        )
        for name in names:
            walker.walk(ET.fromstring(z.read(name)).find(f"{XHTML}body"))
    walker._flush_verse()
    return walker.sections, walker.notes


def select(sections: list[Section], first: str, last: str) -> list[Section]:
    headings = [s.heading for s in sections]
    for name in (first, last):
        if headings.count(name) != 1:
            raise ValueError(f"heading {name!r} found {headings.count(name)}× in {headings}")
    return sections[headings.index(first) : headings.index(last) + 1]


def download(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_suffix(".part")
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as resp:
            resp.raise_for_status()
            with partial.open("wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        shutil.move(partial, dest)
    return dest


def _chapter_xhtml(section: Section) -> str:
    html = ET.Element("html", xmlns="http://www.w3.org/1999/xhtml")
    body = ET.SubElement(ET.SubElement(html, "body"), "section")
    ET.SubElement(body, "h2").text = section.full_heading
    for text in section.paragraphs:
        append_marked(ET.SubElement(body, "p"), text)
    ET.indent(html)
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(html, encoding="unicode") + "\n"


def write_reference(
    epub: Path, ebook: int, url: str, chapters: tuple[str, str], out: Path
) -> list[Section]:
    sections, notes = read_epub(epub)
    chosen = select(sections, *chapters)
    text_dir = out / "text"
    if text_dir.exists():
        for old in text_dir.glob("chapter-*.xhtml"):
            old.unlink()
    text_dir.mkdir(parents=True, exist_ok=True)
    for i, section in enumerate(chosen, 1):
        (text_dir / f"chapter-{i}.xhtml").write_text(_chapter_xhtml(section))

    digest = hashlib.sha256(epub.read_bytes()).hexdigest()
    note_lines = "\n".join(f"> {n}" for n in notes) or "(none)"
    (out / "PROVENANCE.md").write_text(f"""\
# Provenance

Generated by `roboscriptorium golden derive`; don't edit by hand.

- Source: Project Gutenberg eBook #{ebook}, {url}
- EPUB sha256 at derivation: `{digest}` (Gutenberg rebuilds its EPUBs, so a
  fresh download hashes differently; this text is the pinned artefact)
- Chapters: {chapters[0]!r} to {chapters[1]!r}, {len(chosen)} chapters,
  {sum(len(s.paragraphs) for s in chosen)} paragraphs
- Left out: page numbers, illustrations, captions, transcriber's notes.
  Consecutive verse lines are joined into one paragraph.

## Transcriber's notes

Changes the transcribers made to the printed text, as they state them:

{note_lines}
""")
    return chosen
