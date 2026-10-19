"""Derive a golden book's reference text from a publisher's EPUB.

For books with no Gutenberg transcription: a retail EPUB of the same printing, or an
omnibus holding the scanned book as one part. The manifest names the content files to
read, in order. Paragraphs are `p`, or a `div` or `blockquote` holding none (some EPUBs
set every paragraph as one; calibre's conversion of a Mobipocket e-book as
`blockquote`). Paragraphs of the manifest's blank classes stand for blank lines (a ".."
to keep the line open). Headings are `h1`–`h6`, or paragraphs whose class starts with
one of the manifest's heading prefixes; each heading starts a chapter, even when no text
follows it ("Eerste episode 1945" above "1"), unless it holds no letter or digit (an
ornament, "******"). Empty paragraphs (blank lines) are left out. Paragraphs of the note
classes are footnotes: they go to a notes file, not the text, and the text's links to
them ("railbus[*]") read as printed ("railbus*"); where the EPUB numbers its notes ("*",
"**", …) and the print sets one mark for each, every link and note reads that mark
(`note_mark`). An element of the break classes holding no letter or digit, or a
paragraph of ornaments alone ("* * *"), is a scene break before the next paragraph; so
is a paragraph of the opening classes (the unindented first one of a scene) before
itself, and one of the closing classes after itself. An EPUB that sets its dashes as a
spaced hyphen-minus, a spaced double one ("--") or a minus sign ("−"), gets the print's
dash instead (`hyphen_dash`); hyphens inside words and numbers, and a number's minus
sign, stay. Text of the capital classes
(small capitals the EPUB writes in lower case, "vnr") is set in capitals, as the print
shows it and a reader reads it. A heading set as an image (a drawn chapter number) gets
its text from the image's alt text through `image_heading`, a regex whose group 1 is the
heading as printed. Text before the first heading belongs to no chapter, unless
`leading_text` makes it an untitled one (an epigraph, or a text without headings). Where
the print sets every quotation in single marks and the EPUB some in double ones, those
become single (`single_quotes`). Text of the hidden classes (set in white, so no reader
sees it) is left out.
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
BLOCK_TAGS = {f"{XHTML}p", f"{XHTML}div", f"{XHTML}blockquote"}


# A note's link back to the text, after its marker: "* – [terug]", "[1.] – [terug]".
_BACK_LINK = re.compile(r"^\[?(\*+|\d+)\.?\]?\s*–\s*\[[^\]]*\]")
_NOTE_LINK = re.compile(r"\[(\*+|\d+)\]")
# A paragraph of ornaments alone ("* * *", "•  •  •") is a scene break, not text.
_ORNAMENT = re.compile(r"^[\s*•·⁂◆◇❖✻✽✦○●#~]+$")
# Between words, at a paragraph's end ("kwam -", an interruption) or at its start ("- Denk na!"),
# single or doubled ("kwam -- en").
_SPACED_HYPHEN = re.compile(r"(?<=\S) --?(?= |$)|^--? (?=\S)")
# A minus sign set as a dash: any but a number's sign.
_MINUS_DASH = re.compile("\u2212(?!\\d)")
_XML_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}


# A space before a stop, comma, closing mark (not an elision's apostrophe) or a hyphen
# joined to the word after it, italic marks between them aside; a space after a dot
# (spaced dots, ". . .") or a dash ("hel -- ,", which `hyphen_dash` reads as spaced) stays.
_MARKUP_SPACE = re.compile(
    r"(?<=\S)(?<![.\-–—])\s+(?=[\x01\x02]*(?:[,;:!?…)]|\.(?!\s?\.)|[’”](?!\w)|-\w))"
)

# Double quote marks as the single ones a print sets instead (`single_quotes`).
_SINGLE = str.maketrans("“”", "‘’")


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


def _capitalise(body: ET.Element, capitals: Classes) -> None:
    """Sets the text inside elements of the `capitals` classes in capitals, in place."""
    for el in body.iter():
        if set((el.get("class") or "").split()) & capitals:
            for inner in el.iter():
                if inner.text:
                    inner.text = inner.text.upper()
                if inner is not el and inner.tail:
                    inner.tail = inner.tail.upper()


def _hide(body: ET.Element, hidden: Classes) -> None:
    """Empties the text inside elements of the `hidden` classes, in place."""
    for el in body.iter():
        if set((el.get("class") or "").split()) & hidden:
            for inner in el.iter():
                inner.text = None
                if inner is not el:
                    inner.tail = None


def _member(z: zipfile.ZipFile, name: str) -> str:
    matches = [n for n in z.namelist() if n == name or n.endswith("/" + name)]
    if len(matches) != 1:
        raise ValueError(f"{name!r} matches {len(matches)} files in the EPUB")
    return matches[0]


def _is_heading(el: ET.Element, prefixes: tuple[str, ...]) -> bool:
    """A heading tag, or a paragraph of a heading class, or one whose whole text sits in
    a span of a heading class (calibre's conversions mark headings only so)."""
    if el.tag in HEADING_TAGS:
        return True
    if not _is_paragraph(el) or not prefixes:
        return False
    if any(c.startswith(prefixes) for c in (el.get("class") or "").split()):
        return True
    text = "".join(el.itertext()).strip()
    return bool(text) and any(
        any(c.startswith(prefixes) for c in (d.get("class") or "").split())
        and "".join(d.itertext()).strip() == text
        for d in el.iter()
        if d is not el
    )


def _initial_letters(body: ET.Element, pattern: str) -> None:
    """Gives each drawn initial its letter, in place: group 1 of `pattern` on the image's
    file name ("letter_D.jpg" is "D"), read before the word it begins."""
    for img in body.iter(f"{XHTML}img"):
        if m := re.search(pattern, (img.get("src") or "").rsplit("/", 1)[-1]):
            img.text = m.group(1)


def _image_heading(el: ET.Element, pattern: str) -> str:
    """The heading an image inside `el` stands for: group 1 of `pattern` on its alt text."""
    for img in el.iter(f"{XHTML}img"):
        if m := re.search(pattern, img.get("alt") or ""):
            return m.group(1)
    return ""


def _is_paragraph(el: ET.Element) -> bool:
    if el.tag == f"{XHTML}p":
        return True
    # A div or blockquote holding no paragraphs is one: some EPUBs set every paragraph so
    # (calibre's conversion of a Mobipocket e-book sets them as blockquotes). One holding
    # a heading wraps the heading ("title-block").
    return el.tag in (f"{XHTML}div", f"{XHTML}blockquote") and not any(
        d.tag in BLOCK_TAGS | HEADING_TAGS for d in el.iter() if d is not el
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
    capitals: Classes = frozenset(),
    note_mark: str = "",
    breaks: Classes = frozenset(),
    opening: Classes = frozenset(),
    closing: Classes = frozenset(),
    initial_images: str = "",
    leading_text: bool = False,
    markup_spaces: bool = False,
    single_quotes: bool = False,
    hidden: Classes = frozenset(),
) -> list[Section]:
    """The chapters; with `found_notes`, the note paragraphs' text is added to it."""

    def mark(m: re.Match) -> str:
        return note_mark or m.group(1)

    sections: list[Section] = []
    with zipfile.ZipFile(epub) as z:
        for name in files:
            body = _parse(z.read(_member(z, name))).find(f"{XHTML}body")
            _hide(body, hidden)
            _capitalise(body, capitals)
            if initial_images:
                _initial_letters(body, initial_images)
            for el in body.iter():
                classes = set((el.get("class") or "").split())
                # Of the break classes, only an element without letters or digits is a
                # break: a class may set an unindented paragraph of text as well.
                if breaks & classes and not any(c.isalnum() for c in "".join(el.itertext())):
                    if sections:
                        sections[-1].scene_break()
                    continue
                if el.tag not in HEADING_TAGS and not _is_paragraph(el):
                    continue
                if notes & classes and found_notes is not None:
                    note = _clean(unmarked("".join(_text(el))))
                    found_notes.append(_BACK_LINK.sub(mark, note))
                if (blank | notes) & classes:
                    continue
                inside = _italic(el, False, italic, roman)
                text = "".join(_text(el, italic, roman, inside)).replace("\u00a0", " ")
                # Italic spans that touch are one ("Hors" + "e" in two spans is "Horse").
                text = text.replace(ITALIC_END + ITALIC_START, "")
                if inside:
                    text = ITALIC_START + text + ITALIC_END
                text = _clean(text)
                if markup_spaces:
                    text = _MARKUP_SPACE.sub("", text)
                if single_quotes:
                    text = text.translate(_SINGLE)
                if hyphen_dash:
                    text = _SPACED_HYPHEN.sub(
                        lambda m: m.group(0).replace("--", "-").replace("-", hyphen_dash), text
                    )
                    text = _MINUS_DASH.sub(hyphen_dash, text)
                if notes:
                    text = _NOTE_LINK.sub(mark, text)
                if not unmarked(text).strip() and image_heading and el.tag in HEADING_TAGS:
                    text = _image_heading(el, image_heading)
                if not unmarked(text).strip():
                    continue
                if _ORNAMENT.match(unmarked(text)):
                    if sections:
                        sections[-1].scene_break()
                    continue
                if _is_heading(el, heading_prefixes):
                    if not any(c.isalnum() for c in unmarked(text)):
                        continue  # a heading of marks alone is no chapter
                    sections.append(Section(unmarked(text), unmarked(text)))
                elif sections or leading_text:
                    if not sections:
                        sections.append(Section("", ""))
                    if opening & classes:
                        sections[-1].scene_break()
                    sections[-1].add(text)
                    if closing & classes:
                        sections[-1].scene_break()
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
    capitals: Classes = frozenset(),
    note_mark: str = "",
    breaks: Classes = frozenset(),
    opening: Classes = frozenset(),
    closing: Classes = frozenset(),
    initial_images: str = "",
    leading_text: bool = False,
    markup_spaces: bool = False,
    single_quotes: bool = False,
    hidden: Classes = frozenset(),
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
        capitals,
        note_mark,
        breaks,
        opening,
        closing,
        initial_images,
        leading_text,
        markup_spaces,
        single_quotes,
        hidden,
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
    scenes = sum(len(s.breaks) for s in sections)
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
- Markup spaces before punctuation: {"dropped" if markup_spaces else "kept"}
- Double quote marks: {"set single, as the print does" if single_quotes else "kept"}
- Capital classes: {", ".join(sorted(capitals)) or "none"}
- Hidden classes, left out: {", ".join(sorted(hidden)) or "none"}
- Image headings: {image_heading or "none"}
- Note classes: {", ".join(sorted(notes)) or "none"} ({len(found_notes)} notes in notes.txt)
- Note marks set as: {note_mark or "numbered, as the EPUB sets them"}
- Scene-break classes: {", ".join(sorted(breaks)) or "none"}; opening a scene:
  {", ".join(sorted(opening)) or "none"}; closing one: {", ".join(sorted(closing)) or "none"}
  ({scenes} breaks, ornaments included)
- {len(sections)} chapters, {sum(len(s.paragraphs) for s in sections)} paragraphs
- Left out: blank lines, everything outside the listed files.
""")
    return sections
