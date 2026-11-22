import numpy as np

from roboscriptorium import lists
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText


def _strip(top, bottom, left, right, fill=1.0, high=100, wide=60):
    ink = np.zeros((high, wide), np.float32)
    ink[top:bottom, left:right] = fill
    return ink


def test_a_solid_blob_at_the_letters_middle_is_a_bullet():
    # Nervous System's squares: 20 of a strip's 100 rows tall, as wide, at its middle.
    assert lists.bullet(_strip(50, 70, 12, 32)) == 1.0
    # A capital I: tall and thin.
    assert lists.bullet(_strip(40, 82, 12, 20)) is None
    # A dash: wide and flat.
    assert lists.bullet(_strip(63, 69, 12, 60)) is None
    # A full stop: too small.
    assert lists.bullet(_strip(76, 82, 12, 18)) is None
    # A blob of the right size but hollow, like an o.
    ring = _strip(50, 70, 12, 32)
    ring[54:66, 16:28] = 0
    assert lists.bullet(ring) is None
    # A speck as big, but at the foot of the line.
    assert lists.bullet(_strip(78, 98, 12, 32)) is None


def test_only_a_short_token_with_text_after_it_may_be_a_bullet():
    assert lists.marker("e Square mountains.") == "e"
    assert lists.marker("¢ A librarian") == "¢"
    assert lists.marker("Square mountains.") is None
    assert lists.marker("e") is None


def test_items_lose_their_bullets_and_their_lines_after_them_join(tmp_path):
    found = lists.Lists(tmp_path / "lists.json")
    found.items = {SourceRef(1, 1): "e", SourceRef(1, 2): "e", SourceRef(1, 3): "¢"}
    found.continued = {SourceRef(1, 4)}
    found.kind = "square"
    texts = [
        "these ideas:",
        "e Square mountains.",
        "A pregnant woman who couldn't give birth.",  # an answer took the bullet out
        "• People addicted to a sweetness they",  # a fix read it as a bullet
        "remembered from childhood.",
        "When I had done this before,",
    ]
    page = PageText(
        1, 300, 400, [Line(t, 40, 20 * i, 280, 20 * i + 10) for i, t in enumerate(texts)]
    )
    out = found.apply([page])[0].lines
    assert [ln.text for ln in out] == [
        "these ideas:",
        "Square mountains.",
        "A pregnant woman who couldn't give birth.",
        "People addicted to a sweetness they",
        "remembered from childhood.",
        "When I had done this before,",
    ]
    assert [ln.item for ln in out] == ["", "square", "square", "square", "", ""]
    assert [ln.starts_paragraph for ln in out] == [None, True, True, True, False, True]
    assert found.markers() == {SourceRef(1, 1): 1, SourceRef(1, 2): 1, SourceRef(1, 3): 1}


def test_a_book_without_bullets_is_left_as_it_is(tmp_path):
    page = PageText(1, 300, 400, [Line("e Square mountains.", 40, 0, 280, 10)])
    assert lists.Lists(tmp_path / "lists.json").apply([page]) == [page]
