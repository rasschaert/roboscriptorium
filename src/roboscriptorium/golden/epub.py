"""Derive a golden book's reference text from a publisher's EPUB.

For books with no Gutenberg transcription: a retail EPUB of the same printing, or
an omnibus holding the scanned book as one part. The manifest names the content
files to read, in order. Paragraphs are `p`, or `div` holding no `p` or `div`
(some EPUBs set every paragraph as one). Paragraphs of the manifest's blank
classes stand for blank lines (a ".." to keep the line open). Headings are `h1`–`h6`, or paragraphs
whose class starts with one of the manifest's heading prefixes; each heading starts a chapter,
even when no text follows it ("Eerste episode 1945" above "1"). Empty paragraphs
(blank lines) are left out.
"""

import hashlib
import re
import xml.etree.ElementTree as ET
import zipfile
from html.entities import name2codepoint
from pathlib import Path

from roboscriptorium.golden.gutenberg import Section, _chapter_xhtml, _clean
from roboscriptorium.golden.reference import ITALIC_END, ITALIC_START, ITALIC_TAGS, unmarked

XHTML = "{http://www.w3.org/1999/xhtml}"
Classes = frozenset[str]
HEADING_TAGS = {f"{XHTML}h{n}" for n in range(1, 7)}
BLOCK_TAGS = {f"{XHTML}p", f"{XHTML}div"}


_XML_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}


def _parse(raw: bytes) -> ET.Element:
    """Parse XHTML that uses HTML's named entities (`&nbsp;`), which XML doesn't define."""

    def numeric(m: re.Match) -> str:
        name = m.group(1)
        if name in _XML_ENTITIES or name not in name2codepoint:
            return m.group(0)
        return f"&#{name2codepoint[name]};"

    return ET.fromstring(re.sub(r"&(\w+);", numeric, raw.decode("utf-8")))


def _italic(el: ET.Element, inside: bool, italic: Classes, roman: Classes) -> bool:
    """Whether `el` sets its text in italics, inside text that is (or isn't) already."""
    classes = set((el.get("class") or "").split())
    if classes & roman:
        return False
    return inside or el.tag in ITALIC_TAGS or bool(classes & italic)


def _text(
    el: ET.Element, italic: Classes = frozenset(), roman: Classes = frozenset(), inside=False
):
    """An element's text, italics marked, with a space where a `<br/>` breaks the line.

    Italics are `<i>`, `<em>` and the `italic` classes; a `roman` class inside
    italic text sets it upright again.
    """
    if el.tag == f"{XHTML}br":
        yield " "
    if el.text:
        yield el.text
    for child in el:
        now = _italic(child, inside, italic, roman)
        if now != inside:
            yield ITALIC_START if now else ITALIC_END
        yield from _text(child, italic, roman, now)
        if now != inside:
            yield ITALIC_END if now else ITALIC_START
        if child.tail:
            yield child.tail


def _member(z: zipfile.ZipFile, name: str) -> str:
    matches = [n for n in z.namelist() if n == name or n.endswith("/" + name)]
    if len(matches) != 1:
        raise ValueError(f"{name!r} matches {len(matches)} files in the EPUB")
    return matches[0]


def _is_heading(el: ET.Element, prefixes: tuple[str, ...]) -> bool:
    if el.tag in HEADING_TAGS:
        return True
    classes = (el.get("class") or "").split()
    return _is_paragraph(el) and any(c.startswith(prefixes) for c in classes)


def _is_paragraph(el: ET.Element) -> bool:
    if el.tag == f"{XHTML}p":
        return True
    return el.tag == f"{XHTML}div" and not any(
        d.tag in BLOCK_TAGS for d in el.iter() if d is not el
    )


def read(
    epub: Path,
    files: list[str],
    heading_prefixes: tuple[str, ...] = (),
    italic: Classes = frozenset(),
    roman: Classes = frozenset(),
    blank: Classes = frozenset(),
) -> list[Section]:
    sections: list[Section] = []
    with zipfile.ZipFile(epub) as z:
        for name in files:
            body = _parse(z.read(_member(z, name))).find(f"{XHTML}body")
            for el in body.iter():
                if el.tag not in HEADING_TAGS and not _is_paragraph(el):
                    continue
                if blank & set((el.get("class") or "").split()):
                    continue
                inside = _italic(el, False, italic, roman)
                text = "".join(_text(el, italic, roman, inside)).replace("\u00a0", " ")
                if inside:
                    text = ITALIC_START + text + ITALIC_END
                text = _clean(text)
                if not unmarked(text).strip():
                    continue
                if _is_heading(el, heading_prefixes):
                    sections.append(Section(unmarked(text), unmarked(text)))
                elif sections:
                    sections[-1].paragraphs.append(text)
    return sections


def write_reference(
    epub: Path,
    source: str,
    files: list[str],
    heading_prefixes: tuple[str, ...],
    out: Path,
    italic: Classes = frozenset(),
    roman: Classes = frozenset(),
    blank: Classes = frozenset(),
) -> list[Section]:
    sections = read(epub, files, heading_prefixes, italic, roman, blank)
    text_dir = out / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    for old in text_dir.glob("chapter-*.xhtml"):
        old.unlink()
    for i, section in enumerate(sections, 1):
        (text_dir / f"chapter-{i}.xhtml").write_text(_chapter_xhtml(section))

    digest = hashlib.sha256(epub.read_bytes()).hexdigest()
    (out / "PROVENANCE.md").write_text(f"""\
# Provenance

Generated by `roboscriptorium golden derive`; don't edit by hand.

- Source: {source}
- EPUB sha256: `{digest}`
- Files: {", ".join(files)}
- Italic classes: {", ".join(sorted(italic)) or "none"}
- Roman inside italics: {", ".join(sorted(roman)) or "none"}
- Blank-line classes: {", ".join(sorted(blank)) or "none"}
- {len(sections)} chapters, {sum(len(s.paragraphs) for s in sections)} paragraphs
- Left out: blank lines, everything outside the listed files.
""")
    return sections
