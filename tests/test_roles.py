from roboscriptorium.clients.ollaya import Answer
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import DecisionCache, Repeats, _title_key, bare_numeral, classify


def _page(number: int, top: str) -> PageText:
    lines = [Line(top, 100, 50, 300, 60)] + [
        Line("body text " * 5, 50, 80 + 15 * i, 350, 92 + 15 * i) for i in range(10)
    ]
    return PageText(number, 400, 600, lines)


def test_running_heads_repeat_but_chapter_numbers_differ():
    pages = [_page(1, "CHAPTER I.")] + [
        _page(n, f"SENSE AND SENSIBILITY. {n}" if n % 3 else f"CHAPTER {'I' * (n // 3 + 1)}.")
        for n in range(2, 20)
    ]
    repeats = Repeats(pages)
    assert repeats.other_pages("CHAPTER II.", 3) == 0
    assert repeats.other_pages("SENSE AND SENSIBILTY. 4", 4) >= 5  # OCR noise still matches


def test_ordinal_headings_are_not_repeats_of_each_other():
    ordinals = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH", "EIGHTH"]
    pages = [_page(i + 1, f"THE {o} CHAPTER") for i, o in enumerate(ordinals)]
    pages += [_page(20 + i, f"More Money Troubles {i}") for i in range(3)]
    pages.append(_page(30, "More Monev Troubles"))
    repeats = Repeats(pages)
    assert repeats.other_pages("THE SIXTH CHAPTER", 6) == 0
    assert repeats.other_pages("More Monev Troubles", 30) == 3


def test_garbled_lines_are_candidates():
    from roboscriptorium.roles import garbled

    assert garbled(Line("r^fl rgeiKh WBpSBjlHpilT rtttnf: f- ''.'.", 0, 0, 1, 1))
    assert not garbled(Line("Then his sister, Sarah Dolittle, came to him", 0, 0, 1, 1))
    assert not garbled(Line('"John, how can you expect sick people—', 0, 0, 1, 1))


def test_bare_numerals():
    assert bare_numeral("VIII") == "VIII"
    assert bare_numeral("Ill") == "III"
    assert bare_numeral("IV.") == "IV"
    assert bare_numeral("I wrote") == ""
    assert bare_numeral("lll") == ""


def test_bare_numeral_on_a_sunk_page_is_a_heading(tmp_path):
    pages = [_page(n, f"Running head {n}") for n in range(1, 10)]
    sunk = PageText(10, 400, 600, [Line("V", 190, 150, 210, 162)] + _page(10, "x").lines[1:])
    pages.append(sunk)

    class Client:
        model = "fake"

        def decide(self, state, questions):
            return {"role": Answer("choice", "page_number", 0.9, {"page_number": 0.9, "body": 0.1})}

    roles = classify(pages, Client(), DecisionCache(tmp_path / "decisions.jsonl"))
    assert roles[SourceRef(10, 0)].role == "chapter_heading"
    assert roles[SourceRef(3, 0)].role == "page_number"


def test_running_title_keys():
    assert _title_key("Animal Language II") == _title_key("ANIMAL LANGUAGE")
    assert _title_key("12 The Story of Doctor Dolittle") == "THESTORYOFDOCTORDOLITTLE"
    assert _title_key("CHAPTER XL1I.") != _title_key("CHAPTER XLI.")
