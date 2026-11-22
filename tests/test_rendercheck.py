import json
from dataclasses import asdict

import pymupdf
import pytest
from PIL import ImageFont

from roboscriptorium import ocrcheck, pipeline, rendercheck
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.pdf import PageText
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
    words = rendercheck.scan_words(path, [PageText(1, 400, 120, [])], 20)
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
    assert (answer.value, answer.confidence) == ("neither", 0.0)


def test_a_place_in_display_type_is_not_its_to_judge(tmp_path):
    from roboscriptorium.pdf import Line

    path, box = _scan(tmp_path, "world")
    high = box[3] - box[1]
    held = _judge(path)

    def judge(line_height: float) -> rendercheck.Judge:
        lines = [Line("there the quick world jumps", 30, 50, 300, 50 + line_height)] * 3
        return rendercheck.Judge(path, held._face, held._match, [PageText(1, 400, 120, lines)])

    state = {"page": 1, "line": 0, "readings": ["world", "wor1d"], "box": list(box)}
    question = _question(["world", "wor1d"])
    # A line of the text, a little taller or shorter than its neighbours: judged.
    assert judge(high).decide(state, question)["reading"].value == "a"
    assert judge(high * 0.85).decide(state, question)["reading"].value == "a"
    # Twice as tall as the book's lines: a heading, no vote.
    answer = judge(high / 2).decide(state, question)["reading"]
    assert (answer.value, answer.confidence) == ("neither", 0.0)


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


def test_a_build_without_the_font_folder_goes_on_without_the_judge(tmp_path, capsys):
    class Book:
        source = tmp_path / "source.pdf"
        body_pages = (1, 1)
        stages = tmp_path
        typeface = None

    settings = Settings(alarm_model="render", fonts=str(tmp_path / "no-fonts"))
    assert pipeline._alarm("render", settings, Book(), []) is None
    assert "without the judge 'render'" in capsys.readouterr().err
    with pytest.raises(ValueError, match="no such folder"):
        rendercheck.judge(Book.source, [], tmp_path / "no-fonts", tmp_path / "typeface.json")


def test_a_books_match_is_kept_for_any_slice_of_it(tmp_path):
    library = tmp_path / "fonts"
    library.mkdir()
    (library / "face.otf").write_bytes(b"")
    cache = tmp_path / "typeface.json"
    held = rendercheck.Match("face.otf", "Face", 0.7, 3, 50.0)
    key = {"version": rendercheck.VERSION, "typeface": None}
    cache.write_text(json.dumps({"key": key, "match": asdict(held)}))
    assert rendercheck.match(tmp_path / "none.pdf", [], library, cache) == held


def _library(tmp_path):
    """A font folder with the two faces PyMuPDF carries: a sans (the scan's) and a serif."""
    library = tmp_path / "fonts"
    library.mkdir()
    for name in ("helv", "tiro"):
        (library / f"{name}.otf").write_bytes(pymupdf.Font(name).buffer)
    return library


def test_the_match_is_the_face_the_scan_is_set_in_and_names_what_it_chose_among(tmp_path):
    path, _ = _scan(tmp_path, "world")
    cache = tmp_path / "typeface.json"
    found = rendercheck.match(path, [PageText(1, 400, 120, [])], _library(tmp_path), cache)
    assert found.file == "helv.otf" and found.size > 20
    tried = rendercheck.near(cache)
    assert [f["file"] for f in tried] == ["helv.otf", "tiro.otf"]
    assert tried[0]["place_fit"] > tried[1]["place_fit"] > 0


def test_book_tomls_typeface_overrules_the_match_and_must_be_in_the_folder(tmp_path):
    path, _ = _scan(tmp_path, "world")
    library, cache = _library(tmp_path), tmp_path / "typeface.json"
    pages = [PageText(1, 400, 120, [])]
    assert rendercheck.match(path, pages, library, cache).file == "helv.otf"
    assert rendercheck.match(path, pages, library, cache, "tiro.otf").file == "tiro.otf"
    # The key gone again, the book is matched again.
    assert rendercheck.match(path, pages, library, cache).file == "helv.otf"
    with pytest.raises(ValueError, match="no file in"):
        rendercheck.match(path, pages, library, cache, "gone.otf")


