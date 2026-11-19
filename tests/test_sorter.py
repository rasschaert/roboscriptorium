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
    # A line the role model dropped is body where the trees say so; silent body lines stay out.
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


def _folio_pages() -> list[PageText]:
    """Dolittle's kind: a chapter's title opens page 30 (its number at the foot), and on
    its right-hand pages runs atop with the page's number, two pages in all."""
    pages = []
    for n in range(30, 42):
        lines = [Line("Gewone tekst", 10, 40 + 15 * i, 280, 50 + 15 * i) for i in range(8)]
        if n == 30:
            lines = [Line("The Great Journey", 100, 60, 200, 72)] + lines
        if n in (31, 33):
            lines = [Line(f"The Great Journey {n - 22}", 30, 20, 280, 30)] + lines
        else:
            lines = lines + [Line(str(n - 22), 140, 470, 150, 480)]
        pages.append(PageText(n, 300, 500, lines))
    return pages


def test_a_title_with_its_pages_number_on_two_pages_is_a_running_head():
    class Headings(_Trees):
        def predict_proba(self, X):
            out = np.tile([0.9, 0.05, 0.05], (len(X), 1))
            out[X[:, sorter.FEATURES.index("i_top")] == 0] = [0.2, 0.7, 0.1]
            out[X[:, sorter.FEATURES.index("digits_only")] == 1] = [0.05, 0.05, 0.9]
            return out

    roles = sorter.apply(sorter.Sorter(Headings()), _folio_pages(), {}, {})
    assert {roles[SourceRef(n, 0)].role for n in (31, 33)} == {"running_head"}
    # The title itself, without the page's number, recurs only twice: still the chapter's.
    assert roles[SourceRef(30, 0)].role == "chapter_heading"


def test_a_heading_number_one_digit_off_the_folio_printed_below_is_no_folio():
    from roboscriptorium import page as P

    # Vals alarm PDF 99: "15 Eerder" atop a page printing "95" at its foot.
    lines = [Line("15 Eerder", 100, 60, 200, 72), Line("Tekst", 10, 90, 280, 100)]
    printed = PageText(99, 300, 500, [*lines, Line("95", 140, 470, 150, 480)])
    assert not P.carries_folio(printed, 0, 4)
    assert P.carries_folio(
        PageText(99, 300, 500, [Line("Animal Language 95", 30, 20, 280, 30)]), 0, 4
    )
    # Only a page number on its own: no running head's words.
    assert not P.carries_folio(printed, 2, 4)


def test_a_labelled_number_opening_sunk_pages_is_no_running_head_though_it_recurs():
    # Vals alarm: "11 Later", "13 Later" open sunk pages, where no running head stands;
    # its ordinary pages' text starts at the top.
    pages = []
    for n in range(5, 15):
        lines = [Line(f"Gewone tekst {i}", 10, 30 + 15 * i, 280, 40 + 15 * i) for i in range(12)]
        pages.append(PageText(n, 300, 500, lines))
    for n, label in ((20, "11 Later"), (30, "13 Later"), (40, "16 Later"), (50, "21 Later")):
        lines = [Line(label, 120, 110, 180, 122)]
        lines += [Line(f"Gewone tekst {i}", 10, 150 + 15 * i, 280, 160 + 15 * i) for i in range(8)]
        pages.append(PageText(n, 300, 500, lines))

    class Headings(_Trees):
        def predict_proba(self, X):
            out = np.tile([0.9, 0.05, 0.05], (len(X), 1))
            out[X[:, sorter.FEATURES.index("sunk")] == 1.0] = [0.05, 0.9, 0.05]
            return out

    roles = sorter.apply(sorter.Sorter(Headings()), pages, {}, {})
    assert {roles[SourceRef(n, 0)].role for n in (20, 30, 40, 50)} == {"chapter_heading"}


def test_running_text_away_from_the_edges_is_never_dropped_silently():
    from roboscriptorium.layout import Region

    class Drops(_Trees):
        def predict_proba(self, X):
            out = np.tile([0.05, 0.05, 0.9], (len(X), 1))
            out[3] = [0.1, 0.8, 0.1]
            return out

    page = _page()
    text = {5: [Region("plain text", 0.95, 0, 30, 300, 170)]}
    roles = sorter.apply(sorter.Sorter(Drops()), [page], {}, {}, text)
    # Mid-page lines in a text block stay body; a heading the trees find there still counts.
    assert SourceRef(5, 4) not in roles
    assert roles[SourceRef(5, 3)].role == "chapter_heading"
    # At the edges, or asked, or outside any text block, the trees decide.
    assert roles[SourceRef(5, 8)].role == "artifact"
    asked = {SourceRef(5, 4): LineRole("artifact", 0.6, 0.3)}
    assert sorter.apply(sorter.Sorter(Drops()), [page], asked, {}, text)[SourceRef(5, 4)].role == (
        "artifact"
    )
    assert sorter.apply(sorter.Sorter(Drops()), [page], {}, {}, {})[SourceRef(5, 4)].role == (
        "artifact"
    )


def test_every_lines_features_are_the_ones_the_trees_were_trained_on():
    from roboscriptorium.layout import Region
    from roboscriptorium.typestyle import Style

    page = _page()
    regions = {5: [Region("plain text", 0.9, 0, 0, 300, 500), Region("figure", 0.7, 0, 0, 50, 50)]}
    styles = {SourceRef(5, 0): Style(1.1, 1.0, 1.0, False)}
    roles = {SourceRef(5, 0): LineRole("page_number", 0.9, 0.1)}
    found = sorter.features([page], roles, styles, regions)
    assert all(tuple(f) == sorter.FEATURES for f in found.values())


