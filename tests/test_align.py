from roboscriptorium.golden.align import align
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText


def _page(number, texts):
    return PageText(
        number, 300, 500, [Line(t, 20, 20 + 15 * i, 280, 30 + 15 * i) for i, t in enumerate(texts)]
    )


def test_lines_get_their_reference_words_and_roles():
    pages = [
        _page(11, ["EEN", "Charlie liep naar de ver-", "der gelegen school.", "11"]),
        _page(12, ["Goede dochter", "lets later kwam", "ze thuis."]),
    ]
    reference = [
        Chapter("EEN", ["Charlie liep naar de verder gelegen school. Iets later kwam ze thuis."])
    ]
    labels = align(pages, reference)
    assert labels[SourceRef(11, 0)].role == "heading"
    assert labels[SourceRef(11, 1)].role == "body"
    assert labels[SourceRef(11, 1)].truth.startswith("Charlie liep naar de")
    assert labels[SourceRef(11, 3)].role == "other"  # the page number
    assert labels[SourceRef(12, 0)].role == "other"  # the running head
    assert labels[SourceRef(12, 1)].truth == "Iets later kwam"
    assert labels[SourceRef(12, 2)].truth == "ze thuis."


def test_words_broken_over_a_line_end_are_broken_in_the_truth():
    pages = [_page(5, ["het ge-", "luid van de wc-", "rol en ‘zo’"])]
    labels = align(pages, [Chapter("", ["het geluid van de wc-rol en ‘zo’"])])
    assert [labels[SourceRef(5, k)].truth for k in range(3)] == [
        "het ge-",
        "luid van de wc-",
        "rol en ‘zo’",
    ]


def test_capitals_numerals_and_spaced_dots_are_still_the_reference():
    pages = [_page(9, ["Ill", "ZORG DAT JE THUIS BENT.", "never sinned . . .", "12"])]
    reference = [Chapter("III", ["Zorg dat je thuis bent. never sinned..."])]
    labels = align(pages, reference)
    assert [labels[SourceRef(9, k)].role for k in range(4)] == ["heading", "body", "body", "other"]
