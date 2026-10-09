import numpy as np
import pytest

from roboscriptorium import sorter
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole


def _page() -> PageText:
    lines = [Line("12", 140, 20, 150, 30)]
    lines += [
        Line(f"Gewone tekst van de bladzijde {i}", 10, 40 + 15 * i, 280, 50 + 15 * i)
        for i in range(8)
    ]
    return PageText(5, 300, 500, lines)


class _Trees:
    """Calls the first line other, the third a heading, the rest body."""

    classes_ = np.array(["body", "heading", "other"])

    def predict_proba(self, X):
        out = np.tile([0.9, 0.05, 0.05], (len(X), 1))
        out[0] = [0.1, 0.1, 0.8]
        out[2] = [0.3, 0.6, 0.1]
        out[6] = [0.3, 0.05, 0.65]
        return out


def test_the_trees_roles_replace_the_rules_and_keep_the_role_models_names():
    page = _page()
    asked = {
        SourceRef(5, 0): LineRole("page_number", 0.9, 0.05),
        SourceRef(5, 4): LineRole("artifact", 0.6, 0.3),
    }
    roles = sorter.apply(sorter.Sorter(_Trees()), [page], asked, {})
    assert roles[SourceRef(5, 0)].role == "page_number"
    assert roles[SourceRef(5, 2)].role == "chapter_heading" and roles[SourceRef(5, 2)].p_body < 0.5
    # A line the role model dropped is body where the trees say so; unasked body lines stay out.
    assert roles[SourceRef(5, 4)] == LineRole("body", 0.9, 0.9, "trees")
    assert SourceRef(5, 5) not in roles
    # One the trees would drop but aren't sure enough of is kept as text, and flagged.
    assert roles[SourceRef(5, 6)] == LineRole("artifact", 0.65, 0.5, "trees-kept")


def test_a_missing_or_stale_model_stops_the_build(tmp_path):
    with pytest.raises(sorter.Mismatch):
        sorter.load(tmp_path / "line-roles.pkl")
    sorter.save(sorter.Sorter(_Trees()), tmp_path / "line-roles.pkl")
    assert isinstance(sorter.load(tmp_path / "line-roles.pkl").model, _Trees)
    monkey = tmp_path / "old.pkl"
    import pickle

    monkey.write_bytes(pickle.dumps({"version": 1, "features": ("x",), "model": _Trees()}))
    with pytest.raises(sorter.Mismatch):
        sorter.load(monkey)


def test_a_heading_repeated_on_other_pages_is_a_running_head():
    pages = []
    for n in range(5, 10):
        lines = [Line("STEPHEN KING", 100, 20, 200, 30)]
        lines += [Line(f"Gewone tekst {i}", 10, 40 + 15 * i, 280, 50 + 15 * i) for i in range(8)]
        pages.append(PageText(n, 300, 500, lines))

    class Headings(_Trees):
        def predict_proba(self, X):
            out = np.tile([0.9, 0.05, 0.05], (len(X), 1))
            out[::9] = [0.2, 0.7, 0.1]
            return out

    roles = sorter.apply(sorter.Sorter(Headings()), pages, {}, {})
    assert {roles[SourceRef(n, 0)].role for n in range(5, 10)} == {"running_head"}
