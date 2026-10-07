from roboscriptorium.ir import Paragraph, SourceRef
from roboscriptorium.quotes import problems, unbalanced


def test_apostrophes_need_no_partner():
    assert problems("‘Zo’n auto’s, zei hij, om zes uur ’s avonds.’") == []
    assert problems("‘Ik kom ’t halen.’") == []
    # The layer's ‘ for the article ’s, and a straight one, are apostrophes too.
    assert problems("Om zes uur ‘s avonds en 's morgens.") == []


def test_a_plural_possessive_needs_no_partner():
    assert problems("He spoke the animals’ language, as in Jezus’ tijd.") == []


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
