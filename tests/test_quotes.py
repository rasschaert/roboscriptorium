from roboscriptorium import quotes
from roboscriptorium.ir import Paragraph, SourceRef
from roboscriptorium.quotes import problems, unbalanced


def test_a_flemish_elision_or_a_year_needs_no_partner():
    assert problems("‘Ken ik ’m?’ vroeg ik, en ’k zei: ‘Uit ’73.’") == []
    assert problems("Ik schopte ’m tegen z’n kop.") == []


def test_an_elision_read_with_an_opening_mark_is_still_asked():
    # The print sets ’m; the layer's ‘ is its error, and the question catches it.
    assert problems("Ik zei ‘m dat ik veel geld had.") != []


def test_a_mark_before_an_elisions_short_word_needs_no_partner():
    assert problems("I sell ’em to make ’em sick, in the late ’80s.") == []
    assert problems("Kom ’ns hier, zei ’ie.") == []


def test_a_mark_before_a_whole_word_is_still_asked():
    # The layer's ’ for a printed opening ‘ ("dat ‘alles heel anders verliep").
    assert problems("omdat het een vrouw was dat ’alles heel anders verliep.") != []


def test_apostrophes_need_no_partner():
    assert problems("‘Zo’n auto’s, zei hij, om zes uur ’s avonds.’") == []
    assert problems("‘Ik kom ’t halen.’") == []
    # The layer's ‘ for the article ’s, and a straight one, are apostrophes too.
    assert problems("Om zes uur ‘s avonds en 's morgens.") == []


def test_a_plural_possessive_needs_no_partner():
    assert problems("He spoke the animals’ language, as in Jezus’ tijd.") == []


def test_a_possessive_after_a_name_ending_in_an_s_sound_needs_no_partner():
    assert problems("Het lezen van Maurice’ handschrift maakte me nerveus.") == []
    assert problems("Felix’ fiets en Louise’ boek.") == []
    assert problems("‘Ik zag Maurice’ moeder,’ zei hij.") == []
    # A closing mark after such a word still closes, where nothing else can.
    assert problems("‘Hij reed de race’ en won.") == []
    assert problems("‘Wat een race’ zei hij. ‘Kom.’") == []
    # A name not ending in an s-sound keeps its mark a quote: one is missing.
    assert problems("Het lezen van Marie’ handschrift.") != []


def test_a_closing_quote_after_an_s_still_closes():
    # The only ’ that can close the quotation is the one after the s.
    assert problems("‘Hij zei ja tegen Jans’ en ging.") == []
    assert problems("‘Ja, Jans’ zei hij. ‘Kom.’") == []
    assert problems("‘Ik zei ‘arme Jans’ in het Hongaars!’") == []


def test_a_plural_possessive_inside_a_quotation_doesnt_close_it():
    assert problems("‘The animals’ language is hard,’ he said.") == []
    assert problems("‘Ik ken de Jansens’ huis wel,’ zei ze.") == []
    assert problems("‘Ik zag Jans’ fiets,’ zei hij, ‘en ging.’") == []
    # Possessive or closing, a mark is still missing: flagged either way.
    assert problems("‘The animals’ language is hard, he said. ‘Yes.") != []


def test_quotes_nest_in_the_same_mark():
    assert problems("‘Ik zei ‘arme kerel’ in het Hongaars!’") == []
    assert problems("‘Wat is ‘beroepshypochondrie’, dokter?’ vroeg ik.") == []
    assert problems("Hij schreef: ‘Mijn vingers zeggen ‘nee’.’") == []


def test_a_quote_open_at_a_paragraphs_end_is_asked_whatever_follows():
    # A quotation running over into the next paragraph looks the same as a closing
    # mark lost at the end, and is the rarer of the two.
    assert problems("‘Het begon in Boedapest.") == [(23, "open at end")]


def test_a_lost_mark_is_found():
    assert problems("Je gaat naar rechts,’ zei hij.") == [(20, "no opening")]
    assert problems("‘Kom op, zei Zach. ‘Dat was de afspraak.’") == [(19, "no closing")]
    assert problems("‘Nee.") == [(4, "open at end")]


def test_places_point_at_the_lines_where_the_mark_is_missing():
    refs = [SourceRef(3, k) for k in range(6)]
    p = Paragraph("‘" + "woord " * 59 + "einde.", refs)
    (place,) = unbalanced([p])
    assert place.why == "open at end"
    assert place.sources == refs[-2:]
    q = Paragraph("Woord " * 59 + "einde.’", refs)
    (place,) = unbalanced([q])
    assert place.why == "no opening"
    assert place.sources == refs[-2:]


