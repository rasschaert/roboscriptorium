from roboscriptorium import evaluate, italics
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import Document, Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText


def test_a_short_word_between_italic_ones_is_italic():
    assert italics._fill([False, None, True, None, True, None, False]) == [2, 3, 4]
    assert italics._fill([None, True, None]) == [1]


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


def test_the_ink_threshold_follows_a_pale_scan():
    import numpy as np

    from roboscriptorium.italics import ink_threshold

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
