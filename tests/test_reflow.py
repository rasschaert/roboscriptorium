import pytest

from roboscriptorium.ir import Heading, Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText, _core, _visual_lines
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


def _layer_line(spans: list[tuple[str, float, float]]) -> dict:
    return {
        "bbox": (0, min(s[1] for s in spans), 300, max(s[2] for s in spans)),
        "spans": [{"text": t, "bbox": (0, y0, 10, y1)} for t, y0, y1 in spans],
    }


def test_a_large_initial_does_not_pull_the_next_printed_line_into_its_own():
    # The text layer sets a three-line drop cap and the first line as one line.
    opening = _layer_line([("T", 178, 245), ("he crowd had come", 219, 232)])
    assert _core(opening) == (219, 232)
    # A capital barely taller than the text is no initial.
    assert _core(_layer_line([("W", 217, 232), ("hen they", 220, 232)])) == (217, 232)
    fragments = [
        Line("The crowd had come", 22, 178, 300, 245),
        Line("them had no idea", 66, 237, 300, 250),
        Line("Square for the spectacle", 66, 255, 300, 268),
    ]
    cores = [_core(opening), (237, 250), (255, 268)]
    assert [ln.text for ln in _visual_lines(fragments, cores)] == [
        "The crowd had come",
        "them had no idea",
        "Square for the spectacle",
    ]
    # Grouping by the whole boxes glues the second line to the first.
    assert len(_visual_lines(fragments)) == 2


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


def test_a_break_hyphen_stays_where_the_book_prints_the_word_with_it():
    from collections import Counter

    seen = Counter({"thief-taker": 5, "thieftaker": 0, "dankbaar": 3})
    assert join("the thief-", "taker came", seen) == "the thief-taker came"
    # A word the book prints whole, or never inside a line, loses the hyphen.
    assert join("ik ben dank-", "baar voor", seen) == "ik ben dankbaar voor"
    assert join("een paar-", "lemoer", seen) == "een paarlemoer"
    assert join("the thief-", "taker came") == "the thieftaker came"


def test_spellings_count_words_inside_lines_only():
    from roboscriptorium.reflow import spellings

    texts = ["money-box on the shelf", "the thief-taker’s thief-", "taker came"]
    lines = [Line(t, 0, 12 * i, 100, 12 * i + 10) for i, t in enumerate(texts)]
    seen = spellings([PageText(1, 300, 400, lines)])
    assert seen["money-box"] == 1 and seen["thief-takers"] == 1
    # The halves of a word cut at a line's end aren't words.
    assert seen["thief-"] == seen["thief"] == seen["taker"] == 0


def test_a_word_set_in_capitals_is_not_a_proper_noun_at_a_break():
    # The counterexamples first: a capital after the break keeps the hyphen …
    assert join("Noord-", "Holland") == "Noord-Holland"
    assert join("naar Nieuw-", "Zeeland.") == "naar Nieuw-Zeeland."
    # … but a word set in capitals is broken like any other.
    assert join("GEK OP WE-", "RELDGESCHIEDENIS.") == "GEK OP WERELDGESCHIEDENIS."
    assert join("DE TUIN VAN DE AVONDNE-", "VEL.") == "DE TUIN VAN DE AVONDNEVEL."


def test_the_word_list_settles_a_break_the_book_does_not():
    from collections import Counter

    words = {"wc-rol", "twenty-four", "anti-piracy", "afstormde", "homebrew", "makeup", "make-up"}
    known = lambda w: w.lower() in words  # noqa: E731
    # Only one form in the list: that form.
    assert join("de wc-", "rol was nat", known=known) == "de wc-rol was nat"
    assert join("Twenty-", "four", known=known) == "Twenty-four"
    assert join("the anti-", "piracy law", known=known) == "the anti-piracy law"
    assert join("ze af-", "stormde", known=known) == "ze afstormde"
    # The book's own spelling comes before the list.
    seen = Counter({"home-brew": 2})
    assert join("some home-", "brew", seen, known) == "some home-brew"


