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
