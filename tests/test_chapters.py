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


def test_a_title_of_words_atop_an_opening_is_a_heading_where_the_others_are_titles():
    def titled(number: int, title: str) -> PageText:
        page = _page(number, None)
        width = 6 * len(title)
        head = Line(title, 165 - width / 2, 80, 165 + width / 2, 92)
        return PageText(number, 330, 450, [head, *page.lines])

    titles = ["De smalfilm", "Ziekenbezoek", "Chrysanten", "Addis Abeba", "Olivecrona"]
    titles.append("Het vonnis wordt uitgesproken")
    pages = []
    for k, title in enumerate(titles):
        pages += [titled(10 * k + 1, title), _full(10 * k + 2), _full(10 * k + 3)]
    heading = LineRole("chapter_heading", 0.9, 0.0)
    roles = {SourceRef(10 * k + 1, 0): heading for k in range(5)}
    for p_body in (0.44, 0.6):
        roles[SourceRef(51, 0)] = LineRole("body", p_body, p_body, "trees")
        assert chapters.openings(pages, roles)[SourceRef(51, 0)].role == "chapter_heading"


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
    # Below a page's running text, a line set so is no subtitle.
    pages[2] = PageText(161, 300, 500, pages[2].lines[:1] + _full(162).lines + pages[2].lines[1:])
    below = {SourceRef(161, 0): heading, SourceRef(161, 29): dropped} | {
        SourceRef(161, i): LineRole("body", 0.9, 0.9) for i in range(1, 29)
    }
    styles_below = styles | {SourceRef(161, 29): big}
    assert (
        chapters.title_lines(pages, roles | below, styles_below)[SourceRef(161, 29)].role
        == "artifact"
    )


def test_a_label_recurring_under_chapter_numbers_is_part_of_the_heading():
    from roboscriptorium.typestyle import Style

    def opening(n: int, lines: list[str]) -> PageText:
        heads = [Line(t, 140, 60 + 40 * k, 180, 75 + 40 * k) for k, t in enumerate(lines)]
        return PageText(n, 300, 500, heads + _full(n).lines[:3])

    number, name = LineRole("chapter_heading", 0.9, 0.0), LineRole("artifact", 0.8, 0.02)
    body = LineRole("body", 0.99, 0.99)
    label = Style(1.6, 1.0, 1.0, True)
    pages = [opening(11, ["ALEX"]), opening(20, ["2", "ALEX"]), opening(30, ["3", "RENEE"]),
             opening(51, ["5", "ALEX"]), _full(52)]  # fmt: skip
    roles, styles = {}, {}
    for p in pages[:4]:
        heads = len(p.lines) - 3
        for i in range(len(p.lines)):
            ref = SourceRef(p.number, i)
            roles[ref] = body if i >= heads else (name if p.lines[i].text.isalpha() else number)
            styles[ref] = label
    for i in range(len(pages[4].lines)):
        roles[SourceRef(52, i)] = body
    out = chapters.title_lines(pages, roles, styles)
    for ref in [SourceRef(20, 1), SourceRef(30, 1), SourceRef(51, 1)]:
        assert out[ref].role == "chapter_heading"
    # The same name opening a page whose number the layer lacks.
    assert out[SourceRef(11, 0)].role == "chapter_heading"
    # Under two headings only, the type isn't the book's own: both stay dropped.
    two = {r: v for r, v in roles.items() if r.page != 51}
    out = chapters.title_lines(pages[:3], two, styles)
    assert out[SourceRef(20, 1)].role == "artifact" and out[SourceRef(11, 0)].role == "artifact"
    # A running head over pages of text, though it recurs, is under no heading.
    head = [PageText(n, 300, 500, [Line("HET SCHADUWHUIS", 120, 20, 200, 30)] + _full(n).lines[:3])
            for n in range(60, 66)]  # fmt: skip
    head_roles = {SourceRef(n, 0): name for n in range(60, 66)} | {
        SourceRef(n, i): body for n in range(60, 66) for i in range(1, 4)}  # fmt: skip
    head_styles = {SourceRef(n, 0): label for n in range(60, 66)}
    out = chapters.title_lines(pages + head, roles | head_roles, styles | head_styles)
    assert all(out[SourceRef(n, 0)].role == "artifact" for n in range(60, 66))
    # Lines of more than a few words under the numbers are no labels.
    long = {**styles}
    pages_long = [opening(20, ["2", "Een motto van zes korte woorden"]),
                  opening(30, ["3", "Een motto van zes korte woorden"]),
                  opening(51, ["5", "Een motto van zes korte woorden"])]  # fmt: skip
    long_roles = {SourceRef(n, 0): number for n in (20, 30, 51)} | {
        SourceRef(n, 1): name for n in (20, 30, 51)} | {
        SourceRef(n, i): body for n in (20, 30, 51) for i in range(2, 5)}  # fmt: skip
    out = chapters.title_lines(pages_long, long_roles, long)
    assert all(out[SourceRef(n, 1)].role == "artifact" for n in (20, 30, 51))


