from roboscriptorium import evaluate


def test_normalise_folds_typography_the_epub_may_choose():
    assert evaluate.normalise("‘No . . . I don’t’") == "'No ... I don't'"
    assert evaluate.normalise("wait…  then – go") == "wait... then — go"
    assert evaluate.normalise("a. b. c.") == "a. b. c."
    assert evaluate.normalise("Yes . . . .") == "Yes ...."


def test_folds_count_each_kind():
    counted = evaluate.folds(["‘No . . . I don’t’", "wait… – go", "a\u00a0b"])
    assert counted == {"quotes": 4, "dashes": 1, "ellipses": 2, "spaces": 1}
