import json
from types import SimpleNamespace

from roboscriptorium import bench


def _run(pages: dict[int, list[float]]) -> dict:
    # Through JSON, as saved runs are read back: page numbers become strings.
    return json.loads(json.dumps({"books": {"b": {"pages": pages}}}))


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
    counts = bench.page_counts([1, 2], [], asked, slip_rate=0.25)
    assert counts == {1: [0, 0, 2, 0.5], 2: [0, 0, 0, 0.0]}


def test_a_book_is_scored_with_the_trust_model_trained_without_it(tmp_path):
    from roboscriptorium.config import Settings

    settings = Settings(ocr_trust_model=str(tmp_path / "ocr-trust.pkl"))
    assert bench.unseen(settings, "crime") == settings
    (tmp_path / "ocr-trust-without-crime.pkl").write_bytes(b"")
    assert bench.unseen(settings, "crime").ocr_trust_model == str(
        tmp_path / "ocr-trust-without-crime.pkl"
    )
