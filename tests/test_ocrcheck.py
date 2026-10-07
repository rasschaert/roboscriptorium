from roboscriptorium import flags, ocrcheck, pdf
from roboscriptorium.ocrcheck import Suspect, differences
from roboscriptorium.pdf import Line, PageText


def _spans(ours: str, theirs: str) -> list[tuple[str, str]]:
    return [(ours[a0:a1], theirs[b0:b1]) for a0, a1, b0, b1 in differences(ours, theirs)]


def test_differences_are_whole_words():
    assert _spans("up if they come", "up—if they come") == [("up if", "up—if")]
    assert _spans("say, Tolly wants", "say, ‘Polly wants") == [("Tolly", "‘Polly")]


def test_quote_style_and_opening_quotes_alone_are_not_differences():
    assert _spans('"What is it?" he said', "“What is it?” he said") == []
    assert _spans('"Now listen to me', "‘Now listen to me") == []
    assert _spans("fee-fee?' said", "fee-fee?” said") == [("fee-fee?'", "fee-fee?”")]


def _page() -> PageText:
    lines = [
        Line("he was so tired up if they come", 10, 10, 200, 20),
        Line("other", 10, 30, 50, 40),
    ]
    return PageText(7, 300, 400, lines)


def _suspect(choice: str) -> Suspect:
    chosen = "up—if" if choice == "other" else None
    original = "he was so tired up if they come"
    votes = {"clef:27b": "up if", "winnow:e4b": "up—if"}
    return Suspect(7, 0, original, 16, 21, "up if", ("up—if",), (0, 0, 1, 1), choice, chosen, votes)


def test_fixes_go_into_a_copy_and_only_onto_unchanged_lines():
    page = _page()
    fixed = ocrcheck.apply([page], [_suspect("other")])
    assert fixed[0].lines[0].text == "he was so tired up—if they come"
    assert page.lines[0].text == "he was so tired up if they come"
    page.lines[0] = Line("typed by a human", 10, 10, 200, 20)
    assert ocrcheck.apply([page], [_suspect("other")])[0].lines[0].text == "typed by a human"


def test_doubted_lines_are_flagged_with_their_other_reading():
    page = _page()
    found = flags.find([page], {}, None, ocrcheck.doubts([_suspect("review")]))
    assert [(f.first, f.reasons) for f in found] == [(0, ["ocr-doubt"])]
    assert found[0].readings == [
        {"text": "he was so tired up if they come", "votes": ["clef:27b"]},
        {"text": "he was so tired up—if they come", "votes": ["winnow:e4b"]},
    ]
    assert ocrcheck.doubts([_suspect("other")]) == {}


def test_a_line_reading_stops_at_the_restart_and_spells_em_dashes(monkeypatch):
    import httpx

    chunks = ['{"response": "course一of the"}', '{"response": " day\\ncourse"}']

    def transport(request):
        return httpx.Response(200, content="\n".join(chunks).encode())

    client = httpx.Client(transport=httpx.MockTransport(transport))
    monkeypatch.setattr(httpx, "stream", client.stream)
    assert ocrcheck.read_line(b"png", "glm-ocr:bf16", "http://x") == "course—of the day"


def test_differences_from_several_readings_merge_into_one_span_per_place():
    from roboscriptorium.ocrcheck import merged_differences

    ours = "said Tolly up if they come"
    glm = "said Polly up-if they come"
    tess = "said ‘Polly up—if they come"
    found = merged_differences(ours, [glm, tess])
    assert [(ours[a0:a1], versions) for a0, a1, versions in found] == [
        ("Tolly", ["Polly", "‘Polly"]),
        ("up if", ["up-if", "up—if"]),
    ]
    # A reading that agrees with the text layer adds no version.
    assert merged_differences(ours, [ours, glm]) == merged_differences(ours, [glm])


def test_quote_style_alone_doesnt_make_another_version():
    from roboscriptorium.ocrcheck import merged_differences

    ours = "said fee-fee?' in"
    found = merged_differences(ours, ['said fee-fee?" in', "said fee-fee?” in"])
    assert [versions for _, _, versions in found] == [['fee-fee?"']]


def test_typographic_differences_have_the_same_letters():
    from roboscriptorium.ocrcheck import _typographic

    assert _typographic(["year at", "year-at", "year—at"])
    assert not _typographic(["Tolly", "‘Polly"])
    assert not _typographic(["was 3 thing", "was a thing"])
    assert _typographic(["Action ?", "Action?"])
    assert not _typographic(["have never", "havenever"])


def test_a_not_sign_line_end_hyphen_is_not_a_difference():
    assert _spans("present to me are both your¬", "present to me are both your-") == []


def test_tesseract_text_where_a_word_table_was_asked_for_is_an_error(monkeypatch):
    import pytest

    from roboscriptorium import ocrcheck

    monkeypatch.setattr(ocrcheck.ocr, "tesseract", lambda png, lang, tsv=False: "LICHAAMSTAAL")
    with pytest.raises(ValueError, match="no word table"):
        ocrcheck._tesseract_page(b"png", "nld")


class _WordsPage:
    def __init__(self, words):
        self.words = words

    def get_text(self, kind):
        return self.words


def test_words_go_to_the_nearest_of_overlapping_lines():
    # Line boxes from font metrics, twice the height of the printed words.
    lines = [
        Line("are, I suppose,", 20, 188, 270, 223),
        Line("Rome. It is", 20, 209, 270, 238),
    ]
    page = PageText(25, 300, 400, lines)
    words = [
        (20, 203, 50, 218, "are,"),
        (60, 203, 70, 218, "I"),
        (80, 203, 130, 218, "suppose,"),
        (20, 220, 60, 235, "Rome."),
        (70, 219, 80, 235, "It"),
        (90, 221, 100, 235, "is"),
    ]
    assert [[w[4] for w in ws] for ws in pdf.line_words(words, page)] == [
        ["are,", "I", "suppose,"],
        ["Rome.", "It", "is"],
    ]
    assert ocrcheck.line_boxes(_WordsPage(words), page) == [
        (20, 203, 130, 218),
        (20, 219, 100, 235),
    ]


def test_a_line_its_words_dont_spell_keeps_its_own_box():
    page = PageText(3, 300, 400, [Line("one two", 20, 100, 120, 114)])
    words = [(20, 101, 60, 114, "one"), (70, 100, 120, 113, "tw")]
    assert ocrcheck.line_boxes(_WordsPage(words), page) == [(20, 100, 120, 114)]


def test_a_suspect_at_a_line_end_has_room_for_a_missed_dash():
    words = [(20, 100, 40, 110, "his"), (45, 100, 70, 110, "name"), (75, 100, 110, 110, "Dolittle")]
    line = "his name Dolittle"
    assert ocrcheck._box(words, (20, 100, 110, 110), line, 9, 17) == (75, 100, 120, 110)
    assert ocrcheck._box(words, (20, 100, 110, 110), line, 4, 8) == (45, 100, 70, 110)
    assert ocrcheck._box(words, (20, 100, 110, 110), line, 0, 3) == (10, 100, 40, 110)


def test_tesseract_words_go_to_the_nearest_line_box():
    boxes = [(20, 203, 130, 218), (20, 219, 100, 235)]
    words = [("Rome.", 20, 219, 60, 234), ("suppose,", 80, 203, 130, 217)]
    assert [[w[0] for w in ws] for ws in ocrcheck._by_line(boxes, words)] == [
        ["suppose,"],
        ["Rome."],
    ]
