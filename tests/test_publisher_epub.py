import zipfile

from roboscriptorium.golden import epub as publisher_epub
from roboscriptorium.golden.reference import unmarked

PAGE = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"><body>{}</body></html>"""


def test_class_headings_and_blank_lines(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr("OEBPS/Text/a.html", PAGE.format('<p class="P_kop">SKIPPED PART</p>'))
        z.writestr(
            "OEBPS/Text/b.html",
            PAGE.format(
                '<p class="P_kop">1 LICHAAMSTAAL</p><p class="P_plat">&nbsp;</p>'
                '<p class="P_kop_2">1 DE THUISKOMST</p>'
                "<p><span>Katrien</span> <span>schond haar aangezicht.</span></p>"
                "<h2>2<br/>DAGBOEK</h2>"
                '<p>Caf&eacute; &amp; de <span class="sc">nsb</span>-leider.</p>'
            ),
        )
    sections = publisher_epub.read(epub, ["Text/b.html"], ("P_kop",))
    assert [s.full_heading for s in sections] == ["1 LICHAAMSTAAL", "1 DE THUISKOMST", "2 DAGBOEK"]
    assert sections[0].paragraphs == []
    assert sections[1].paragraphs == ["Katrien schond haar aangezicht."]
    assert sections[2].paragraphs == ["Café & de nsb-leider."]


def test_divs_holding_no_blocks_are_paragraphs(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.xhtml",
            PAGE.format(
                '<div class="class80">HOOFDSTUK EEN</div><div class="class84">1</div>'
                '<div class="class86">De eerste <span>die</span> ik sprak.</div>'
                '<div class="wrap"><p>Binnen een omslag.</p></div>'
            ),
        )
    sections = publisher_epub.read(epub, ["Text/a.xhtml"], ("class80", "class84"))
    assert [s.full_heading for s in sections] == ["HOOFDSTUK EEN", "1"]
    assert sections[1].paragraphs == ["De eerste die ik sprak.", "Binnen een omslag."]


def test_italic_classes_and_roman_inside_them(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.xhtml",
            PAGE.format(
                '<p class="kop">I</p>'
                '<p>Het was <span class="cursief">vroeg in</span> de ochtend.</p>'
                '<p class="platcursief">Op <span class="romein">12 september</span>'
                " regende het.</p>"
            ),
        )
    (section,) = publisher_epub.read(
        epub,
        ["Text/a.xhtml"],
        ("kop",),
        frozenset({"cursief", "platcursief"}),
        frozenset({"romein"}),
    )
    (tmp_path / "out").mkdir()
    from roboscriptorium.golden.gutenberg import _chapter_xhtml
    from roboscriptorium.golden.reference import load_chapters

    (tmp_path / "out" / "chapter-1.xhtml").write_text(_chapter_xhtml(section))
    (chapter,) = load_chapters(tmp_path / "out")
    assert chapter.paragraphs == ["Het was vroeg in de ochtend.", "Op 12 september regende het."]
    assert chapter.italic == [frozenset({2, 3}), frozenset({0, 3, 4})]


def test_italic_spans_that_touch_are_one_word(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.xhtml",
            PAGE.format(
                '<p class="kop">I</p><p>Of <span class="txit">The Fan Dancer’s Hors</span>'
                '<span class="txit">e</span>?</p>'
            ),
        )
    (section,) = publisher_epub.read(epub, ["Text/a.xhtml"], ("kop",), frozenset({"txit"}))
    (tmp_path / "out").mkdir()
    from roboscriptorium.golden.gutenberg import _chapter_xhtml
    from roboscriptorium.golden.reference import load_chapters

    (tmp_path / "out" / "chapter-1.xhtml").write_text(_chapter_xhtml(section))
    (chapter,) = load_chapters(tmp_path / "out")
    assert chapter.paragraphs == ["Of The Fan Dancer’s Horse?"]
    assert chapter.italic == [frozenset({1, 2, 3, 4})]


def test_blank_line_classes_are_left_out(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<p class="kop">Hoofdstuk een</p><p class="standaard">Op een berg.</p>'
                '<p class="witregel">..</p><p class="standaard">Zesendertig jaar.</p>'
            ),
        )
    sections = publisher_epub.read(epub, ["Text/a.html"], ("kop",), blank=frozenset({"witregel"}))
    assert sections[0].paragraphs == ["Op een berg.", "Zesendertig jaar."]