def test_a_proposal_takes_only_the_readings_marks():
    from roboscriptorium.quotes import proposed

    # Letters the reading changes stay the layer's, whatever its marks.
    assert proposed("krampachtig, ‘vergissing…", "krimpachtig, ‘vergissing...’") == (
        "krampachtig, ‘vergissing…’"
    )
    # A word that differs in a mark other than a quote stays as it is.
    assert proposed("Ja, ja, goedemorgen…!", "Ja, ja, goedemorgen.!") == "Ja, ja, goedemorgen…!"
    # A reading without the space before ’s doesn't join the words.
    assert proposed("om zes uur ’s avonds", "om zes uur’s avonds") == "om zes uur ’s avonds"
    # Nothing to propose where the marks agree.
    assert proposed("‘Nou dan.’", "'Nou dan.'") == "‘Nou dan.’"


def test_a_proposal_puts_back_a_lost_quote_and_its_period():
    from roboscriptorium.quotes import proposed

    assert proposed(
        "Je zei immers over acht, tien dagen”", "'Je zei immers over acht, tien dagen.'"
    ) == ("‘Je zei immers over acht, tien dagen.’")
    assert proposed("domme gans, herhaalde ik", "domme gans,’ herhaalde ik") == (
        "domme gans,’ herhaalde ik"
    )
    # A contraction the layer split by losing its apostrophe is joined again.
    assert proposed("I m not going to kill you", "‘I’m not going to kill you") == (
        "‘I’m not going to kill you"
    )
    # Ellipses come in the book's own form.
    assert proposed("een zuigeling…", "een zuigeling...’", "...") == "een zuigeling...’"


def test_the_style_prompt_names_the_books_marks():
    from roboscriptorium.quotes import style_prompt

    dutch = style_prompt("nl", True, "…", "–")
    assert "Dutch" in dutch and "curly quotes ‘ ’" in dutch and "en dashes" in dutch
    english = style_prompt("en", False, "...", None)
    assert "curly quotes “ ”" in english and "dash" not in english.split("Transcribe")[0]


def test_the_style_prompt_is_unchanged_for_the_glyph_and_tight_dots():
    # The read model's cache is keyed on this prompt.
    from roboscriptorium.quotes import style_prompt

    tail = (
        "Use exactly these characters, never straight quotes. Transcribe the printed text in "
        "this image exactly as printed: every letter, accent, quote mark, dash and punctuation "
        "mark. It is one line of a book. Output only the text."
    )
    assert style_prompt("nl", True, "…", "–") == (
        "This book is Dutch and set in this style: dialogue in curly quotes ‘ ’, a quotation "
        "inside dialogue in “ ”, the apostrophe ’, the ellipsis as one character …, en dashes "
        "–. " + tail
    )
    assert style_prompt("en", False, "...", None) == (
        "This book is English and set in this style: dialogue in curly quotes “ ”, a quotation "
        "inside dialogue in ‘ ’, the apostrophe ’, the ellipsis as .... " + tail
    )


def test_spaced_dots_are_named_in_the_style():
    from roboscriptorium.quotes import style_note

    assert "the ellipsis as spaced dots . . ." in style_note("en", False, ". . .", "—")


def test_the_books_ellipsis_comes_from_its_style_where_that_is_spaced_dots():
    from roboscriptorium.quotes import ellipsis
    from roboscriptorium.typography import EllipsisStyle

    tight = "Wel... ja. " * 12
    glyph = "Wel… ja. " * 12
    spaced = "Wel . . . ja. Nou... nee. " * 12
    assert ellipsis(tight) == "..." and ellipsis(glyph) == "…"
    assert ellipsis(spaced) == ". . ."
    # book.toml's style wins over the layer.
    assert ellipsis(tight, EllipsisStyle(". . .", True)) == ". . ."
    assert ellipsis(spaced, EllipsisStyle("...", False)) == "..."
    assert ellipsis(glyph, EllipsisStyle("…", False)) == "…"


def test_a_proposal_sets_a_spaced_reading_in_the_books_ellipsis():
    from roboscriptorium.quotes import proposed

    assert proposed("Nou. . . nee, zei hij.", "Nou. . . nee,’ zei hij.", ". . .") == (
        "Nou. . . nee,’ zei hij."
    )
    assert proposed("Nou... nee, zei hij.", "Nou. . . nee,’ zei hij.", "...") == (
        "Nou... nee,’ zei hij."
    )
    assert proposed("Ja nee... zei hij.", "Ja nee. . .’ zei hij.", "...") == "Ja nee...’ zei hij."


def test_a_proposal_takes_no_dash_or_letter_from_the_reading():
    from roboscriptorium.quotes import proposed

    assert proposed("in de buurt van de directeursk—", "in de buurt van de directeursk-’") == (
        "in de buurt van de directeursk—’"
    )


