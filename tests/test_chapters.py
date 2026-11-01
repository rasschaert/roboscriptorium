"""Chapter numbers: the book's run of numbered chapters, read where the layer can't."""

from roboscriptorium import chapters
from roboscriptorium.ir import Heading, Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole


def _headings(*texts: str) -> list:
    blocks = []
    for t in texts:
        blocks += [Heading(t, [], [t]), Paragraph("Tekst.")]
    return blocks


def _read(blocks: list) -> list[str]:
    return [b.text for b in blocks if isinstance(b, Heading)]


def test_headings_of_words_or_a_run_too_short_are_left_alone():
    titles = _headings("Proloog", "Aan de Dender", "Een ramp", "Jan Byl", "Epiloog")
    assert chapters.numbered(titles) == titles
    few = _headings("I", "2", "SE")
    assert chapters.numbered(few) == few
    # Short headings that don't run in order are no numbered run.
    loose = _headings("A", "B", "C", "D", "E", "F")
    assert chapters.numbered(loose) == loose


def test_a_reading_off_the_run_stands_unless_both_neighbours_agree():
    # 8 → 10 skips one: nothing says what lies between, so "10" stands.
    blocks = _headings("6", "7", "8", "10", "11", "12")
    assert _read(chapters.numbered(blocks)) == ["6", "7", "8", "10", "11", "12"]


def test_old_style_lookalikes_and_short_misreads_take_the_runs_number():
    blocks = _headings("I", "2", "3", "4", "5", "6", "7", "8", "9", "Io", "II", "I2", "zi", "14")
    blocks += _headings("17.", "18")
    out = chapters.numbered(blocks)
    assert _read(out) == [str(n) for n in range(1, 13)] + ["13", "14", "17", "18"]
    # A title of words among the numbers is no part of the run and stays as it is.
    mixed = [Heading("Bruni en Thomas Eggers", [], [])]
    mixed += _headings("47", "48", "49", "50", "SE", "S2")
    assert _read(chapters.numbered(mixed)) == ["Bruni en Thomas Eggers"] + [
        str(n) for n in range(47, 53)
    ]
    # The input is left as it was.
    assert _read(blocks)[0] == "I"


def _page(number: int, first: str | None) -> PageText:
    body = [Line(f"Tekst tot de marge, regel {i}", 30, 140 + 14 * i, 300, 150 + 14 * i)
            for i in range(20)]  # fmt: skip
    head = [Line(first, 150, 80, 165, 92)] if first is not None else []
    return PageText(number, 330, 450, head + body)


def _full(number: int) -> PageText:
    lines = [Line(f"Tekst tot de marge, regel {i}", 30, 40 + 14 * i, 300, 50 + 14 * i)
             for i in range(28)]  # fmt: skip
    return PageText(number, 330, 450, lines)


def test_a_dropped_short_line_atop_an_opening_is_a_heading_where_the_others_are():
    firsts = ["1", "2", "3", "4", "5", "zi"]
    pages = []
    for k, first in enumerate(firsts):
        pages += [_page(10 * k + 1, first), _full(10 * k + 2), _full(10 * k + 3)]
    heading = LineRole("chapter_heading", 0.9, 0.0)
    roles = {SourceRef(10 * k + 1, 0): heading for k in range(5)}
    roles[SourceRef(51, 0)] = LineRole("artifact", 0.6, 0.05)
    out = chapters.openings(pages, roles)
    assert out[SourceRef(51, 0)].role == "chapter_heading"
    assert out[SourceRef(51, 0)].rule == chapters.RULE
    assert roles[SourceRef(51, 0)].role == "artifact"
    # Where most openings carry no heading, a short line atop one stays dropped.
    sparse = {SourceRef(1, 0): heading, SourceRef(51, 0): roles[SourceRef(51, 0)]}
    assert chapters.openings(pages, sparse)[SourceRef(51, 0)].role == "artifact"
    # A speck in the corner, or a mark with no letter or digit, is no number either.
    corner = list(pages)
    corner[15] = PageText(51, 330, 450, [Line("zi", 20, 80, 35, 92)] + pages[15].lines[1:])
    assert chapters.openings(corner, roles)[SourceRef(51, 0)].role == "artifact"
    corner[15] = _page(51, "-")
    assert chapters.openings(corner, roles)[SourceRef(51, 0)].role == "artifact"
    # A line of words atop an opening is no number: the rule leaves it to the roles.
    pages[15] = _page(51, "Een titel")
    assert chapters.openings(pages, roles)[SourceRef(51, 0)].role == "artifact"