def test_near_ties_are_the_best_text_cuts_and_the_judges_fit_chooses_among_them(tmp_path):
    ranked = [
        {"file": "a/Face-Bold.otf", "name": "Face Bold", "fit": 0.8},
        {"file": "a/Face-Medium.otf", "name": "Face Medium", "fit": 0.79},
        {"file": "a/Other.otf", "name": "Other Regular", "fit": 0.7},
    ]
    assert [e["name"] for e in rendercheck.near_ties(ranked)] == ["Face Medium", "Other Regular"]
    assert rendercheck.near_ties(ranked[:1]) == ranked[:1]
    path, _ = _scan(tmp_path, "world")
    strips = rendercheck.word_strips(path, [PageText(1, 400, 120, [])], 24)
    assert {"there", "quick", "world"} <= {word for word, _ in strips}
    sans, serif = (
        rendercheck.Face(lambda px, n=n: ImageFont.truetype(_font(n), px)) for n in ("helv", "tiro")
    )
    words = rendercheck.scan_words(path, [PageText(1, 400, 120, [])], 20)
    fit = {
        face: rendercheck.place_fit(face, 0, rendercheck.em_size(words, face.at()), strips)
        for face in (sans, serif)
    }
    assert fit[sans] > fit[serif]
    assert rendercheck.place_fit(sans, 0, 50.0, []) == 0.0


def test_digits_are_drawn_in_the_fonts_other_figures_too_and_an_ordinals_ending_as_a_superscript():
    plain = rendercheck.Face(lambda px: ImageFont.load_default(px))
    # A stand-in for old-style figures: the digits drawn as other marks.
    old = rendercheck.Face(lambda px: ImageFont.load_default(px), [{ord("1"): ord("x")}])
    assert len(rendercheck.drawings(plain, "in 1914")) == 1
    assert len(rendercheck.drawings(old, "in 1914")) == 2
    assert len(rendercheck.drawings(old, "in time")) == 1
    # A superscript only after a digit: "je" and "twee" are words.
    assert len(rendercheck.drawings(plain, "14e")) == 1 + len(rendercheck.SUPERSCRIPT)
    assert len(rendercheck.drawings(plain, "de 2de keer")) == 1 + len(rendercheck.SUPERSCRIPT)
    for word in ("je", "twee", "14 en", "e14"):
        assert len(rendercheck.drawings(plain, word)) == 1
    raised, level = rendercheck.drawings(plain, "14e")[1], rendercheck.drawings(plain, "14e")[0]
    assert raised.shape[1] < level.shape[1]


def test_a_pick_is_surer_the_better_it_fits_and_the_wider_its_margin():
    sure = rendercheck.sureness
    assert 0 < sure(0.5, 0.0) < sure(0.5, 0.05) < sure(0.9, 0.05) < sure(0.9, 0.2) < 1
    # A good fit with no margin is a coin toss at best; a poor fit is doubted whatever the margin.
    assert sure(0.95, 0.0) < 0.75 and sure(0.6, 0.1) < 0.85 < sure(0.95, 0.1)


def test_a_font_without_other_figures_has_none(tmp_path):
    (tmp_path / "helv.otf").write_bytes(pymupdf.Font("helv").buffer)
    (tmp_path / "broken.otf").write_bytes(b"no font")
    assert rendercheck.other_figures(tmp_path / "helv.otf") == []
    assert rendercheck.other_figures(tmp_path / "broken.otf") == []


def _font(name: str):
    import io

    return io.BytesIO(pymupdf.Font(name).buffer)


