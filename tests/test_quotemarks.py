"""Nested quotation marks every reader drops: offered where the scan shows three ticks."""

from types import SimpleNamespace

import pymupdf
import pytest

from roboscriptorium import ocrcheck, quotemarks
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import read_text_layer
from roboscriptorium.roles import DecisionCache

FONT = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"


def _scan(tmp_path, lines: list[str]):
    """A one-page PDF printing `lines` in a typeface with curly marks, and its text layer."""
    path = tmp_path / "book.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=60 + 30 * len(lines))
    for k, text in enumerate(lines):
        page.insert_text((30, 50 + 30 * k), text, fontname="times", fontfile=FONT, fontsize=14)
    doc.save(path)
    return path, read_text_layer(path)


needs_font = pytest.mark.skipif(not __import__("pathlib").Path(FONT).exists(), reason="no Times")


@pytest.mark.parametrize(
    ("token", "opening", "outer", "want"),
    [
        ("“Lucy", True, "s", "‘“Lucy"),
        ("kind,”", False, "s", "kind,”’"),
        ("“Lucy", True, "d", "“‘Lucy"),
        ("it.”", False, "d", "it.’”"),
    ],
)
def test_the_nested_version_sets_the_single_mark_by_the_books_outer_mark(
    token, opening, outer, want
):
    assert quotemarks.nested(token, opening, outer) == want


@needs_font
def test_three_ticks_measure_wider_than_two_and_a_letters_overhang_is_no_mark(tmp_path):
    path, _ = _scan(tmp_path, ["zei “Toen ging ‘“Toen weg Toen"])
    with pymupdf.open(path) as doc:
        words = {w[4]: w[:4] for w in doc[0].get_text("words")}
        double = quotemarks.span(doc[0], words["“Toen"], True)
        triple = quotemarks.span(doc[0], words["‘“Toen"], True)
        none = quotemarks.span(doc[0], words["Toen"], True)
    assert none == 0
    assert double > 0.2
    assert triple > quotemarks.RATIO * double


@needs_font
def test_the_check_offers_the_nested_version_where_the_scan_shows_three_ticks(tmp_path):
    doubles = ["hij zei “Goed zo” en “Kom nu” toen", "ze zei “Nee hoor” en “Ga weg” dus"] * 3
    singles = ["‘Kom,’ zei hij. ‘Nu,’ zei ze. ‘Ja,’ zei ik."] * 5
    path, pages = _scan(tmp_path, [*singles, *doubles, "hij las ‘“Lucy was hier” voor"])
    last = len(singles) + len(doubles)
    # Every reading has the last line's three ticks as a double mark.
    texts = [ln.text for ln in pages[0].lines]
    texts[last] = texts[last].replace("‘“", "“")
    pages[0].lines[last] = (
        pages[0].lines[last].__class__(**{**pages[0].lines[last].__dict__, "text": texts[last]})
    )
    readings = {"glm": {SourceRef(1, k): t for k, t in enumerate(texts)}}
    judge = SimpleNamespace(
        model="clef",
        decide=lambda state, questions, image_png=None: {
            "reading": SimpleNamespace(value="b", confidence=0.9)
        },
    )
    nested = quotemarks.Nested(tmp_path / "quote-marks.json")
    nested.survey(path, pages, readings)
    found = ocrcheck.check(
        path, pages, readings, "nld", judge, judge, DecisionCache(tmp_path / "d.jsonl"),
        marks=(nested,),
    )  # fmt: skip
    assert [(s.ours, s.others) for s in found] == [("“Lucy", ("‘“Lucy",))]
    assert (tmp_path / "quote-marks.json").exists()


def test_a_book_with_few_double_marks_gets_no_offers(tmp_path):
    nested = quotemarks.Nested(tmp_path / "quote-marks.json")
    assert nested.doubts(None, 1, 0, "hij zei “Goed zo” toen", [], lambda a, b: None) == []
