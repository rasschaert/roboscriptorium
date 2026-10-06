from roboscriptorium import flags, ocrcheck
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
