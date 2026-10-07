import numpy as np

from roboscriptorium import typestyle
from roboscriptorium.ir import SourceRef
from roboscriptorium.typestyle import Style


def test_ink_height_runs_from_the_tallest_letter_to_the_baseline():
    ink = np.zeros((40, 60), bool)
    ink[15:30, 5:55] = True  # x-height band
    ink[5:15, 10:13] = True  # an ascender
    ink[30:36, 40:43] = True  # a descender
    measured = typestyle._ink(ink)
    assert measured["height"] == 29 - 5
    assert measured["width"] == 50


def test_groups_split_by_size_capitals_and_place():
    def s(size, caps=True):
        return Style(size, 1.0, 1.0, caps)

    styles = {
        SourceRef(1, 0): s(1.50),
        SourceRef(2, 0): s(1.52),
        SourceRef(3, 0): s(1.60),  # a chain of small steps stays one size
        SourceRef(4, 0): s(2.00),
        SourceRef(5, 0): s(1.50, caps=False),
        SourceRef(6, 30): s(1.50),
        SourceRef(7, 0): Style(None, None, None, True),
    }
    places = {ref: "foot" if ref.line == 30 else "top" for ref in styles}
    found = sorted(sorted(r.page for r in g) for g in typestyle.groups(styles, places))
    assert found == [[1, 2, 3], [4], [5], [6]]
    assert typestyle.display(s(1.0))
    assert not typestyle.display(s(1.1, caps=False))
