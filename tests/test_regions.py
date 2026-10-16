from roboscriptorium import corrections, flags
from roboscriptorium.corrections import Corrections
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole


def _page(number: int = 1) -> PageText:
    lines = [Line("body text " * 5, 50, 80 + 15 * i, 350, 92 + 15 * i) for i in range(10)]
    lines[5] = Line("G.J. Sorgdrager * 1919", 150, 155, 250, 167)
    return PageText(number, 400, 600, lines)


def test_flags_a_dropped_inscription_and_centred_lines():
    page = _page()
    roles = {SourceRef(1, 5): LineRole("artifact", 0.5, 0.3)}
    found = flags.find([page], roles)
    assert [(f.first, f.treatment) for f in found] == [(5, "dropped")]
    assert set(found[0].reasons) == {"dropped-mid-page", "dropped-unsure"}


def test_answers_apply_and_go_stale_when_the_text_layer_changes(tmp_path):
    page = _page()
    roles = {SourceRef(1, 5): LineRole("artifact", 0.5, 0.3)}
    region = flags.find([page], roles)[0]
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(region, "text", "G.J. Sorgdrager * 13.6.1919")

    fixed, fixed_roles, applied = corrections.apply(
        [page], roles, Corrections(tmp_path / "regions.jsonl")
    )
    assert applied == 1
    assert fixed_roles[SourceRef(1, 5)].role == "body"
    assert fixed[0].lines[5].text == "G.J. Sorgdrager * 13.6.1919"
    # The text layer itself is left as it was: the review keys its answers on it.
    assert page.lines[5].text == "G.J. Sorgdrager * 1919"
    assert roles[SourceRef(1, 5)].role == "artifact"
    assert [f.key for f in flags.find([page], roles)] == [region.key]

    changed = _page()
    changed.lines[5] = Line("G.J. Sorgdrager", 150, 155, 250, 167)
    assert corrections.apply([changed], {}, answers)[2] == 0


def test_text_typed_for_a_missing_region_is_inserted_with_its_paragraphs(tmp_path):
    from roboscriptorium.reflow import reflow

    page = _page()
    roles: dict = {}
    region = flags.Flag("p1-x", 1, 3, 2, "", "missing", ["missing-text"], (50, 125, 350, 150))
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(region, "text", "First para-\ngraph wraps here.\n\nSecond one.")
    fixed, fixed_roles, applied = corrections.apply([page], roles, answers)
    assert applied == 1
    assert [ln.text for ln in fixed[0].lines[3:5]] == ["First paragraph wraps here.", "Second one."]
    # Lines below the insertion keep pointing at their text-layer lines.
    assert [ln.source for ln in fixed[0].lines[2:7]] == [2, 3, 3, 3, 4]
    blocks = reflow(fixed, fixed_roles)
    texts = [b.text for b in blocks]
    assert any(t.endswith("First paragraph wraps here.") for t in texts)
    assert any(t.startswith("Second one.") for t in texts)
    assert max(s.line for b in blocks for s in b.sources) == len(page.lines) - 1
    assert len(page.lines) == 10


def test_a_retyped_line_keeps_its_text_layer_identity_below_an_insertion(tmp_path):
    page = _page()
    roles = {SourceRef(1, 5): LineRole("artifact", 0.5, 0.3)}
    retyped = flags.find([page], roles)[0]
    missing = flags.Flag("p1-x", 1, 3, 2, "", "missing", ["missing-text"], (50, 125, 350, 150))
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(retyped, "text", "G.J. Sorgdrager * 13.6.1919")
    answers.record(missing, "text", "An inserted line.")
    fixed, _, applied = corrections.apply([page], roles, answers)
    assert applied == 2
    line = next(ln for ln in fixed[0].lines if ln.text.startswith("G.J."))
    assert fixed[0].lines.index(line) == 6
    assert line.source == 5


def test_a_drawn_initial_goes_back_in_front_of_its_word(tmp_path):
    from roboscriptorium.epub import _block
    from roboscriptorium.reflow import reflow

    lines = [
        Line("NCE upon a time", 110, 80, 350, 92),
        Line("there was a doctor", 110, 95, 350, 107),
    ]
    lines += [Line("body text " * 5, 50, 110 + 15 * i, 350, 122 + 15 * i) for i in range(8)]
    page = PageText(1, 400, 600, lines)
    picture = flags.Flag("p1-o", 1, 0, -1, "", "missing", ["picture"], (50, 78, 105, 110))
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(picture, "initial", "O")
    fixed, fixed_roles, applied = corrections.apply([page], {}, answers)
    assert applied == 1
    first = reflow(fixed, fixed_roles)[0]
    assert first.text.startswith("ONCE upon a time there was")
    assert first.initial
    assert _block(first).startswith('<p class="opening"><span class="initial">O</span>NCE')


