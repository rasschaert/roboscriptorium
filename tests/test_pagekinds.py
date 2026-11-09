from types import SimpleNamespace

from roboscriptorium import pagekinds
from roboscriptorium.pdf import Line, PageText


def _page(number: int, words: int = 150) -> PageText:
    text = " ".join(["woord"] * words)
    return PageText(
        number, 280, 500, [Line(text, 10, 20 + i * 12, 250, 30 + i * 12) for i in range(25)]
    )


class _Client:
    """A decision model that calls the two pages at either end a cover and every other
    page text, or what `kinds` says of it, counting its calls."""

    def __init__(self, kinds: dict[int, str] | None = None):
        self.calls = []
        self.kinds = kinds or {}

    def decide(self, state, questions, image_png=None):
        self.calls.append(state["page"])
        n, total = (int(w) for w in state["page"].split(" of "))
        kind = "cover" if n <= 2 or n >= total - 1 else "text"
        return {"kind": SimpleNamespace(value=self.kinds.get(n, kind), confidence=0.9)}


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
    assert all(out[n] == "cover" for n in (1, 2, 39, 40))
    assert all(out[n] == "text" for n in range(3, 39))


def test_past_the_edge_the_model_goes_on_inward_until_the_text_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(pagekinds, "render_png", lambda pdf, n: b"png")
    pages = [_page(n) for n in range(1, 61)]
    # The publisher's lists and blurbs from p. 45, more than the edge's eight pages.
    client = _Client({n: "also-by" for n in range(45, 59)})
    out = pagekinds.kinds(
        tmp_path / "work" / "book" / "source.pdf", pages, client, tmp_path / "a.json"
    )
    asked = sorted(int(c.split(" ")[0]) for c in client.calls)
    assert asked == list(range(1, 9)) + list(range(42, 61))
    assert pagekinds.ends(out) == (3, 44)


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


def test_answers_to_another_wording_of_the_question_are_asked_again(tmp_path, monkeypatch):
    monkeypatch.setattr(pagekinds, "render_png", lambda pdf, n: b"png")
    pages = [_page(n) for n in range(1, 21)]
    pdf, cache = tmp_path / "work" / "book" / "source.pdf", tmp_path / "a.json"
    pagekinds.kinds(pdf, pages, _Client(), cache)
    monkeypatch.setattr(pagekinds, "TAG", "another")
    second = _Client()
    pagekinds.kinds(pdf, pages, second, cache)
    assert len(second.calls) == len(pagekinds.edge_pages(20))


def test_answers_of_another_model_are_asked_again(tmp_path, monkeypatch):
    monkeypatch.setattr(pagekinds, "render_png", lambda pdf, n: b"png")
    pages = [_page(n) for n in range(1, 21)]
    pdf, cache = tmp_path / "work" / "book" / "source.pdf", tmp_path / "a.json"
    small, large = _Client(), _Client()
    small.model, large.model = "small", "large"
    pagekinds.kinds(pdf, pages, small, cache)
    pagekinds.kinds(pdf, pages, large, cache)
    assert len(large.calls) == len(pagekinds.edge_pages(20))


def test_a_listing_page_inside_the_text_is_asked_and_a_contents_page_left_out(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(pagekinds, "render_png", lambda pdf, n: b"png")
    toc = PageText(11, 280, 500, [
        Line(f"{1884 + k}: Een hoofdstuk {13 + 20 * k}", 10, 20 + k * 12, 250, 30 + k * 12)
        for k in range(12)
    ])  # fmt: skip
    # A page of running text with a few years in it ends no line in a number.
    pages = [_page(10), toc, _page(12)]
    client = _Client({11: "contents"})
    out = pagekinds.set_apart(
        tmp_path / "w" / "b" / "source.pdf", pages, 300, client, tmp_path / "s.json"
    )
    assert out == {11: "omit"}
    assert [c.split(" ")[0] for c in client.calls] == ["11"]


def test_a_long_page_before_the_first_heading_is_asked_one_after_it_is_not(tmp_path, monkeypatch):
    monkeypatch.setattr(pagekinds, "render_png", lambda pdf, n: b"png")
    pages = [_page(7), _page(9)]
    client = _Client({7: "motto", 9: "motto"})
    cache = tmp_path / "s.json"
    out = pagekinds.set_apart(tmp_path / "w" / "b" / "source.pdf", pages, 300, client, cache, {7})
    assert out == {7: "epigraph"}
    assert [c.split(" ")[0] for c in client.calls] == ["7"]


def _headed(number: int, head: str, lines: int) -> PageText:
    rows = [head] + ["a line of running text"] * (lines - 1)
    return PageText(
        number, 280, 500, [Line(t, 10, 20 + i * 12, 250, 30 + i * 12) for i, t in enumerate(rows)]
    )


def test_a_half_title_that_shares_the_running_heads_words_stays_out():
    # The half-title "Nervous System" sits before a blank page: not next to the text.
    pages = [_headed(1, "Nervous System", 3), _page(2, 0)]
    pages += [
        _headed(n, "JAN LARS JENSEN" if n % 2 else "NERVOUS SYSTEM", 25) for n in range(3, 30)
    ]
    kinds = {1: "half-title", 2: "blank"} | {n: "text" for n in range(3, 30)}
    assert pagekinds.run_on(kinds, pages) == kinds


def test_a_lone_head_without_text_under_it_stays_out():
    pages = [_headed(n, "JAN LARS JENSEN", 25) for n in range(1, 21)]
    pages.append(_headed(21, "JAN LARS JENSEN", 1))
    kinds = {n: "text" for n in range(1, 21)} | {21: "blank"}
    assert pagekinds.run_on(kinds, pages)[21] == "blank"


def test_a_page_under_the_running_head_past_the_end_carries_the_text_on():
    pages = [_headed(n, "JAN LARS JENSEN" if n % 2 else "NERVOUS SYSTEM", 25) for n in range(1, 21)]
    pages += [_headed(21, "JAN LARS JENSEN", 4), _page(22, 30)]
    kinds = {n: "text" for n in range(1, 20)} | {20: "acknowledgements", 21: "praise", 22: "praise"}
    out = pagekinds.run_on(kinds, pages)
    assert out[21] == "text" and out[22] == "praise"
    assert pagekinds.ends(out) == (1, 21)


def test_the_text_proper_starts_after_the_title_page_the_model_is_sure_of():
    kinds = {1: "cover", 2: "about-author", 3: "also-by", 4: "title", 5: "colophon"}
    kinds |= {6: "dedication", 7: "text", 8: "text"}
    out = pagekinds.after_title(kinds, {4: "title", 5: "colophon"})
    assert out[2] == "about-author (before the title page)"
    assert pagekinds.ends(out) == (6, 8)


def test_an_unsure_colophon_after_the_dedication_moves_nothing():
    kinds = {1: "cover", 2: "title", 3: "colophon", 4: "dedication", 5: "colophon", 6: "text"}
    # Page 5 was called a colophon below `SURE_FRONT`: it isn't in `sure`.
    out = pagekinds.after_title(kinds, {2: "title", 3: "colophon"})
    assert pagekinds.ends(out) == (4, 6)
