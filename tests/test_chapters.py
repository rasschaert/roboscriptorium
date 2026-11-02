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


def test_a_dropped_line_of_a_title_page_set_like_another_title_pages_heading_is_one():
    from roboscriptorium.typestyle import Style

    def title(n: int, part: str, sub: str) -> PageText:
        return PageText(n, 300, 500, [Line(part, 120, 30, 180, 40), Line(sub, 100, 50, 200, 62)])

    pages = [title(13, "BOEK EEN", "De cijnskiezers"), _full(14),
             title(161, "BOEK TWEE", "Meervoudig stemrecht"), _full(162),
             title(300, "BOEK DRIE", "17"), _full(301)]  # fmt: skip
    heading, dropped = LineRole("chapter_heading", 0.9, 0.0), LineRole("artifact", 0.5, 0.03)
    roles = {SourceRef(n, 0): heading for n in (13, 161, 300)}
    roles |= {SourceRef(13, 1): heading, SourceRef(161, 1): dropped, SourceRef(300, 1): dropped}
    big = Style(1.4, 1.0, 1.0, False)
    styles = {SourceRef(n, i): big for n in (13, 161, 300) for i in range(2)}
    out = chapters.title_lines(pages, roles, styles)
    assert out[SourceRef(161, 1)].role == "chapter_heading"
    # A number, or a line in another type, stays dropped; so does one on a page of text.
    assert out[SourceRef(300, 1)].role == "artifact"
    small = styles | {SourceRef(161, 1): Style(1.0, 1.0, 1.0, False)}
    assert chapters.title_lines(pages, roles, small)[SourceRef(161, 1)].role == "artifact"
    pages[2] = PageText(161, 300, 500, pages[2].lines + _full(162).lines)
    assert chapters.title_lines(pages, roles, styles)[SourceRef(161, 1)].role == "artifact"


def test_a_heading_in_its_confirmed_run_is_settled_a_lone_or_misread_one_not():
    blocks = []
    for k, t in enumerate(["1", "2", "3", "Proloog", "9", "SE"], 1):
        blocks += [Heading(t, [SourceRef(k, 0)], [t]), Paragraph("Tekst.")]
    assert chapters.settled(blocks) == {SourceRef(1, 0), SourceRef(2, 0), SourceRef(3, 0)}


def test_titles_opening_on_years_in_order_and_parts_counted_in_order_are_settled():
    texts = ["Woord vooraf", "BOEK EEN De cijnskiezers", "1840-1884: Aan de Dender",
             "1885: Een ramp", "1886: Jan Byl", "BOEK TWEE", "1887-1888: ‘De Toekomst’",
             "1889–1890: Cieske Luyckx", "Nawoord"]  # fmt: skip
    blocks = [Heading(t, [SourceRef(k, 0)], [t]) for k, t in enumerate(texts, 1)]
    assert chapters.settled(blocks) == {SourceRef(k, 0) for k in range(2, 9)}
    # Years out of order settle nothing.
    shuffled = [Heading(t, [SourceRef(k, 0)], [t]) for k, t in enumerate(
        ["1885: A", "1840: B", "1886: C", "1887: D", "1888: E"], 1)]  # fmt: skip
    assert chapters.settled(shuffled) == set()
