from roboscriptorium import quotes
from roboscriptorium.ir import Paragraph, SourceRef
from roboscriptorium.quotes import problems, unbalanced


def test_a_flemish_elision_or_a_year_needs_no_partner():
    assert problems("‘Ken ik ’m?’ vroeg ik, en ’k zei: ‘Uit ’73.’") == []
    assert problems("Ik schopte ’m tegen z’n kop.") == []


def test_an_elision_read_with_an_opening_mark_is_still_asked():
    # The print sets ’m; the layer's ‘ is its error, and the question catches it.
    assert problems("Ik zei ‘m dat ik veel geld had.") != []


def test_apostrophes_need_no_partner():
    assert problems("‘Zo’n auto’s, zei hij, om zes uur ’s avonds.’") == []
    assert problems("‘Ik kom ’t halen.’") == []
    # The layer's ‘ for the article ’s, and a straight one, are apostrophes too.
    assert problems("Om zes uur ‘s avonds en 's morgens.") == []


def test_a_plural_possessive_needs_no_partner():
    assert problems("He spoke the animals’ language, as in Jezus’ tijd.") == []


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
