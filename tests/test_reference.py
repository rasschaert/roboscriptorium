from roboscriptorium.golden.reference import load_chapters

CHAPTER = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><section>
{heading}
<p>Once upon a time.</p>
<p>The end.</p>
</section></body></html>"""


def test_hgroup_title_is_heading_not_paragraph(tmp_path):
    (tmp_path / "chapter-1.xhtml").write_text(
        CHAPTER.format(heading="<hgroup><h2>I</h2><p>Puddleby</p></hgroup>")
    )
    (tmp_path / "chapter-2.xhtml").write_text(CHAPTER.format(heading="<h2>II</h2>"))
    one, two = load_chapters(tmp_path)
    assert one.heading == "I Puddleby"
    assert one.paragraphs == ["Once upon a time.", "The end."]
    assert two.heading == "II"
    assert two.paragraphs == ["Once upon a time.", "The end."]
