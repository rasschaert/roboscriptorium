import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

from roboscriptorium import bench, cli, quality


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
