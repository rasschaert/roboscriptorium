import pymupdf

from roboscriptorium import pageroles
from roboscriptorium.pdf import Line, PageText


def test_a_reply_names_headings_and_furniture_and_leaves_the_rest_running_text():
    reply = 'Lines 1 and 9 are furniture.\n{"H": [2], "F": [1, 9]}'
    assert pageroles.parse(reply, 9) == {0: "other", 1: "heading", 8: "other"}
    # A number past the page, or not a number, names no line.
    assert pageroles.parse('{"H": [2, 40, "3"], "F": "none"}', 9) == {1: "heading"}
    assert pageroles.parse('{"H": []}', 9) == {}


def test_a_reply_without_an_answer_is_none():
    assert pageroles.parse("I cannot read this page.", 9) is None
    assert pageroles.parse('{"H": [2,}', 9) is None


def _page(texts: list[str]) -> PageText:
    return PageText(
        1, 400, 600, [Line(t, 40, 60 + 18 * i, 300, 72 + 18 * i) for i, t in enumerate(texts)]
    )


def test_the_lines_inside_a_picture_are_marked_so():
    from roboscriptorium.layout import Region

    page = _page(["Chapter One", "HEY BABY", "It was a cold day."])
    picture = Region("figure", 0.9, 30, 70, 310, 95)
    assert pageroles.listing(page, [picture]).splitlines() == [
        "1. Chapter One",
        "2. [inside a picture] HEY BABY",
        "3. It was a cold day.",
    ]
    assert "[inside" not in pageroles.listing(page)


def test_a_page_is_asked_once_and_again_when_its_lines_change(tmp_path, monkeypatch):
    doc = pymupdf.open()
    doc.new_page(width=400, height=600)
    doc.save(tmp_path / "source.pdf")
    asked = []

    def ask(png, text, model, url):
        asked.append(text)
        return '{"H": [1], "F": []}' if len(asked) < 3 else "no answer"

    monkeypatch.setattr(pageroles, "ask", ask)
    args = (tmp_path / "source.pdf",)
    rest = ("qwen", "", tmp_path / "page-roles.json")
    page = _page(["HOOFDSTUK 1", "Het begon op een dinsdag."])
    assert pageroles.page_roles(*args, [page], *rest) == {1: {0: "heading"}}
    assert pageroles.page_roles(*args, [page], *rest) == {1: {0: "heading"}}
    assert len(asked) == 1
    # A line the missing-lines stage added changes what the page is asked with.
    more = _page(["HOOFDSTUK 1", "Het begon op een dinsdag.", "Een regel erbij."])
    assert pageroles.page_roles(*args, [more], *rest) == {1: {0: "heading"}}
    assert len(asked) == 2 and "3. Een regel erbij." in asked[-1]
    # A page whose reply holds no answer is left out, as if never asked.
    other = _page(["Iets anders."])
    assert pageroles.page_roles(*args, [other], *rest) == {}
