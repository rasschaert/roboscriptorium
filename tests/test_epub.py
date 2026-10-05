import zipfile

from roboscriptorium.epub import write_epub
from roboscriptorium.ir import Document, Heading, Paragraph


def test_epub_structure(tmp_path):
    doc = Document(
        "Titel & co",
        "Auteur",
        "nl",
        [
            Paragraph("Een <zin>.", opening=True),
            Heading("CHAPTER II."),
            Paragraph("Tweede.", opening=True),
        ],
    )
    out = tmp_path / "book.epub"
    write_epub(doc, out, cover_jpeg=b"jpeg")

    with zipfile.ZipFile(out) as z:
        first = z.infolist()[0]
        assert first.filename == "mimetype" and first.compress_type == zipfile.ZIP_STORED
        names = set(z.namelist())
        assert {"OEBPS/content.opf", "OEBPS/nav.xhtml", "OEBPS/cover.jpg"} <= names
        assert '<p class="opening">Een &lt;zin&gt;.</p>' in z.read("OEBPS/text-001.xhtml").decode()
        assert "<h2>CHAPTER II.</h2>" in z.read("OEBPS/text-002.xhtml").decode()
        assert "CHAPTER II." in z.read("OEBPS/nav.xhtml").decode()
        assert "Titel &amp; co" in z.read("OEBPS/content.opf").decode()
