import numpy as np
import pytest

from roboscriptorium import trust
from roboscriptorium.ocrcheck import Suspect


def _suspect(ours: str, other: str, clef: str, sure: float) -> Suspect:
    return Suspect(
        3, 0, f"zat {ours} daar", 4, 4 + len(ours), ours, (other,), (0, 0, 1, 1), "review",
        votes={"vision": clef, "text": clef}, confidence={"vision": sure, "text": 0.9},
        support={"glm": (False, True), "tess": (True, False)}, known=(False, True),
    )  # fmt: skip


class _Model:
    """Trusts whatever the vision judge picked, as sure as it was."""

    def predict_proba(self, X):
        p = np.where(X[:, -12] > 0, X[:, -11], 0.05)
        return np.column_stack([1 - p, p])


def test_the_least_sure_are_asked_and_the_rest_take_their_best_version():
    sure = _suspect("lemand", "Iemand", "Iemand", 0.95)
    unsure = _suspect("hygiéne", "hygiëne", "hygiéne", 0.4)
    kept = _suspect("foto's", "foto’s", "foto's", 0.9)
    out = trust.decide([sure, unsure, kept], trust.Trust(_Model(), {}), questions=1)
    assert [(s.choice, s.chosen) for s in out] == [
        ("other", "Iemand"),
        ("review", None),
        ("ours", None),
    ]
    # A new list: the suspects given stay as they were.
    assert sure.choice == "review"


def test_within_the_budget_a_suspect_the_model_is_sure_of_is_not_asked():
    sure = _suspect("lemand", "Iemand", "Iemand", 0.95)
    unsure = _suspect("hygiéne", "hygiëne", "hygiéne", 0.4)
    model = trust.Trust(_Model(), {})
    out = trust.decide([sure, unsure], model, questions=2, below=0.92)
    assert [(s.choice, s.chosen) for s in out] == [("other", "Iemand"), ("review", None)]
    out = trust.decide([sure, unsure], model, questions=2, below=1.0)
    assert [s.choice for s in out] == ["review", "review"]


def test_a_reading_the_vision_judge_saw_none_of_is_asked_first_and_never_applied():
    sure = _suspect("lemand", "Iemand", "Iemand", 0.95)
    blind = _suspect("shirt.", "but he knew better than to argue.", "", 0.6)
    blind = Suspect(**{**blind.__dict__, "votes": {"vision": "", "text": blind.others[0]}})
    model = trust.Trust(_Model(), {})
    out = trust.decide([sure, blind], model, questions=1, below=0.8)
    assert [s.choice for s in out] == ["other", "review"]
    out = trust.decide([sure, blind], model, questions=0)
    assert [s.choice for s in out] == ["other", "ours"]


def test_the_judges_count_by_role_whatever_the_models_are_called():
    a = _suspect("lemand", "Iemand", "Iemand", 0.95)
    b = trust.features(a, 1)
    votes, confidence = {"x": "Iemand", "y": "Iemand"}, {"x": 0.95, "y": 0.9}
    renamed = Suspect(**{**a.__dict__, "votes": votes, "confidence": confidence})
    assert trust.features(renamed, 1) == b


def test_a_substitution_seen_in_two_books_becomes_a_prior_and_one_books_does_not():
    assert trust.pair("lemand", "Iemand") == "'l'→'I'"
    assert trust.pair("zei", "zei’") == "''→'’'"
    assert trust.pair("zei", "zei") == "="
    lost_quote = [_suspect("zei", "zei’", "zei’", 0.9) for _ in range(6)]
    bar = [_suspect("|", "I", "I", 0.9) for _ in range(4)]
    right = [[False, True]] * 10
    books = ["a", "a", "a", "b", "b", "b", "c", "c", "c", "c"]
    pairs = trust.pairs_table(lost_quote + bar, right, books)
    assert pairs == {"''→'’'": (6, 6)}
    # The other version's prior is its share, the layer's the complement; a pair the
    # table lacks is even.
    assert trust.prior(lost_quote[0], 1, pairs)[0] == pytest.approx(7 / 8)
    assert trust.prior(lost_quote[0], 0, pairs)[0] == pytest.approx(1 / 8)
    assert trust.prior(bar[0], 1, pairs) == [0.5, 0.0]
    assert len(trust.features(bar[0], 1, pairs)) == trust.FEATURES


def test_a_training_suspect_gets_its_prior_from_the_other_books_only():
    a = _suspect("zei", "zei’", "zei’", 0.9)
    b = _suspect("zag", "zag’", "zag’", 0.9)
    c = _suspect("zat", "zat’", "zat’", 0.9)
    right = [[False, True], [True, False], [False, True]]
    X, y = trust.training_matrix([a, b, c], right, ["x", "y", "z"])
    # a's other version sees b's and c's labels (1 of 2), b's sees a's and c's (2 of 2).
    assert X[1, -2] == pytest.approx(2 / 4)
    assert X[3, -2] == pytest.approx(3 / 4)
    assert X[5, -2] == pytest.approx(2 / 4)
    assert y.tolist() == [0, 1, 1, 0, 0, 1]


def test_a_saved_model_of_another_width_stops_the_build_instead_of_being_skipped(tmp_path):
    assert len(trust.features(_suspect("a", "b", "a", 0.9), 0)) == trust.FEATURES
    narrow = trust.train([_suspect("a", "b", "a", 0.9)] * 20, [[True, False]] * 20)
    path = tmp_path / "trust.pkl"
    trust.save(narrow, path)
    loaded = trust.load(path)
    assert loaded.model.n_features_in_ == trust.FEATURES and loaded.pairs == {}
    narrow.model.n_features_in_ = trust.FEATURES - 1
    trust.save(narrow, path)
    with pytest.raises(trust.Mismatch):
        trust.load(path)
    assert trust.load(tmp_path / "none.pkl") is None


def test_a_second_vision_judge_has_its_own_features_and_none_reads_as_absent():
    from dataclasses import replace

    plain = _suspect("a", "b", "b", 0.9)
    alarmed = replace(
        plain,
        votes={"vision": "b", "text": "b", "imajev": "a", "word list": "b"},
        confidence={"vision": 0.9, "text": 0.9, "imajev": 0.6},
    )
    f0, f1 = trust.features(plain, 0), trust.features(alarmed, 0)
    assert len(f0) == len(f1) == trust.FEATURES
    # From the end: the prior (2), the two judges' agreement, then the third judge's three.
    # Everything else is the same with or without it.
    assert f0[:-6] == f1[:-6] and f0[-3:] == f1[-3:]
    assert f0[-6:-3] == [0.0, 0.0, 0.0] and f1[-6:-3] == [1.0, 0.6, 0.0]


def test_a_threshold_of_one_asks_within_the_budget_even_a_calibrated_certainty():
    class _Certain:
        def predict(self, raw):
            return np.ones_like(raw)

    sure = _suspect("lemand", "Iemand", "Iemand", 0.95)
    out = trust.decide(
        [sure], trust.Trust(_Model(), {}, calibration=_Certain()), questions=1, below=1.0
    )
    assert [s.choice for s in out] == ["review"]