def test_a_hyphen_already_in_the_word_keeps_the_breaks_only_between_words():
    words = {
        "mens",
        "erger",
        "niet",
        "good",
        "for",
        "nothing",
        "lon",
        "den",
        "londen",
        "tem",
        "pel",
        "tempel",
    }
    known = lambda w: w.lower() in words  # noqa: E731
    # A chained compound broken at one of its own hyphens.
    assert join("Mens-", "erger-je-niet", known=known) == "Mens-erger-je-niet"
    assert join("a good-for-", "nothing", known=known) == "a good-for-nothing"
    # A compound with a real hyphen earlier and a break hyphen later.
    # The parts beside the break are both in the list, but so is the word they make.
    assert join("Zuid-Lon-", "den", known=known) == "Zuid-Londen"
    assert join("de Yasukuni-tem-", "pel", known=known) == "de Yasukuni-tempel"
    assert join("Majuba-theeplan-", "tage", known=known) == "Majuba-theeplantage"
    assert join("Serpukhovsko-Timiryazev-", "skaya", known=known) == "Serpukhovsko-Timiryazevskaya"
    # Without a word list the old rule stands: the hyphen stays.
    assert join("Zuid-Lon-", "den") == "Zuid-Lon-den"


@pytest.mark.xfail(
    strict=True, reason="checklist 6b: a compound the word list knows both ways is a question"
)
def test_a_compound_the_list_knows_both_ways_keeps_its_hyphen():
    words = {"makeup", "make-up"}
    known = lambda w: w.lower() in words  # noqa: E731
    assert join("her make-", "up", known=known) == "her make-up"


@pytest.mark.xfail(strict=True, reason="checklist 6b: a compound the word list lacks is a question")
def test_a_compound_the_list_lacks_keeps_its_hyphen():
    known = lambda w: w.lower() in {"makeup", "make-up"}  # noqa: E731
    assert join("the night-", "vision", known=known) == "the night-vision"


def test_the_word_list_settles_a_hyphen_in_a_pages_last_run_of_body_lines():
    known = lambda w: w.lower() in {"wc-rol"}  # noqa: E731
    pages = [page(1, [(20, "Hij pakte een wc-"), (10, "rol uit de kast.")])]
    assert reflow(pages, known=known)[0].text == "Hij pakte een wc-rol uit de kast."


def test_a_numeral_under_a_heading_label_is_read_as_one():
    pages = [page(1, [(100, "CHAPTER"), (120, "Ill."), (20, "It began."), (10, "And so on.")])]
    head = LineRole("chapter_heading", 0.9, 0.0)
    blocks = reflow(pages, {SourceRef(1, 0): head, SourceRef(1, 1): head})
    assert isinstance(blocks[0], Heading)
    assert blocks[0].text == "CHAPTER III."
    assert blocks[0].parts == ["CHAPTER III."]


def test_a_section_number_under_a_numbered_chapter_label_is_its_own_heading():
    head = LineRole("chapter_heading", 0.9, 0.0)
    roles = {SourceRef(1, 0): head, SourceRef(1, 1): head}
    split = [page(1, [(100, "CHAPTER 2"), (130, "1"), (20, "It began."), (10, "And so on.")])]
    assert [b.text for b in reflow(split, roles) if isinstance(b, Heading)] == ["CHAPTER 2", "1"]
    # A label still waiting for its number takes it.
    whole = [page(1, [(100, "CHAPTER"), (130, "12"), (20, "It began."), (10, "And so on.")])]
    assert [b.text for b in reflow(whole, roles) if isinstance(b, Heading)] == ["CHAPTER 12"]


def _lines(rows: list[tuple[float, float, str]], pitch: float = SPACING) -> PageText:
    """Rows of (x0, x1, text) at a steady pitch."""
    lines = [Line(t, x0, 20 + i * pitch, x1, 30 + i * pitch) for i, (x0, x1, t) in enumerate(rows)]
    return PageText(5, 300, HEIGHT, lines)


