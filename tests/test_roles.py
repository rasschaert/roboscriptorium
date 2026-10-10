from roboscriptorium.clients.decide import Answer
from roboscriptorium.ir import SourceRef
from roboscriptorium.page import Repeats, bare_numeral, title_key
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import DecisionCache, classify


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
    from roboscriptorium.page import garbled

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
    # A role a rule set says which rule; the model's own answer has none.
    assert roles[SourceRef(10, 0)].rule == "sunk-numeral"
    assert roles[SourceRef(3, 0)].rule == ""


def test_a_number_and_title_opening_a_sunk_page_is_a_heading(tmp_path):
    # Running heads hold a page number and a title too, but not on a sunk page.
    pages = [_page(n, f"{n + 4} Vals alarm") for n in range(1, 10)]
    for n, top in [(10, "1 Later"), (11, "3 mei kwam hij eindelijk thuis, moe en nat.")]:
        pages.append(PageText(n, 400, 600, [Line(top, 150, 150, 250, 162)] + pages[0].lines[1:]))

    class Client:
        model = "fake"

        def decide(self, state, questions):
            if state["line"].startswith("body text"):
                return {"role": Answer("choice", "body", 0.9, {"body": 0.9})}
            return {"role": Answer("choice", "page_number", 0.9, {"page_number": 0.9, "body": 0.1})}

    roles = classify(pages, Client(), DecisionCache(tmp_path / "decisions.jsonl"))
    assert roles[SourceRef(10, 0)].role == "chapter_heading"
    assert roles[SourceRef(10, 0)].rule == "section-number"
    assert roles[SourceRef(3, 0)].role == "page_number"
    assert roles[SourceRef(11, 0)].role != "chapter_heading"


def test_running_title_keys():
    assert title_key("Animal Language II", 11) == title_key("ANIMAL LANGUAGE", 10)
    assert title_key("12 The Story of Doctor Dolittle", 12) == "THESTORYOFDOCTORDOLITTLE"
    assert title_key("SENSE AND SENSIBILITY 28", 23) == "SENSEANDSENSIBILITY"  # a misread folio
    assert title_key("SENSE AND SENSIBILITY 23") == "SENSEANDSENSIBILITY"  # folio unknown
    assert title_key("CHAPTER XL1I.") != title_key("CHAPTER XLI.")


def test_chapter_numbers_are_not_page_numbers():
    assert title_key("CHAPTER 2", 29) != title_key("CHAPTER 3", 53)
    assert title_key("Hoofdstuk 3", 41) == "HOOFDSTUK3"
    assert title_key("DEEL II", 11) == "DEEL"  # only where it reads as the folio
    assert title_key("DEEL II", 40) != title_key("DEEL III", 90)


def test_short_last_line_of_a_sentence_is_body(tmp_path):
    page = _page(1, "Running head")
    page.lines.append(Line("weten.", 50, 260, 90, 272))

    class Client:
        model = "fake"

        def decide(self, state, questions):
            return {"role": Answer("choice", "artifact", 0.6, {"artifact": 0.6, "body": 0.3})}

    roles = classify([page], Client(), DecisionCache(tmp_path / "decisions.jsonl"))
    assert roles[SourceRef(1, len(page.lines) - 1)].role == "body"
    assert roles[SourceRef(1, 0)].role == "artifact"


def test_a_chapter_label_off_centre_is_a_candidate():
    from roboscriptorium.roles import candidates

    lines = [Line("body text " * 6, 12, 20 + 12 * i, 258, 30 + 12 * i) for i in range(20)]
    lines[10] = Line("» CHAPTER XXV.", 65, 140, 179, 152)
    lines[12] = Line("the next chapter of her life", 12, 164, 150, 174)
    found = candidates(PageText(139, 270, 400, lines))
    assert 10 in found and 12 not in found


def test_a_set_apart_first_line_of_a_sunk_opening_is_its_heading(tmp_path):
    body = [Line("body text " * 5, 50, 200 + 15 * i, 350, 212 + 15 * i) for i in range(10)]
    pages = [_page(n, f"{n} Running head") for n in range(1, 10)]
    # A label at the usual height above text that starts low, like "EEN".
    pages.append(PageText(10, 400, 600, [Line("EEN", 180, 50, 220, 60)] + body))
    # A short line run on into the text is not set apart.
    close = [Line("Kort.", 180, 185, 220, 197)] + body
    pages.append(PageText(11, 400, 600, close))

    class Client:
        model = "fake"

        def decide(self, state, questions):
            if state["line"].startswith("body text"):
                return {"role": Answer("choice", "body", 0.9, {"body": 0.9})}
            return {"role": Answer("choice", "page_number", 0.9, {"page_number": 0.9, "body": 0.1})}

    roles = classify(pages, Client(), DecisionCache(tmp_path / "decisions.jsonl"))
    assert roles[SourceRef(10, 0)].rule == "sunk-opening"
    assert roles[SourceRef(11, 0)].role != "chapter_heading"
    assert roles[SourceRef(3, 0)].role != "chapter_heading"


