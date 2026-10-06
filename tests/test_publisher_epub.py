import zipfile

from roboscriptorium.golden import epub as publisher_epub

PAGE = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"><body>{}</body></html>"""


def test_class_headings_merge_and_blank_lines_drop(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr("OEBPS/Text/a.html", PAGE.format('<p class="P_kop">SKIPPED PART</p>'))
        z.writestr(
            "OEBPS/Text/b.html",
            PAGE.format(
                '<p class="P_kop">1 LICHAAMSTAAL</p><p class="P_plat">&nbsp;</p>'
                '<p class="P_kop_2">1 DE THUISKOMST</p>'
                "<p><span>Katrien</span> <span>schond haar aangezicht.</span></p>"
                "<h2>2 DAGBOEK</h2><p>Caf&eacute; &amp; zo.</p>"
            ),
        )
    sections = publisher_epub.read(epub, ["Text/b.html"], ("P_kop",))
    assert [s.full_heading for s in sections] == ["1 LICHAAMSTAAL 1 DE THUISKOMST", "2 DAGBOEK"]
    assert sections[0].paragraphs == ["Katrien schond haar aangezicht."]
    assert sections[1].paragraphs == ["Café & zo."]
