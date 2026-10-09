import json

import pymupdf

from roboscriptorium import flags, ocrcheck, pdf
from roboscriptorium.ir import SourceRef
from roboscriptorium.ocrcheck import Suspect, differences
from roboscriptorium.pdf import Line, PageText


def _spans(ours: str, theirs: str) -> list[tuple[str, str]]:
    return [(ours[a0:a1], theirs[b0:b1]) for a0, a1, b0, b1 in differences(ours, theirs)]


def test_differences_are_whole_words():
    assert _spans("up if they come", "up—if they come") == [("up if", "up—if")]
    assert _spans("say, Tolly wants", "say, ‘Polly wants") == [("Tolly", "‘Polly")]


def test_quote_style_and_an_opening_quotes_kind_are_not_differences():
    assert _spans('"What is it?" he said', "“What is it?” he said") == []
    assert _spans('"Now listen to me', "‘Now listen to me") == []


def test_a_lost_opening_quote_or_apostrophe_is_a_difference():
    assert _spans("Nee, zei hij.", "‘Nee, zei hij.") == [("Nee,", "‘Nee,")]
    assert _spans("s avonds laat", "’s avonds laat") == [("s", "’s")]
    assert _spans("t Is laat", "’t Is laat") == [("t", "’t")]
    assert _spans("fee-fee?' said", "fee-fee?” said") == [("fee-fee?'", "fee-fee?”")]


def test_a_reading_without_the_space_before_an_apostrophe_is_not_a_difference():
    # A possessive or plural stays a difference either way round.
    assert _spans("de foto's hier", "de foto ’s hier") == [("foto's", "foto ’s")]
    assert _spans("Rózsi’s zoontje", "Rózsi zoontje") == [("Rózsi’s", "Rózsi")]
    # The layer joining the article to the word before is a difference.
    assert _spans("zat ik's avonds", "zat ik ’s avonds") == [("ik's", "ik ’s")]
    # OCR models set the narrow space before Dutch ’s tight: no difference.
    assert _spans("zes uur ’s avonds", "zes uur’s avonds") == []
    assert _spans("je 's morgens", "je's morgens") == []


def test_a_dashs_kind_and_spacing_are_no_difference_but_a_lost_dash_is():
    assert _spans("dat irriteert—een beetje", "dat irriteert – een beetje") == []
    assert _spans("dat irriteert - een beetje", "dat irriteert—een beetje") == []
    assert _spans("‘Ik zei toch—’", "‘Ik zei toch –’") == []
    assert _spans("up if they come", "up—if they come") == [("up if", "up—if")]
    # A hyphen inside a word is a letter of it.
    assert _spans("een wc-bril", "een wc—bril") == [("wc-bril", "wc—bril")]


def test_how_an_ellipsis_is_set_is_no_difference_but_a_lost_one_is():
    assert _spans("ik weet het al… Daar", "ik weet het al... Daar") == []
    assert _spans("ik weet het al . . . Daar", "ik weet het al… Daar") == []
    assert _spans("ge kra. ook", "ge kra… ook") == [("kra.", "kra…")]


def test_readings_that_differ_only_in_how_an_ellipsis_is_set_are_one_version():
    found = ocrcheck.merged_differences("ge kra. ook", ["ge kra... ook", "ge kra… ook"])
    assert found == [(3, 7, ["kra..."])]
    assert ocrcheck.supports("ge kra. ook", "ge kra… ook", 3, 7, ["kra.", "kra..."]) == (
        False,
        True,
    )


def _page() -> PageText:
    lines = [
        Line("he was so tired up if they come", 10, 10, 200, 20),
        Line("other", 10, 30, 50, 40),
    ]
    return PageText(7, 300, 400, lines)