def test_lines_set_like_the_headings_are_headings(tmp_path):
    from roboscriptorium.typestyle import Style

    tops = {2: "EEN", 4: "TWEE", 6: "DONDERDAG 16 MAART", 3: "Stempel"}
    pages = [_page(n, tops.get(n, f"Kop {n}")) for n in range(1, 10)]
    pages[7].lines.append(Line("SO", 300, 260, 320, 270))  # p8, at the foot
    answers = {
        "EEN": ("chapter_heading", 0.6),
        "TWEE": ("chapter_heading", 0.5),
        "DONDERDAG 16 MAART": ("artifact", 0.4),
        "Stempel": ("artifact", 0.4),
        "SO": ("artifact", 0.3),
    }

    class Client:
        model = "fake"

        def decide(self, state, questions):
            role, p = answers.get(state["line"], ("running_head", 0.9))
            return {"role": Answer("choice", role, p, {role: p, "body": 0.05})}

    display = Style(1.5, 1.0, 1.5, True)
    styles = {SourceRef(n, 0): display for n in (2, 4, 6)}
    styles[SourceRef(8, 11)] = display
    styles[SourceRef(3, 0)] = Style(1.0, 1.0, 1.0, False)
    roles = classify(pages, Client(), DecisionCache(tmp_path / "decisions.jsonl"), styles)
    assert roles[SourceRef(6, 0)].role == "chapter_heading"
    assert roles[SourceRef(6, 0)].rule == "heading-style"
    assert roles[SourceRef(2, 0)].rule == ""
    # Not set like the headings: body type, or in another place on the page.
    assert roles[SourceRef(3, 0)].role == "artifact"
    assert roles[SourceRef(8, 11)].role == "artifact"


def _numbered_pages(heads: dict[int, str], offset: int = 16) -> list[PageText]:
    """Pages with a printed folio at the foot (page number minus `offset`) and `heads` on top."""
    pages = []
    for n in range(20, 100):
        lines = _page(n, heads.get(n, "body text " * 5)).lines
        lines.append(Line(str(n - offset), 190, 560, 210, 570))
        pages.append(PageText(n, 400, 600, lines))
    return pages


def test_chapter_labels_with_numbers_are_not_repeats_of_each_other():
    pages = _numbered_pages({25: "CHAPTER 1", 45: "CHAPTER 2", 69: "CHAPTER 3", 80: "CHAPTER 4"})
    repeats = Repeats(pages)
    assert repeats.other_pages("CHAPTER 2", 45) == 0
    assert repeats.other_pages("Hoofdstuk 3", 69) == 0


def test_a_running_head_of_digits_repeats_and_page_numbers_alone_do_not():
    heads = {n: "11/22/63" if n % 2 else "STEPHEN KING" for n in range(27, 60)}
    heads[63] = "11/22/63 “A"
    repeats = Repeats(_numbered_pages(heads))
    assert repeats.other_pages("11/22/63 “A", 63) >= 10
    assert repeats.other_pages("11/22/63", 27) >= 10
    assert repeats.other_pages(str(40 - 16), 40) == 0
    assert repeats.other_pages("124", 40) == 0


def test_a_running_head_with_its_folio_at_either_end_repeats():
    heads = {n: f"SENSE AND SENSIBILITY {n - 16}" for n in range(30, 60, 2)}
    heads |= {n: f"{n - 16} SENSE AND SENSIBILITY" for n in range(31, 60, 2)}
    repeats = Repeats(_numbered_pages(heads))
    assert repeats.other_pages("SENSE AND SENSIBILITY 23", 39) >= 20
    assert repeats.other_pages("28 SENSE AND SENSIBILITY", 39) >= 20  # a misread folio


def test_numbered_chapter_labels_stay_headings(tmp_path):
    pages = _numbered_pages({25: "CHAPTER 1", 45: "CHAPTER 2", 69: "CHAPTER 3"})

    class Client:
        model = "fake"

        def decide(self, state, questions):
            if state["line"].startswith("CHAPTER"):
                return {"role": Answer("choice", "chapter_heading", 0.9, {"body": 0.1})}
            return {"role": Answer("choice", "body", 0.9, {"body": 0.9})}

    roles = classify(pages, Client(), DecisionCache(tmp_path / "decisions.jsonl"))
    assert [roles[SourceRef(n, 0)].role for n in (25, 45, 69)] == ["chapter_heading"] * 3


