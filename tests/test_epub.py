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


def test_a_scene_break_is_set_before_its_paragraph():
    from roboscriptorium.epub import _block
    from roboscriptorium.ir import Paragraph

    html = _block(Paragraph("Een nieuwe scène.", opening=True, break_before=True))
    assert html == '<hr class="break"/>\n<p class="opening">Een nieuwe scène.</p>'


def test_a_linked_note_links_both_ways_and_an_unlinked_one_still_follows_its_paragraph():
    from roboscriptorium.epub import _block
    from roboscriptorium.ir import Note

    notes = [
        Note("*", Paragraph("Een berg bij de stad."), linked=True),
        Note("**", Paragraph("Een trein."), linked=False),
    ]
    html = _block(Paragraph("Op de berg*. Met 2*3 erbij.", notes=[0, 1]), notes)
    assert html == (
        '<p>Op de berg<a class="noteref" epub:type="noteref" href="#note-1" id="noteref-1">*'
        "</a>. Met 2*3 erbij.</p>"
        '\n<aside class="footnote" epub:type="footnote" id="note-1"><p><a href="#noteref-1">*</a>'
        " Een berg bij de stad.</p></aside>"
        '\n<aside class="footnote" epub:type="footnote" id="note-2"><p>** Een trein.</p></aside>'
    )


def test_a_mottos_lines_are_set_apart_as_one_block(tmp_path):
    doc = Document("T", "A", "nl", [
        Paragraph("‘It’s closing time’", epigraph=True),
        Paragraph("(Leonard Cohen)", epigraph=True),
        Paragraph("Ik zou mijn haar.", opening=True),
    ])  # fmt: skip
    out = tmp_path / "book.epub"
    write_epub(doc, out)
    with zipfile.ZipFile(out) as z:
        html = z.read("OEBPS/text-001.xhtml").decode()
    assert (
        '<blockquote class="epigraph" epub:type="epigraph"><p>‘It’s closing time’</p>'
        "<p>(Leonard Cohen)</p></blockquote>\n"
        '<p class="opening">Ik zou mijn haar.</p>'
    ) in html


def test_a_translator_is_named_in_the_translators_role(tmp_path):
    out = tmp_path / "book.epub"
    write_epub(Document("T", "A", "nl", [Paragraph("Een.")], translator="Ria van Hengel"), out)
    with zipfile.ZipFile(out) as z:
        opf = z.read("OEBPS/content.opf").decode()
    assert '<dc:contributor id="translator">Ria van Hengel</dc:contributor>' in opf
    assert 'refines="#translator" property="role" scheme="marc:relators">trl<' in opf
    write_epub(Document("T", "A", "nl", [Paragraph("Een.")]), out)
    with zipfile.ZipFile(out) as z:
        assert "contributor" not in z.read("OEBPS/content.opf").decode()


def test_each_build_is_kept_dated_unless_it_holds_the_same_book(tmp_path):
    from datetime import datetime

    from roboscriptorium.epub import keep_dated

    out, kept = tmp_path / "stella.epub", tmp_path / "epubs"
    write_epub(Document("T", "A", "nl", [Paragraph("Een.")]), out)
    first = keep_dated(out, kept, datetime(2026, 10, 7, 12, 21))
    assert first.name == "stella-2026-10-07.epub"
    # Built again, the same book: only the package's date differs, nothing is kept.
    write_epub(Document("T", "A", "nl", [Paragraph("Een.")]), out)
    assert keep_dated(out, kept, datetime(2026, 10, 7, 15, 0)) is None
    write_epub(Document("T", "A", "nl", [Paragraph("Twee.")]), out)
    assert keep_dated(out, kept, datetime(2026, 10, 7, 15, 5)).name == "stella-2026-10-07-1505.epub"
    write_epub(Document("T", "A", "nl", [Paragraph("Drie.")]), out)
    assert keep_dated(out, kept, datetime(2026, 10, 11, 9, 0)).name == "stella-2026-10-11.epub"
