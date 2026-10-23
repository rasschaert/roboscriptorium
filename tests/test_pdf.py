import json

import pymupdf

from roboscriptorium import ocrcheck, pdf


def _image_only(tmp_path, lines: list[str]):
    """A PDF whose one page is a picture of printed lines, with no text layer."""
    printed = pymupdf.open()
    page = printed.new_page(width=400, height=200)
    for i, text in enumerate(lines):
        page.insert_text((40, 60 + 24 * i), text, fontsize=14)
    picture = page.get_pixmap(dpi=300)
    doc = pymupdf.open()
    doc.new_page(width=400, height=200).insert_image(pymupdf.Rect(0, 0, 400, 200), pixmap=picture)
    doc.save(tmp_path / "source.pdf")
    return tmp_path / "source.pdf"


def test_an_image_only_pdf_gets_tesseracts_lines_with_boxes(tmp_path):
    source = _image_only(tmp_path, ["The first line of it", "and the second line"])
    assert pdf.read_text_layer(source)[0].lines == []
    lines = pdf.read_text_layer(source, "eng")[0].lines
    assert [ln.text for ln in lines] == ["The first line of it", "and the second line"]
    assert lines[0].y1 <= lines[1].y0 and 30 < lines[0].x0 < 50


def test_an_image_only_page_keeps_its_first_readings_words_for_the_word_measures(tmp_path):
    source = _image_only(tmp_path, ["The first line of it", "and the second line"])
    cache = tmp_path / "textlayer.json"
    page = pdf.cached_text_layer(source, cache, "eng")[0]
    with pymupdf.open(source) as doc:
        assert pdf.page_words(doc[0]) == []  # the PDF itself has none
        words = pdf.page_words(doc[0], page)
    assert [w[4] for w in words] == "The first line of it and the second line".split()
    # Each word's line is the visual line holding it, so a line's words spell it.
    held = pdf.line_words(words, page)
    assert all(pdf.spells(ws, ln.text) for ws, ln in zip(held, page.lines, strict=True))
    # Measures cached on these words aren't mistaken for ones made without them.
    assert pdf.lines_digest(page) != pdf.lines_digest(pdf.replace(page, words=()))
    # The words survive the cache; one written before they were kept is read again.
    assert pdf.cached_text_layer(source, cache)[0].words == page.words
    raw = json.loads(cache.read_text())
    for p in raw["pages"]:
        p.pop("words")
    cache.write_text(json.dumps(raw))
    assert pdf.cached_text_layer(source, cache)[0].words == page.words


def test_an_image_only_pdf_counts_as_a_scan(tmp_path):
    assert ocrcheck.scanned(_image_only(tmp_path, ["The first line of it"]))


def test_a_cache_written_without_a_language_is_read_again_with_one(tmp_path):
    source = _image_only(tmp_path, ["The first line of it"])
    cache = tmp_path / "textlayer.json"
    assert pdf.cached_text_layer(source, cache)[0].lines == []
    assert [ln.text for ln in pdf.cached_text_layer(source, cache, "eng")[0].lines] == [
        "The first line of it"
    ]
    assert json.loads(cache.read_text())["first_reader"] == "eng"
    assert pdf.cached_text_layer(source, cache)[0].lines != []


def test_a_pdf_with_a_text_layer_is_never_read_by_tesseract(tmp_path, monkeypatch):
    doc = pymupdf.open()
    doc.new_page(width=400, height=200).insert_text((40, 60), "Printed text", fontsize=11)
    doc.save(tmp_path / "source.pdf")
    monkeypatch.setattr(pdf.ocr, "tesseract_words", lambda *a: 1 / 0)
    assert [ln.text for ln in pdf.read_text_layer(tmp_path / "source.pdf", "eng")[0].lines] == [
        "Printed text"
    ]


def test_a_tall_fragment_boxed_alone_does_not_merge_two_printed_lines():
    words = [
        pdf.Line("Tall", 40, 100, 60, 122),  # a drop cap or speck reaching into the next line
        pdf.Line("first", 70, 100, 120, 112),
        pdf.Line("line", 125, 101, 160, 112),
        pdf.Line("second", 70, 116, 130, 128),
        pdf.Line("line", 135, 117, 170, 128),
    ]
    assert [ln.text for ln in pdf._visual_lines(words)] == ["Tall first line", "second line"]


def test_ascenders_descenders_and_superscripts_still_join_their_line():
    words = [
        pdf.Line("Then", 40, 100, 70, 112),
        pdf.Line("gypsy", 75, 102, 110, 115),  # descenders
        pdf.Line("1", 112, 99, 116, 107),  # a superscript
        pdf.Line("hold", 120, 99, 150, 112),
        pdf.Line("next", 40, 116, 70, 128),
    ]
    assert [ln.text for ln in pdf._visual_lines(words)] == ["Then gypsy 1 hold", "next"]


def test_a_page_number_beside_a_line_is_a_line_of_its_own():
    words = [
        pdf.Line("16", 6, 30, 15, 40),  # in the margin, at the first line's height
        pdf.Line("Daarna stapte hij op", 34, 29, 278, 42),
        pdf.Line("netjes in de schappen moes-", 34, 44, 250, 55),
        pdf.Line("15", 274, 44, 283, 54),
        pdf.Line("ten worden.", 34, 58, 120, 69),
    ]
    assert [ln.text for ln in pdf._visual_lines(words)] == [
        "16",
        "Daarna stapte hij op",
        "15",
        "netjes in de schappen moes-",
        "ten worden.",
    ]


def test_a_number_inside_the_text_or_close_to_it_stays_in_its_line():
    words = [
        pdf.Line("In", 40, 100, 52, 112),
        pdf.Line("1924", 56, 100, 84, 112),  # a word space away
        pdf.Line("he left", 88, 100, 130, 112),
        pdf.Line("Chapter", 40, 120, 90, 132),
        pdf.Line("3", 94, 120, 100, 132),  # a heading's own number
        pdf.Line("next", 40, 140, 70, 152),
    ]
    assert [ln.text for ln in pdf._visual_lines(words)] == [
        "In 1924 he left",
        "Chapter 3",
        "next",
    ]


def test_a_running_head_keeps_its_page_number():
    words = [
        pdf.Line("THE STORY OF DOCTOR DOLITTLE", 80, 10, 220, 20),
        pdf.Line("23", 270, 10, 280, 20),
        pdf.Line("The Doctor went into the garden and he", 34, 30, 278, 41),
        pdf.Line("sat down under the tree to think it over.", 34, 44, 276, 55),
    ]
    assert [ln.text for ln in pdf._visual_lines(words)][0] == "THE STORY OF DOCTOR DOLITTLE 23"
