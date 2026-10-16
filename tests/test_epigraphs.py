"""Epigraphs: a motto on a page of its own, set apart from the running text."""

from roboscriptorium import epigraphs
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.reflow import reflow
from roboscriptorium.roles import LineRole


def _text_page(number: int) -> PageText:
    lines = [Line(f"Tekst tot de marge, regel {i}", 30, 40 + 14 * i, 300, 50 + 14 * i)
             for i in range(20)]  # fmt: skip
    return PageText(number, 330, 450, lines)


def _short_page(number: int, rows: list[tuple[float, float, str]]) -> PageText:
    lines = [Line(t, x0, 60 + 14 * i, x1, 70 + 14 * i) for i, (x0, x1, t) in enumerate(rows)]
    return PageText(number, 330, 450, lines)


def test_a_chapters_last_lines_or_a_heading_page_are_no_epigraph():
    # A chapter's last page: a few short lines, but at the margin.
    end = _short_page(8, [(30, 200, "en toen ging ze weg."), (42, 120, "‘Dag.’")])
    assert epigraphs.lines([_text_page(7), end, _text_page(9)], {}) == set()
    # A page holding a heading is a part or chapter opening.
    part = _short_page(8, [(150, 220, "Deel een"), (160, 210, "Proloog")])
    roles = {SourceRef(8, 0): LineRole("chapter_heading", 0.9, 0.05)}
    assert epigraphs.lines([_text_page(7), part, _text_page(9)], roles) == set()
    # A full page of text isn't one either.
    assert epigraphs.lines([_text_page(7), _text_page(8)], {}) == set()


def test_a_few_short_lines_set_in_from_the_margin_are_an_epigraph():
    motto = _short_page(
        7, [(104, 172, "‘It’s closing time’"), (80, 195, "(Leonard Cohen, The Future)")]
    )
    roles = {SourceRef(7, 1): LineRole("artifact", 0.33, 0.24)}
    pages = [motto, _text_page(8), _text_page(9)]
    found = epigraphs.lines(pages, roles)
    assert found == {SourceRef(7, 0), SourceRef(7, 1)}
    blocks = reflow(pages, {ref: epigraphs.ROLE for ref in found})
    assert [(b.text, b.epigraph) for b in blocks[:2]] == [
        ("‘It’s closing time’", True),
        ("(Leonard Cohen, The Future)", True),
    ]
    assert not blocks[2].epigraph and blocks[2].opening


def test_a_pictures_garbled_reading_or_a_title_in_capitals_is_no_epigraph():
    pages = [_text_page(7), None, _text_page(9)]
    for rows in (
        [(120, 200, "eKey THAAM a1 DAC Age"), (130, 160, "= – 2")],
        [(150, 220, "DEEL EEN")],
        [(150, 160, "\\")],
        [(140, 200, "Pl Me _")],
    ):
        pages[1] = _short_page(8, rows)
        assert epigraphs.lines(pages, {}) == set(), rows


def test_specks_read_as_short_words_are_no_epigraph():
    from roboscriptorium.epigraphs import _reads

    specks = [
        Line("de", 120, 100, 130, 112),
        Line("De |", 118, 116, 140, 128),
        Line("ap", 121, 132, 131, 144),
    ]
    assert not _reads(specks)
    motto = [
        Line("‘It’s closing time’", 104, 100, 172, 112),
        Line("(Leonard Cohen, The Future)", 80, 116, 195, 128),
    ]
    assert _reads(motto)
