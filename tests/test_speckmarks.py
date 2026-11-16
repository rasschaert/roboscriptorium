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
