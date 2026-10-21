from roboscriptorium import bookinit, pagekinds
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import Line, PageText


def _page(number: int, text: str, footer: str = "") -> PageText:
    lines = [Line(text, 10, 20, 250, 30)]
    if footer:
        lines.append(Line(footer, 130, 480, 140, 490))
    return PageText(number, 280, 500, lines)


def test_a_folder_name_comes_from_the_files_name():
    assert (
        bookinit.slug("Het Geluid van Bananen (2013).pdf".removesuffix(".pdf"))
        == "het-geluid-van-bananen-2013"
    )
    assert bookinit.slug("???") == "book"


def test_the_language_is_the_one_whose_word_list_knows_more_of_the_text():
    pages = [_page(1, "de man liep naar het huis en zag een hond in de tuin")]
    lexicons = {
        "nl": Lexicon(
            {"de", "man", "liep", "naar", "het", "huis", "en", "zag", "een", "hond", "in", "tuin"}
        ),
        "en": Lexicon({"man", "in", "the", "and"}),
    }
    language, shares = bookinit.language_of(pages, lexicons)
    assert language == "nl" and shares["nl"] > shares["en"]


def _draft() -> bookinit.Draft:
    pages = [
        _page(n, "tekst op de pagina", footer=str(n - 2) if n > 2 else "") for n in range(1, 13)
    ]
    kinds = {
        1: "cover",
        2: "title",
        3: "colophon",
        **{n: "text" for n in range(4, 11)},
        11: "ads",
        12: "back-cover",
    }
    return bookinit.draft(
        "het-boek",
        pages,
        kinds,
        {"nl": Lexicon({"tekst", "op", "de", "pagina"}), "en": Lexicon(set())},
    )


def test_the_draft_names_the_ends_by_both_numbers_and_leaves_title_and_author_to_a_person():
    d = _draft()
    assert (d.first, d.last) == (4, 10) and d.cover == 1 and d.language == "nl"
    text = bookinit.toml(d)
    assert "body_pages = [4, 10]" in text
    assert "PDF page 4 (the page prints 2)" in text and "PDF page 10 (the page prints 8)" in text
    assert 'title = ""' in text and 'author = ""' in text and "confirm" in text


def test_the_report_shows_the_pages_around_each_end_with_both_numbers():
    d = _draft()
    report = bookinit.report(d)
    assert "**First page:** PDF page 4 (the page prints 2)" in report
    assert "**Last page:** PDF page 10 (the page prints 8)" in report
    # The page after the last end is an advert, which doesn't go in the book.
    assert "| PDF page 11 (the page prints 9) | ads | no |" in report
    assert "**← the end**" in report


def test_the_title_pages_lines_are_kept_for_confirmation():
    pages = [_page(1, "Een Titel"), _page(2, "Voor Mia")]
    assert bookinit.title_lines(pages, {1: "title", 2: "dedication"}) == ["Een Titel"]
    assert bookinit.title_lines(pages, {1: "text"}) == []
    assert pagekinds.fate("title") == "details"
