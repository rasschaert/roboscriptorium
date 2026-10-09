"""Derive a golden book's reference text from a publisher's EPUB.

For books with no Gutenberg transcription: a retail EPUB of the same printing, or
an omnibus holding the scanned book as one part. The manifest names the content
files to read, in order. Paragraphs are `p`, or `div` holding no `p` or `div`
(some EPUBs set every paragraph as one). Paragraphs of the manifest's blank
classes stand for blank lines (a ".." to keep the line open). Headings are `h1`–`h6`, or paragraphs
whose class starts with one of the manifest's heading prefixes; each heading starts a chapter,
even when no text follows it ("Eerste episode 1945" above "1"), unless it holds no letter
or digit (an ornament, "******"). Empty paragraphs
(blank lines) are left out. Paragraphs of the note classes are footnotes: they go
to a notes file, not the text, and the text's links to them ("railbus[*]") read
as printed ("railbus*"). An EPUB that sets its dashes as spaced hyphen-minus gets
the print's dash instead (`hyphen_dash`); hyphens inside words and numbers stay. A
heading set as an image (a drawn chapter number) gets its text from the image's alt
text through `image_heading`, a regex whose group 1 is the heading as printed.
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


# A note's link back to the text, after its marker: "* – [terug]", "[1.] – [terug]".
_BACK_LINK = re.compile(r"^\[?(\*+|\d+)\.?\]?\s*–\s*\[[^\]]*\]")
_NOTE_LINK = re.compile(r"\[(\*+|\d+)\]")
# Between words, at a paragraph's end ("kwam -", an interruption) or at its start ("- Denk na!").
_SPACED_HYPHEN = re.compile(r"(?<=\S) -(?= |$)|^- (?=\S)")
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


def _image_heading(el: ET.Element, pattern: str) -> str:
    """The heading an image inside `el` stands for: group 1 of `pattern` on its alt text."""
    for img in el.iter(f"{XHTML}img"):
        if m := re.search(pattern, img.get("alt") or ""):
            return m.group(1)
    return ""


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
    notes: Classes = frozenset(),
    found_notes: list[str] | None = None,
    hyphen_dash: str = "",
    image_heading: str = "",
) -> list[Section]:
    """The chapters; with `found_notes`, the note paragraphs' text is added to it."""
    sections: list[Section] = []
    with zipfile.ZipFile(epub) as z:
        for name in files:
            body = _parse(z.read(_member(z, name))).find(f"{XHTML}body")
            for el in body.iter():
                if el.tag not in HEADING_TAGS and not _is_paragraph(el):
                    continue
                classes = set((el.get("class") or "").split())
                if notes & classes and found_notes is not None:
                    note = _clean(unmarked("".join(_text(el))))
                    found_notes.append(_BACK_LINK.sub(r"\1", note))
                if (blank | notes) & classes:
                    continue
                inside = _italic(el, False, italic, roman)
                text = "".join(_text(el, italic, roman, inside)).replace("\u00a0", " ")
                # Italic spans that touch are one ("Hors" + "e" in two spans is "Horse").
                text = text.replace(ITALIC_END + ITALIC_START, "")
                if inside:
                    text = ITALIC_START + text + ITALIC_END
                text = _clean(text)
                if hyphen_dash:
                    text = _SPACED_HYPHEN.sub(lambda m: m.group(0).replace("-", hyphen_dash), text)
                if notes:
                    text = _NOTE_LINK.sub(r"\1", text)
                if not unmarked(text).strip() and image_heading and el.tag in HEADING_TAGS:
                    text = _image_heading(el, image_heading)
                if not unmarked(text).strip():
                    continue
                if _is_heading(el, heading_prefixes):
                    if not any(c.isalnum() for c in unmarked(text)):
                        continue  # an ornament set as a heading ("******")
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
    notes: Classes = frozenset(),
    hyphen_dash: str = "",
    image_heading: str = "",
) -> list[Section]:
    found_notes: list[str] = []
    sections = read(
        epub,
        files,
        heading_prefixes,
        italic,
        roman,
        blank,
        notes,
        found_notes,
        hyphen_dash,
        image_heading,
    )
    text_dir = out / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    if notes:
        (out / "notes.txt").write_text("".join(n + "\n" for n in found_notes))
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
- Spaced hyphens set as: {hyphen_dash or "kept"}
- Image headings: {image_heading or "none"}
- Note classes: {", ".join(sorted(notes)) or "none"} ({len(found_notes)} notes in notes.txt)
- {len(sections)} chapters, {sum(len(s.paragraphs) for s in sections)} paragraphs
- Left out: blank lines, everything outside the listed files.
""")
    return sections
