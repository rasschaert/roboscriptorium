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