def _suspect(choice: str) -> Suspect:
    chosen = "up—if" if choice == "other" else None
    original = "he was so tired up if they come"
    votes = {"clef:27b": "up if", "winnow-ollama:e4b": "up—if"}
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
        {"text": "he was so tired up—if they come", "votes": ["winnow-ollama:e4b"]},
    ]
    assert found[0].span == (16, 21)
    assert ocrcheck.doubts([_suspect("other")]) == []


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
    found = ocrcheck.merged_differences(ours, [glm, tess])
    assert [(ours[a0:a1], versions) for a0, a1, versions in found] == [
        ("Tolly", ["Polly", "‘Polly"]),
        ("up if", ["up-if", "up—if"]),
    ]
    # A reading that agrees with the text layer adds no version.
    assert merged_differences(ours, [ours, glm]) == merged_differences(ours, [glm])


def test_quote_style_alone_doesnt_make_another_version():

    ours = "said fee-fee?' in"
    found = ocrcheck.merged_differences(ours, ['said fee-fee?" in', "said fee-fee?” in"])
    assert [versions for _, _, versions in found] == [['fee-fee?"']]


def test_a_mark_each_reading_lost_is_offered_together():

    ours = "‘Ga naar huis’ zei ze"
    found = ocrcheck.merged_differences(ours, ["‘Ga naar huis. zei ze", "'Ga naar huis.' zei ze"])
    assert [versions for _, _, versions in found] == [["huis.", "huis.’"]]
    found = ocrcheck.merged_differences(ours, ["‘Ga naar huis. zei ze"])
    assert [versions for _, _, versions in found] == [["huis.", "huis.’"]]


def test_readings_that_disagree_on_a_mark_arent_combined():

    ours = "‘Ga naar huis’ zei ze"
    found = ocrcheck.merged_differences(ours, ["‘Ga naar huis. zei ze", "‘Ga naar huis: zei ze"])
    assert [versions for _, _, versions in found] == [["huis.", "huis:"]]
    # Other letters, or one reading holding both marks, make no combination.
    found = ocrcheck.merged_differences("‘Ja?’ vroeg", ["‘Ja? vroeg"])
    assert [versions for _, _, versions in found] == [["‘Ja?"]]
    found = ocrcheck.merged_differences("‘Nee’ zei", ["‘Neen. zei"])
    assert [versions for _, _, versions in found] == [["‘Neen."]]


def test_straight_quotes_take_a_curly_layers_style():

    found = ocrcheck.merged_differences("‘Ja’ zei ze", ["'Ja.' zei ze"])
    assert [versions for _, _, versions in found] == [["‘Ja.’"]]
    # A straight-quoted layer keeps the readings as they are.
    found = ocrcheck.merged_differences("'Ja' zei ze", ["'Ja.' zei ze"])
    assert [versions for _, _, versions in found] == [["'Ja.'"]]


def test_typographic_differences_have_the_same_letters():
    from roboscriptorium.ocrcheck import _typographic

    assert _typographic(["year at", "year-at", "year—at"])
    assert not _typographic(["Tolly", "‘Polly"])
    assert not _typographic(["was 3 thing", "was a thing"])
    assert _typographic(["Action ?", "Action?"])
    assert not _typographic(["have never", "havenever"])
    assert not _typographic(["ik's", "ik ’s"])
    assert _typographic(["liggen,’", "liggen,", "‘liggen"])


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


def test_the_word_list_votes_but_decides_nothing(monkeypatch):
    from types import SimpleNamespace

    answers = iter([])
    monkeypatch.setattr(ocrcheck, "_ask", lambda *args, **kwargs: next(answers))
    clef, winnow = SimpleNamespace(model="clef"), SimpleNamespace(model="winnow")

    def decide(seen: str, read: str, vouched: int | None):
        nonlocal answers
        answers = iter([{"value": seen, "confidence": 0.9}, {"value": read, "confidence": 0.9}])
        line = "Toen kwam lemand binnen"
        return ocrcheck._decide(
            None, 1, 0, line, 10, 16, ["Iemand"], (0, 0, 1, 1), "nld", clef, winnow, None,
            vouched=vouched,
        )  # fmt: skip

    (choice, chosen, votes), confidence = decide("a", "b", 1)
    assert (choice, chosen) == ("review", None)
    assert votes == {"clef": "lemand", "winnow": "Iemand", "word list": "Iemand"}
    assert confidence == {"clef": 0.9, "winnow": 0.9}
    assert decide("a", "a", 1)[0][:2] == decide("a", "a", None)[0][:2] == ("ours", None)


