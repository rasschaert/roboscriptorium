from roboscriptorium import corrections, flags
from roboscriptorium.corrections import Corrections
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole


def _page(number: int = 1) -> PageText:
    lines = [Line("body text " * 5, 50, 80 + 15 * i, 350, 92 + 15 * i) for i in range(10)]
    lines[5] = Line("G.J. Sorgdrager * 1919", 150, 155, 250, 167)
    return PageText(number, 400, 600, lines)


def test_flags_a_dropped_inscription_and_centred_lines():
    page = _page()
    roles = {SourceRef(1, 5): LineRole("artifact", 0.5, 0.3)}
    found = flags.find([page], roles)
    assert [(f.first, f.treatment) for f in found] == [(5, "dropped")]
    assert set(found[0].reasons) == {"dropped-mid-page", "dropped-unsure"}


def test_answers_apply_and_go_stale_when_the_text_layer_changes(tmp_path):
    page = _page()
    roles = {SourceRef(1, 5): LineRole("artifact", 0.5, 0.3)}
    region = flags.find([page], roles)[0]
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(region, "text", "G.J. Sorgdrager * 13.6.1919")

    assert corrections.apply([page], roles, Corrections(tmp_path / "regions.jsonl")) == 1
    assert roles[SourceRef(1, 5)].role == "body"
    assert page.lines[5].text == "G.J. Sorgdrager * 13.6.1919"

    changed = _page()
    changed.lines[5] = Line("G.J. Sorgdrager", 150, 155, 250, 167)
    assert corrections.apply([changed], {}, answers) == 0


def test_text_typed_for_a_missing_region_is_inserted_with_its_paragraphs(tmp_path):
    from roboscriptorium.reflow import reflow

    page = _page()
    roles: dict = {}
    region = flags.Flag("p1-x", 1, 3, 2, "", "missing", ["missing-text"], (50, 125, 350, 150))
    answers = Corrections(tmp_path / "regions.jsonl")
    answers.record(region, "text", "First para-\ngraph wraps here.\n\nSecond one.")
    assert corrections.apply([page], roles, answers) == 1
    assert [ln.text for ln in page.lines[3:5]] == ["First paragraph wraps here.", "Second one."]
    texts = [b.text for b in reflow([page], roles)]
    assert any(t.endswith("First paragraph wraps here.") for t in texts)
    assert any(t.startswith("Second one.") for t in texts)
