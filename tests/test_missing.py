import json

import pymupdf
import pytest

from roboscriptorium import missing, ocrcheck
from roboscriptorium.layout import Region
from roboscriptorium.pdf import Line, PageText


def _page() -> PageText:
    lines = [
        Line(f"line {i} of the running text", 20, 100 + 15 * i, 300, 111 + 15 * i) for i in range(6)
    ]
    return PageText(22, 333, 580, lines)


def test_line_sized_regions_without_lines_are_candidates():
    page = _page()
    number = Region("abandon", 0.6, 159, 60, 167, 72)
    regions = {
        22: [
            number,
            Region("title", 0.3, 160, 61, 168, 73),  # the same spot again, less sure
            Region("plain text", 0.9, 20, 100, 300, 190),  # holds lines
            Region("abandon", 0.8, 150, 400, 200, 460),  # taller than a line
            Region("figure", 0.9, 20, 300, 300, 380),
            Region("abandon", 0.5, 100, 320, 120, 330),  # inside the figure
            Region("figure_caption", 0.7, 20, 385, 300, 395),
            Region("abandon", 0.6, 280, 129, 300, 141),  # the end of a text-layer line
        ]
    }
    assert missing.candidates([page], regions, {}) == [(22, number)]
    assert missing.candidates([page], regions, {22: [(150, 50, 180, 80)]}) == []


def test_read_lines_go_into_a_copy_in_reading_order():
    page = _page()
    number = Region("abandon", 0.6, 159, 60, 167, 72)
    folio = Region("abandon", 0.8, 300, 546, 310, 554)
    smudge = Region("abandon", 0.4, 20, 500, 40, 510)
    found = [(22, number), (22, folio), (22, smudge)]
    readings = {
        missing._key(22, number): "3",
        missing._key(22, folio): "18",
        missing._key(22, smudge): "~ .",
    }
    out = missing.add([page], found, readings)[0]
    assert [ln.text for ln in out.lines] == ["3"] + [ln.text for ln in page.lines] + ["18"]
    assert len(page.lines) == 6


def test_an_answer_finds_its_lines_after_a_line_is_added_above():
    from roboscriptorium.corrections import Correction, _located

    page = _page()
    moved = PageText(22, 333, 580, [Line("3", 159, 60, 167, 72)] + page.lines)
    answer = Correction(
        "k",
        22,
        2,
        3,
        "line 2 of the running text\nline 3 of the running text",
        "text",
        "fixed",
        "now",
    )
    assert (_located(page, answer).first, _located(page, answer).last) == (2, 3)
    assert (_located(moved, answer).first, _located(moved, answer).last) == (3, 4)
    gap = Correction("g", 22, 2, 1, "", "text", "typed", "now", box=(20, 128, 300, 129))
    assert _located(moved, gap).first == 3


def test_reads_done_before_a_failure_are_kept(tmp_path, monkeypatch):
    doc = pymupdf.open()
    doc.new_page(width=333, height=580)
    doc.save(tmp_path / "source.pdf")
    found = [
        (1, Region("abandon", 0.6, 10, 10, 50, 20)),
        (1, Region("abandon", 0.6, 10, 40, 50, 50)),
    ]
    replies = iter(["3"])

    def read_line(png, model, url):
        if (reply := next(replies, None)) is None:
            raise RuntimeError("model gone")
        return reply

    monkeypatch.setattr(ocrcheck, "read_line", read_line)
    cache = tmp_path / "missing-lines.json"
    with pytest.raises(RuntimeError):
        missing.read(tmp_path / "source.pdf", found, "m", "", cache)
    assert json.loads(cache.read_text())["lines"] == {missing._key(*found[0]): "3"}


def test_a_drawn_number_above_a_sunk_opening_is_a_candidate_though_tall():
    pages = [_page() for _ in range(4)]
    pages = [PageText(20 + i, 333, 580, p.lines) for i, p in enumerate(pages)]
    sunk = PageText(
        24, 333, 580, [Line(ln.text, ln.x0, ln.y0 + 80, ln.x1, ln.y1 + 80) for ln in pages[0].lines]
    )
    circle = Region("abandon", 0.6, 140, 68, 186, 106)  # above the sunk text
    regions = {
        24: [circle, Region("abandon", 0.6, 140, 300, 186, 338)],  # as tall, below the top
        20: [Region("abandon", 0.6, 140, 30, 186, 68)],  # as tall, on an ordinary page
    }
    assert missing.candidates(pages + [sunk], regions, {}) == [(24, circle)]
