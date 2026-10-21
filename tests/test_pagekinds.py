from types import SimpleNamespace

from roboscriptorium import pagekinds
from roboscriptorium.pdf import Line, PageText


def _page(number: int, words: int = 150) -> PageText:
    text = " ".join(["woord"] * words)
    return PageText(
        number, 280, 500, [Line(text, 10, 20 + i * 12, 250, 30 + i * 12) for i in range(25)]
    )


class _Client:
    """A decision model that calls every page it is shown a cover, counting its calls."""

    def __init__(self):
        self.calls = []

    def decide(self, state, questions, image_png=None):
        self.calls.append(state["page"])
        return {"kind": SimpleNamespace(value="cover", confidence=0.9)}


def test_a_page_is_named_by_both_its_numbers_or_says_it_prints_none():
    assert pagekinds.page_label(9, 2) == "PDF page 9 (the page prints 7)"
    assert pagekinds.page_label(9, None) == "PDF page 9 (the page prints no number)"
    # Front matter sits before the first printed number: the offset gives none above zero.
    assert pagekinds.page_label(2, 2) == "PDF page 2 (the page prints no number)"


def test_the_model_answers_the_edge_pages_and_the_signals_the_middle(tmp_path, monkeypatch):
    monkeypatch.setattr(pagekinds, "render_png", lambda pdf, n: b"png")
    pages = [_page(n) for n in range(1, 41)]
    client = _Client()
    out = pagekinds.kinds(
        tmp_path / "work" / "book" / "source.pdf", pages, client, tmp_path / "a.json"
    )
    edge = pagekinds.edge_pages(40)
    assert edge == set(range(1, 9)) | set(range(33, 41))
    assert sorted(int(c.split(" ")[0]) for c in client.calls) == sorted(edge)
    assert all(out[n] == "cover" for n in edge)
    assert all(out[n] == "text" for n in range(9, 33))


def test_a_rerun_asks_only_what_the_cache_lacks(tmp_path, monkeypatch):
    monkeypatch.setattr(pagekinds, "render_png", lambda pdf, n: b"png")
    pages = [_page(n) for n in range(1, 21)]
    pdf, cache = tmp_path / "work" / "book" / "source.pdf", tmp_path / "a.json"
    first = _Client()
    pagekinds.kinds(pdf, pages, first, cache)
    second = _Client()
    again = pagekinds.kinds(pdf, pages, second, cache)
    assert first.calls and not second.calls
    assert again[1] == "cover"


def test_the_text_proper_runs_from_its_first_to_its_last_page_that_goes_into_the_book():
    kinds = {
        1: "cover",
        2: "blank",
        3: "colophon",
        4: "text",
        5: "text",
        6: "afterword",
        7: "ads",
        8: "back-cover",
    }
    assert pagekinds.ends(kinds) == (4, 6)
