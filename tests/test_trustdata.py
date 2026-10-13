"""The trust data's books and the arbiter's saved models."""

import numpy as np

from roboscriptorium import bench, trust, trustdata
from roboscriptorium.ocrcheck import Suspect


def _row(book: str, right: bool) -> dict:
    s = Suspect(
        5, 0, "het boek", 0, 3, "het", ("hct",), (0, 0, 1, 1), "review",
        votes={"vision": "het" if right else "hct", "text": "het"},
        confidence={"vision": 0.9, "text": 0.6},
        judges=("vision", "text"),
    )  # fmt: skip
    return {"s": s, "right": [right, not right], "book": book}


def test_the_tuning_books_without_trust_data_are_the_ones_its_specs_lack():
    tuning = {spec.split(":")[0] for spec in bench.SETS["tuning"]}
    assert bench.NO_TRUST_DATA == tuning - set(trustdata.SPECS)
    # Validation books may have data, which is never trained on; the test set has none.
    assert not set(trustdata.SPECS) & bench.TEST_BOOKS
    assert all(not trustdata.trainable(spec.split(":")[0]) for spec in bench.SETS["validation"])


def test_the_arbiter_is_saved_whole_and_without_each_tuning_book(tmp_path):
    books = {
        "a--scan": [_row("a--scan", k % 3 > 0) for k in range(30)],
        "b--scan": [_row("b--scan", k % 4 > 0) for k in range(30)],
        "vuurspel--ia-scan": [_row("vuurspel--ia-scan", True) for _ in range(30)],
    }
    asked = []

    def score(names, rows):
        asked.append(sorted(names))
        return [np.array([0.8, 0.2]) for _ in rows]

    models = trustdata.models_to_save(books, tmp_path / "ocr-trust.pkl", score)
    paths = [m[0] for m in models]
    assert paths == [
        tmp_path / "ocr-trust.pkl",
        trust.without(tmp_path / "ocr-trust.pkl", "a--scan"),
        trust.without(tmp_path / "ocr-trust.pkl", "b--scan"),
    ]
    # A validation book is never trained on, nor scored to calibrate.
    assert [m[2] for m in models] == [60, 30, 30]
    assert all("vuurspel--ia-scan" not in names for names in asked)
    assert all(m[1].calibration is not None for m in models)