def test_the_page_roles_are_features_only_for_trees_trained_with_them(tmp_path):
    page = _page()
    plain = sorter.features([page], {}, {})
    assert all(tuple(f) == sorter.FEATURES for f in plain.values())
    said = sorter.features([page], {}, {}, None, {5: {2: "heading", 0: "other"}})
    want = sorter.FEATURES + sorter.PAGE_FEATURES
    assert all(tuple(f) == want for f in said.values())
    assert [said[SourceRef(5, i)]["page_heading"] for i in range(3)] == [0.0, 0.0, 1.0]
    assert said[SourceRef(5, 0)]["page_other"] == 1.0
    # A page the read model didn't answer for has nothing to say.
    silent = sorter.features([page], {}, {}, None, {})[SourceRef(5, 2)]
    assert silent["page_asked"] == 0.0 and np.isnan(silent["page_heading"])

    sorter.save(sorter.Sorter(_Trees(), want), tmp_path / "pages.pkl")
    assert sorter.load(tmp_path / "pages.pkl", page_roles=True).page_roles
    with pytest.raises(sorter.Mismatch, match="ROBO_PAGE_ROLES"):
        sorter.load(tmp_path / "pages.pkl")
    sorter.save(sorter.Sorter(_Trees()), tmp_path / "plain.pkl")
    with pytest.raises(sorter.Mismatch, match="ROBO_PAGE_ROLES"):
        sorter.load(tmp_path / "plain.pkl", page_roles=True)


def test_a_bare_page_number_at_a_pages_edge_is_never_a_body_label():
    from roboscriptorium.sorterdata import folio_label

    def row(label: str, top: int, bottom: int, folio: float, digits: float) -> dict:
        f = {"i_top": top, "i_bottom": bottom, "page_number": folio, "digits_only": digits}
        return {"f": f, "label": label}

    assert folio_label(row("body", 30, 0, 1.0, 1.0)) == "other"  # "130" at the foot
    assert folio_label(row("body", 0, 30, 1.0, 1.0)) == "other"
    # Not: a line mid-page, a line with words beside its number, one that isn't the page's
    # number, or a heading label.
    assert folio_label(row("body", 12, 18, 1.0, 1.0)) == "body"
    assert folio_label(row("body", 30, 0, 1.0, 0.0)) == "body"
    assert folio_label(row("body", 30, 0, 0.0, 1.0)) == "body"
    assert folio_label(row("heading", 0, 30, 1.0, 1.0)) == "heading"


def test_text_recurring_under_a_pages_running_head_is_no_second_running_head():
    # Artemis: "Dear Kelvin," opens four letters, each just under the running head.
    pages = []
    for n in range(5, 25):
        head = Line("ANDY WEIR" if n % 2 else "ARTEMIS", 100, 10, 200, 20)
        lines = [head] + [
            Line(f"Gewone tekst {n} {i}", 10, 40 + 15 * i, 280, 50 + 15 * i) for i in range(8)
        ]
        if n in (6, 10, 14, 18):
            lines[1] = Line("Dear Kelvin,", 10, 40, 80, 50)
        pages.append(PageText(n, 300, 500, lines))

    class Body(_Trees):
        def predict_proba(self, X):
            return np.tile([0.9, 0.05, 0.05], (len(X), 1))

    roles = sorter.apply(sorter.Sorter(Body()), pages, {}, {})
    assert {roles[SourceRef(n, 0)].role for n in range(5, 25)} == {"running_head"}
    assert all(SourceRef(n, 1) not in roles for n in (6, 10, 14, 18))


def test_where_two_sets_of_trees_disagree_the_referee_picks_and_is_asked_nowhere_else():
    page = _page()

    class Second(_Trees):
        """Calls the third line body where the first set says heading, the fifth other."""

        def predict_proba(self, X):
            out = super().predict_proba(X)
            out[2] = [0.9, 0.05, 0.05]
            out[4] = [0.1, 0.1, 0.8]
            return out

    asked = []

    def referee(ref):
        asked.append(ref)
        # With the second set on the third line, with neither on the fifth.
        return "body" if ref.line == 2 else "heading"

    first, second = sorter.Sorter(_Trees()), sorter.Sorter(Second())
    roles = sorter.apply(first, [page], {}, {}, second=second, referee=referee)
    assert asked == [SourceRef(5, 2), SourceRef(5, 4)]
    assert SourceRef(5, 2) not in roles  # body now, as the second set and the referee say
    assert SourceRef(5, 4) not in roles  # the first set's body stands
    alone = sorter.apply(first, [page], {}, {})
    assert alone[SourceRef(5, 2)].role == "chapter_heading"
    assert roles[SourceRef(5, 0)] == alone[SourceRef(5, 0)]


def test_the_referee_is_shown_the_page_and_keeps_its_answers(tmp_path):
    import pymupdf

    from roboscriptorium.roles import DecisionCache

    path = tmp_path / "book.pdf"
    doc = pymupdf.open()
    for _ in range(5):
        doc.new_page(width=300, height=500)
    doc.save(path)
    calls = []

    class Judge:
        def decide(self, state, questions, image_png=None):
            calls.append((state, image_png[:4]))
            return {"role": type("A", (), {"value": "heading", "confidence": 0.8})()}

    cache = DecisionCache(tmp_path / "d.jsonl")
    referee = sorter.Referee(path, [_page()], Judge(), "clef", cache)
    assert referee(SourceRef(5, 2)) == "heading"
    assert referee(SourceRef(5, 2)) == "heading"
    assert len(calls) == 1 and calls[0][1] == b"\x89PNG"
    assert calls[0][0]["text"] == "Gewone tekst van de bladzijde 1"
