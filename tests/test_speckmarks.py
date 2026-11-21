"""Specks read as punctuation: the lesser mark offered where a mark is unlike the book's own."""

from types import SimpleNamespace

import numpy as np
import pymupdf
import pytest

from roboscriptorium import ocrcheck, speckmarks
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import read_text_layer
from roboscriptorium.roles import DecisionCache

FONT = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
needs_font = pytest.mark.skipif(not __import__("pathlib").Path(FONT).exists(), reason="no Times")


@pytest.mark.parametrize(
    ("token", "want"),
    [
        ("late,", (",", "late")),
        ("lippen;", (";", "lippen,")),
        ("wil:", (":", "wil.")),
        ("mij,’", (",", "mij’")),
        # No word before the mark, or no such mark at its end: no offer.
        (",", None),
        ("...,", None),
        ("late", None),
        ("3,5", None),
    ],
)
def test_the_lesser_version_drops_the_part_a_speck_would_add(token, want):
    assert speckmarks.lesser(token) == want


def test_two_known_words_a_mark_joins_are_offered_parted_and_a_known_joined_word_is_not():
    known = {"je", "vader", "had", "him", "don", "ma", "am", "ma'am", "zo"}.__contains__
    assert speckmarks.parted("je'vader", known) == "je vader"
    assert speckmarks.parted("‘had’him,", known) == "‘had him,"
    assert (
        speckmarks.parted("ma’am", lambda w: w.replace("’", "'") in {"ma", "am", "ma'am"}) is None
    )
    assert speckmarks.parted("don't", known) is None  # a part of one letter
    assert speckmarks.parted("je'xqz", known) is None
    assert speckmarks.parted("vader", known) is None


def test_a_joined_form_the_book_repeats_is_its_spelling(tmp_path):
    from roboscriptorium.pdf import Line, PageText

    def page(number, texts):
        lines = [Line(text=t, x0=0, y0=10 * k, x1=100, y1=10 * k + 8) for k, t in enumerate(texts)]
        return PageText(number=number, width=200, height=300, lines=lines)

    lexicon = SimpleNamespace(knows={"je", "vader", "sp", "ers"}.__contains__)
    specks = speckmarks.Specks(tmp_path / "s.json", lexicon)
    pages = [page(1, ["dan je'vader of", "de sp'ers en", "de sp'ers. De", "alle sp'ers"])]
    path = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page(width=200, height=300)
    doc.save(path)
    specks.survey(path, pages)
    assert specks.doubts(None, 1, 0, "dan je'vader of", [], None) == [(4, 12, ["je vader"])]
    assert specks.doubts(None, 1, 1, "de sp'ers en", [], None) == []


def test_only_pictures_far_from_the_books_usual_one_are_odd_and_a_small_book_has_none():
    rng = np.random.default_rng(0)
    comma = np.zeros((40, 18), np.float32)
    comma[26:34, 8:12] = 1
    speck = np.zeros((40, 18), np.float32)
    speck[10:13, 3:6] = 1
    usual = [np.clip(comma + rng.normal(0, 0.05, comma.shape), 0, 1) for _ in range(30)]
    assert speckmarks.odd_pictures([*usual, speck.astype(np.float32)]) == [30]
    assert speckmarks.odd_pictures(usual) == []
    assert speckmarks.odd_pictures([comma] * 5 + [speck]) == []


