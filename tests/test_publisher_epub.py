import zipfile

from roboscriptorium.golden import epub as publisher_epub

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