def test_sideways_caption_becomes_one_region():
    scraps = ["o", "s", "c", ".6", "<u", "(ft", "o", "I-o"]
    lines = [Line(s, 241, 164 + 14 * i, 245, 173 + 14 * i) for i, s in enumerate(scraps)]
    page = PageText(25, 319, 493, lines)
    found = flags.find([page], {})
    assert [(f.first, f.last, f.reasons) for f in found] == [(0, 7, ["rotated"])]
    assert found[0].box[1] < 164 and found[0].box[3] > 271


def test_turned_caption_is_one_region_and_the_scraps_over_the_picture_are_not_judged():
    from roboscriptorium.layout import Region

    scraps = ["W", "a", "~", "n", "e", "o", "r"]
    lines = [
        Line(s, 20 + 30 * i, 100 + 40 * i, 26 + 30 * i, 109 + 40 * i) for i, s in enumerate(scraps)
    ]
    lines.append(Line("an", 280, 200, 290, 210))
    page = PageText(83, 319, 493, lines)
    layout = {
        83: [
            Region("figure", 0.9, 10, 20, 270, 470),
            Region("figure_caption", 0.8, 275, 30, 300, 460, turned=True),
        ]
    }
    found = flags.find([page], {}, layout)
    assert [(f.first, f.last, f.reasons) for f in found] == [
        (0, 6, ["picture"]),
        (7, 7, ["rotated"]),
    ]


def test_sideways_regions_are_mapped_back_onto_the_upright_page():
    from roboscriptorium.layout import _unturn

    # A 100×200 page: a strip down its right edge is a strip along the bottom turned 90°.
    assert _unturn([10, 80, 190, 100], 90, 100, 200) == (80, 10, 100, 190)
    assert _unturn([10, 0, 190, 20], 270, 100, 200) == (80, 10, 100, 190)


def test_initial_candidates_come_from_the_word_it_begins():
    from roboscriptorium import initials

    vocab = {"once", "nce", "that", "what", "chat"}
    assert initials.candidates(initials.fragment("NCE upon a time"), vocab) == ["O"]
    assert initials.candidates(initials.fragment("HAT Winter"), vocab) == ["C", "T", "W"]


def test_a_caption_stays_out_of_the_text_and_keeps_its_turn(tmp_path):
    page = _page()
    roles: dict = {}
    sideways = flags.Flag("p1-c", 1, 0, -1, "", "missing", ["rotated"], (360, 80, 380, 400))
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(sideways, "caption", "“And the voyage began”", turn=270)

    reread = Corrections(tmp_path / "regions.jsonl")
    assert reread.by_key["p1-c"].turn == 270
    fixed, _, applied = corrections.apply([page], roles, reread)
    assert applied == 1
    assert len(fixed[0].lines) == 10


def test_a_dropped_speck_is_not_flagged():
    page = _page()
    page.lines.insert(3, Line("1", 258, 78, 260, 81))
    roles = {SourceRef(1, 3): LineRole("artifact", 0.6, 0.2)}
    assert 3 not in [f.first for f in flags.find([page], roles)]


def test_an_answer_that_matches_no_reading_is_queried_once_then_saved(tmp_path):
    from roboscriptorium import review

    page = _page()
    doubt = flags.Flag(
        "k1", 1, 2, 2, "De sheriff stuurt een patrouillewagen, zei ze.", "text", ["ocr-doubt"],
        readings=[
            {"text": "De sheriff stuurt een patrouillewagen, zei ze.", "votes": []},
            {"text": "De sheriff stuurt een patrouillewagen,’ zei ze.", "votes": ["a"]},
        ],
        span=(22, 39),
    )  # fmt: skip
    answers = Corrections(tmp_path / "review" / "regions.jsonl")
    page_review = review.RegionReview(
        tmp_path / "none.pdf", [page], [doubt], answers, lambda: ([page], [doubt], 0), "nld"
    )
    # A reading chosen as it is saves at once.
    saved = page_review.record({"key": "k1", "action": "text", "text": doubt.readings[1]["text"]})
    assert saved["text"] == doubt.readings[1]["text"]
    # A typed line that matches none of the readings is queried, not saved …
    typed = "De sheriff stuurt een patrouilewagen,’ zei ze."
    out = page_review.record({"key": "k1", "action": "text", "text": typed})
    assert "none of the readings" in out["warning"]
    assert answers.for_flag(doubt).text == doubt.readings[1]["text"]
    assert "patrouilewagen" in (tmp_path / "review" / "warnings.jsonl").read_text()
    # … and saved when the reviewer confirms it.
    out = page_review.record({"key": "k1", "action": "text", "text": typed, "confirm": True})
    assert out["text"] == typed
    # A straight quote in a book set with curly ones is a slip, whatever the readings.
    straight = "De sheriff stuurt een patrouillewagen,' zei ze."
    assert (
        "straight quote"
        in page_review.record({"key": "k1", "action": "text", "text": straight})["warning"]
    )
    # Spacing and quote glyphs alone don't make a typed line a stranger.
    spaced = "De sheriff  stuurt een patrouillewagen,’ zei ze. "
    assert "warning" not in page_review.record({"key": "k1", "action": "text", "text": spaced})
    # Dropping the region carries no text to check.
    assert "warning" not in page_review.record({"key": "k1", "action": "drop", "text": None})


