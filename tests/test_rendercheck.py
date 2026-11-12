import pymupdf
import pytest
from PIL import ImageFont

from roboscriptorium import ocrcheck, pipeline, rendercheck
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.roles import DecisionCache

LINE = "there the quick {} jumps over them"


def _scan(tmp_path, word: str):
    """A one-page PDF printing `LINE` with `word` in it, and the word's box."""
    path = tmp_path / f"{word}.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=120)
    page.insert_text((30, 60), LINE.format(word), fontname="helv", fontsize=14)
    box = next(w[:4] for w in page.get_text("words") if w[4] == word)
    doc.save(path)
    return path, box


def _judge(path) -> rendercheck.Judge:
    face = rendercheck.Face(lambda px: ImageFont.load_default(px))
    words = rendercheck.scan_words(path, 1, 1, 20)
    found = rendercheck.Match("default", "default", 0.5, 0, rendercheck.em_size(words, face.at()))
    return rendercheck.Judge(path, face, found)


def _question(versions: list[str]) -> dict:
    options = {c: f"exactly ⟨{v}⟩" for c, v in zip("ab", versions, strict=True)}
    return {"reading": decide.choice("Which text?", {**options, "neither": "something else"})}


@pytest.mark.parametrize(
    ("printed", "versions", "picked"),
    [
        ("world", ["world", "wor1d"], "a"),
        ("wor1d", ["world", "wor1d"], "b"),
        ("world", ["wodd", "world"], "b"),
        ("world.", ["world", "world."], "b"),
        ("world", ["world", "world."], "a"),
    ],
)
def test_the_version_the_scan_prints_fits_best(tmp_path, printed, versions, picked):
    path, box = _scan(tmp_path, printed)
    state = {"page": 1, "line": 0, "readings": versions, "box": [round(v, 1) for v in box]}
    answer = _judge(path).decide(state, _question(versions))["reading"]
    assert answer.value == picked
    assert 0 < answer.confidence <= 1


def test_where_the_layer_has_no_words_it_picks_nothing(tmp_path):
    path, _ = _scan(tmp_path, "world")
    state = {"page": 1, "line": 0, "readings": ["world", "wor1d"], "box": [30, 90, 80, 110]}
    answer = _judge(path).decide(state, _question(["world", "wor1d"]))["reading"]
    assert (answer.value, answer.confidence) == ("", 0.0)


def test_its_pick_is_a_vote_beside_the_vision_judges(tmp_path):
    path, box = _scan(tmp_path, "world")

    class Vision:
        model = "vision"

        def decide(self, state, questions, image_png=None):
            return {"reading": decide.Answer("choice", "b", 0.6, {})}

    with pymupdf.open(path) as doc:
        (_, _, votes), confidence = ocrcheck._decide(
            doc[0], 1, 0, LINE.format("world"), 16, 21, ["wor1d"], box, "en",
            Vision(), None, DecisionCache(tmp_path / "decisions.jsonl"),
            alarms=[_judge(path)],
        )  # fmt: skip
    assert votes == {"vision": "wor1d", "render": "world"}
    assert confidence["render"] > 0


def test_a_text_cut_is_preferred_to_a_better_fitting_bold_or_italic():
    ranked = [
        {"file": "a/Face-Bold.otf", "name": "Face Bold", "fit": 0.8},
        {"file": "a/Face-Medium.otf", "name": "Face Medium", "fit": 0.79},
        {"file": "a/Face-It.otf", "name": "Face Italic", "fit": 0.7},
    ]
    assert rendercheck.text_cut(ranked)["name"] == "Face Medium"
    assert rendercheck.text_cut(ranked[::2])["name"] == "Face Bold"


def test_the_build_makes_the_judge_from_its_name_and_needs_the_fonts(tmp_path):
    class Book:
        source = tmp_path / "source.pdf"
        body_pages = (1, 1)
        stages = tmp_path

    settings = Settings(alarm_model="render", fonts=str(tmp_path / "no-fonts"))
    with pytest.raises(ValueError, match="no such folder"):
        pipeline._alarm("render", settings, Book())
