from roboscriptorium import quality
from roboscriptorium.disagreements import Disagreement
from roboscriptorium.flags import Flag


def _error(page, lines, got="lets", want="Iets"):
    return Disagreement("k", got, want, "", "", page, lines)


def _flag(page, first, last, reason="ocr-doubt"):
    return Flag(f"{page}-{first}", page, first, last, "", "text", [reason])


def test_a_question_catches_errors_on_its_lines_only():
    assert quality.catches(_flag(5, 3, 4), _error(5, (4, 6)))
    assert not quality.catches(_flag(5, 3, 4), _error(5, (5, 6)))
    assert not quality.catches(_flag(6, 3, 4), _error(5, (4, 4)))
    # Text the layer lacks: a region with no lines asks about it.
    assert quality.catches(_flag(5, 2, 1), _error(5, None))
    assert not quality.catches(_flag(5, 2, 1), _error(5, (2, 2)))


def test_budgets_ask_the_kinds_of_question_that_caught_errors_elsewhere_first():
    errors = [_error(1, (0, 0)), _error(2, (5, 5), "a b c", "x")]
    flags = [_flag(1, 9, 9, "centred"), _flag(2, 5, 5, "ocr-doubt"), _flag(1, 0, 0, "ocr-doubt")]
    rates = {"ocr-doubt": (8, 10), "centred": (0, 10)}
    assert [quality.reason(f) for f in quality.ranked(flags, rates)][0] == "ocr-doubt"
    out = quality.report([1, 2, 3, 4], errors, flags, rates)
    assert out["wrong words"].mean == (1 + 3) / 4
    assert out["questions"].mean == 3 / 4
    assert out["unasked, all questions"].mean == 0
    # One question at 0.25/page: an ocr-doubt, which leaves the other error unasked.
    assert out["unasked at 0.25/page"].mean in (1 / 4, 3 / 4)
    assert out["unasked at 1/page"].mean == 0


def test_bootstrap_interval_holds_the_mean():
    e = quality.bootstrap([0, 0, 1, 5, 0, 2, 0, 0])
    assert e.low <= e.mean <= e.high
    assert e.low < e.high


def test_errors_are_sorted_into_kinds():
    def kind(got, want):
        return quality.category(_error(1, (0, 0), got, want))

    assert kind("lets", "Iets") == "letters"
    assert kind("niet...'", "niet…'") == "punctuation"
    assert kind("“Wat", "‘Wat") == "quotes"
    assert kind("we-bril", "wc-bril") == "letters"
    assert kind("zeize", "ze ize") == "word breaks"
    assert kind("", "geen") == "missing words"
    assert kind("naaije", "je") == "letters"


def test_typesetting_choices_are_no_errors():
    from roboscriptorium.evaluate import normalise

    assert normalise("omdat…’ ‘De sheriff…’") == normalise("omdat...' 'De sheriff...'")
