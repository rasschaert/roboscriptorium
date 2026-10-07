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


def test_a_private_use_glyph_spells_the_ligature_ocr_reads_in_its_place():
    from roboscriptorium.pdf import ligature_read

    assert ligature_read("ploe.", "", "plofje.") == "fj"
    assert ligature_read("ea...", "", "Thea...") == "Th"
    # Dutch tesseract reads the Th as "Ih": not a ligature, so no vote.
    assert ligature_read("uis", "", "'Ihuis") is None


def test_unindented_paragraph_starts_after_a_sentence_short_of_the_margin():
    rows = [
        ("Ze zweeg. Wat viel er nog te zeggen over", 250),
        ("de jaren die voorbij waren gegaan.", 160),
        ("Hij ging zitten, en las verder in de", 250),
        ("krant van gisteren, die al geel zag", 250),
        ("van ouderdom en", 120),
        (". . . en toen viel hij in slaap op de", 250),
        ("stoel bij het raam, tot de avond viel", 250),
    ]
    lines = [Line(t, 10, 20 + i * SPACING, x1, 30 + i * SPACING) for i, (t, x1) in enumerate(rows)]
    paragraphs = reflow([PageText(5, 280, HEIGHT, lines)])
    assert [p.text[:10] for p in paragraphs] == ["Ze zweeg. ", "Hij ging z"]


def test_ragged_right_text_has_no_paragraphs_by_line_length():
    rows = [("Een regel.", 200), ("Nog een regel", 150), ("Derde regel.", 230), ("Vierde", 120)]
    lines = [Line(t, 10, 20 + i * SPACING, x1, 30 + i * SPACING) for i, (t, x1) in enumerate(rows)]
    assert len(reflow([PageText(5, 280, HEIGHT, lines)])) == 1


def test_a_closing_double_quote_read_as_single_is_mended():
    from roboscriptorium.reflow import close_quotes

    assert close_quotes("\"One evening when the Doctor was asleep in his chair'") == (
        '"One evening when the Doctor was asleep in his chair"'
    )
    assert close_quotes("\"You never talked that way to me before.' said he") == (
        '"You never talked that way to me before." said he'
    )
    # A plural possessive, a quote within a quote, apostrophes and curly text stay.
    possessive = '"I know the animals\' language," said the Doctor.'
    assert close_quotes(possessive) == possessive
    nested = "\"She said 'never' to me,\" he said. Don't."
    assert close_quotes(nested) == nested
    assert close_quotes("“It is,’ she said") == "“It is,’ she said"


def test_a_real_double_quote_in_single_quoted_text_stays():
    from roboscriptorium.reflow import open_single

    nested = "‘Hij zei: “Kom hier,” en liep weg.’"
    assert open_single(nested) == nested
    assert open_single("“Zo’n ding,” zei hij.") == "“Zo’n ding,” zei hij."
    assert open_single("het woord “ontmoeten’’.") == "het woord “ontmoeten’’."
    assert open_single("een boek met de titel “De ’s avonds zingende vogels”.") == (
        "een boek met de titel “De ’s avonds zingende vogels”."
    )


def test_double_quoted_books_are_not_single_quoted():
    from roboscriptorium.ir import Paragraph
    from roboscriptorium.reflow import single_quoted

    english = [Paragraph("“What is it?” he said. “I don’t know.”"), Paragraph("‘Tis so.")]
    assert not single_quoted(english)
    dutch = [Paragraph("‘Wat is het?’ zei hij. ‘Kom.’"), Paragraph("‘Ja.’"), Paragraph("“Nee’.")]
    assert single_quoted(dutch)


def test_an_opening_double_quote_closed_by_a_single_one_was_misread():
    from roboscriptorium.reflow import open_single

    assert open_single("“Wat doe je?’ vroeg ze.") == "‘Wat doe je?’ vroeg ze."
    assert open_single("“Ja, zei hij. ‘Nee.’") == "‘Ja, zei hij. ‘Nee.’"
    assert open_single("“Ik ben er klaar mee") == "‘Ik ben er klaar mee"
