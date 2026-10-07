import numpy as np

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
        p = np.where(X[:, -7] > 0, X[:, -6], 0.05)
        return np.column_stack([1 - p, p])


def test_the_least_sure_are_asked_and_the_rest_take_their_best_version():
    sure = _suspect("lemand", "Iemand", "Iemand", 0.95)
    unsure = _suspect("hygiéne", "hygiëne", "hygiéne", 0.4)
    kept = _suspect("foto's", "foto’s", "foto's", 0.9)
    out = trust.decide([sure, unsure, kept], _Model(), questions=1)
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