def test_an_image_only_pages_words_are_its_first_readings(tmp_path):
    path, box = _scan(tmp_path, "world")
    with pymupdf.open(path) as doc:
        words = tuple(tuple(w) for w in doc[0].get_text("words"))
        doc[0].add_redact_annot(doc[0].rect)
        doc[0].apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
        pix = pymupdf.open(path)[0].get_pixmap(dpi=300)
        doc[0].insert_image(doc[0].rect, pixmap=pix)
        bare = tmp_path / "image-only.pdf"
        doc.save(bare)
    with pymupdf.open(bare) as doc:
        assert not doc[0].get_text("words")
    text = PageText(1, 400, 120, [], words=words)
    judge = rendercheck.Judge(bare, *(lambda j: (j._face, j._match))(_judge(path)), [text])
    state = {"page": 1, "line": 0, "readings": ["wor1d", "world"], "box": list(box)}
    assert judge.decide(state, _question(["wor1d", "world"]))["reading"].value == "b"
    assert rendercheck.scan_words(bare, [text], 20)


@pytest.mark.parametrize(
    ("printed", "versions", "picked"),
    [
        ("world. . .", ["world.", "world..."], "b"),
        ("world.", ["world.", "world..."], "a"),
    ],
)
def test_an_ellipsis_with_its_dots_apart_is_read_whole(tmp_path, printed, versions, picked):
    path = tmp_path / "dots.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=120)
    page.insert_text((30, 60), f"there the quick {printed}  He jumps", fontname="helv", fontsize=14)
    box = next(w[:4] for w in page.get_text("words") if w[4].startswith("world"))
    doc.save(path)
    state = {"page": 1, "line": 0, "readings": versions, "box": [round(v, 1) for v in box]}
    assert _judge(path).decide(state, _question(versions))["reading"].value == picked


def test_no_ink_to_compare_is_no_vote(tmp_path):
    path, _ = _scan(tmp_path, "world")

    class Vision:
        model = "vision"

        def decide(self, state, questions, image_png=None):
            return {"reading": decide.Answer("choice", "b", 0.6, {})}

    with pymupdf.open(path) as doc:
        (_, _, votes), _ = ocrcheck._decide(
            doc[0], 1, 0, LINE.format("world"), 16, 21, ["wor1d"], (30, 90, 80, 110), "en",
            Vision(), None, DecisionCache(tmp_path / "decisions.jsonl"),
            alarms=[_judge(path)],
        )  # fmt: skip
    assert votes == {"vision": "wor1d", "render": ""}


def test_on_a_tightly_set_line_the_strip_ends_before_the_next_word(tmp_path):
    path = tmp_path / "tight.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=120)
    x = 30.0
    for word in ("there", "the", "quick", "world", "jumps", "over"):
        page.insert_text((x, 60), word, fontname="helv", fontsize=14)
        x += pymupdf.get_text_length(word, "helv", 14) + 2.6
    box = next(w[:4] for w in page.get_text("words") if w[4] == "world")
    doc.save(path)
    versions = ["wor1d", "world"]
    state = {"page": 1, "line": 0, "readings": versions, "box": [round(v, 1) for v in box]}
    assert _judge(path).decide(state, _question(versions))["reading"].value == "b"


def test_a_crop_cut_short_by_the_neighbours_is_keyed_apart_and_drawn_within_its_span(tmp_path):
    path, box = _scan(tmp_path, "world")
    seen = []

    class Vision:
        model = "vision"

        def decide(self, state, questions, image_png=None):
            seen.append((dict(state), pymupdf.open(stream=image_png).load_page(0).rect.height))
            return {"reading": decide.Answer("choice", "a", 0.9, {})}

    def ask(span):
        with pymupdf.open(path) as doc:
            ocrcheck._decide(
                doc[0], 1, 0, LINE.format("world"), 16, 21, ["wor1d"], box, "en",
                Vision(), None, DecisionCache(tmp_path / f"d{len(seen)}.jsonl"), span=span,
            )  # fmt: skip

    ask(None)
    ask((box[1] - ocrcheck.CROP_PAD, box[3] + ocrcheck.CROP_PAD))  # the pad as it was
    ask((box[1], box[3] + ocrcheck.CROP_PAD))  # the line above's descenders cut off
    (plain, h0), (same, h1), (cut, h2) = seen
    assert "span" not in plain and "span" not in same and h0 == h1
    assert cut["span"] == [round(box[1], 1), round(box[3] + ocrcheck.CROP_PAD, 1)]
    assert h2 < h0