def test_a_second_vision_judge_is_asked_the_same_question_and_only_votes(monkeypatch):
    from types import SimpleNamespace

    asked = []

    def ask(client, cache, state, questions, image=None):
        asked.append((client.model, state, questions))
        return {
            "value": {"clef": "a", "winnow": "a", "imajev": "b"}[client.model],
            "confidence": 0.7,
        }

    monkeypatch.setattr(ocrcheck, "_ask", ask)
    clef, winnow = SimpleNamespace(model="clef"), SimpleNamespace(model="winnow")
    imajev = SimpleNamespace(model="imajev")
    line = "Toen kwam lemand binnen"
    (choice, chosen, votes), confidence = ocrcheck._decide(
        None, 1, 0, line, 10, 16, ["Iemand"], (0, 0, 1, 1), "nld", clef, winnow, None,
        vouched=1, alarm=imajev,
    )  # fmt: skip
    (_, s1, q1), _, (_, s3, q3) = asked
    assert (s1, q1) == (s3, q3)
    # The fixed rule goes by clef and winnow alone.
    assert (choice, chosen) == ("ours", None)
    assert list(votes) == ["clef", "winnow", "imajev", "word list"]
    assert votes["imajev"] == "Iemand" and confidence["imajev"] == 0.7


def test_the_vision_judge_is_told_the_books_style_and_the_text_judge_isnt(monkeypatch):
    from types import SimpleNamespace

    asked = []

    def ask(client, cache, state, questions, image=None):
        asked.append((client.model, questions["reading"]))
        return {"value": "a", "confidence": 0.9}

    monkeypatch.setattr(ocrcheck, "_ask", ask)
    clef, winnow = SimpleNamespace(model="clef"), SimpleNamespace(model="winnow")
    style = "This book is Dutch and set in this style: dialogue in curly quotes ‘ ’."
    line = "“Kom hier, zei hij."
    ocrcheck._decide(
        None, 1, 0, line, 0, 4, ["‘Kom"], (0, 0, 1, 1), "nld", clef, winnow, None, style=style
    )
    (_, seen), (_, read) = asked
    assert style in seen["instructions"] and style not in read["instructions"]
    # The versions are set off by marks that none of them contains.
    assert seen["criteria"]["a"] == "exactly ⟨“Kom⟩" and seen["criteria"]["b"] == "exactly ⟨‘Kom⟩"


def test_each_doubted_place_is_its_own_question_and_answers_combine(tmp_path):
    from roboscriptorium.corrections import Corrections, apply

    line = "zag ik uit, rondhangt, en dan"
    page = PageText(9, 300, 400, [Line(line, 10, 10, 200, 20)])

    def doubt(start, end, other, chosen=None):
        choice = "other" if chosen else "review"
        return Suspect(9, 0, line, start, end, line[start:end], (other,), (start, 0, end, 1),
                       choice, chosen, {"clef": line[start:end], "winnow": other})  # fmt: skip

    first, second = doubt(7, 11, "uit,’"), doubt(12, 22, "rondhangt,’")
    fixed = doubt(26, 29, "dan.", chosen="dan.")
    found = flags.find([page], {}, None, ocrcheck.doubts([first, second, fixed]))
    assert [(f.span, f.box[0]) for f in found] == [((7, 11), 7), ((12, 22), 12)]
    assert len({f.key for f in found}) == 2

    answers = Corrections(tmp_path / "regions.jsonl")
    for f in found:
        answers.record(f, "text", f.readings[1]["text"])
    out, _, applied = apply([page], {}, Corrections(tmp_path / "regions.jsonl"), [fixed])
    # Both answers and the machine's fix elsewhere in the line, none lost.
    assert out[0].lines[0].text == "zag ik uit,’ rondhangt,’ en dan."
    assert applied == 2
    assert page.lines[0].text == line


