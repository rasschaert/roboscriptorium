import zipfile

from roboscriptorium.golden import gutenberg

PAGE = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>{}</body></html>"""

FRONT = PAGE.format(
    '<div class="pg-boilerplate"><h2>The Project Gutenberg eBook</h2></div>'
    "<h2>CONTENTS</h2><p>Puddleby 1</p>"
)
CHAPTER = PAGE.format(
    "<h2><i>THE FIRST CHAPTER</i><br/><small>PUDDLEBY</small></h2>"
    '<p><span class="x-ebookmaker-pageno" title="[1]"><a id="Page_1"></a></span></p>'
    '<p class="drop-capi">ONCE upon a time<span class="x-ebookmaker-pageno" title="[2]"/>'
    " there was a doctor.</p>"
    '<div class="figcenter"><img src="a.jpg" alt=""/><div class="caption"><p>A town</p></div></div>'
    '<div class="poem"><div class="verse">I sail the sea;</div>'
    '<div class="verse"><span>And back to you.</span></div></div>'
    "<p>The end.</p>"
    '<div class="tnote"><p>Page 7, period added.</p></div>'
)


def test_read_epub_keeps_text_and_drops_apparatus(tmp_path):
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr("OEBPS/x_501-h-0.htm.html", FRONT)
        z.writestr("OEBPS/x_501-h-1.htm.html", CHAPTER)
    sections, notes = gutenberg.read_epub(epub)
    assert [s.heading for s in sections] == ["CONTENTS", "THE FIRST CHAPTER"]
    first = gutenberg.select(sections, "THE FIRST CHAPTER", "THE FIRST CHAPTER")[0]
    assert first.full_heading == "THE FIRST CHAPTER PUDDLEBY"
    assert first.paragraphs == [
        "ONCE upon a time there was a doctor.",
        "I sail the sea; And back to you.",
        "The end.",
    ]
    assert notes == ["Page 7, period added."]
