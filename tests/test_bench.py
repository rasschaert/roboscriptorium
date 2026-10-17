import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from roboscriptorium import bench, cli, evaluate, quality
from roboscriptorium.golden import scoring
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole


def _run(pages: dict[int, list[float]], **books: dict[int, list[float]]) -> dict:
    """A saved run of book "b" (and any others), each page's counts padded to six (the
    paragraph breaks, a seventh, only where given).
    Through JSON, as saved runs are read back: page numbers become strings."""
    every = {"b": pages, **books}
    padded = {
        n: {p: c if len(c) >= 7 else (c + [c[-1]] * 6)[:6] for p, c in pg.items()}
        for n, pg in every.items()
    }
    return json.loads(json.dumps({"books": {n: {"pages": pg} for n, pg in padded.items()}}))


def test_a_change_on_every_page_is_real_and_one_page_of_many_is_not():
    before = _run({p: [2, 1, 1, 1.1] for p in range(40)})
    everywhere = _run({p: [2, 0, 1, 0.1] for p in range(40)})
    one_page = _run({p: [2, 1 if p else 0, 1, 1.1] for p in range(40)})
    unasked = {c.measure: c for c in bench.compare(before, everywhere)}["unasked"]
    assert unasked.real and (unasked.before, unasked.after) == (1.0, 0.0)
    unasked = {c.measure: c for c in bench.compare(before, one_page)}["unasked"]
    assert not unasked.real


def test_only_pages_both_runs_scored_are_compared():
    before = _run({1: [5, 5, 0, 5], 2: [1, 1, 0, 1]})
    after = _run({2: [1, 1, 0, 1], 3: [9, 9, 0, 9]})
    wrong = {c.measure: c for c in bench.compare(before, after)}["wrong words"]
    assert (wrong.before, wrong.after) == (1.0, 1.0)


def test_after_review_counts_the_reviewers_slips_and_time_on_each_question():
    asked = [SimpleNamespace(page=1, first=0, last=0, reasons=["x"])] * 2
    counts = bench.page_counts([1, 2], [], asked, slips=(0.1, 0.25, 0.5))
    # Each question: its chance of a wrong answer, plus 1/20 of a wrong word for the time.
    assert counts[1][:3] == [0, 0, 2] and counts[1][6:] == [0, 0]
    assert counts[1][3:6] == pytest.approx([0.6, 0.3, 1.1])
    assert counts[2] == [0, 0, 0, 0.0, 0.0, 0.0, 0, 0]


def test_twenty_questions_that_catch_one_error_cost_more_than_they_save():
    # Before: one error a page, unasked. After: twenty questions a page catch it.
    before = _run({p: [1, 1, 0] for p in range(30)}, c={p: [1, 1, 0] for p in range(30)})
    after = _run({p: [1, 0, 20] for p in range(30)}, c={p: [1, 0, 20] for p in range(30)})
    assert bench.verdict(before, after).outcome == "worse"
    few = _run({p: [1, 0, 2] for p in range(30)}, c={p: [1, 0, 2] for p in range(30)})
    assert bench.verdict(before, few).outcome == "better"


def test_a_run_saved_under_another_question_cost_is_compared_at_todays():
    # The after-review figure saved (9.0) is not what is compared: unasked 1, 1 question.
    old = _run({p: [1, 1, 1, 9.0] for p in range(30)})
    new = _run({p: [1, 1, 1] for p in range(30)})
    change = {c.measure: c for c in bench.compare(old, new)}["after review"]
    assert change.before == change.after


def test_a_washed_out_page_is_a_question_per_line_typed():
    page = SimpleNamespace(page=1, first=0, last=29, reasons=["washed-out"])
    assert bench.page_counts([1], [], [page], slips=(0.1, 0.1, 0.1))[1][2] == 30


def test_a_question_about_one_place_catches_only_errors_at_that_place():
    from roboscriptorium.disagreements import Disagreement
    from roboscriptorium.flags import Flag

    line = "Hij keek naar buiten en zei niets"
    other = line.replace("buiten", "bulten")
    readings = [{"text": line, "votes": []}, {"text": other, "votes": []}]
    flag = Flag("k", 3, 0, 0, line, "text", ["ocr-doubt"], span=(14, 20), readings=readings)
    there = Disagreement("a", "buiten", "buiten.’", "", "", 3, (0, 0))
    elsewhere = Disagreement("b", "zei", "zegt", "", "", 3, (0, 0))
    no_words = Disagreement("c", "–", "—", "", "", 3, (0, 0))
    assert quality.catches(flag, there)
    assert not quality.catches(flag, elsewhere)
    assert quality.catches(flag, no_words)


