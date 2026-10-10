from roboscriptorium.golden import signals
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText


def _page(number, texts):
    return PageText(
        number, 300, 500, [Line(t, 20, 20 + 15 * i, 280, 30 + 15 * i) for i, t in enumerate(texts)]
    )


PAGES = [_page(11, ["Charlie liep naar de", "verder gelegen school.", "11"])]
REFERENCE = [Chapter("", ["Charlie liep naar de verder gelegen school."])]


def test_furniture_counts_as_unplaced_only_when_counted():
    everything = signals.measure(PAGES, REFERENCE)
    assert everything.cer == 0
    assert everything.unplaced == 1 / 3  # the page number
    body = signals.measure(PAGES, REFERENCE, {SourceRef(11, 0), SourceRef(11, 1)})
    assert body.unplaced == 0


def test_layer_slips_count_against_the_reference():
    pages = [_page(11, ["Charlie liep naar de", "verder gelegen schooi."])]
    assert signals.measure(pages, REFERENCE).cer > 0


def test_a_book_is_suspect_far_from_the_sets_usual_rate_or_with_lines_unplaced():
    ok = signals.Signals(0.002, 0.002, 0.01, 4)
    books = {"a": ok, "b": ok, "c": ok, "far": signals.Signals(0.01, 0.01, 0.01, 4)}
    books["lost"] = signals.Signals(0.002, 0.002, 0.08, 4)
    found = signals.suspects(books)
    assert set(found) == {"far", "lost"}
    assert "unplaced" in found["lost"][0]


def test_a_line_without_words_is_unplaced_not_a_crash():
    pages = [_page(11, ["Charlie liep naar de", "­", "verder gelegen school."])]
    measured = signals.measure(pages, REFERENCE)
    assert measured.cer == 0 and measured.unplaced == 1 / 3