def test_a_washed_out_page_is_one_region_and_nothing_on_it_is_asked_apart():
    roles = {SourceRef(n, 5): LineRole("artifact", 0.5, 0.3) for n in (1, 2)}
    found = flags.find([_page(1), _page(2)], roles, faint={1})
    assert [(f.page, f.first, f.last, f.reasons) for f in found] == [
        (1, 0, 9, ["washed-out"]),
        (2, 5, 5, ["dropped-mid-page", "dropped-unsure"]),
    ]
    assert found[0].box == (0.0, 0.0, 400, 600) and found[0].treatment == "text"


def _gapped(above: str, picture: bool = False):
    """Ten running-text lines with a line's worth of white space after line 4."""
    lines = []
    for i in range(10):
        y = 80 + 15 * i + (15 if i >= 5 else 0)
        lines.append(Line(above if i == 4 else "en zo verder in de tekst", 50, y, 350, y + 12))
    regions = {1: [flags.Region("figure", 0.9, 50, 155, 350, 168)]} if picture else None
    return PageText(1, 400, 600, lines), regions


def test_white_space_inside_a_sentence_is_a_lost_line():
    page, _ = _gapped("Haar intonatie geeft de woorden een andere be-")
    found = flags.find([page], {})
    assert [(f.first, f.last, f.reasons) for f in found] == [(5, 4, ["lost-line"])]


def test_white_space_after_a_sentence_or_around_a_picture_is_no_lost_line():
    page, _ = _gapped("en toen was het stil.")
    assert flags.find([page], {}) == []
    page, _ = _gapped("en toen liep hij naar de")
    page.lines[5] = Line("*_Een voetnoot onder de tekst", 50, 170, 350, 182)
    assert flags.find([page], {}) == []
    page, regions = _gapped("en toen liep hij naar de", picture=True)
    assert [f.reasons for f in flags.find([page], {}, regions)] == [["picture"]]