def test_paragraph_breaks_set_wrong_count_and_decide_a_change():
    flat = {p: [2, 1, 1, 1.0, 1.0, 1.0, 2] for p in range(30)}
    fewer = {p: [2, 1, 1, 1.0, 1.0, 1.0, 0] for p in range(30)}
    found = bench.verdict(_run(flat, c=flat), _run(fewer, c=fewer))
    assert found.outcome == "better" and found.breaks.after == 0
    assert bench.verdict(_run(fewer, c=fewer), _run(flat, c=flat)).outcome == "worse"


def test_fewer_breaks_set_wrong_dont_carry_words_worse_at_one_slip_rate():
    # More questions, fewer unasked: better at a low slip rate, worse at a high one.
    flat = {p: [2, 1, 1, 0, 0, 0, 2] for p in range(30)}
    mixed = {p: [2, 0.75, 3, 0, 0, 0, 0] for p in range(30)}
    found = bench.verdict(_run(flat, c=flat), _run(mixed, c=mixed))
    assert found.breaks.high < 0 and any(c.low > 0 for c in found.pooled)
    assert found.outcome == "worse"


def test_a_book_whose_breaks_go_clearly_wrong_vetoes():
    flat = {p: [2, 1, 1, 0, 0, 0, 2] for p in range(30)}
    fewer = {p: [2, 0, 1, 0, 0, 0, 0] for p in range(30)}
    broken = {p: [2, 0, 1, 0, 0, 0, 4] for p in range(30)}
    found = bench.verdict(_run(flat, c=flat, d=flat), _run(fewer, c=fewer, d=broken))
    assert (found.outcome, found.vetoes) == ("vetoed", ["d"])


def test_where_breaks_go_wrong():
    from roboscriptorium.disagreements import break_errors
    from roboscriptorium.ir import Document, Paragraph

    page = PageText(4, 300, 500, [Line("Een twee drie", 0, 0, 1, 1), Line("vier vijf", 0, 2, 1, 3)])
    joined = Document(
        "", "", "", [Paragraph("Een twee drie vier vijf", [SourceRef(4, 0), SourceRef(4, 1)])]
    )
    reference = [Chapter("", ["Een twee drie", "vier vijf"])]
    assert break_errors(joined, reference, [page]) == [4]
    split = Document(
        "",
        "",
        "",
        [Paragraph("Een twee drie", [SourceRef(4, 0)]), Paragraph("vier vijf", [SourceRef(4, 1)])],
    )
    assert break_errors(split, reference, [page]) == []


def test_the_slip_rate_is_an_interval_around_the_counts():
    low, mean, high = quality.slip_rates(8, 68)
    assert round(mean, 3) == 0.129 and 0.05 < low < 0.07 and 0.2 < high < 0.22


def test_a_gain_pooled_over_books_counts_unless_one_book_gets_worse():
    flat = {p: [2, 1, 1, 1.0] for p in range(30)}
    fewer = {p: [2, 0, 1, 0.0] for p in range(30)}
    worse = {p: [2, 2, 1, 2.0] for p in range(30)}
    before = _run(flat, c=flat, d=flat)
    assert bench.verdict(before, _run(fewer, c=fewer, d=fewer)).outcome == "better"
    vetoed = bench.verdict(before, _run(fewer, c=fewer, d=worse))
    assert (vetoed.outcome, vetoed.vetoes) == ("vetoed", ["d"])
    many = {p: [2, 1, 1, 1.0] for p in range(30)}
    many[0] = [2, 0, 1, 0.0]
    assert bench.verdict(before, _run(many, c=flat, d=flat)).outcome == "no change"


