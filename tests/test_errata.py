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


def test_a_hyphen_an_en_dash_and_an_em_dash_match_either_way():
    for built in ("-twee maanden", "–twee maanden", "—twee maanden"):
        out = errata.apply(
            [Erratum(1, "–twee maanden", "– twee maanden")], [_para(f"ja {built} eerder", 1)], {1}
        )
        assert out[0].text == "ja – twee maanden eerder"


def test_words_that_differ_in_more_than_a_dash_still_stop_the_build():
    with pytest.raises(errata.Unmatched, match="0 times"):
        errata.apply([Erratum(1, "–twee maanden", "– twee")], [_para("ja twee maanden", 1)], {1})


def test_a_heading_takes_an_erratum_too():
    out = errata.apply(
        [Erratum(1, "HOOFSTUK", "HOOFDSTUK")], [Heading("HOOFSTUK", [SourceRef(1, 0)])], {1}
    )
    assert out[0].text == "HOOFDSTUK"
    # The EPUB sets a heading's parts: the erratum lands in the part that holds it.
    lines = Heading("HOOFSTUK 3 De zee", [SourceRef(1, 0)], ["HOOFSTUK 3", "De zee"])
    out = errata.apply([Erratum(1, "HOOFSTUK", "HOOFDSTUK")], [lines], {1})
    assert out[0].parts == ["HOOFDSTUK 3", "De zee"]
    # Printed words across two parts: the mended text as one part.
    out = errata.apply([Erratum(1, "3 De", "3: De")], [lines], {1})
    assert out[0].parts == ["HOOFSTUK 3: De zee"]


def test_words_twice_on_their_page_or_not_at_all_stop_the_build():
    blocks = [_para("zeI ik en zeI hij", 1)]
    with pytest.raises(errata.Unmatched, match="2 times"):
        errata.apply([Erratum(1, "zeI", "zei")], blocks, {1})
    with pytest.raises(errata.Unmatched, match="0 times"):
        errata.apply([Erratum(1, "zij", "zei")], blocks, {1})


def test_a_golden_books_build_leaves_out_an_erratum_its_page_lacks_but_not_one_twice():
    blocks = [_para("zeI ik en zeI hij", 1)]
    assert errata.apply([Erratum(1, "zij", "zei")], blocks, {1}, missing_ok=True) == blocks
    with pytest.raises(errata.Unmatched, match="2 times"):
        errata.apply([Erratum(1, "zeI", "zei")], blocks, {1}, missing_ok=True)


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


def test_a_wording_that_reaches_beyond_the_layer_line_is_compared_on_the_shared_stretch_only():
    layer = ["Kelly’s", "gezicht . ‘Ze is goddomme nog erger dan haar pa.’"]
    wording = "man met zijn voet tegen Kelly’s gezicht. ‘Ze is goddomme nog erger dan"
    assert errata.from_layer(69, layer[1], wording, layer, 1) == Erratum(
        69, "gezicht .", "gezicht."
    )


def test_an_edition_slip_kept_as_printed_leaves_the_build_and_round_trips(tmp_path):
    slip = Erratum(53, "HOOFDSTUK 6", "HOOFDSTUK 5", errata.PRINT, 6)
    errata.save(tmp_path, slip)
    errata.save(tmp_path, Erratum(8, "zeI", "zei"))
    assert errata.load(tmp_path) == [slip, Erratum(8, "zeI", "zei")]
    heading = Heading("HOOFDSTUK 6", [SourceRef(53, 0)], ["HOOFDSTUK 6"])
    # The build keeps the print: nothing to apply, nothing unmatched.
    assert errata.apply([slip], [heading], {53}) == [heading]
    # An edition erratum on the same heading still changes it.
    edition = Erratum(53, "HOOFDSTUK 6", "HOOFDSTUK 5")
    assert errata.apply([edition], [heading], {53})[0].parts == ["HOOFDSTUK 5"]


def test_the_reference_is_set_back_as_printed_in_a_heading_placed_by_its_chapter():
    from roboscriptorium.golden.reference import Chapter

    reference = [
        Chapter("HOOFDSTUK 4", ["Vier."]),
        Chapter("HOOFDSTUK 5", ["Vijf."]),
        Chapter("HOOFDSTUK 5", ["Zes."]),
    ]
    slip = Erratum(53, "HOOFDSTUK 6", "HOOFDSTUK 5", errata.PRINT, 3)
    printed = errata.as_printed(reference, [slip])
    assert [c.heading for c in printed] == ["HOOFDSTUK 4", "HOOFDSTUK 5", "HOOFDSTUK 6"]
    assert reference[2].heading == "HOOFDSTUK 5"  # the reference itself is untouched
    # Twice in the reference and no chapter named: left out.
    unplaced = Erratum(53, "HOOFDSTUK 6", "HOOFDSTUK 5", errata.PRINT)
    assert [c.heading for c in errata.as_printed(reference, [unplaced])][2] == "HOOFDSTUK 5"
    # Only the errata kept as printed are scored as printed.
    assert errata.printed_only([slip, Erratum(8, "zeI", "zei")]) == [slip]
