"""Write a Document as an EPUB 3 file."""

import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from roboscriptorium.ir import Block, Document, Heading

CSS = """\
body { margin: 0 5%; }
p { margin: 0; text-indent: 1.5em; text-align: justify; hyphens: auto; }
p.opening { text-indent: 0; }
h2 { text-align: center; margin: 2em 0 1em; font-weight: normal; }
img.cover { display: block; max-width: 100%; max-height: 100vh; margin: 0 auto; }
"""

CONTAINER = """\
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _xhtml(title: str, lang: str, body: str) -> str:
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" \
lang="{lang}" xml:lang="{lang}">
<head><meta charset="UTF-8"/><title>{escape(title)}</title>\
<link rel="stylesheet" href="style.css"/></head>
<body>
{body}
</body>
</html>
"""


def _book_id(doc: Document) -> str:
    # Stable across rebuilds, so readers treat a rebuild as the same book.
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'roboscriptorium:{doc.author}:{doc.title}')}"


@dataclass
class _Section:
    file: str
    title: str
    blocks: list[Block]


def _sections(doc: Document) -> list[_Section]:
    """Split the document into one file per chapter, starting at each heading."""
    sections: list[_Section] = []
    for block in doc.blocks:
        if isinstance(block, Heading) or not sections:
            title = block.text if isinstance(block, Heading) else doc.title
            sections.append(_Section(f"text-{len(sections) + 1:03}.xhtml", title, []))
        sections[-1].blocks.append(block)
    return sections


def _opf(doc: Document, sections: list[_Section], has_cover: bool) -> str:
    modified = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cover_items = (
        '    <item id="cover-image" href="cover.jpg" media-type="image/jpeg" '
        'properties="cover-image"/>\n'
        '    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>\n'
        if has_cover
        else ""
    )
    cover_spine = '    <itemref idref="cover"/>\n' if has_cover else ""
    text_items = "".join(
        f'    <item id="s{i}" href="{s.file}" media-type="application/xhtml+xml"/>\n'
        for i, s in enumerate(sections)
    )
    text_spine = "".join(f'    <itemref idref="s{i}"/>\n' for i in range(len(sections)))
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" \
xml:lang="{doc.language}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">{_book_id(doc)}</dc:identifier>
    <dc:title>{escape(doc.title)}</dc:title>
    <dc:creator>{escape(doc.author)}</dc:creator>
    <dc:language>{doc.language}</dc:language>
    <meta property="dcterms:modified">{modified}</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="style" href="style.css" media-type="text/css"/>
{text_items}{cover_items}  </manifest>
  <spine>
{cover_spine}{text_spine}  </spine>
</package>
"""


def _nav(doc: Document, sections: list[_Section]) -> str:
    entries = "\n".join(f'    <li><a href="{s.file}">{escape(s.title)}</a></li>' for s in sections)
    first = sections[0].file if sections else ""
    body = f"""\
<nav epub:type="toc" id="toc"><h1>{escape(doc.title)}</h1>
  <ol>
{entries}
  </ol>
</nav>
<nav epub:type="landmarks" hidden="hidden">
  <ol><li><a epub:type="bodymatter" href="{first}">{escape(doc.title)}</a></li></ol>
</nav>"""
    return _xhtml(doc.title, doc.language, body)


def _block(block: Block) -> str:
    if isinstance(block, Heading):
        return f"<h2>{'<br/>'.join(escape(p) for p in block.parts or [block.text])}</h2>"
    if block.opening:
        return f'<p class="opening">{escape(block.text)}</p>'
    return f"<p>{escape(block.text)}</p>"


def _section(doc: Document, section: _Section) -> str:
    body = "\n".join(_block(b) for b in section.blocks)
    return _xhtml(
        section.title, doc.language, f'<section epub:type="bodymatter">\n{body}\n</section>'
    )


def write_epub(doc: Document, out: Path, cover_jpeg: bytes | None = None) -> None:
    sections = _sections(doc)
    with zipfile.ZipFile(out, "w") as z:
        # The mimetype entry must come first and be stored uncompressed.
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        deflate = zipfile.ZIP_DEFLATED
        opf = _opf(doc, sections, cover_jpeg is not None)
        z.writestr("META-INF/container.xml", CONTAINER, compress_type=deflate)
        z.writestr("OEBPS/content.opf", opf, compress_type=deflate)
        z.writestr("OEBPS/nav.xhtml", _nav(doc, sections), compress_type=deflate)
        z.writestr("OEBPS/style.css", CSS, compress_type=deflate)
        for section in sections:
            z.writestr(f"OEBPS/{section.file}", _section(doc, section), compress_type=deflate)
        if cover_jpeg is not None:
            z.writestr("OEBPS/cover.jpg", cover_jpeg)
            cover = f'<img class="cover" src="cover.jpg" alt="{escape(doc.title)}"/>'
            z.writestr(
                "OEBPS/cover.xhtml", _xhtml(doc.title, doc.language, cover), compress_type=deflate
            )