def test_an_indented_list_is_not_split_line_by_line():
    # A hanging list: its letters at 30, its lines at 50, ending short of the page's
    # right margin at 280; the page's margin, from the text above, is 10.
    rows = [(10, 280, f"Gewone tekst die tot de rand loopt, regel {i}") for i in range(5)]
    for letter in "ABC":
        rows += [(30, 260, f"{letter}) Een punt van de lijst dat over")]
        rows += [(50, 260, f"meerdere regels doorloopt, regel {i}") for i in range(3)]
        rows += [(50, 120, "het punt.")]
    paragraphs = reflow([_lines(rows)])
    later = [p.text for p in paragraphs if p.text.startswith(("B)", "C)"))]
    assert len(later) == 2 and all(t.endswith("het punt.") for t in later)


def test_jittery_boxes_are_no_gap():
    # Some layers' boxes differ by several points line to line; only a gap at the
    # top and the bottom alike is white space.
    lines = []
    for i in range(8):
        jitter = 6 if i % 2 else -6
        lines.append(Line(f"regel {i} van de tekst", 10, 20 + i * 15 + jitter, 280, 32 + i * 15))
    assert len(reflow([PageText(5, 300, HEIGHT, lines)])) == 1


def test_a_run_of_one_line_dialogue_paragraphs_is_split():
    # Every line in the window starts at the indent; the full lines show the margin.
    rows = [(10, 280, f"Een lange zin die tot de rechterrand loopt, deel {i}") for i in range(4)]
    rows += [(10, 150, "en dan stopt.")]
    rows += [(22, 120 + 10 * i, f"‘Nee,’ zei ze {i}.") for i in range(6)]
    paragraphs = reflow([_lines(rows)])
    assert len(paragraphs) == 7


def test_a_gap_after_a_line_broken_mid_word_is_a_lost_line_not_a_paragraph():
    rows = [(10, 280, f"Tekst tot de rand, regel {i}") for i in range(4)]
    rows += [(10, 280, "Haar intonatie geeft de woorden een andere be-")]
    page_ = _lines(rows)
    page_.lines.append(Line("weg? Hoewel het", 10, 30 + 6 * SPACING, 280, 40 + 6 * SPACING))
    assert len(reflow([page_])) == 1


def test_a_blank_line_starts_an_unindented_paragraph():
    rows = [(10, 280, f"Tekst tot de rand, regel {i}") for i in range(4)] + [(10, 120, "Eind.")]
    page_ = _lines(rows)
    below = [
        Line(f"Na de witregel {i}", 10, 30 + (6 + i) * SPACING, 280, 40 + (6 + i) * SPACING)
        for i in range(3)
    ]
    page_.lines.extend(below)
    paragraphs = reflow([page_])
    assert [p.text[:6] for p in paragraphs] == ["Tekst ", "Na de "]


def test_a_speck_or_an_ordinary_gap_is_no_scene_break():
    rows = [(10, 280, f"Tekst tot de rand, regel {i}") for i in range(4)] + [(10, 120, "Eind.")]
    page_ = _lines(rows)
    page_.lines.insert(3, Line("*", 140, 20 + 3 * SPACING - 4, 143, 20 + 3 * SPACING - 1))
    # Letters spaced apart (1.6 pitches): a paragraph, but no scene break.
    y = 20 + 4 * SPACING + 1.6 * SPACING
    page_.lines.append(Line("Nieuwe alinea na wit", 10, y, 280, y + 10))
    paragraphs = reflow([page_])
    assert paragraphs[-1].text.startswith("Nieuwe")
    assert not any(p.break_before for p in paragraphs)


def test_an_ornament_line_or_two_blank_lines_set_a_scene_break():
    rows = [(10, 280, f"Tekst tot de rand, regel {i}") for i in range(4)] + [(10, 120, "Eind.")]
    rows += [(130, 160, "* * *"), (22, 280, "Een nieuwe scène begint"), (10, 280, "en loopt")]
    rows += [(10, 120, "door. Klaar.")]
    page_ = _lines(rows)
    y = 30 + 10 * SPACING + 2 * SPACING
    page_.lines.append(Line("Na een grote witruimte", 10, y, 280, y + 10))
    paragraphs = reflow([page_])
    assert [(p.text[:10], p.break_before) for p in paragraphs] == [
        ("Tekst tot ", False),
        ("Een nieuwe", True),
        ("Na een gro", True),
    ]
    assert "* * *" not in " ".join(p.text for p in paragraphs)