def test_a_capital_no_letter_touches_is_drawn_as_a_small_capital_too_one_opening_a_word_not():
    face = rendercheck.Face(lambda px: ImageFont.load_default(px))
    plain = len(rendercheck.drawings(face, "Toen"))
    assert len(rendercheck.drawings(face, "‘Tom")) == plain
    assert len(rendercheck.drawings(face, "T-shirt,")) == plain + len(rendercheck.SMALL_CAPS)
    assert len(rendercheck.drawings(face, "FBI-beleid")) == plain + len(rendercheck.SMALL_CAPS)


@pytest.mark.parametrize(("marked", "plain"), [("zíjn", "zijn"), ("één", "een")])
def test_a_printed_mark_scores_above_its_absence(tmp_path, marked, plain):
    scores = {}
    for printed in (marked, plain):
        path, box = _scan(tmp_path, printed)
        held = _judge(path)
        with pymupdf.open(path) as doc:
            ink = rendercheck.place_ink(doc[0], box)
        scores[printed] = rendercheck.mark_differ(held._face, held._match, ink, marked, plain)
    assert scores[marked] > scores[plain]


@pytest.mark.parametrize(
    ("score", "versions", "picked"),
    [
        (0.4, ["zijn", "zíjn"], "b"),
        (-0.3, ["zijn", "zíjn"], "a"),
        (0.4, ["één", "een"], "a"),
        (-0.3, ["één", "een"], "b"),
    ],
)
def test_the_mark_judge_picks_the_marks_the_scan_shows(
    tmp_path, monkeypatch, score, versions, picked
):
    path, box = _scan(tmp_path, "zijn")
    monkeypatch.setattr(rendercheck, "mark_differ", lambda *a: score)
    state = {"page": 1, "line": 0, "readings": versions, "box": [round(v, 1) for v in box]}
    answer = rendercheck.MarkJudge(_judge(path)).decide(state, _question(versions))["reading"]
    assert answer.value == picked
    assert 0.5 <= answer.confidence <= 1


def test_the_mark_judge_has_no_vote_where_the_letters_differ(tmp_path):
    path, box = _scan(tmp_path, "world")
    state = {
        "page": 1,
        "line": 0,
        "readings": ["world", "wor1d"],
        "box": [round(v, 1) for v in box],
    }
    judge = rendercheck.MarkJudge(_judge(path))
    assert judge.model == "render-mark"
    answer = judge.decide(state, _question(["world", "wor1d"]))["reading"]
    assert (answer.value, answer.confidence) == ("neither", 0.0)


def test_a_face_finds_its_italic_beside_it(tmp_path):
    for name in (
        "JansonTextLTStd-Roman.otf",
        "JansonTextLTStd-Italic.otf",
        "JansonTextLTStd-BoldItalic.otf",
    ):
        (tmp_path / name).write_bytes(b"")
    assert rendercheck.italic_of(tmp_path / "JansonTextLTStd-Roman.otf") == (
        tmp_path / "JansonTextLTStd-Italic.otf"
    )
    (tmp_path / "Plain.ttf").write_bytes(b"")
    assert rendercheck.italic_of(tmp_path / "Plain.ttf") is None


def test_the_italic_is_weighed_only_where_the_versions_differ_in_letters():
    assert rendercheck.same_marks(["7a.", "Ja."])
    assert rendercheck.same_marks(["boren", "horen"])
    # A stop or quote after an italic word is upright on the print.
    assert not rendercheck.same_marks(["lekker?", "lekker.’"])
    assert not rendercheck.same_marks(["Puan,", "Puan,’"])