def test_spaced_hyphens_become_the_prints_dash(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                "<h1>1</h1><p>Toen - heel terloops - zei hij: wc-rol, 1914-1918.</p>"
                "<p>Hij kwam -</p><p>- Denk na!</p>"
            ),
        )
    (section,) = publisher_epub.read(epub, ["Text/a.html"], hyphen_dash="–")
    assert section.paragraphs == [
        "Toen – heel terloops – zei hij: wc-rol, 1914-1918.",
        "Hij kwam –",
        "– Denk na!",
    ]
    (section,) = publisher_epub.read(epub, ["Text/a.html"])
    assert section.paragraphs == [
        "Toen - heel terloops - zei hij: wc-rol, 1914-1918.",
        "Hij kwam -",
        "- Denk na!",
    ]


def test_doubled_hyphens_become_the_prints_dash(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                "<h1>1</h1><p>Toen -- heel terloops -- zei hij: ex-vrouw.</p><p>Maar --</p>"
            ),
        )
    (section,) = publisher_epub.read(epub, ["Text/a.html"], hyphen_dash="–")
    assert section.paragraphs == ["Toen – heel terloops – zei hij: ex-vrouw.", "Maar –"]


def test_capital_classes_are_set_in_capitals(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<h1>1</h1><p>De <span class="kk">fbi</span> en de <span class="kk">b '
                "<i>&amp;</i> b</span> bleven, de vnr niet.</p>"
            ),
        )
    (section,) = publisher_epub.read(epub, ["Text/a.html"], capitals=frozenset({"kk"}))
    assert unmarked(section.paragraphs[0]) == "De FBI en de B & B bleven, de vnr niet."


def test_an_ornament_set_as_a_heading_is_no_chapter(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format("<h1>23</h1><p>Het eind is goed.</p><h3><b>******</b></h3><p></p>"),
        )
    (section,) = publisher_epub.read(epub, ["Text/a.html"])
    assert (section.full_heading, section.paragraphs) == ("23", ["Het eind is goed."])


def test_a_bracketed_note_marker_and_its_back_link_are_stripped(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<p class="kop">5</p><p>Na de <i>Hotelgevechten</i><a href="#n1">[1]</a> dan.</p>'
                '<p class="noten"><a id="n1">[1.] – [<span>terug</span>]</a> Een van de eerste.</p>'
            ),
        )
    notes: list[str] = []
    (section,) = publisher_epub.read(
        epub, ["Text/a.html"], ("kop",), notes=frozenset({"noten"}), found_notes=notes
    )
    assert [unmarked(p) for p in section.paragraphs] == ["Na de Hotelgevechten1 dan."]
    assert notes == ["1 Een van de eerste."]


def test_notes_numbered_in_asterisks_read_as_the_prints_one_mark(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<p class="kop">5</p><p>De railbus<a href="#n1">[*]</a> en de wasplaat'
                '<a href="#n2">[**]</a>.</p>'
                '<p class="noten"><a id="n2">[**] – [<span>terug</span>]</a> Een plaat.</p>'
            ),
        )
    for mark, text, note in (
        ("", "De railbus* en de wasplaat**.", "** Een plaat."),
        ("*", "De railbus* en de wasplaat*.", "* Een plaat."),
    ):
        notes: list[str] = []
        (section,) = publisher_epub.read(epub, ["Text/a.html"], ("kop",),
                                         notes=frozenset({"noten"}), found_notes=notes,
                                         note_mark=mark)  # fmt: skip
        assert [unmarked(p) for p in section.paragraphs] == [text]
        assert notes == [note]


def test_a_heading_set_as_an_image_reads_its_alt_text(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<h2><img alt="Chapter Header, Chapter 2" src="x.jpg"/></h2><p>Armstrong sucks.</p>'
                '<h2><img alt="ornament" src="y.jpg"/></h2><p>Still chapter 2.</p>'
            ),
        )
    (section,) = publisher_epub.read(
        epub, ["Text/a.html"], image_heading=r"Chapter Header, Chapter (\d+)"
    )
    assert (section.full_heading, section.paragraphs) == (
        "2",
        ["Armstrong sucks.", "Still chapter 2."],
    )
    assert publisher_epub.read(epub, ["Text/a.html"]) == []


