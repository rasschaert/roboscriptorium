from types import SimpleNamespace

import pymupdf

from roboscriptorium import accentmarks, ocrcheck
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import read_text_layer
from roboscriptorium.roles import DecisionCache


class Drawer:
    """Stands in for the render judge: the fit of each marked word it is asked about."""

    marks = "a-face"

    def __init__(self, fits: dict[str, float]):
        self.fits, self.asked = fits, []

    def mark(self, page, number, box, marked, plain):
        self.asked.append(marked)
        return self.fits.get(marked, 0.1)


def test_a_word_is_stressed_on_each_vowel_group_and_never_twice():
    assert accentmarks.stressed("zijn") == ["zíjn"]
    assert accentmarks.stressed("een") == ["één"]
    assert accentmarks.stressed("normaal") == ["nórmaal", "normáál"]
    assert accentmarks.stressed("Hij") == ["Híj"]
    # No vowel to mark, or a mark already: nothing to offer.
    assert accentmarks.stressed("pfff") == []
    assert accentmarks.stressed("één") == []
    assert accentmarks.stressed("coördinatrice") == []


def test_no_doubt_under_the_cut_in_a_disputed_span_or_without_ink(tmp_path):
    drawer = Drawer({"zíjn": accentmarks.CUT - 0.01, "wérk": 0.95})
    marks = accentmarks.Marks(drawer, tmp_path / "marks.json")
    box = lambda a0, a1: (0, 0, 1, 1)  # noqa: E731
    # Under the cut: an i's dot looks like this.
    assert marks.doubts(None, 1, 0, "dat zijn", [], box) == []
    # A span the readings dispute is theirs to settle.
    assert marks.doubts(None, 1, 1, "het werk", [(4, 8)], box) == []
    none = accentmarks.Marks(
        SimpleNamespace(marks="a-face", mark=lambda *a: None), tmp_path / "n.json"
    )
    assert none.doubts(None, 1, 0, "het werk", [], box) == []


def test_a_mark_the_scan_shows_is_offered_once_and_kept(tmp_path):
    drawer = Drawer({"zíjn": 0.93})
    marks = accentmarks.Marks(drawer, tmp_path / "marks.json")
    box = lambda a0, a1: (0, 0, 1, 1)  # noqa: E731
    assert marks.doubts(None, 3, 2, "en dat zijn wil", [], box) == [(7, 11, ["zíjn"])]
    marks.save()
    again = Drawer({})
    kept = accentmarks.Marks(again, tmp_path / "marks.json")
    assert kept.doubts(None, 3, 2, "en dat zijn wil", [], box) == [(7, 11, ["zíjn"])]
    assert not again.asked
    # Another typeface is another drawing: asked anew.
    other = Drawer({})
    other.marks = "b-face"
    assert (
        accentmarks.Marks(other, tmp_path / "marks.json").doubts(
            None, 3, 2, "en dat zijn wil", [], box
        )
        == []
    )
    assert other.asked


def test_the_ocr_check_puts_a_marked_word_to_the_judges(tmp_path):
    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    doc.new_page(width=300, height=400).insert_text((20, 50), "en dat zijn wil", fontsize=11)
    doc.save(pdf)
    pages = read_text_layer(pdf)
    readings = {"glm": {SourceRef(1, 0): pages[0].lines[0].text}}
    judge = SimpleNamespace(
        model="clef",
        decide=lambda state, questions, image_png=None: {
            "reading": SimpleNamespace(value="b", confidence=0.9)
        },
    )
    marks = accentmarks.Marks(Drawer({"zíjn": 0.93}), tmp_path / "marks.json")
    plain = ocrcheck.check(
        pdf, pages, readings, "nld", judge, judge, DecisionCache(tmp_path / "a.jsonl")
    )
    found = ocrcheck.check(
        pdf,
        pages,
        readings,
        "nld",
        judge,
        judge,
        DecisionCache(tmp_path / "b.jsonl"),
        marks=(marks,),
    )
    assert plain == []
    assert [(s.ours, s.others, s.chosen) for s in found] == [("zijn", ("zíjn",), "zíjn")]
    assert (tmp_path / "marks.json").exists()


def test_a_stopped_ocr_check_keeps_the_marks_drawn_before_the_stop(tmp_path, monkeypatch):
    class Stop(Exception):
        pass

    class Stopping(Drawer):
        def mark(self, page, number, box, marked, plain):
            if number == 3:
                raise Stop
            return super().mark(page, number, box, marked, plain)

    pdf = tmp_path / "book.pdf"
    doc = pymupdf.open()
    for words in ("en dat zijn wil", "zo was het werk", "maar niet hier"):
        doc.new_page(width=300, height=400).insert_text((20, 50), words, fontsize=11)
    doc.save(pdf)
    pages = read_text_layer(pdf)
    readings = {"glm": {SourceRef(p.number, 0): p.lines[0].text for p in pages}}
    judge = SimpleNamespace(
        model="clef",
        decide=lambda state, questions, image_png=None: {
            "reading": SimpleNamespace(value="b", confidence=0.9)
        },
    )
    monkeypatch.setattr(ocrcheck, "SAVE_EVERY", 0)
    cache = DecisionCache(tmp_path / "a.jsonl")
    stopping = Stopping({})
    try:
        ocrcheck.check(
            pdf, pages, readings, "nld", judge, judge, cache,
            marks=(accentmarks.Marks(stopping, tmp_path / "marks.json"),),
        )  # fmt: skip
    except Stop:
        pass
    drawn = list(stopping.asked)
    again = Drawer({})
    ocrcheck.check(
        pdf, pages, readings, "nld", judge, judge, cache,
        marks=(accentmarks.Marks(again, tmp_path / "marks.json"),),
    )  # fmt: skip
    assert drawn
    assert not set(drawn) & set(again.asked)
    assert set(again.asked) <= set(accentmarks.stressed("maar") + accentmarks.stressed("niet")
                                   + accentmarks.stressed("hier"))  # fmt: skip