def test_a_heading_in_its_confirmed_run_is_settled_a_lone_or_misread_one_not():
    blocks = []
    for k, t in enumerate(["1", "2", "3", "Proloog", "9", "SE"], 1):
        blocks += [Heading(t, [SourceRef(k, 0)], [t]), Paragraph("Tekst.")]
    assert chapters.settled(blocks) == {SourceRef(1, 0), SourceRef(2, 0), SourceRef(3, 0)}


def test_a_number_with_its_label_and_a_recurring_label_are_settled_a_running_head_not():
    def h(n: int, *lines: str) -> Heading:
        # As reflow sets them: a number and the line under it are one part ("2 ALEX").
        text = " ".join(lines)
        return Heading(text, [SourceRef(n, i) for i in range(len(lines))], [text])

    blocks = [h(11, "ALEX"), h(20, "2", "ALEX"), h(30, "3", "RENEE"), h(37, "ALEX"),
              h(51, "5", "ALEX"), h(55, "6", "RENEE"), h(66, "7", "ALEX")]  # fmt: skip
    out = chapters.settled(blocks)
    assert {SourceRef(n, 0) for n in (20, 30, 51, 55, 66)} <= out
    # "ALEX" stands under three numbers: settled there and alone; "RENEE" under two only.
    assert {SourceRef(n, 1) for n in (20, 51, 66)} | {SourceRef(11, 0), SourceRef(37, 0)} <= out
    assert SourceRef(30, 1) not in out and SourceRef(55, 1) not in out
    # A title recurring only as a heading's first line (a running head taken for one) is asked.
    heads = [h(n, "HET SCHADUWHUIS") for n in (60, 61, 62, 63)]
    assert not chapters.settled(heads)


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


def test_labelled_chapter_numbers_run_with_the_books_commonest_label():
    texts = ["HOOFDSTUK 1", "HOOFDSTUK 2", "HOOFDSTUK 3", "HOOFDSTUK 4", "HOOFDSTUK 5",
             "Hoorpstuk 6", "HOOFDSTUK 7", "HOOFDSTUK 8", "HOOFDSTUK 9", "HOOFDSTUK 10",
             "HOOFDSTUK II", "HOOFDSTUK 12", "Hoorpstvk 13", "HOOFDSTUK I4", "HOOFDSTUK 15",
             "Hoofdstuk IY", "HOOFDSTUK 17"]  # fmt: skip
    blocks = [Heading(t, [], [t]) for t in texts]
    assert _read(chapters.numbered(blocks)) == [f"HOOFDSTUK {n}" for n in range(1, 18)]
    # Another label among them, or labels that don't run, stay as read.
    mixed = [Heading(t, [], [t]) for t in ["Proloog", "Deel 1", "Deel 3", "Hoofdstuk A"]]
    assert _read(chapters.numbered(mixed)) == ["Proloog", "Deel 1", "Deel 3", "Hoofdstuk A"]


def test_a_heading_running_on_into_the_sentence_below_is_body_a_real_one_stays():
    text = "them had no idea who the men were, regel"
    full = [Line(f"{text} {i}", 30, 100 + 14 * i, 330, 110 + 14 * i) for i in range(20)]
    page = PageText(13, 360, 500, [
        Line("BERREN", 150, 40, 210, 52),
        Line("The crowd had come to watch three men die. Most of", 20, 80, 335, 92),
        *full,
    ])  # fmt: skip
    heading = LineRole("chapter_heading", 1.0, 0.0, "trees")
    roles = {SourceRef(13, 0): heading, SourceRef(13, 1): heading}
    out = chapters.running_text([page], roles)
    assert out[SourceRef(13, 1)].role == "body" and out[SourceRef(13, 0)].role == "chapter_heading"
    # A heading over two lines, both headings, stays one; so does a wide title before a
    # capital, and a narrow heading ending in a word.
    two = dict(roles) | {SourceRef(13, 2): heading}
    assert chapters.running_text([page], two)[SourceRef(13, 1)].role == "chapter_heading"
    capital = PageText(13, 360, 500, [page.lines[0], page.lines[1], Line("Them", 30, 100, 330, 110),
                                      *full[1:]])  # fmt: skip
    assert chapters.running_text([capital], roles)[SourceRef(13, 1)].role == "chapter_heading"
    narrow = PageText(
        13, 360, 500, [page.lines[0], Line("A NICE BOTTLE OF", 120, 80, 240, 92), *full]
    )
    assert chapters.running_text([narrow], roles)[SourceRef(13, 1)].role == "chapter_heading"