def test_quote_readings_offer_the_checked_line_and_combine_a_nested_quotation():
    from roboscriptorium.quotes import readings

    # The print sets the wrong mark: the checked line keeps it, the scan reading "corrects" it.
    layer = "‘Tk snap het niet,’ zei Charlie.’ Waarom doe je dit?’"
    checked = "‘Ik snap het niet,’ zei Charlie.’ Waarom doe je dit?’"
    found = readings(
        layer, checked, "‘Ik snap het niet,’ zei Charlie. ‘Waarom doe je dit?’", "…", True
    )
    assert found["OCR check"] == checked
    assert found["scan reading"] == "‘Ik snap het niet,’ zei Charlie. ‘Waarom doe je dit?’"
    assert "marks combined" not in found
    # A quotation inside dialogue: the layer lost the outer ’, the reader read “ as ‘.
    line = "valboek voorgelezen. ‘“Maar dan moet het gevonden worden.”"
    read = "valboek voorgelezen. ‘‘Maar dan moet het gevonden worden.’’"
    found = readings(line, line, read, "…", True)
    assert found["marks combined"] == "valboek voorgelezen. ‘“Maar dan moet het gevonden worden.”’"
    # The layer read the outer ‘ as “.
    line = "had Charlie gelezen. ““Wanneer je tot stilstand komt"
    found = readings(line, line, "had Charlie gelezen. “Wanneer je tot stilstand komt", "…", True)
    assert found["marks combined"] == "had Charlie gelezen. ‘“Wanneer je tot stilstand komt"


def test_a_quotation_closed_on_a_letter_at_a_paragraphs_end_lost_its_stop():
    # Not a lost stop: a short quoted term or title, punctuation before the mark, a
    # plural possessive, a closing mark mid-paragraph.
    assert problems("Ik vrees vooral het ‘invoelend’") == []
    assert problems("Hij las ‘Le mie prigioni’") == []
    assert problems("‘Alsjeblieft, Frederik.’") == []
    assert problems("‘Waar was je?’") == []
    assert problems("Dat waren de schoenen van Jezus’") == []
    assert problems("‘Kom mee,’ zei hij. Ze kwam") == []
    # A dialogue's last word right before its closing mark: the print's kerned stop.
    assert problems("‘Alsjeblieft, Frederik’") == [(22, "no stop at end")]
    assert problems("Hij keek op. ‘Vermoord door de CT’") == [(33, "no stop at end")]
    assert problems("“Then you turn it on, Ew”") == [(24, "no stop at end")]


def test_an_open_mark_after_a_word_is_asked_where_it_stands():
    text = "Als ‘het nog geen moordzaak is, wordt het een zaak voor de wijkagent."
    assert problems(text) == [(4, "no closing")]
    # Speech opened after a comma or a colon lost its closing mark at the end.
    assert problems("Hij zei: ‘Kom hier.") == [(18, "open at end")]
    assert problems("Toen zei ze, ‘Ga weg.") == [(20, "open at end")]


def test_a_straight_mark_that_says_neither_way_stays_straight():
    # A foot and an inch, a decade's apostrophe kept as such, a mark spaced on both sides.
    assert quotes.curled("hij was 6' 2\" lang") == "hij was 6' 2\" lang"
    assert quotes.curled("een ' los teken") == "een ' los teken"
    # Elisions opening a word are apostrophes, not opening quotes.
    assert quotes.curled("'s Morgens zag hij 't huis") == "’s Morgens zag hij ’t huis"
    assert quotes.curled("give 'em hell, back in the '60s") == "give ’em hell, back in the ’60s"
    assert quotes.curled("'Tis true") == "’Tis true"
    # Speech broken off by a dash closes after it.
    assert quotes.curled("van een minderjarige –'") == "van een minderjarige –’"
    assert quotes.curled('he said—" and stopped') == "he said—” and stopped"


def test_straight_quotes_and_apostrophes_curl_by_their_place():
    assert quotes.curled("'Kom je?' vroeg ze. 'Zo'n dag!'") == "‘Kom je?’ vroeg ze. ‘Zo’n dag!’"
    assert quotes.curled("\"Who said 'no'?\" he asked.") == "“Who said ‘no’?” he asked."
    assert quotes.curled('the animals\' language ("so")') == "the animals’ language (“so”)"
    assert quotes.curled('"Ja," zei ze', opening="„") == "„Ja,” zei ze"
    assert quotes.curled("—'Nee'") == "—‘Nee’"


def test_a_book_curls_its_straight_quotes_as_it_opens_its_own():
    from roboscriptorium.ir import Heading, Paragraph

    blocks = [
        Paragraph("„Ja,” zei ze.", []),
        Paragraph('"Nee," zei hij, \'t was laat.', []),
        Heading("'Titel'", [], ["'Titel'"]),
    ]
    out = quotes.curl(blocks)
    assert out[1].text == "„Nee,” zei hij, ’t was laat."
    assert out[2] is blocks[2]  # headings keep what the reviewer or the layer gave
    assert blocks[1].text.startswith('"')  # the input is left alone