def test_a_line_retyped_whole_takes_no_fixes_and_answers_its_places(tmp_path):
    from roboscriptorium.corrections import Corrections, apply

    page = _page()
    whole = flags.Flag(flags.region_key(7, page.lines[0].text), 7, 0, 0, page.lines[0].text,
                       "text", ["centred"])  # fmt: skip
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(whole, "text", "he was so tired, up—if they come")
    out, _, _ = apply([page], {}, answers, [_suspect("other")])
    assert out[0].lines[0].text == "he was so tired, up—if they come"
    (slot,) = flags.find([page], {}, None, ocrcheck.doubts([_suspect("review")]))
    assert answers.for_flag(slot) is answers.by_key[whole.key]


def test_a_break_hyphen_is_asked_as_the_word_across_the_break(tmp_path):
    from roboscriptorium.corrections import Corrections, apply

    line, after = "en daar was ik dank", "baar voor, zei ze"
    assert ocrcheck.hyphen_only(line, len(line), ["dank", "dank-"], after) == "baar"
    # Not at the line's end, or differing in more than the hyphen: no.
    assert ocrcheck.hyphen_only(line, 14, ["ik", "ik-"], after) == ""
    assert ocrcheck.hyphen_only(line, len(line), ["dank", "danks-"], after) == ""
    assert ocrcheck.across("dank-", "baar") == "dankbaar"
    assert ocrcheck.across("dank", "baar") == "dank baar"

    page = PageText(9, 300, 400, [Line(line, 10, 10, 200, 20), Line(after, 10, 30, 200, 40)])
    s = Suspect(9, 0, line, 15, 19, "dank", ("dank-",), (150, 10, 200, 20), "review", None,
                {"clef": "dank", "winnow": "dank-"}, joined="baar")  # fmt: skip
    (question,) = flags.find([page], {}, None, ocrcheck.doubts([s]))
    assert [r["text"] for r in question.readings] == [
        "en daar was ik dank baar",
        "en daar was ik dankbaar",
    ]
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(question, "text", "en daar was ik dankbaar")
    out, _, _ = apply([page], {}, answers)
    assert [ln.text for ln in out[0].lines] == ["en daar was ik dank-", after]


def test_identical_lines_each_take_only_their_own_fix():
    lines = [Line("zon", 10, 10, 50, 20), Line("ja", 10, 30, 50, 40), Line("zon", 10, 50, 50, 60)]
    page = PageText(7, 300, 400, lines)
    suspects = [
        Suspect(7, i, "zon", 0, 3, "zon", ("zo'n",), (0, 0, 1, 1), "other", "zo'n") for i in (0, 2)
    ]
    assert [ln.text for ln in ocrcheck.apply([page], suspects)[0].lines] == ["zo'n", "ja", "zo'n"]
    assert [ln.text for ln in ocrcheck.apply([page], suspects[:1])[0].lines] == [
        "zo'n",
        "ja",
        "zon",
    ]


def test_a_build_read_via_is_cached_under_the_models_name_and_marked(monkeypatch, tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=200)
    for i, text in enumerate(["The first line of it", "and the second line"]):
        page.insert_text((40, 60 + 18 * i), text, fontsize=11)
    doc.save(tmp_path / "source.pdf")
    pages = pdf.read_text_layer(tmp_path / "source.pdf")
    checked = {SourceRef(1, k) for k in range(len(pages[0].lines))}
    used = []

    def read(png, model, url, prompt):
        used.append(model)
        return "read"

    monkeypatch.setattr(ocrcheck, "transcribe", read)
    cache = tmp_path / "third-reading.json"
    hosted = "openrouter:qwen/qwen3.8-27b@deepinfra/bf16"
    got = ocrcheck.line_readings(
        tmp_path / "source.pdf", pages, checked, "qwen3.8:27b-nvfp4", "", cache, "Read.", hosted
    )
    assert set(used) == {hosted} and set(got.values()) == {"read"}
    blob = json.loads(cache.read_text())
    assert blob["model"] == "qwen3.8:27b-nvfp4"
    assert sorted(blob["via"][hosted]) == sorted(blob["lines"])
    used.clear()
    ocrcheck.line_readings(
        tmp_path / "source.pdf", pages, checked, "qwen3.8:27b-nvfp4", "", cache, "Read."
    )
    assert used == []  # the local model finds them cached