def _mid_page(number: int, *texts: str) -> PageText:
    """A page of full lines, with each of `texts` as a short centred line in the middle."""
    lines = [
        Line(f"tekst {k} van de bladzijde", 20, 40 + 15 * k, 320, 50 + 15 * k) for k in range(6)
    ]
    y = 40 + 15 * 6
    for t in texts:
        lines.append(Line(t, 165, y, 175, y + 10))
        y += 15
    lines += [
        Line(f"verder {k} op de bladzijde", 20, y + 15 * k, 320, y + 10 + 15 * k) for k in range(6)
    ]
    return PageText(number, 340, 580, lines)


def _roles(pages: list[PageText], headings: dict[int, str]) -> dict:
    body = LineRole("body", 0.9, 0.9, "model")
    out = {}
    for p in pages:
        for i, ln in enumerate(p.lines):
            dropped = len(ln.text) <= 3
            heading = headings.get(p.number) == ln.text
            role = "chapter_heading" if heading else "artifact" if dropped else None
            out[SourceRef(p.number, i)] = LineRole(role, 0.8, 0.1, "trees") if role else body
    return out


def test_a_dropped_number_filling_the_runs_gap_is_a_heading_others_not():
    # Headings 1, 2, 5, 6, 7 kept; "3" and "4" dropped mid-page between them; then "9".
    texts = {10: "1", 11: "2", 12: "3", 13: "4", 14: "5", 15: "6", 16: "7", 17: "9", 18: "13"}
    pages = [_mid_page(n, t) for n, t in texts.items()]
    roles = _roles(pages, {10: "1", 11: "2", 14: "5", 15: "6", 16: "7"})
    out = chapters.run_gaps(pages, roles)
    mid = 6  # each page's number line
    assert out[SourceRef(12, mid)].role == out[SourceRef(13, mid)].role == "chapter_heading"
    # Past the run within `RUN_GAP` ("9" after "7") is taken; too far ("13" after "9") not.
    assert out[SourceRef(17, mid)].role == "chapter_heading"
    assert out[SourceRef(18, mid)].role == "artifact"
    assert all(out[SourceRef(p.number, 0)] == roles[SourceRef(p.number, 0)] for p in pages)


def test_a_page_number_a_number_off_centre_or_past_the_next_heading_is_no_gap():
    texts = {10: "1", 11: "2", 14: "5", 15: "6", 16: "7"}
    pages = [_mid_page(n, t) for n, t in texts.items()]
    # Page 12 ends on a lone "3" (where its page number would stand); page 13's "4" stands
    # off the middle; page 14 holds a "6" before its heading "5".
    last = _mid_page(12)
    last = PageText(12, 340, 580, [*last.lines, Line("3", 165, 560, 175, 570)])
    aside = _mid_page(13)
    aside = PageText(
        13, 340, 580, [*aside.lines[:6], Line("4", 20, 130, 30, 140), *aside.lines[6:]]
    )
    early = _mid_page(14, "6", "5")
    pages = [pages[0], pages[1], last, aside, early, pages[3], pages[4]]
    roles = _roles(pages, {10: "1", 11: "2", 14: "5", 15: "6", 16: "7"})
    out = chapters.run_gaps(pages, roles)
    assert out[SourceRef(12, len(last.lines) - 1)].role == "artifact"
    assert out[SourceRef(13, 6)].role == "artifact"
    assert out[SourceRef(14, 6)].role == "artifact"


def test_too_few_numbered_headings_make_no_run():
    texts = {10: "1", 11: "2", 12: "3", 13: "4"}
    pages = [_mid_page(n, t) for n, t in texts.items()]
    roles = _roles(pages, {10: "1", 11: "2", 13: "4"})
    assert chapters.run_gaps(pages, roles) == roles
