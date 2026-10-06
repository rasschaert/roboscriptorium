from roboscriptorium.ir import Heading, Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText, _visual_lines
from roboscriptorium.reflow import join, reflow, tidy
from roboscriptorium.roles import LineRole

SPACING = 15.0
HEIGHT = 500.0


def page(number: int, rows: list[tuple[float, str]], footer: list[str] = ()) -> PageText:
    """Synthetic page: rows of (x0, text) from the top, footer lines at the bottom."""
    lines = [
        Line(text, x, 20 + i * SPACING, 250, 30 + i * SPACING) for i, (x, text) in enumerate(rows)
    ]
    for i, text in enumerate(footer):
        y = HEIGHT * 0.9 + i * SPACING
        lines.append(Line(text, 130, y, 140, y + 10))
    return PageText(number, 280, HEIGHT, lines)


def test_join_undoes_hyphenation_only_before_lowercase():
    assert join("af-", "stormde") == "afstormde"
    assert join("Noord-", "Holland") == "Noord-Holland"
    assert join("alles—", "en het") == "alles—en het"
    assert join("ziet –", "hoe") == "ziet – hoe"
    assert join("Mens-", "erger-je-niet") == "Mens-erger-je-niet"
    assert join("glas-in-", "loodruitjes") == "glas-in-loodruitjes"
    assert join("de", "kerk") == "de kerk"


def test_indent_starts_paragraph_and_footer_is_dropped():
    rows = [
        (10, "Eerste regel van de"),
        (10, "alinea."),
        (20, "Tweede alinea"),
        (10, "loopt door."),
    ]
    paragraphs = reflow([page(5, rows, footer=["><", "5"])])
    assert [p.text for p in paragraphs] == [
        "Eerste regel van de alinea.",
        "Tweede alinea loopt door.",
    ]
    assert paragraphs[0].opening and not paragraphs[1].opening


def test_paragraph_continues_across_page_break():
    first = page(10, [(10, "Een zin die door-")], footer=["Io"])
    second = page(11, [(10, "loopt op de volgende pagina."), (20, "Nieuwe alinea.")])
    paragraphs = reflow([first, second])
    assert paragraphs[0].text == "Een zin die doorloopt op de volgende pagina."
    assert [(s.page, s.line) for s in paragraphs[0].sources] == [(10, 0), (11, 0)]


def test_margin_follows_skew():
    # Line starts drift 1pt per line; only the 10pt jump is an indent.
    rows = [(10 + i, f"regel {i}") for i in range(8)]
    rows[5] = (25, "inspringing")
    paragraphs = reflow([page(5, rows)])
    assert len(paragraphs) == 2
    assert paragraphs[1].text.startswith("inspringing")


def test_roles_drop_artefacts_and_keep_blocks_in_page_order():
    rows = [
        (10, "20 SENSE AND SENSIBILITY."),
        (10, "einde van een zin."),
        (60, "CHAPTER"),
        (70, "V."),
        (10, "Begin van het hoofdstuk"),
        (10, "dat doorloopt."),
    ]
    not_body = {0: "running_head", 2: "chapter_heading", 3: "chapter_heading"}
    roles = {SourceRef(20, i): LineRole(role, 0.9, 0.05) for i, role in not_body.items()}
    blocks = reflow([page(20, rows)], roles)
    assert [type(b) for b in blocks] == [Paragraph, Heading, Paragraph]
    assert blocks[0].text == "einde van een zin."
    assert blocks[1].text == "CHAPTER V."
    assert blocks[2].text == "Begin van het hoofdstuk dat doorloopt." and blocks[2].opening


def test_tidy_removes_space_before_punctuation_only():
    assert tidy("Sussex , and ; then !") == "Sussex, and; then!"
    assert tidy("a — b") == "a — b"


def test_word_boxes_of_one_skewed_line_form_one_line():
    words = [  # one printed line, word boxes differing by up to 5 pt at the top
        Line("when", 118, 231.7, 150, 246.0),
        Line("our", 155, 233.4, 175, 245.4),
        Line("grandfathers", 181, 236.5, 250, 247.8),
        Line("were", 255, 233.0, 280, 245.7),
        Line("little children", 105, 250.1, 180, 261.4),  # next line, 16 pt down
    ]
    lines = _visual_lines(words)
    assert [ln.text for ln in lines] == ["when our grandfathers were", "little children"]


def test_headings_match_in_order_and_split_subtitles_count():
    from roboscriptorium.evaluate import match_headings

    expected = ["CHAPTER I.", "CHAPTER II.", "THE FIRST CHAPTER PUDDLEBY", "I", "II"]
    found = ["CHAPTER I.", "Animal Language", "CHAPTER IL", "THE FIRST CHAPTER", "I", "Il"]
    assert match_headings(found, expected) == 4


def test_a_missing_heading_does_not_shift_later_matches():
    from roboscriptorium.evaluate import match_headings

    expected = ["CHAPTER XXIV.", "CHAPTER XXV.", "CHAPTER XXVI.", "CHAPTER XXVII."]
    found = ["CHAPTER XXIV.", "CHAPTER XXVI.", "CHAPTER XXVII."]
    assert match_headings(found, expected) == 3


def test_numeral_under_a_title_starts_its_own_heading():
    lines = [
        Line("The Nature of", 150, 100, 250, 112),
        Line("a Crime", 170, 115, 230, 127),
        Line("I", 195, 140, 205, 152),
    ] + [Line("body text " * 5, 50, 170 + 15 * i, 350, 182 + 15 * i) for i in range(10)]
    page = PageText(1, 400, 600, lines)
    heading = LineRole("chapter_heading", 0.9, 0.0)
    roles = {SourceRef(1, i): heading for i in range(3)}
    texts = [b.text for b in reflow([page], roles) if isinstance(b, Heading)]
    assert texts == ["The Nature of a Crime", "I"]


def test_tidy_spells_out_ligatures():
    assert tidy("koﬃe op de ﬁets bij Graaﬀ") == "koffie op de fiets bij Graaff"


def test_chapter_label_and_title_are_separate_parts_of_one_heading():
    lines = [
        Line("THE STORY OF", 120, 100, 280, 112),
        Line("DOCTOR DOLITTLE", 110, 115, 290, 127),
        Line("THE FIRST CHAPTER", 110, 140, 290, 152),
        Line("PUDDLEBY", 160, 160, 240, 172),
    ] + [Line("body text " * 5, 50, 190 + 15 * i, 350, 202 + 15 * i) for i in range(10)]
    page = PageText(1, 400, 600, lines)
    heading = LineRole("chapter_heading", 0.9, 0.0)
    roles = {SourceRef(1, i): heading for i in range(4)}
    found = [b for b in reflow([page], roles) if isinstance(b, Heading)]
    assert [h.parts for h in found] == [
        ["THE STORY OF DOCTOR DOLITTLE"],
        ["THE FIRST CHAPTER", "PUDDLEBY"],
    ]
    assert found[1].text == "THE FIRST CHAPTER PUDDLEBY"
