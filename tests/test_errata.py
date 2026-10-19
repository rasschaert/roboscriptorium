import pytest

from roboscriptorium import errata
from roboscriptorium.errata import Erratum
from roboscriptorium.ir import Heading, Paragraph, SourceRef


def _para(text: str, *pages: int) -> Paragraph:
    return Paragraph(text, [SourceRef(p, 0) for p in pages])


def test_an_erratum_on_a_page_outside_the_build_is_left_alone():
    blocks = [_para("zeI ik", 3)]
    assert errata.apply([Erratum(94, "zeI", "zei")], blocks, {3}) == blocks


def test_the_same_words_on_another_page_dont_count():
    blocks = [_para("zeI ik", 3), _para("zeI hij", 4)]
    out = errata.apply([Erratum(4, "zeI", "zei")], blocks, {3, 4})
    assert [b.text for b in out] == ["zeI ik", "zei hij"]


def test_a_paragraph_across_a_page_turn_counts_on_both_pages():
    out = errata.apply([Erratum(5, "zeI", "zei")], [_para("ja, zeI ik", 4, 5)], {4, 5})
    assert out[0].text == "ja, zei ik"


def test_quote_glyphs_match_either_way_and_the_rest_of_the_text_keeps_its_own():
    out = errata.apply([Erratum(1, "zo,' zeI", "zo,’ zei")], [_para("‘Ach zo,’ zeI ik", 1)], {1})
    assert out[0].text == "‘Ach zo,’ zei ik"


def test_a_heading_takes_an_erratum_too():
    out = errata.apply(
        [Erratum(1, "HOOFSTUK", "HOOFDSTUK")], [Heading("HOOFSTUK", [SourceRef(1, 0)])], {1}
    )
    assert out[0].text == "HOOFDSTUK"


def test_words_twice_on_their_page_or_not_at_all_stop_the_build():
    blocks = [_para("zeI ik en zeI hij", 1)]
    with pytest.raises(errata.Unmatched, match="2 times"):
        errata.apply([Erratum(1, "zeI", "zei")], blocks, {1})
    with pytest.raises(errata.Unmatched, match="0 times"):
        errata.apply([Erratum(1, "zij", "zei")], blocks, {1})


def test_the_file_round_trips_quotes_and_backslashes(tmp_path):
    e = Erratum(7, 'een "rare\\" zeI', "een ‘rare’ zei")
    errata.save(tmp_path, e)
    errata.save(tmp_path, Erratum(8, "a", "b"))
    assert errata.load(tmp_path) == [e, Erratum(8, "a", "b")]
    assert errata.load(tmp_path / "nowhere") == []


def test_an_erratum_whose_reading_already_stands_is_met_not_unmatched():
    blocks = [_para("Kelly’s gezicht. ‘Ze is", 5)]
    assert errata.apply([Erratum(5, "gezicht . ‘Ze", "gezicht. ‘Ze")], blocks, {5}) == blocks


def test_an_erratum_matching_neither_form_still_stops_the_build():
    with pytest.raises(errata.Unmatched):
        errata.apply([Erratum(5, "gezicht . ‘Ze", "gezicht. ‘Ze")], [_para("iets anders", 5)], {5})


def test_an_entry_that_carries_words_from_another_line_is_not_local():
    assert errata.local(Erratum(1, "zeI ik", "zei ik"))
    assert not errata.local(
        Erratum(87, "inspanningen -twee", "– na eeuwen van vergeefse inspanningen – twee")
    )