def test_a_chapter_label_on_its_own_printed_page_number_stays_a_heading(tmp_path):
    pages = _numbered_pages({25: "CHAPTER 1", 40: "16 SENSE AND SENSIBILITY"}, offset=24)

    class Client:
        model = "fake"

        def decide(self, state, questions):
            if "SENSE" in state["line"] or "CHAPTER" in state["line"]:
                return {"role": Answer("choice", "chapter_heading", 0.9, {"body": 0.1})}
            return {"role": Answer("choice", "body", 0.9, {"body": 0.9})}

    roles = classify(pages, Client(), DecisionCache(tmp_path / "decisions.jsonl"))
    assert roles[SourceRef(25, 0)].role == "chapter_heading"
    assert roles[SourceRef(40, 0)].rule == "printed-page-number"


def test_an_answer_cut_off_by_an_interrupted_run_does_not_swallow_the_next(tmp_path):
    path = tmp_path / "decisions.jsonl"
    path.write_text('{"key": "a", "answer": {"role": "body"}}\n{"key": "b", "answ')
    DecisionCache(path).put("c", {"role": "page_number"})
    assert DecisionCache(path).get("c") == {"role": "page_number"}
    assert DecisionCache(path).get("a") == {"role": "body"}


def _foliated(number: int, middle: list[Line] = ()) -> PageText:
    """A page with a running head, body lines with `middle` set among them, and its
    printed number (the page's number less 4) centred at the foot."""
    body = [Line("body text " * 5, 50, 80 + 15 * i, 350, 92 + 15 * i) for i in range(20)]
    lines = [Line("RUNNING TITLE", 150, 40, 250, 50), *body[:8], *middle, *body[8:]]
    return PageText(number, 400, 600, lines + [Line(str(number - 4), 195, 560, 205, 570)])


class _NumbersAsPageNumbers:
    model = "fake"

    def decide(self, state, questions):
        if state["line"].startswith("body text"):
            return {"role": Answer("choice", "body", 0.9, {"body": 0.9})}
        return {"role": Answer("choice", "page_number", 0.9, {"page_number": 0.9, "body": 0.1})}


def test_a_numeral_that_isnt_the_folio_is_no_page_number_mid_page_either(tmp_path):
    pages = [_foliated(n) for n in range(5, 15)]
    # Not headings: a speck in the margin, the folio's own number mid-page, a number
    # with no text below it.
    pages.append(_foliated(15, [Line("4", 20, 205, 26, 215)]))
    pages.append(_foliated(16, [Line("12", 194, 205, 206, 215)]))
    pages.append(PageText(17, 400, 600, [*_foliated(17).lines[:-1], Line("3", 195, 540, 205, 550)]))
    # A heading: a centred section number between two paragraphs, close to the folio (14).
    pages.append(_foliated(18, [Line("9", 196, 205, 204, 215)]))
    roles = classify(pages, _NumbersAsPageNumbers(), DecisionCache(tmp_path / "d.jsonl"))
    assert roles[SourceRef(18, 9)].role == "chapter_heading"
    assert roles[SourceRef(18, 9)].rule == "section-number"
    for ref in [SourceRef(15, 9), SourceRef(16, 9), SourceRef(17, 21), SourceRef(18, 22)]:
        assert roles[ref].role != "chapter_heading", ref


def test_numbered_chapter_labels_differ_when_the_folio_is_unknown():
    # A born-digital PDF prints no page numbers, so no number can be taken for a folio
    # after a label word; a running head's trailing number still can.
    assert title_key("Hoofdstuk 2") != title_key("Hoofdstuk 3")
    assert title_key("SENSE AND SENSIBILITY 23") == title_key("SENSE AND SENSIBILITY 24")
    pages = [
        PageText(n, 400, 600, [Line(f"Hoofdstuk {n}", 150, 60, 250, 90), *_page(n, "x").lines[1:]])
        for n in range(1, 13)
    ]
    repeats = Repeats(pages)
    assert repeats.other_pages("Hoofdstuk 5", 5) == 0