def _page_of(tmp_path, leading: float) -> tuple[pymupdf.Document, list]:
    """Five lines of synthetic text set `leading` points apart, and their boxes."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    for i in range(5):
        page.insert_text(
            (40, 60 + leading * i), f"Line {i} of a tightly set page goes on", fontsize=12
        )
    doc.save(tmp_path / "source.pdf")
    doc = pymupdf.open(tmp_path / "source.pdf")
    layer = pdf.read_text_layer(tmp_path / "source.pdf")[0]
    return doc, ocrcheck.line_boxes(doc[0], layer)


def test_a_crop_on_a_tight_page_stays_out_of_its_neighbours(tmp_path):
    doc, boxes = _page_of(tmp_path, 13)
    assert boxes[2][1] - boxes[1][3] < ocrcheck.LINE_PAD  # the pad would reach line 1
    top, bottom = ocrcheck.crop_span(boxes, 2)
    # Up to the neighbour's box, or to its own where the two overlap.
    assert top >= min(boxes[1][3], boxes[2][1]) and bottom <= max(boxes[3][1], boxes[2][3])
    assert top <= boxes[2][1] and bottom >= boxes[2][3]  # its own line stays whole


def test_a_crop_with_room_keeps_its_pad(tmp_path):
    doc, boxes = _page_of(tmp_path, 30)
    box = boxes[2]
    assert ocrcheck.crop_span(boxes, 2) == (box[1] - ocrcheck.LINE_PAD, box[3] + ocrcheck.LINE_PAD)


def test_only_a_crop_cut_short_is_read_again(monkeypatch, tmp_path):
    reads = []
    monkeypatch.setattr(ocrcheck, "transcribe", lambda png, m, u, p: reads.append(png) or "r")
    for leading, first_line_read_again in ((30, False), (13, True)):
        sub = tmp_path / str(leading)
        sub.mkdir()
        doc, boxes = _page_of(sub, leading)
        pages = pdf.read_text_layer(sub / "source.pdf")
        checked = {SourceRef(1, k) for k in range(len(boxes))}
        cache = sub / "third-reading.json"
        ocrcheck.line_readings(sub / "source.pdf", pages, checked, "m", "", cache, "Read.")
        blob = json.loads(cache.read_text())
        cut = [k for k in blob["lines"] if k.count(":") == 4]
        assert bool(cut) == first_line_read_again


def test_readings_by_another_prompt_are_kept_aside_and_come_back(monkeypatch, tmp_path):
    reads = []
    monkeypatch.setattr(ocrcheck, "transcribe", lambda png, m, u, p: reads.append(p) or p)
    doc, boxes = _page_of(tmp_path, 30)
    pages = pdf.read_text_layer(tmp_path / "source.pdf")
    checked = {SourceRef(1, k) for k in range(len(boxes))}
    cache = tmp_path / "third-reading.json"

    def read(prompt):
        return ocrcheck.line_readings(
            tmp_path / "source.pdf", pages, checked, "m", "", cache, prompt
        )

    assert set(read("A").values()) == {"A"}
    assert set(read("B").values()) == {"B"}
    reads.clear()
    assert set(read("A").values()) == {"A"} and reads == []
    assert set(read("B").values()) == {"B"} and reads == []
    # The cache itself holds the prompt read last, as its readers expect.
    assert json.loads(cache.read_text())["prompt"] == "B"


def test_a_reading_supports_its_version_of_a_span_wider_than_its_own_difference():
    ours = "the cat sat down"
    glm, tess = "the cot sat down", "the cotsat down"
    [(a0, a1, versions)] = ocrcheck.merged_differences(ours, [glm, tess])
    versions = [ours[a0:a1], *versions]
    assert ocrcheck.supports(ours, glm, a0, a1, versions) == (False, True, False)
    assert ocrcheck.supports(ours, tess, a0, a1, versions) == (False, False, True)
    assert ocrcheck.supports(ours, ours, a0, a1, versions) == (True, False, False)
