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
        p = np.where(X[:, -9] > 0, X[:, -8], 0.05)
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
