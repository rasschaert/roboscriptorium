import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from roboscriptorium import bench, cli, evaluate, quality
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole


def _run(pages: dict[int, list[float]], **books: dict[int, list[float]]) -> dict:
    """A saved run of book "b" (and any others), each page's counts padded to six.
    Through JSON, as saved runs are read back: page numbers become strings."""
    every = {"b": pages, **books}
    padded = {n: {p: (c + [c[-1]] * 6)[:6] for p, c in pg.items()} for n, pg in every.items()}
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


def test_after_review_counts_the_reviewers_slips_on_each_question():
    asked = [SimpleNamespace(page=1, first=0, last=0, reasons=["x"])] * 2
    counts = bench.page_counts([1, 2], [], asked, slips=(0.1, 0.25, 0.5))
    assert counts == {1: [0, 0, 2, 0.5, 0.2, 1.0], 2: [0, 0, 0, 0.0, 0.0, 0.0]}


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


def test_a_book_is_scored_with_the_trust_model_trained_without_it(tmp_path):
    from roboscriptorium.config import Settings

    settings = Settings(ocr_trust_model=str(tmp_path / "ocr-trust.pkl"))
    assert bench.unseen(settings, "crime") == settings
    (tmp_path / "ocr-trust-without-crime.pkl").write_bytes(b"")
    assert bench.unseen(settings, "crime").ocr_trust_model == str(
        tmp_path / "ocr-trust-without-crime.pkl"
    )


def test_each_book_weighs_the_same_whatever_its_pages():
    big = [(1.0, 1.0)] * 300
    small = [(1.0, 0.0)] * 10
    before, after, low, high = bench.pooled([big, small])
    assert (before, after) == (1.0, 0.5) and high < 0


def test_a_book_slightly_worse_does_not_veto():
    flat = {p: [2, 1, 1, 1.0] for p in range(30)}
    fewer = {p: [2, 0, 1, 0.0] for p in range(30)}
    slightly = {p: [2, 1, 1, 1.02] for p in range(30)}
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
            pages=[p], model_roles=roles, suspects=[], ocr_decider="fixed rule"
        )
        return spec.split(":")[0].split("/")[-1], None, stages, reference, [], [], 0

    monkeypatch.setitem(bench.SETS, "probe", ["a", "b", "garbled"])
    monkeypatch.setattr(cli, "_questions_and_errors", build)
    monkeypatch.setattr(cli, "_scored", lambda book, stages: None)
    monkeypatch.setattr(
        evaluate, "score", lambda doc, ref: evaluate.Score(0, 0, 1, 1, 7, 7, 0, 0, 0)
    )
    monkeypatch.setattr(cli, "_model_versions", lambda settings: {})
    monkeypatch.setattr(bench, "OUT", tmp_path)
    monkeypatch.setattr(bench.save, "__defaults__", (tmp_path,))
    result = CliRunner().invoke(cli.app, ["bench", "probe"])
    assert result.exit_code == 0, result.output
    assert "suspect pair, consider retiring garbled" in result.output
    assert "consider retiring a" not in result.output
    record = json.loads(next(tmp_path.glob("probe-*.json")).read_text())
    assert record["books"]["garbled"]["pair"]["unplaced"] == 1 / 3
    assert record["books"]["a"]["pair"]["cer"] == 0