def test_break_classes_and_ornaments_are_scene_breaks_that_survive_the_files(tmp_path):
    from roboscriptorium.golden.reference import load_chapters

    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<p class="kop">1</p><p class="witregel"> </p><p>Een.</p><p>Twee.</p>'
                '<p class="witregel"> </p><p>Drie.</p><p class="sec">•  •  •</p>'
                "<p>Vier.</p><p>‘…’</p><p>* * *</p>"
            ),
        )
    sections = publisher_epub.write_reference(
        epub, "test", ["Text/a.html"], ("kop",), tmp_path, breaks=frozenset({"witregel"})
    )
    # No break before a chapter's first paragraph; a line of dots in quotes is text.
    assert sections[0].paragraphs == ["Een.", "Twee.", "Drie.", "Vier.", "‘…’"]
    assert sections[0].breaks == {2, 3}
    (chapter,) = load_chapters(tmp_path / "text")
    assert chapter.paragraphs == ["Een.", "Twee.", "Drie.", "Vier.", "‘…’"]
    assert chapter.breaks == {2, 3}


def test_a_break_class_that_also_sets_text_breaks_only_where_empty(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<p class="kop">1</p><p class="plat">Een.</p><p>Twee.</p>'
                '<p class="plat"> </p><p class="plat">Drie.</p>'
            ),
        )
    (section,) = publisher_epub.read(epub, ["Text/a.html"], ("kop",), breaks=frozenset({"plat"}))
    assert section.paragraphs == ["Een.", "Twee.", "Drie."]
    assert section.breaks == {2}


def test_opening_and_closing_classes_set_a_break_beside_their_paragraph(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<p class="kop">1</p><p class="eerste">Een.</p><p>Twee.</p>'
                '<p class="eerste">Drie.</p><p class="einde">Vier.</p><p>Vijf.</p>'
                '<p class="einde">Zes.</p><p class="kop">2</p><p>Zeven.</p>'
            ),
        )
    s1, s2 = publisher_epub.read(epub, ["Text/a.html"], ("kop",), opening=frozenset({"eerste"}),
                                 closing=frozenset({"einde"}))  # fmt: skip
    # None before a chapter's first paragraph, none carried into the next chapter.
    assert s1.breaks == {2, 4}
    assert s2.breaks == set()


def test_a_drawn_initial_gets_its_letter_and_a_text_without_headings_is_one_chapter(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<p><img src="../Images/letter_D.jpg" alt=""/>e jaarwisseling was stil.</p>'
                "<p>Vijftienduizend gasten.</p>"
                '<p><img src="../Images/kaart.jpg" alt=""/>Een kaart.</p>'
            ),
        )
    (section,) = publisher_epub.read(epub, ["Text/a.html"], (), initial_images=r"letter_(\w)\.",
                                     one_chapter=True)  # fmt: skip
    assert section.heading == ""
    assert section.paragraphs == [
        "De jaarwisseling was stil.",
        "Vijftienduizend gasten.",
        "Een kaart.",
    ]
    # Without the option, text before any heading belongs to no chapter.
    assert publisher_epub.read(epub, ["Text/a.html"], ()) == []


def test_a_blockquote_holding_no_paragraphs_is_a_paragraph(tmp_path):
    # calibre sets a Mobipocket e-book's paragraphs as blockquotes; a quotation that
    # holds paragraphs is read through them, as before.
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr(
            "OEBPS/Text/a.html",
            PAGE.format(
                '<blockquote class="kop"><span>1</span></blockquote>'
                "<blockquote>‘Wat doe jij hier?’</blockquote>"
                "<blockquote><p>Een citaat.</p><p>Nog een.</p></blockquote>"
            ),
        )
    (section,) = publisher_epub.read(epub, ["Text/a.html"], ("kop",))
    assert section.heading == "1"
    assert section.paragraphs == ["‘Wat doe jij hier?’", "Een citaat.", "Nog een."]
