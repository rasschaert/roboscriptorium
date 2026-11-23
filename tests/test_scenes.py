from dataclasses import replace

from roboscriptorium import flags, scenes
from roboscriptorium.clients.decide import Answer
from roboscriptorium.corrections import Corrections, apply
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.reflow import reflow
from roboscriptorium.roles import DecisionCache, LineRole

MARGIN, INDENT, RIGHT = 40.0, 52.0, 360.0


def _page(number: int, rows: list[tuple[str, float, float]]) -> PageText:
    """A page of (text, x0, x1) rows, one under the other."""
    lines = [Line(t, x0, 60 + 16 * i, x1, 72 + 16 * i) for i, (t, x0, x1) in enumerate(rows)]
    return PageText(number, 400, 600, lines)


def _book(last_before: str = "het huis. Ze zei niets meer en ging weg.", next_x0: float = MARGIN):
    """Two pages of a book that indents its paragraphs: the first ends on a full line, the
    second opens at `next_x0`."""
    one = _page(
        1,
        [
            ("Hij keek op en zag haar staan in de deur", INDENT, RIGHT),
            ("van de keuken, met de brief nog in haar", MARGIN, RIGHT),
            ("hand. Hij wist wat erin stond.", MARGIN, 250),
            ("Zij liep naar het raam en keek naar buiten,", INDENT, RIGHT),
            ("waar de regen over de daken van", MARGIN, RIGHT),
            (last_before, MARGIN, RIGHT),
        ],
    )
    two = _page(
        2,
        [
            ("De volgende morgen was alles anders dan", next_x0, RIGHT),
            ("de avond ervoor. De straat lag stil.", MARGIN, 280),
            ("Hij stond op en zette koffie, zoals hij", INDENT, RIGHT),
            ("altijd deed als hij niet slapen kon.", MARGIN, 300),
        ],
    )
    return [one, two]


def test_a_page_opening_flush_after_a_finished_sentence_is_a_turn_to_ask():
    pages = _book()
    found = scenes.turns(pages, reflow(pages), indented=True)
    assert [(ref, before) for ref, before, _ in found] == [(SourceRef(2, 0), SourceRef(1, 5))]
    state = found[0][2]
    assert state["end of the page before"].endswith("ging weg.")
    assert state["start of the next page"].startswith("De volgende morgen")


def test_no_turn_where_the_page_indents_the_sentence_runs_on_or_the_book_sets_flush():
    # The next page opens on an indent: a paragraph the build already starts.
    pages = _book(next_x0=INDENT)
    assert scenes.turns(pages, reflow(pages), indented=True) == []
    # The page before ends mid-sentence.
    pages = _book(last_before="het huis, en zij zei niets meer en ging")
    assert scenes.turns(pages, reflow(pages), indented=True) == []
    # A book that sets its paragraphs flush tells nothing by a flush line.
    pages = _book()
    assert scenes.turns(pages, reflow(pages), indented=False) == []


def test_no_turn_where_the_build_already_sets_a_break():
    pages = _book()
    two = pages[1]
    pages[1] = PageText(2, 400, 600, [replace(two.lines[0], scene=True), *two.lines[1:]])
    assert scenes.turns(pages, reflow(pages), indented=True) == []


class Model:
    model = "shisa"

    def __init__(self, new_scene: float):
        self.new_scene = new_scene
        self.asked = 0

    def decide(self, state, questions):
        self.asked += 1
        rest = (1 - self.new_scene) / 2
        p = {"new_scene": self.new_scene, "document": rest, "continues": rest}
        return {"scene": Answer("choice", max(p, key=p.get), max(p.values()), p)}


def test_a_turn_is_asked_where_a_new_scene_is_likely_and_each_answer_is_cached(tmp_path):
    pages = _book()
    cache = DecisionCache(tmp_path / "decisions.jsonl")
    sure = Model(0.7)
    assert scenes.asked(pages, reflow(pages), True, "nl", sure, cache) == {
        SourceRef(2, 0): (0.7, SourceRef(1, 5))
    }
    again = Model(0.7)
    scenes.asked(pages, reflow(pages), True, "nl", again, DecisionCache(cache.path))
    assert again.asked == 0
    unsure = Model(0.3)
    unsure.model = "other"
    assert scenes.asked(pages, reflow(pages), True, "nl", unsure, cache) == {}


def test_the_question_shows_the_last_line_of_the_page_before():
    pages = _book()
    roles = {
        SourceRef(p.number, i): LineRole("body", 0.99, 0.99)
        for p in pages
        for i in range(len(p.lines))
    }
    found = flags.find(pages, roles, scenes={SourceRef(2, 0): SourceRef(1, 5)})
    asked = [f for f in found if "scene" in f.reasons]
    assert [(f.page, f.first, f.across) for f in asked] == [(2, 0, (1, 5))]


def test_the_answer_scene_sets_a_break_before_its_line(tmp_path):
    pages = _book()
    assert not any(getattr(b, "break_before", False) for b in reflow(pages))
    roles = {
        SourceRef(p.number, i): LineRole("body", 0.99, 0.99)
        for p in pages
        for i in range(len(p.lines))
    }
    answers = Corrections(tmp_path / "regions.jsonl")
    line = pages[1].lines[0].text
    answers.record(flags.Flag("k", 2, 0, 0, line, "text", ["scene"]), "scene", None)
    corrected, new_roles, applied = apply(pages, roles, answers)
    assert applied == 1 and corrected[1].lines[0].scene
    assert corrected[1].lines[0].text == line
    assert new_roles[SourceRef(2, 0)].role == "body"
    blocks = reflow(corrected, new_roles)
    opened = [b for b in blocks if getattr(b, "break_before", False)]
    assert [b.text[:18] for b in opened] == ["De volgende morgen"]
    assert blocks[blocks.index(opened[0]) - 1].text.endswith("ging weg.")
