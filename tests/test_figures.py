"""Which pictures go in the book, and their captions."""

from roboscriptorium import figures, flags
from roboscriptorium.corrections import Corrections
from roboscriptorium.layout import Region
from roboscriptorium.pdf import Line, PageText


def _plate_page() -> PageText:
    # A picture over most of the page, its caption in two text-layer lines beneath it.
    lines = [Line("THE DOCTOR AND THE", 120, 520, 280, 532), Line("ANIMALS", 160, 534, 240, 546)]
    return PageText(36, 400, 600, lines)


def _figure() -> dict:
    return {36: [Region("figure", 0.9, 40, 40, 360, 500)]}


def test_a_caption_answered_on_its_lines_goes_with_the_picture(tmp_path):
    page = _plate_page()
    answers = Corrections(tmp_path / "regions.jsonl")
    text = "\n".join(ln.text for ln in page.lines)
    answers.record(flags.Flag(flags.region_key(36, text), 36, 0, 1, text, "dropped", []), "caption",
                   None)  # fmt: skip
    (picture,) = figures.select(None, [page], _figure(), answers, "eng")
    assert picture.caption == "THE DOCTOR AND THE ANIMALS"


def test_a_caption_answer_whose_lines_are_gone_gives_no_caption(tmp_path):
    page = _plate_page()
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(flags.Flag("k", 36, 0, 1, "Some other\nlines", "dropped", []), "caption", None)
    (picture,) = figures.select(None, [page], _figure(), answers, "eng")
    assert picture.caption == ""