def test_a_top_number_is_a_section_where_the_page_prints_its_folio_elsewhere(tmp_path):
    pages = [_foliated(n) for n in range(5, 15)]
    # Page 11 prints its folio, 7, at the foot: a "1" at the top, near 7, is a section.
    top = Line("1", 196, 30, 204, 40)
    pages[6] = PageText(11, 400, 600, [top, *_foliated(11).lines[1:]])
    # Page 12 prints no folio of its own: a "6" at the top may be a misread 8.
    pages[7] = PageText(12, 400, 600, [Line("6", 196, 30, 204, 40), *_foliated(12).lines[1:-1]])
    roles = classify(pages, _NumbersAsPageNumbers(), DecisionCache(tmp_path / "d.jsonl"))
    assert roles[SourceRef(11, 0)].role == "chapter_heading"
    assert roles[SourceRef(12, 0)].role != "chapter_heading"


def test_a_misread_numeral_in_a_numeral_headings_place_is_a_heading(tmp_path):
    def opening(number: int, top: Line) -> PageText:
        return PageText(number, 400, 600, [top] + _page(number, "x").lines[1:])

    pages = [opening(n, Line(str(k), 190, 40, 210, 62)) for k, n in enumerate((11, 15, 19), 1)]
    pages += [
        opening(24, Line("l", 192, 41, 208, 63)),  # the "1" of a later part, misread
        opening(25, Line("peeters bent och kane eg u.", 60, 40, 340, 62)),  # a washed-out line
        opening(26, Line("e,", 60, 41, 80, 63)),  # boxed alike, but off-centre
        opening(27, Line("°", 196, 50, 204, 56)),  # a speck, not a numeral's height
    ]

    class Client:
        model = "fake"

        def decide(self, state, questions):
            if state["line"].startswith("body text"):
                return {"role": Answer("choice", "body", 0.9, {"body": 0.9})}
            return {"role": Answer("choice", "artifact", 0.5, {"artifact": 0.5, "body": 0.05})}

    roles = classify(pages, Client(), DecisionCache(tmp_path / "decisions.jsonl"))
    assert [roles[SourceRef(n, 0)].rule for n in (11, 15, 19)] == ["section-number"] * 3
    assert roles[SourceRef(24, 0)].role == "chapter_heading"
    assert roles[SourceRef(24, 0)].rule == "numeral-slot"
    for n in (25, 26, 27):
        assert roles[SourceRef(n, 0)].role == "artifact", n


def test_a_superscript_or_circled_digit_is_no_page_number():
    from roboscriptorium.page import digits, page_number, page_offset

    assert not digits("¹") and not digits("③") and digits("12")
    assert page_number("¹ Zie de inleiding.") is None
    assert page_number("Puddleby 5") == 5
    pages = [_page(n, "¹ Zie noot") for n in range(1, 4)]
    assert page_offset(pages) is None  # no ValueError from int("¹")
    assert title_key("CHAPTER ¹") == "CHAPTER"


def test_a_short_pages_edge_lines_count_once():
    from roboscriptorium.page import edge_lines, page_offset

    assert edge_lines(PageText(7, 400, 600, [Line("5 tekst", 50, 50, 300, 60)] * 3)) == [0, 1, 2]
    # Two pages with a number each are two pages, not four: the offset stays unknown.
    pages = [
        PageText(
            n,
            400,
            600,
            [
                Line(f"{n - 2} tekst" if i == 0 else "tekst", 50, 50 + 15 * i, 300, 60 + 15 * i)
                for i in range(3)
            ],
        )
        for n in (7, 8)
    ]
    assert page_offset(pages) is None


def test_a_heading_labels_number_is_never_taken_for_the_folio():
    # "Hoofdstuk 12" on printed page 15 is a digit's misread away from the folio; it is
    # still chapter 12, so two such headings don't collide as repeated titles.
    assert title_key("Hoofdstuk 12", 15) == "HOOFDSTUK12"
    assert title_key("Hoofdstuk 12", 15) != title_key("Hoofdstuk 13", 17)
    assert title_key("Hoofdstuk 12") == "HOOFDSTUK12"
    # A folio after a label line is still a folio.
    assert title_key("Hoofdstuk 3 41", 41) == "HOOFDSTUK3"


def test_a_lone_number_on_a_page_is_no_section_heading():
    from roboscriptorium.roles import _section_number

    lone = PageText(6, 400, 600, [Line("12", 190, 300, 210, 310)])
    assert not _section_number(lone, 0, None, {}, sunk=False)
    above = PageText(
        6, 400, 600, [Line("12", 190, 80, 210, 90), Line("tekst " * 6, 50, 110, 350, 122)]
    )
    assert _section_number(above, 0, None, {}, sunk=False)
    # A numbered title alone on a sunk opening still heads it.
    titled = PageText(6, 400, 600, [Line("1 Later", 190, 300, 240, 310)])
    assert _section_number(titled, 0, None, {}, sunk=True)
