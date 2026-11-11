from roboscriptorium import evaluate, italics
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import Document, Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText


def test_a_short_word_between_italic_ones_is_italic():
    assert italics._fill([False, None, True, None, True, None, False]) == [2, 3, 4]
    assert italics._fill([None, True, None]) == [1]


def test_a_short_word_leaning_a_little_among_upright_ones_stays_upright():
    # "bereid was het op te geven": "op", one stem, at 10° from the page's upright.
    line, stems = [0.0, None, 0.0, 10.0, -1.0], [4, 0, 2, 1, 1]
    assert italics._italic(line, stems, (None, None)) == [False, None, False, False, False]
    # A short word leaning as far as italic type does is italic alone.
    assert italics._italic([0.0, 13.0, 0.0], [2, 1, 2], (None, None)) == [False, True, False]
    # A word with stems enough to measure keeps the plain cut alone: "You can't *quite*".
    assert italics._italic([0.0, 9.0, 0.0], [2, 5, 2], (None, None)) == [False, True, False]
    # Beside another leaning word the plain cut holds for any word.
    assert italics._italic([9.0, 8.0, 0.0], [1, 2, 2], (None, None)) == [True, True, False]


def test_a_run_over_a_line_end_keeps_its_first_word():
    # "boekpublicatie De" / "laatste drie dagen …", the title italic on the next line.
    assert italics._italic([0.0, 9.0], [4, 1], (None, 15.0)) == [False, True]
    assert italics._italic([9.0, 0.0], [1, 4], (14.0, None)) == [True, False]
    assert italics._italic([0.0, 9.0], [4, 1], (None, 0.0)) == [False, False]


def test_slants_count_from_the_pages_upright():
    page = {"0": [2.0] * 12, "1": [2.0, 11.0, None]}
    assert italics._upright(page) == 2.0
    assert italics._leaning(page["1"], 2.0) == [0.0, 9.0, None]
    assert italics._upright({"0": [3.0] * 3}) == 0.0
    # A page set in italic: its few words under the cut are italic ones, not its upright.
    assert italics._upright({"0": [5.0] * 12 + [10.0] * 200}) == 0.0


def test_a_dedication_all_but_one_word_italic_is_set_all_italic_not_running_text():
    ded = [
        Paragraph("Voor mijn ouders", dedication=True, italic=(1, 2)),
        Paragraph("Bruni en Thomas Eggers", dedication=True, italic=(0, 1, 2, 3)),
    ]
    text = Paragraph("Voor mijn ouders schreef hij.", italic=(1, 2))
    out = italics.uniform([*ded, text])
    assert [b.italic for b in out] == [(0, 1, 2), (0, 1, 2, 3), (1, 2)]
    # A motto with two upright words keeps them: it may set its source upright.
    motto = [Paragraph("Zwart paard", epigraph=True, italic=(0, 1)),
             Paragraph("Albert Camus", epigraph=True)]  # fmt: skip
    assert italics.uniform(motto) == motto
    # One word leaning among upright ones is upright.
    upright = [Paragraph("Zwart paard, wit paard", epigraph=True, italic=(0,)),
               Paragraph("Albert Camus", epigraph=True)]  # fmt: skip
    assert [b.italic for b in italics.uniform(upright)] == [(), ()]


def test_marks_follow_words_through_fixes_and_joined_hyphenation():
    page = PageText(
        3,
        400,
        600,
        [Line("he said it was per-", 0, 0, 1, 1), Line("haps quite rernarkable, and", 0, 2, 1, 3)],
    )
    marks = {SourceRef(3, 0): frozenset({4}), SourceRef(3, 1): frozenset({0, 2})}
    para = Paragraph(
        "he said it was perhaps quite remarkable, and", [SourceRef(3, 0), SourceRef(3, 1)]
    )
    (marked,) = italics.mark([para], [page], marks)
    assert marked.italic == (4, 6)
    assert para.italic == ()


def test_italic_words_are_scored_over_aligned_words():
    reference = [Chapter("I", ["it was truly remarkable, and so"], [frozenset({2, 3})])]
    doc = Document("T", "A", "en", [Paragraph("it was truly remarkable, and so", italic=(3, 4))])
    s = evaluate.score(doc, reference)
    assert (s.italic_expected, s.italic_output) == (2, 2)
    assert (s.italic_precision, s.italic_recall) == (0.5, 0.5)


def test_a_misread_italic_word_is_italic_in_the_right_place():
    reference = [Chapter("I", ["it was truly remarkable, and so"], [frozenset({2, 3})])]
    doc = Document("T", "A", "en", [Paragraph("it was truly rernarkable, and so", italic=(2, 3))])
    s = evaluate.score(doc, reference)
    assert (s.italic_precision, s.italic_recall) == (1.0, 1.0)


def test_a_glued_italic_word_has_no_place_to_count_in():
    reference = [Chapter("I", ["it was truly remarkable, and so"], [frozenset({2, 3})])]
    doc = Document("T", "A", "en", [Paragraph("it was trulyremarkable, and so", italic=(2,))])
    s = evaluate.score(doc, reference)
    assert (s.italic_expected, s.italic_output) == (2, 1)
    assert (s.italic_precision, s.italic_recall) == (0.0, 0.0)


def test_the_ink_threshold_follows_a_pale_scan():
    import numpy as np

    from roboscriptorium.ink import threshold as ink_threshold

    page = np.full((100, 100), 225, dtype=np.uint8)
    page[40:60, 20:80] = 135  # grey print on a light page
    assert 135 <= ink_threshold(page) < 225


def test_a_typed_line_does_not_take_its_neighbours_italics():
    from roboscriptorium.reflow import reflow

    layer = PageText(1, 400, 600, [Line("Odyssee van Homerus", 50, 100, 350, 112)])
    # A human typed "en de" where the layer lost it, before the italic line.
    corrected = PageText(
        1,
        400,
        600,
        [
            Line("en de", 50, 85, 120, 97, source=0, typed=True),
            Line("Odyssee van Homerus", 50, 100, 350, 112, source=0),
        ],
    )
    (para,) = italics.mark(reflow([corrected]), [layer], {SourceRef(1, 0): frozenset({0, 1, 2})})
    assert para.text == "en de Odyssee van Homerus"
    assert para.italic == (2, 3, 4)