def test_a_book_is_scored_with_the_trust_model_trained_without_it(tmp_path, monkeypatch):
    from roboscriptorium.config import Settings

    settings = Settings(ocr_trust_model=str(tmp_path / "ocr-trust.pkl"), sorter=False)
    crime = "the-nature-of-a-crime--doubleday-1924"
    # A tuning book was trained on: scoring it with the full model is refused.
    with pytest.raises(FileNotFoundError):
        bench.unseen(settings, crime)
    off = replace(settings, ocr_trust=False)
    assert bench.unseen(off, crime) == off
    (tmp_path / f"ocr-trust-without-{crime}.pkl").write_bytes(b"")
    assert bench.unseen(settings, crime).ocr_trust_model == str(
        tmp_path / f"ocr-trust-without-{crime}.pkl"
    )
    # A validation book, or a tuning book without trust data, was never trained on.
    assert bench.unseen(settings, "vuurspel--ia-scan") == settings
    thief = "the-thief-takers-apprentice--ia-scan"
    monkeypatch.setattr(bench, "TRAINED_ON", bench.TRAINED_ON - {thief})
    assert bench.unseen(settings, thief) == settings
    assert bench.TRAINED_ON <= {s.split(":")[0] for s in bench.SETS["tuning"]}


def test_each_book_weighs_the_same_whatever_its_pages():
    big = [(1.0, 1.0)] * 300
    small = [(1.0, 0.0)] * 10
    before, after, low, high = bench.pooled([big, small])
    assert (before, after) == (1.0, 0.5) and high < 0


def test_a_book_slightly_worse_does_not_veto():
    flat = {p: [2, 1, 1, 1.0] for p in range(30)}
    fewer = {p: [2, 0, 1, 0.0] for p in range(30)}
    slightly = {p: [2, 1.02, 1] for p in range(30)}
    found = bench.verdict(_run(flat, c=flat), _run(fewer, c=slightly))
    assert (found.outcome, found.vetoes) == ("better", [])


def test_the_test_set_is_scored_only_on_purpose():
    book = next(iter(bench.TEST_BOOKS))
    with pytest.raises(typer.BadParameter):
        cli._not_the_test_set(Path("work") / book, False)
    cli._not_the_test_set(Path("work") / book, True)
    cli._not_the_test_set(Path("work/goede-dochter--ia-scan"), False)
    others = {
        s.split(":")[0] for name, specs in bench.SETS.items() if name != "test" for s in specs
    }
    assert not bench.TEST_BOOKS & others


def test_the_bench_records_each_pairs_signals_and_names_a_suspect(monkeypatch, tmp_path):
    def page(texts):
        lines = [Line(t, 20, 20 + 15 * i, 280, 30 + 15 * i) for i, t in enumerate(texts)]
        return PageText(11, 300, 500, lines)

    body = LineRole("body", 1.0, 1.0)
    clean = page(["Charlie liep naar de", "verder gelegen school."])
    garbled = page(["Charlie liep naar de", "verder gelegen school.", "xq zv wk"])
    reference = [Chapter("", ["Charlie liep naar de verder gelegen school."])]

    def build(spec, settings):
        p = garbled if "garbled" in spec else clean
        roles = {SourceRef(11, k): body for k in range(len(p.lines))}
        stages = SimpleNamespace(
            pages=[p], corrected=[p], model_roles=roles, suspects=[], ocr_decider="fixed rule"
        )
        name = spec.split(":")[0].split("/")[-1]
        return scoring.Scored(name, f"book {name}", stages, reference, [], [], 0)

    monkeypatch.setitem(bench.SETS, "probe", ["a", "b", "garbled"])
    monkeypatch.setattr(scoring, "build", build)
    monkeypatch.setattr(scoring, "scored", lambda book, stages: None)
    monkeypatch.setattr(
        evaluate, "score", lambda doc, ref: evaluate.Score(0, 0, 1, 1, 7, 7, 0, 0, 0)
    )
    monkeypatch.setattr(cli, "_model_versions", lambda settings: {})
    monkeypatch.setattr(cli.disagreements, "break_errors", lambda doc, ref, pages: [])
    monkeypatch.setattr(cli.disagreements, "glyph_kinds", lambda ref: set())
    monkeypatch.setattr(scoring, "read_via", lambda book, pages: {book: 1.0})
    monkeypatch.setattr(scoring, "italics_unlike", lambda book: "")
    monkeypatch.setattr(bench, "OUT", tmp_path)
    monkeypatch.setattr(bench.save, "__defaults__", (tmp_path,))
    result = CliRunner().invoke(cli.app, ["bench", "probe"])
    assert result.exit_code == 0, result.output
    assert "suspect pair, consider retiring garbled" in result.output
    assert "consider retiring a" not in result.output
    record = json.loads(next(tmp_path.glob("probe-*.json")).read_text())
    assert record["books"]["garbled"]["pair"]["unplaced"] == 1 / 3
    assert record["books"]["a"]["pair"]["cer"] == 0
    # Each book's own build is recorded, not the last one built.
    assert record["books"]["a"]["read_via"] == {"book a": 1.0}


