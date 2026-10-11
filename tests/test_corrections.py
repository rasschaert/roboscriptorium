"""A human's answers applied to copies of the pages, beside the OCR check's fixes."""

from roboscriptorium import flags
from roboscriptorium.corrections import Corrections, apply
from roboscriptorium.ir import SourceRef
from roboscriptorium.ocrcheck import Suspect
from roboscriptorium.pdf import Line, PageText


def _page(*texts: str) -> PageText:
    return PageText(
        3, 300, 400, [Line(t, 10, 10 + 20 * i, 250, 20 + 20 * i) for i, t in enumerate(texts)]
    )


def _fix(line: str, start: int, end: int, chosen: str) -> Suspect:
    return Suspect(3, 0, line, start, end, line[start:end], (chosen,), (start, 0, end, 1),
                   "other", chosen)  # fmt: skip


def test_a_place_answered_in_a_line_later_retyped_whole_leaves_the_retyped_text(tmp_path):
    line = "Hij zei: “Nee."
    page = _page(line)
    answers = Corrections(tmp_path / "regions.jsonl")
    place = flags.Flag("place", 3, 0, 0, line, "text", ["ocr-doubt"], span=(9, 14))
    answers.record(place, "text", "Hij zei: “Nee.”")
    whole = flags.Flag(flags.region_key(3, line), 3, 0, 0, line, "text", ["centred"])
    answers.record(whole, "text", "Hij zei: “Neen.”")
    out, _, _ = apply([page], {}, Corrections(tmp_path / "regions.jsonl"))
    assert out[0].lines[0].text == "Hij zei: “Neen.”"


def test_a_place_answer_alone_still_changes_its_place(tmp_path):
    line = "Hij zei: “Nee."
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(flags.Flag("place", 3, 0, 0, line, "text", [], span=(9, 14)), "text",
                   "Hij zei: “Nee.”")  # fmt: skip
    out, _, applied = apply([_page(line)], {}, answers)
    assert out[0].lines[0].text == "Hij zei: “Nee.”"
    assert applied == 1


def test_a_role_answered_without_text_keeps_the_ocr_checks_fixes(tmp_path):
    line = "HOOFDSTUK Io"
    page = _page(line, "Het begon op een dinsdag.")
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(flags.Flag(flags.region_key(3, line), 3, 0, 0, line, "heading", []), "heading",
                   None)  # fmt: skip
    out, roles, applied = apply([page], {}, answers, [_fix(line, 10, 12, "10")])
    assert out[0].lines[0].text == "HOOFDSTUK 10"
    assert roles[SourceRef(3, 0)].role == "chapter_heading"
    assert applied == 1


def test_a_line_retyped_with_text_takes_no_fixes(tmp_path):
    line = "HOOFDSTUK Io"
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(flags.Flag(flags.region_key(3, line), 3, 0, 0, line, "heading", []), "heading",
                   "HOOFDSTUK TIEN")  # fmt: skip
    out, _, _ = apply([_page(line)], {}, answers, [_fix(line, 10, 12, "10")])
    assert out[0].lines[0].text == "HOOFDSTUK TIEN"


def _retyped(tmp_path, original: str, typed: str) -> str:
    page = _page(*original.split("\n"))
    answers = Corrections(tmp_path / "regions.jsonl")
    flag = flags.Flag(flags.region_key(3, original), 3, 0, original.count("\n"), original,
                      "text", ["centred"])  # fmt: skip
    answers.record(flag, "text", typed)
    out, _, _ = apply([page], {}, Corrections(tmp_path / "regions.jsonl"))
    return out[0].lines[0].text


def test_lines_retyped_together_keep_a_hyphen_that_is_the_words(tmp_path):
    typed = "ze woonde in Noord-\nHolland, niet ver"
    assert _retyped(tmp_path, typed.replace("ze", "zc"), typed) == (
        "ze woonde in Noord-Holland, niet ver"
    )
    typed = "een zee-egel op\nhet strand"
    assert _retyped(tmp_path, typed.replace("op", "0p"), typed) == "een zee-egel op het strand"


def test_lines_retyped_together_lose_the_breaks_hyphen(tmp_path):
    typed = "al helemáál geen hulp te ver-\nwachten. Voor hem"
    assert _retyped(tmp_path, typed.replace("á", "a"), typed) == (
        "al helemáál geen hulp te verwachten. Voor hem"
    )


def test_lines_merged_into_a_retyped_region_stay_merged_under_a_later_answer(tmp_path):
    lines = ("Ik glimlachte. ‘Lief van je, zei ik, ‘maar", "niet, ze zag er echt", "uit.")
    page = _page(*lines, "Later ging ik zitten.")
    answers = Corrections(tmp_path / "regions.jsonl")
    whole = "\n".join(lines)
    answers.record(flags.Flag(flags.region_key(3, whole), 3, 0, 2, whole, "text", []), "text",
                   whole.replace("je,", "je,’"))  # fmt: skip
    part = "\n".join(lines[1:])
    answers.record(flags.Flag(flags.region_key(3, part), 3, 1, 2, part, "text", []), "text", None)
    later = "Later ging ik zitten."
    answers.record(flags.Flag(flags.region_key(3, later), 3, 3, 3, later, "drop", []), "text",
                   None)  # fmt: skip
    out, roles, _ = apply([page], {}, Corrections(tmp_path / "regions.jsonl"))
    assert (
        out[0].lines[0].text
        == "Ik glimlachte. ‘Lief van je,’ zei ik, ‘maar niet, ze zag er echt uit."
    )
    assert roles[SourceRef(3, 1)].role == roles[SourceRef(3, 2)].role == "artifact"
    assert roles[SourceRef(3, 3)].role == "body"


def test_a_typed_compound_keeps_one_hyphen_across_the_break():
    from roboscriptorium.corrections import Correction, place

    def answer(text):
        return Correction(
            "k", 3, 0, 0, "een vreemde zee-", "text", text, "", span=(12, 16), joined="egel"
        )

    assert place(answer("een vreemde zee-egel")) == "zee-"
    assert place(answer("een vreemde zeeegel")) == "zee-"
    assert place(answer("een vreemde zee egel")) == "zee"


def test_two_regions_typed_above_one_line_land_in_page_order(tmp_path):
    from roboscriptorium.roles import LineRole

    page = PageText(
        3,
        300,
        500,
        [Line("Eerste regel.", 20, 100, 280, 110), Line("Vierde regel.", 20, 130, 280, 140)],
    )
    roles = {SourceRef(3, k): LineRole("body", 0.9, 1.0) for k in range(2)}
    corrections = Corrections(tmp_path / "regions.jsonl")
    upper = flags.Flag("u", 3, 1, 0, "", "missing", ["missing"], box=(20, 112, 280, 114))
    lower = flags.Flag("l", 3, 1, 0, "", "missing", ["missing"], box=(20, 115, 280, 117))
    for order in ((upper, lower), (lower, upper)):
        corrections = Corrections(tmp_path / f"{order[0].key}.jsonl")
        corrections.record(
            order[0], "text", "Tweede regel." if order[0] is upper else "Derde regel."
        )
        corrections.record(
            order[1], "text", "Derde regel." if order[1] is lower else "Tweede regel."
        )
        pages, _, _ = apply([page], roles, corrections)
        assert [ln.text for ln in pages[0].lines] == [
            "Eerste regel.",
            "Tweede regel.",
            "Derde regel.",
            "Vierde regel.",
        ]
