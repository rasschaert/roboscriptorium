from roboscriptorium import evaluate


def test_normalise_folds_typography_the_epub_may_choose():
    assert evaluate.normalise("‘No . . . I don’t’") == "'No ... I don't'"
    assert evaluate.normalise("wait…  then – go") == "wait... then — go"
    assert evaluate.normalise("a. b. c.") == "a. b. c."
    assert evaluate.normalise("Yes . . . .") == "Yes ...."


def test_folds_count_each_kind():
    counted = evaluate.folds(["‘No . . . I don’t’", "wait… – go", "a\u00a0b"])
    assert counted == {"quotes": 3, "dashes": 1, "ellipses": 2, "spaces": 1, "soft hyphens": 0}


def test_soft_hyphens_are_folded_away_on_both_sides_and_counted():
    assert evaluate.normalise("dank­baar") == "dankbaar"
    assert evaluate.folds(["dank­baar"])["soft hyphens"] == 1


def test_spaced_dots_with_any_space_are_one_ellipsis():
    assert evaluate.normalise("a . . . b") == "a ... b"
    counted = evaluate.folds(["a . . . b", "a b", "a b"])
    assert counted["ellipses"] == 1
    assert counted["spaces"] == 2


def test_italic_words_survive_spaced_dots():
    assert evaluate._italic_words(["Wait . . . what now"], [frozenset({4, 5})]) == {2, 3}
    assert evaluate._italic_words(["Wait . . . what now"], [frozenset({0})]) == {0}


def test_headings_keep_their_accented_letters_and_empty_keys_match_nothing():
    assert evaluate.match_headings(["Één"], ["Een"]) == 1
    assert evaluate.match_headings(["Één"], ["Twee"]) == 0
    assert evaluate.match_headings(["—"], ["* * *"]) == 0


def test_an_empty_reference_is_refused():
    import pytest

    from roboscriptorium.golden.reference import Chapter
    from roboscriptorium.ir import Document, Paragraph

    doc = Document("t", "a", "en", [Paragraph("some words")])
    with pytest.raises(ValueError):
        evaluate.score(doc, [Chapter("I", [])])


def test_eval_locates_remaining_disagreements_on_the_layer_pages_by_their_review_keys(
    monkeypatch, tmp_path
):
    from types import SimpleNamespace

    from roboscriptorium import cli, disagreements
    from roboscriptorium.golden.reference import Chapter
    from roboscriptorium.ir import Document, Paragraph, SourceRef
    from roboscriptorium.pdf import Line, PageText

    def page(texts):
        return PageText(
            11, 300, 500, [Line(t, 20, 20 + 15 * i, 280, 30 + 15 * i) for i, t in enumerate(texts)]
        )

    # A human typed a line above the others on the corrected copy; the paragraph's
    # references still point at the lines' places before the answer (`Line.source`).
    raw = page(["a b X d e f", "Y h i j k l"])
    corrected = page(["1", "a b X d e f", "Y h i j k l"])
    doc = Document(
        "t", "a", "en", [Paragraph("a b X d e f Y h i j k l", [SourceRef(11, k) for k in (0, 1)])]
    )
    reference = [Chapter("1", ["a b c d e f g h i j k l"])]
    stages = SimpleNamespace(
        corrected=[corrected], pages=[raw], suspects=[], doc=doc, ocr_decider=""
    )
    book = SimpleNamespace(
        root=tmp_path, source=tmp_path / "source.pdf", stages=tmp_path, language="en"
    )
    # Verdicts as the golden review records them: keyed on the unpatched reference.
    verdicts = disagreements.Verdicts(tmp_path / "v.jsonl")
    ocr, edition = disagreements.find(doc, reference, [raw])
    verdicts.record(ocr, "c", "ocr")
    verdicts.record(edition, "Y", "edition")
    monkeypatch.setattr(cli, "_build_golden", lambda *a: (book, stages, doc, reference))
    monkeypatch.setattr(cli, "_verdicts", lambda book: verdicts)
    monkeypatch.setattr(cli, "_italics_unlike", lambda book: "")
    lines = []
    monkeypatch.setattr(cli.typer, "echo", lambda text="": lines.append(text))
    cli._evaluate_book(tmp_path, None, None, True, False)
    remaining = next(t for t in lines if "remaining disagreements" in t)
    assert remaining.endswith("remaining disagreements: ocr 1")


def test_a_word_split_or_merged_costs_its_letters_once():
    from roboscriptorium.golden.reference import Chapter
    from roboscriptorium.ir import Document, Paragraph

    def cer(text):
        doc = Document("t", "a", "nl", [Paragraph(text, [])])
        return evaluate.score(doc, [Chapter("I", ["a b c vijf jaar d e f g h i j"])])

    split = cer("a b c vijfjaar d e f g h i j")
    letter = cer("a b c vijf jaer d e f g h i j")
    assert split.cer == letter.cer  # one space lost, one letter wrong: one edit each
    assert split.confusions == [("vijfjaar", "vijf jaar", 1)]


def test_a_heading_with_another_number_is_not_found():
    assert evaluate.match_headings(["CHAPTER 2"], ["CHAPTER 3"]) == 0
    assert evaluate.match_headings(["CHAPTER XXV."], ["CHAPTER XXVI."]) == 0
    assert evaluate.match_headings(["CHAPTER 1", "CHAPTER 2"], ["CHAPTER 1", "CHAPTER 3"]) == 1
    # The layer's look-alikes in a number still match.
    assert (
        evaluate.match_headings(
            ["4I", "HOOFDSTUK 1O", "CHAPTER IL"], ["41", "HOOFDSTUK 10", "CHAPTER II."]
        )
        == 3
    )