def test_a_change_to_a_books_structure_is_reported_beside_the_test():
    def run(found, spurious, f1):
        score = {
            "headings_found": found,
            "headings_expected": 24,
            "headings_spurious": spurious,
            "paragraph_precision": f1,
            "paragraph_recall": f1,
        }
        return {"books": {"a": {"score": score}, "b": {"score": dict(score)}}}

    old, new = run(5, 4, 0.95), run(23, 1, 0.95)
    new["books"]["b"]["score"] = dict(old["books"]["b"]["score"])
    lines = bench.structure(old, new)
    assert len(lines) == 1 and "5/24 (+4) → 23/24 (+1)" in lines[0]
    assert bench.structure(old, old) == []


def test_typography_counts_glyphs_set_wrong_where_the_words_agree():
    from roboscriptorium.disagreements import glyph_errors, glyph_kinds
    from roboscriptorium.ir import Document, Paragraph

    text = "‘Kom je?’ vroeg ze – en toen… niets."
    page = PageText(4, 300, 500, [Line(text, 0, 0, 1, 1)])
    # The reference sets spaced dots elsewhere, so it can speak for them.
    reference = [Chapter("", [text, "Dus. . . ja."])]
    assert glyph_kinds(reference) == {"quotes", "dashes", "ellipses"}

    def errors(ours: str, kinds=None) -> list[int]:
        doc = Document("", "", "", [Paragraph(ours, [SourceRef(4, 0)])])
        return glyph_errors(doc, reference, [page], kinds or glyph_kinds(reference))

    assert errors(text) == []
    # The quote turned the wrong way, the dash's kind, the dots spaced: one each.
    assert errors("’Kom je?’ vroeg ze — en toen. . . niets.") == [4, 4, 4]
    # A straight quote where the reference sets a curly one.
    assert errors("‘Kom je?' vroeg ze – en toen… niets.") == [4]
    # The ellipsis glyph and three tight dots look alike on paper.
    assert errors("‘Kom je?’ vroeg ze – en toen... niets.") == []
    # A kind the reference can't speak for isn't scored.
    assert errors("’Kom je?’ vroeg ze — en toen. . . niets.", {"dashes"}) == [4]
    # A word that differs is a wrong word, not typography.
    assert errors("‘Kom je?’ vroeg hij – en toen… niets.") == []
    # A reference that sets every ellipsis tight says nothing of spaced dots.
    assert "ellipses" not in glyph_kinds([Chapter("", [text])])
    # A reference in straight quotes says nothing of the print's quotes.
    assert "quotes" not in glyph_kinds([Chapter("", ["'Kom je?' vroeg ze."])])


def test_settings_that_differ_between_two_runs_are_named():
    old = {"settings": {"sorter": True, "judge_model": "clef:27b", "ocr_trust": True}}
    assert bench.settings_changed(old, old) == []
    new = {"settings": {"sorter": False, "judge_model": "clef:27b", "ocr_ask_below": 0.6}}
    assert bench.settings_changed(old, new) == [
        "ocr_ask_below: None → 0.6",
        "ocr_trust: True → None",
        "sorter: True → False",
    ]


def test_the_quick_tier_is_tuning_books_inside_their_tuning_slices():
    tuning = {s.split(":")[0]: s.split(":")[1:] for s in bench.SETS["tuning"]}
    for spec in bench.SETS["quick"]:
        book, pages, _ = spec.split(":")
        assert book in tuning
        whole = tuning[book][0] if tuning[book] else ""
        if whole:
            first, last = map(int, pages.split("-"))
            lo, hi = map(int, whole.split("-"))
            assert lo <= first <= last <= hi, spec