@needs_font
def test_the_check_offers_a_word_without_the_comma_a_speck_made(tmp_path):
    path = tmp_path / "book.pdf"
    doc = pymupdf.open()
    lines = ["een, twee, drie, vier, acht, zes,"] * 6 + ["hij kwam laat, thuis en at"]
    page = doc.new_page(width=420, height=60 + 30 * len(lines))
    for k, text in enumerate(lines):
        page.insert_text((30, 50 + 30 * k), text, fontname="times", fontfile=FONT, fontsize=14)
    # The last line's comma painted out, and a fleck set high beside the word: the
    # layer and every reading still have a comma there.
    box = next(w for w in page.get_text("words") if w[4] == "laat,")
    page.draw_rect(
        pymupdf.Rect(box[2] - 4, box[1], box[2] + 1, box[3]), color=(1, 1, 1), fill=(1, 1, 1)
    )
    page.draw_rect(pymupdf.Rect(box[2] - 2.5, box[1] + 7, box[2] - 1, box[1] + 8.5), fill=(0, 0, 0))
    doc.save(path)
    pages = read_text_layer(path)
    last = len(lines) - 1
    texts = [ln.text for ln in pages[0].lines]
    readings = {"glm": {SourceRef(1, k): t for k, t in enumerate(texts)}}
    judge = SimpleNamespace(
        model="clef",
        decide=lambda state, questions, image_png=None: {
            "reading": SimpleNamespace(value="b", confidence=0.9)
        },
    )
    specks = speckmarks.Specks(tmp_path / "speck-marks.json")
    specks.survey(path, pages)
    found = ocrcheck.check(
        path, pages, readings, "nld", judge, judge, DecisionCache(tmp_path / "d.jsonl"),
        marks=(specks,),
    )  # fmt: skip
    assert [(s.ours, s.others) for s in found] == [("laat,", ("laat",))]
    assert (tmp_path / "speck-marks.json").exists()
    # Kept: a second survey measures nothing.
    again = speckmarks.Specks(tmp_path / "speck-marks.json")
    again.survey(tmp_path / "missing.pdf", pages)
    assert again.doubts(None, 1, last, texts[last], [], None) != []


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("- I followed him", ("- I", "I")),
        ("-  For a while", ("-  For", "For")),
        # A dash run on to its word, one standing alone, one mid-line, none: no offer.
        ("-doodstil in het vertrek.", None),
        ("-", None),
        ("- —", None),
        ("en toen - zei hij", None),
        ("Gewoon een regel", None),
    ],
)
def test_a_hyphen_opening_a_line_before_a_word_is_offered_away(text, want):
    assert speckmarks.leading_dash(text) == want


@pytest.mark.parametrize(
    ("token", "want"),
    [
        ("system..", "system."),
        ("vermoord..’", "vermoord.’"),
        # Three dots are an ellipsis, a lone pair no word's, one dot plain.
        ("toch...", None),
        ("..", None),
        ("klaar.", None),
    ],
)
def test_a_word_ending_on_two_stops_is_offered_with_one(token, want):
    assert speckmarks.double_stop(token) == want


def test_the_check_offers_a_line_without_its_opening_hyphen_and_a_word_with_one_stop(tmp_path):
    from roboscriptorium.pdf import Line, PageText

    lines = [Line(text=t, x0=0, y0=10 * k, x1=100, y1=10 * k + 8)
             for k, t in enumerate(["- I followed", "the system.. He added"])]  # fmt: skip
    pages = [PageText(number=1, width=200, height=300, lines=lines)]
    path = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page(width=200, height=300)
    doc.save(path)
    off = speckmarks.Specks(tmp_path / "off.json")
    off.survey(path, pages)
    assert off.doubts(None, 1, 0, "- I followed", [], None) == []
    specks = speckmarks.Specks(tmp_path / "s.json", line_marks=True)
    specks.survey(path, pages)
    assert specks.doubts(None, 1, 0, "- I followed", [], None) == [(0, 3, ["I"])]
    assert specks.doubts(None, 1, 1, "the system.. He added", [], None) == [(4, 12, ["system."])]
    # A place a reading already disputes isn't offered again.
    assert specks.doubts(None, 1, 0, "- I followed", [(0, 1)], None) == []
    # A book that ends words on two stops again and again prints them so.
    habit = [Line(text=t, x0=0, y0=10 * k, x1=100, y1=10 * k + 8)
             for k, t in enumerate(["dat wil..’", "en toen..", "nee..’ zei hij"])]  # fmt: skip
    styled = speckmarks.Specks(tmp_path / "h.json", line_marks=True)
    styled.survey(path, [PageText(number=1, width=200, height=300, lines=habit)])
    assert styled.doubts(None, 1, 0, "dat wil..’", [], None) == []