def test_a_quote_open_at_the_end_is_closed_where_the_reading_adds_only_that_mark():
    from roboscriptorium.ir import Paragraph, SourceRef
    from roboscriptorium.quotes import closed_at_end

    end = SourceRef(50, 4)
    lines = {end: "erg, ze zingen."}
    p = Paragraph("Ik schreef: ‘Het is erg, ze zingen.", [SourceRef(50, 3), end])
    out, settled = closed_at_end([p], {end: {"checked": "erg, ze zingen.’"}}, lines)
    assert out[0].text == "Ik schreef: ‘Het is erg, ze zingen.’" and settled == {end}
    assert p.text.endswith("zingen.")
    # The last line starts mid-word: compared as the line, closed as the paragraph.
    split = Paragraph("‘Ik hoor echo’s van lang geleden.", [SourceRef(51, 0), SourceRef(51, 1)])
    out, _ = closed_at_end([split], {SourceRef(51, 1): {"checked": "den.’"}},
                           {SourceRef(51, 1): "den."})  # fmt: skip
    assert out[0].text.endswith("geleden.’")
    # Other words in the reading, a mark that pairs with no open one, or another quote
    # problem in the paragraph: left as a question.
    for reading, text in [
        ("erg, ze zongen.’", p.text),
        ("erg, ze zingen.”", p.text),
        ("erg, ze zingen.’", "Hij zei’ ik: ‘Het is erg, ze zingen."),
    ]:
        q = Paragraph(text, [SourceRef(50, 3), end])
        assert closed_at_end([q], {end: {"checked": reading}}, lines) == ([q], set())


def test_a_quote_cards_reading_takes_its_lines_curly_marks():
    checked = "“They’ll see it,” she said. “They won’t even notice.” ."
    reading = 'They\'ll see it," she said. "They won\'t even notice."'
    found = quotes.readings(checked, checked, reading, "...", False)
    assert all('"' not in t and "'" not in t for t in found.values())


def _lines(*texts: str) -> tuple[Paragraph, dict[SourceRef, str]]:
    refs = [SourceRef(1, i) for i in range(len(texts))]
    return Paragraph(" ".join(texts), refs), dict(zip(refs, texts, strict=True))


def test_a_paired_paragraph_gives_the_ocr_check_no_reading():
    p, lines = _lines("‘The animals’ language is hard,’ he said,", "and it’s late in the ’80s.")
    assert quotes.duel_readings([p], lines) == {quotes.READER: {}, quotes.OPENED: {}}


def test_a_quote_open_at_the_end_reads_its_last_line_closed_in_its_own_mark():
    p, lines = _lines("He said: “It goes on", "and on.")
    found = quotes.duel_readings([p], lines)
    assert found == {quotes.READER: {SourceRef(1, 1): "and on.”"}, quotes.OPENED: {}}


def test_speech_closed_on_a_letter_reads_with_a_stop_before_the_mark():
    p, lines = _lines("He looked up. ‘It goes on and", "on and on’")
    assert quotes.duel_readings([p], lines)[quotes.READER] == {SourceRef(1, 1): "on and on.’"}


def test_a_closing_mark_with_nothing_open_reads_as_a_speck_or_as_a_lost_opening():
    p, lines = _lines("It goes on, he said,", "and on.’ And that", "was that.")
    found = quotes.duel_readings([p], lines)
    assert found[quotes.READER] == {SourceRef(1, 1): "and on. And that"}
    assert found[quotes.OPENED] == {SourceRef(1, 0): "‘It goes on, he said,"}


def test_the_second_unpaired_mark_of_a_line_is_the_one_taken_out():
    p, lines = _lines("‘Yes,’ he said. And on.’ So it", "went.")
    assert quotes.duel_readings([p], lines)[quotes.READER] == {
        SourceRef(1, 0): "‘Yes,’ he said. And on. So it"
    }


def test_a_mark_whose_line_cant_be_told_gives_no_reading():
    p, lines = _lines("It goes on, he said,", "and on.’ And that")
    # The paragraph's text holds a mark its lines don't (a line joined otherwise).
    lines[SourceRef(1, 1)] = "and on. And that"
    assert quotes.duel_readings([p], lines) == {quotes.READER: {}, quotes.OPENED: {}}


def test_a_mark_opening_a_word_is_no_speck_and_no_quotations_end():
    p, lines = _lines("He came ’cross the field", "and went home.")
    assert quotes.problems(p.text)
    assert quotes.duel_readings([p], lines) == {quotes.READER: {}, quotes.OPENED: {}}


def test_a_paragraph_opening_on_a_mark_is_not_opened_again():
    p, lines = _lines("‘Yes,’ he said. And on.’ So it", "went.")
    assert quotes.duel_readings([p], lines)[quotes.OPENED] == {}