def test_verse_with_white_space_between_its_stanzas_is_no_lost_line():
    # Short lines stopping mid-sentence, white space between them: a song, not a gap.
    verse = ["Ik vertel geen", "herinneringen", "En bij het tellen", "van je ogen",
             "En dat je nu pas", "huilt", "Dat kan ik je", "eindelijk vergeven"]  # fmt: skip
    # Stanzas of two lines 15 apart, a blank line between them.
    ys = [80 + 15 * i + 15 * (i // 2) for i in range(len(verse))]
    lines = [Line(t, 50, y, 50 + 9 * len(t), y + 12) for t, y in zip(verse, ys, strict=True)]
    assert flags.find([PageText(1, 400, 600, lines)], {}) == []
    # A short line inside prose isn't one either: a mid-sentence line there is full.
    page, _ = _gapped("en toen liep hij naar de")
    page.lines[4] = Line("en toen liep hij naar de", 50, 140, 220, 152)
    assert flags.find([page], {}) == []


def test_a_section_opening_in_lower_case_asks_for_its_drawn_initial():
    lines = [
        Line("HOOFDSTUK 9", 150, 60, 250, 75),
        Line("et wolvenschip had duidelijk problemen.", 50, 100, 350, 112),
        Line("het zeil hing slap en de roeiers waren moe.", 50, 115, 350, 127),
        Line("Het water was koud.", 50, 130, 350, 142),
    ]
    page = PageText(79, 400, 600, lines)
    heading = {SourceRef(79, 0): LineRole("chapter_heading", 0.9, 0.05)}

    def lost(roles):
        return [f.first for f in flags.find([page], roles) if "initial-lost" in f.reasons]

    # Lower case mid-section, or text below no heading, is no lost initial.
    assert lost({}) == []
    capital = PageText(79, 400, 600, [lines[0], lines[3], lines[2]])
    assert [f for f in flags.find([capital], heading) if "initial-lost" in f.reasons] == []
    # A dropped speck between the heading and the text doesn't hide it.
    speck = PageText(79, 400, 600, [lines[0], Line("~", 200, 85, 205, 90), *lines[1:]])
    speck_roles = heading | {SourceRef(79, 1): LineRole("artifact", 0.9, 0.01)}
    assert [f.first for f in flags.find([speck], speck_roles) if "initial-lost" in f.reasons] == [2]
    assert lost(heading) == [1]
    # A section opening on a word set in capitals: its first letter may be the drawing.
    caps = PageText(79, 400, 600, [lines[0], Line("HAT was the end of it.", 50, 100, 350, 112)])
    assert [f.first for f in flags.find([caps], heading) if "initial-lost" in f.reasons] == [1]
    # A single capital ("I") or a numeral is no such word.
    for opening in ("I was there.", "1914 was a year."):
        page_i = PageText(79, 400, 600, [lines[0], Line(opening, 50, 100, 350, 112)])
        assert [f for f in flags.find([page_i], heading) if "initial-lost" in f.reasons] == []


def test_an_epigraph_is_not_asked_what_it_is():
    motto = PageText(
        7,
        300,
        500,
        [
            Line("‘It’s closing time’", 104, 100, 172, 112),
            Line("(Leonard Cohen, The Future)", 80, 116, 195, 128),
        ],
    )
    body = {SourceRef(7, i): LineRole("body", 0.98, 0.98) for i in range(2)}
    quoted = {SourceRef(7, 0)}
    assert flags.find([motto], body, quotes=quoted)
    assert flags.find([motto], body, quotes=quoted, epigraph=set(body)) == []


def test_an_epigraph_line_with_another_doubt_is_still_asked():
    lines = [Line("nQthiri£,\\and", 120, 100, 170, 112), Line("De |", 118, 116, 140, 128)]
    noise = PageText(58, 300, 500, lines)
    roles = {SourceRef(58, i): LineRole("body", 0.9, 0.9) for i in range(2)}
    found = flags.find([noise], roles, epigraph=set(roles))
    assert any("garbled" in f.reasons for f in found)


def test_a_misprint_keeps_the_answer_as_printed_and_writes_the_edition_line_to_the_errata(
    tmp_path,
):
    from roboscriptorium import errata, review

    page = _page()
    page.lines[2] = Line("‘Ach zo,’ zeI ik, ‘welk soort?’", 50, 110, 350, 122)
    page.lines[7] = Line("en toen zeI hij niets", 50, 185, 350, 197)
    printed = page.lines[2].text
    doubt = flags.Flag(
        "k1", 1, 2, 2, "‘Ach zo,’ zel ik, ‘welk soort?’", "text", ["ocr-doubt"],
        readings=[{"text": "‘Ach zo,’ zel ik, ‘welk soort?’", "votes": []},
                  {"text": printed, "votes": ["glm-ocr"]}],
    )  # fmt: skip
    answers = Corrections(tmp_path / "review" / "regions.jsonl")
    page_review = review.RegionReview(
        tmp_path / "none.pdf",
        [page],
        [doubt],
        answers,
        lambda: ([page], [doubt], 0),
        "nld",
        book_root=tmp_path,
    )
    fix = "‘Ach zo,’ zei ik, ‘welk soort?’"
    saved = page_review.record({"key": "k1", "action": "text", "text": printed, "misprint": fix})
    assert saved["text"] == printed  # the readers are scored on what the page prints
    # "zeI" is printed twice on the page: the erratum takes the word after it too.
    assert errata.load(tmp_path) == [errata.Erratum(1, "zeI ik,", "zei ik,")]
    assert page_review.state()["items"][0]["errata"] == [
        {"page": 1, "printed": "zeI ik,", "reads": "zei ik,"}
    ]
    # Answered again with another correction, the erratum is replaced, not added to.
    page_review.record(
        {"key": "k1", "action": "text", "text": printed, "misprint": fix.replace("zei", "zei,")}
    )
    assert errata.load(tmp_path) == [errata.Erratum(1, "zeI ik,", "zei, ik,")]
    # A "misprint" that changes nothing is refused, and so the answer isn't saved either.
    out = page_review.record({"key": "k1", "action": "text", "text": printed, "misprint": printed})
    assert out["refused"]
