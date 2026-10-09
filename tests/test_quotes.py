from roboscriptorium.ir import Paragraph, SourceRef
from roboscriptorium.quotes import problems, unbalanced


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
    assert problems("‘Hij zei ja tegen Jans’ en ging.", continued="H") == []


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


def test_a_quote_running_on_into_the_next_paragraph_is_open_at_its_end():
    assert problems("‘Het begon in Boedapest.", continued="‘") == []
    assert problems("‘Het begon in Boedapest.", continued="H") == [(23, "open at end")]


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
