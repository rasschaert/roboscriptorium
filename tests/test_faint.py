import pymupdf

from roboscriptorium import faint
from roboscriptorium.pdf import Line, PageText

WORDS = "the night went on and on " * 3


def _pdf(tmp_path, pages: list[tuple[float, float, bool]]):
    """Pages of (paper grey, ink grey, with text), greys from 0 (black) to 1 (white)."""
    doc = pymupdf.open()
    for paper, ink, text in pages:
        page = doc.new_page(width=400, height=600)
        page.draw_rect(page.rect, color=None, fill=(paper,) * 3)
        if text:
            for i in range(20):
                page.insert_text((60, 80 + 22 * i), WORDS, fontsize=14, color=(ink,) * 3)
    doc.save(tmp_path / "scan.pdf")
    return tmp_path / "scan.pdf"


def _layer(number: int, words: int) -> PageText:
    lines = [
        Line(" ".join(["word"] * 10), 60, 68 + 22 * i, 340, 84 + 22 * i) for i in range(words // 10)
    ]
    return PageText(number, 400, 600, lines)


def test_a_washed_out_page_is_faint_and_a_printed_or_blank_one_is_not(tmp_path):
    pdf = _pdf(tmp_path, [(1.0, 0.0, True), (0.61, 0.58, True), (0.61, 0.58, False)])
    body = [_layer(1, 120), _layer(2, 120), _layer(3, 0)]
    cache = tmp_path / "contrast.json"
    assert faint.pages(pdf, body, cache) == {2}
    # A layer with only a few scraps on a faint page is a blank page's show-through.
    assert faint.pages(pdf, [_layer(2, 20)], cache) == set()
    assert cache.exists()
