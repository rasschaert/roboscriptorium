import json
from dataclasses import replace

import pymupdf
import pytest

from roboscriptorium import missing, readers
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


def test_the_models_talk_or_another_scripts_letter_is_no_line_but_an_accent_is():
    page = _page()
    boxes = [Region("abandon", 0.5, 70, 10 + 15 * k, 80, 17 + 15 * k) for k in range(4)]
    found = [(22, b) for b in boxes]
    said = ["```markdown", "境", "«Één»", "‘Ja.’"]
    readings = {missing._key(22, b): s for b, s in zip(boxes, said, strict=True)}
    out = missing.add([page], found, readings)[0]
    assert [ln.text for ln in out.lines[:2]] == ["«Één»", "‘Ja.’"]


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

    monkeypatch.setattr(readers, "read_line", read_line)
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


def _block(first_y: float, n: int = 8) -> PageText:
    lines = [
        Line(f"regel {i} van de tekst", 20, first_y + 15 * i, 360, first_y + 15 * i + 10)
        for i in range(n)
    ]
    return PageText(19, 400, 630, lines)


def test_a_text_regions_strip_without_its_first_line_is_a_candidate():
    region = Region("plain text", 0.96, 11, 24, 360, 153)
    # The layer's lines start one line low: the strip above them is read.
    page = _block(50, 7)
    found = missing.candidates([page], {19: [region]}, {})
    assert [(n, round(r.y0), round(r.y1)) for n, r in found] == [(19, 24, 50)]
    # Lines that fill the region, but for its own margin, leave nothing to read.
    assert missing.candidates([_block(27, 9)], {19: [region]}, {}) == []
    # A strip under a picture or a page's furniture isn't text.
    for label in ("figure", "abandon", "title"):
        assert missing.candidates([page], {19: [replace(region, label=label)]}, {}) == []
    # A strip a human typed text for keeps the human's text.
    assert missing.candidates([page], {19: [region]}, {19: [(11, 24, 360, 50)]}) == []


def test_a_page_the_layer_holds_nothing_of_has_its_display_title_read():
    heights = _page()
    empty = PageText(527, 333, 580, [])
    title = Region("plain text", 0.37, 81, 44, 173, 64)  # display type, 20 pt tall
    regions = {527: [title]}
    assert missing.candidates([heights, empty], regions, {}) == [(527, title)]
    # On a page with text, the same box is no missing line: too tall for one.
    assert missing.candidates([heights], {22: [replace(title, y0=300, y1=320)]}, {}) == []


def test_a_read_line_over_a_misplaced_layer_line_takes_its_place_not_its_neighbours():
    lines = [
        Line("‘Heeft hij de informatie gevonden die je zocht?’", 25, 70, 232, 82),
        Line("qa”", 25, 77, 43, 88),  # the layer's "‘Ja.’", seven points too high
        Line("‘En ben je tevreden?’", 25, 96, 117, 106),
    ]
    page = PageText(105, 300, 500, lines)
    region = Region("plain text", 0.6, 25, 84, 45, 95)
    out = missing.add([page], [(105, region)], {missing._key(105, region): "‘Ja.’"})[0]
    assert [ln.text for ln in out.lines] == [
        "‘Heeft hij de informatie gevonden die je zocht?’",
        "‘Ja.’",
        "‘En ben je tevreden?’",
    ]
    # A line read in the gap between two layer lines is added, as before.
    gap = Region("plain text", 0.6, 25, 108, 60, 118)
    page2 = PageText(105, 300, 500, [lines[0], lines[2], Line("‘Dat doet", 25, 122, 60, 132)])
    out2 = missing.add([page2], [(105, gap)], {missing._key(105, gap): "‘Ja.’"})[0]
    assert len(out2.lines) == 4


def _opening(number: int) -> PageText:
    """A sunk opening: its text from y 100."""
    lines = [Line(f"regel {i} van de tekst", 20, 100 + 15 * i, 320, 110 + 15 * i) for i in range(8)]
    return PageText(number, 340, 580, lines)


def _book(tmp_path, inked: set[int]):
    """Pages 1–10 ordinary, their text from the top; 11–17 sunk openings."""
    doc = pymupdf.open()
    pages = []
    for n in range(1, 18):
        doc.new_page(width=340, height=580)
        if n <= 10:
            lines = [Line(f"regel {i}", 20, 30 + 15 * i, 320, 40 + 15 * i) for i in range(12)]
            pages.append(PageText(n, 340, 580, lines))
        else:
            pages.append(_opening(n))
    for n in inked:
        doc[n - 1].draw_rect(pymupdf.Rect(165, 61, 175, 74), color=(0, 0, 0), fill=(0, 0, 0))
    doc.save(tmp_path / "source.pdf")
    return tmp_path / "source.pdf", pages


def test_the_spotters_usual_box_over_openings_is_placed_where_it_marked_none(tmp_path):
    # The spotter boxed the number on 11, 12 and 13 and none on 14; 15 is blank.
    pdf, pages = _book(tmp_path, inked={11, 12, 13, 14})
    boxes = ((11, 0), (12, 1), (13, -1))
    regions = {n: [Region("title", 0.4, 163, 60 + d, 177, 76 + d)] for n, d in boxes}
    placed = missing.openings(pdf, pages, regions)
    assert placed[11] == regions[11]
    assert [(r.label, r.confidence) for r in placed[14]] == [("title", 0.0)]
    # Fitted to the printed figure, 61–74, a point either side.
    assert (placed[14][0].y0, placed[14][0].y1) == pytest.approx((60, 75), abs=1)
    assert 15 not in placed  # no ink at the place: a blank opening gets no box
    assert (14, placed[14][0]) in missing.candidates(pages, placed, {})


def test_two_boxes_over_openings_are_no_usual_place(tmp_path):
    pdf, pages = _book(tmp_path, inked={11, 12, 14})
    regions = {n: [Region("title", 0.4, 163, 60, 177, 76)] for n in (11, 12)}
    assert missing.openings(pdf, pages, regions) == regions


def test_junk_the_layer_read_in_the_drawing_neither_blocks_nor_hides_the_placed_box(tmp_path):
    # Opening 14's drawn number read "ae" by the layer: still placed, and still read.
    pdf, pages = _book(tmp_path, inked={11, 12, 13, 14})
    k = next(i for i, p in enumerate(pages) if p.number == 14)
    junk = Line("ae", 166, 63, 174, 72)
    pages[k] = PageText(14, 340, 580, [junk, *pages[k].lines])
    boxes = ((11, 0), (12, 1), (13, -1))
    regions = {n: [Region("title", 0.4, 163, 60 + d, 177, 76 + d)] for n, d in boxes}
    placed = missing.openings(pdf, pages, regions)
    assert [r.confidence for r in placed[14]] == [missing.PLACED]
    assert (14, placed[14][0]) in missing.candidates(pages, placed, {})
    # The spotter's own box there is read past the junk too; over a number the layer
    # read ("Io", 10), the box is left to that line.
    spotted = {**regions, 14: [Region("title", 0.4, 163, 60, 177, 76)]}
    assert (14, spotted[14][0]) in missing.candidates(pages, spotted, {})
    pages[k] = PageText(14, 340, 580, [replace(junk, text="Io"), *pages[k].lines[1:]])
    assert all(n != 14 for n, _ in missing.candidates(pages, spotted, {}))
