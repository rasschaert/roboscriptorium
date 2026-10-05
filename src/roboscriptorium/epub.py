"""Write a Document as an EPUB 3 file."""

import uuid
import zipfile
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from roboscriptorium.ir import Document

CSS = """\
body { margin: 0 5%; }
p { margin: 0; text-indent: 1.5em; text-align: justify; hyphens: auto; }
p.opening { text-indent: 0; }
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


def _opf(doc: Document, has_cover: bool) -> str:
    modified = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cover_items = (
        '    <item id="cover-image" href="cover.jpg" media-type="image/jpeg" '
        'properties="cover-image"/>\n'
        '    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>\n'
        if has_cover
        else ""
    )
    cover_spine = '    <itemref idref="cover"/>\n' if has_cover else ""
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
    <item id="text" href="text.xhtml" media-type="application/xhtml+xml"/>
{cover_items}  </manifest>
  <spine>
{cover_spine}    <itemref idref="text"/>
  </spine>
</package>
"""


def _nav(doc: Document) -> str:
    body = f"""\
<nav epub:type="toc" id="toc"><h1>{escape(doc.title)}</h1>
  <ol><li><a href="text.xhtml">{escape(doc.title)}</a></li></ol>
</nav>
<nav epub:type="landmarks" hidden="hidden">
  <ol><li><a epub:type="bodymatter" href="text.xhtml">{escape(doc.title)}</a></li></ol>
</nav>"""
    return _xhtml(doc.title, doc.language, body)


def _text(doc: Document) -> str:
    paragraphs = "\n".join(
        f'<p class="opening">{escape(p.text)}</p>' if p.opening else f"<p>{escape(p.text)}</p>"
        for p in doc.blocks
    )
    return _xhtml(
        doc.title, doc.language, f'<section epub:type="bodymatter">\n{paragraphs}\n</section>'
    )


def write_epub(doc: Document, out: Path, cover_jpeg: bytes | None = None) -> None:
    with zipfile.ZipFile(out, "w") as z:
        # The mimetype entry must come first and be stored uncompressed.
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        deflate = zipfile.ZIP_DEFLATED
        z.writestr("META-INF/container.xml", CONTAINER, compress_type=deflate)
        z.writestr("OEBPS/content.opf", _opf(doc, cover_jpeg is not None), compress_type=deflate)
        z.writestr("OEBPS/nav.xhtml", _nav(doc), compress_type=deflate)
        z.writestr("OEBPS/style.css", CSS, compress_type=deflate)
        z.writestr("OEBPS/text.xhtml", _text(doc), compress_type=deflate)
        if cover_jpeg is not None:
            z.writestr("OEBPS/cover.jpg", cover_jpeg)
            cover = f'<img class="cover" src="cover.jpg" alt="{escape(doc.title)}"/>'
            z.writestr(
                "OEBPS/cover.xhtml", _xhtml(doc.title, doc.language, cover), compress_type=deflate
            )
