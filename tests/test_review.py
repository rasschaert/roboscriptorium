"""The review server: who may post to it, which pages its crops are cut from, and a golden
book's places asked in the same list as a doubt between our text and the reference's."""

import http.client
import json
import socket
import threading
from types import SimpleNamespace

import pytest

from roboscriptorium import cli, review
from roboscriptorium.disagreements import Disagreement, Verdicts


class _Recorder:
    html = "regions.html"

    def __init__(self):
        self.recorded = []
        self.scan = None

    def state(self) -> dict:
        return {}

    def record(self, body: dict) -> dict:
        self.recorded.append(body)
        return {"ok": True}


@pytest.fixture
def server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    target = _Recorder()
    threading.Thread(target=review.serve, args=(target, port), daemon=True).start()
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
            break
        except OSError:
            threading.Event().wait(0.02)
    return port, target


def _post(port: int, headers: dict) -> int:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps({"key": "k"})
    conn.putrequest("POST", "/api/verdict", skip_host=True)
    for k, v in {"Content-Length": str(len(body)), **headers}.items():
        conn.putheader(k, v)
    conn.endheaders(body.encode())
    status = conn.getresponse().status
    conn.close()
    return status


def test_a_post_from_anywhere_but_the_servers_own_page_is_refused(server):
    port, target = server
    own = f"127.0.0.1:{port}"
    refused = [
        {"Host": own},  # no JSON: what a plain form sends
        {"Host": own, "Content-Type": "text/plain"},
        {"Host": own, "Content-Type": "application/x-www-form-urlencoded"},
        {"Host": f"evil.example:{port}", "Content-Type": "application/json"},
        {"Host": "127.0.0.1:1", "Content-Type": "application/json"},
        {"Host": own, "Content-Type": "application/json", "Origin": "http://evil.example"},
        {"Host": own, "Content-Type": "application/json", "Origin": "null"},
    ]
    for headers in refused:
        assert _post(port, headers) == 403, headers
    assert target.recorded == []


def test_the_servers_own_page_may_post(server):
    port, target = server
    for host in (f"127.0.0.1:{port}", f"localhost:{port}"):
        json_type = {"Host": host, "Content-Type": "application/json; charset=utf-8"}
        assert _post(port, json_type) == 200
        assert _post(port, {**json_type, "Origin": f"http://{host}"}) == 200
    assert len(target.recorded) == 4


def test_a_golden_books_places_join_the_review_cropped_from_the_layer(tmp_path, monkeypatch):
    layer = [SimpleNamespace(number=1, name="layer", lines=[])]
    corrected = [SimpleNamespace(number=1, name="corrected", lines=[])]
    stages = SimpleNamespace(
        pages=layer,
        corrected=corrected,
        model_roles={},
        suspects=[],
        quote_lines=[],
        quote_readings={},
        faint_pages=set(),
        epigraph_lines=set(),
        corrections_applied=0,
        read_prompt="",
    )
    book = SimpleNamespace(
        root=tmp_path,
        source=tmp_path / "source.pdf",
        stages=tmp_path,
        language="nl",
        golden="g",
        corrections_path=tmp_path / "review" / "answers.jsonl",
        epub_path=tmp_path / "b.epub",
        epubs=tmp_path / "epubs",
    )
    seen = {}
    monkeypatch.setattr(cli, "_not_the_test_set", lambda *a: None)
    monkeypatch.setattr(cli.Book, "load", lambda d: book)
    monkeypatch.setattr(cli.scoring, "reference", lambda b, chapters: ([], ([], [])))
    monkeypatch.setattr(cli.pipeline, "run", lambda b, pages=None: stages)
    monkeypatch.setattr(cli, "keep_dated", lambda *a: None)
    monkeypatch.setattr(cli.scoring.layout, "available", lambda: False)
    monkeypatch.setattr(cli.scoring, "scored", lambda b, s: "doc")
    monkeypatch.setattr(cli.scoring, "verdicts", lambda b: Verdicts(tmp_path / "v.jsonl"))
    monkeypatch.setattr(cli.initials, "vocabulary", lambda *a: set())

    def find(doc, reference, pages, language, around=([], [])):
        seen["find"] = pages
        seen["language"] = language
        return [_place("geld", "geId"), Disagreement("auto", "x#", "x", "", "", 1, (0, 0), "ocr")]

    monkeypatch.setattr(cli.disagreements, "find", find)
    monkeypatch.setattr(review, "serve", lambda r, port: seen.setdefault("review", r))
    cli.review_regions(tmp_path, None, None, 8765, False)
    # The paragraphs point into the pages before answers (`Line.source`), not the
    # corrected copy, where a typed line above would shift every crop.
    assert seen["find"] is layer
    assert seen["review"].scan.pages[1] is layer[0]
    assert seen["language"] == "nl"
    # One list: the place a human must settle, not the one settled without review.
    items = seen["review"].state()["items"]
    assert [i["key"] for i in items] == ["k"]
    assert items[0]["reasons"] == [review.GoldenQuestions.REASON]


def _place(got: str, want: str) -> Disagreement:
    return Disagreement("k", got, want, "Hij was zo stom geweest zijn", "niet op een", 17, (24, 24))


def _verdicts(tmp_path, d: Disagreement) -> review.RegionReview:
    """A review of a golden book whose one question is the place `d`."""
    return review.RegionReview(
        tmp_path / "s.pdf",
        [],
        [],
        review.Corrections(tmp_path / "answers.jsonl"),
        lambda: None,
        "nld",
        golden=review.GoldenQuestions([d], Verdicts(tmp_path / "v.jsonl")),
    )


def test_a_verdict_is_asked_as_two_readings_labelled_by_who_claims_them(tmp_path):
    item = _verdicts(tmp_path, _place("geld", "geId")).state()["items"][0]
    ours, theirs = item["readings"]
    assert ours == {"text": "Hij was zo stom geweest zijn geld niet op een", "votes": ["our text"]}
    assert theirs["text"] == "Hij was zo stom geweest zijn geId niet op een"
    assert theirs["votes"] == ["the publisher's e-book"]
    # The place in the line, which the page marks in each reading.
    start, end = item["span"]
    assert ours["text"][start:end] == "geld"
    assert item["answer"] is None


def test_the_reading_chosen_is_the_verdict(tmp_path):
    d = _place("geld", "geId")
    r = _verdicts(tmp_path, d)
    r.record({"key": "k", "text": "Hij was zo stom geweest zijn geld niet op een"})
    v = Verdicts(tmp_path / "v.jsonl").by_key["k"]
    assert (v.truth, v.category) == ("geld", "edition")
    r.record({"key": "k", "text": "Hij was zo stom geweest zijn geId niet op een"})
    v = Verdicts(tmp_path / "v.jsonl").by_key["k"]
    assert (v.truth, v.category) == ("geId", "ocr")
    # Typed: the words between the context, and the page shows the answer again.
    typed = {"key": "k", "text": "Hij was zo stom geweest zijn gold niet op een"}
    assert "none of the readings" in r.record(typed)["warning"]
    r.record({**typed, "confirm": True})
    r = _verdicts(tmp_path, d)
    assert r.golden.verdicts.by_key["k"].truth == "gold"
    assert r.state()["items"][0]["answer"]["text"].endswith("zijn gold niet op een")


def test_a_typed_answer_that_changes_the_words_around_the_place_is_refused(tmp_path):
    r = _verdicts(tmp_path, _place("geld", "geId"))
    for text in (
        "Hij was zo stom geweest zijn gold niet op één",
        "Hij was zo DOM geweest zijn gold niet op een",
        "Hij was zo stom geweest zijnx gold niet op een",
    ):
        answer = {"key": "k", "text": text, "confirm": True}
        assert r.record(answer) == {
            "warning": review.GoldenQuestions.CONTEXT_CHANGED,
            "refused": True,
        }
    assert "k" not in Verdicts(tmp_path / "v.jsonl").by_key
    # Only the place's words changed, a word dropped there included: saved.
    r.record({"key": "k", "text": "Hij was zo stom geweest zijn niet op een", "confirm": True})
    assert Verdicts(tmp_path / "v.jsonl").by_key["k"].truth == ""


def test_a_place_one_side_lacks_reads_without_a_double_space(tmp_path):
    ours, theirs = _verdicts(tmp_path, _place("16", "")).state()["items"][0]["readings"]
    assert ours["text"] == "Hij was zo stom geweest zijn 16 niet op een"
    assert theirs["text"] == "Hij was zo stom geweest zijn niet op een"


def test_a_place_across_a_page_break_shows_the_other_page(tmp_path):
    d = Disagreement(
        "k",
        "saying ...'",
        "saying ...'>",
        "That's what you're",
        "'OK, so",
        61,
        (40, 40),
        across=(62, 0),
    )
    item = _verdicts(tmp_path, d).state()["items"][0]
    assert item["across"] == {"page": 62, "first": 0, "last": 0}
    assert _verdicts(tmp_path, _place("geld", "geId")).state()["items"][0]["across"] is None


def test_a_caption_is_answered_as_what_it_is_with_its_words(tmp_path):
    d = _place('"One evening when the Doctor was asleep in his chair"', "")
    r = _verdicts(tmp_path, d)
    text = "\u201cOne evening when the Doctor was asleep in his chair\u201d"
    r.record({"key": "k", "action": "caption", "text": text})
    v = Verdicts(tmp_path / "v.jsonl").by_key["k"]
    # The running text has no such words: the reference is right, and it was a caption,
    # whose words as printed are kept.
    assert (v.truth, v.category, v.note) == ("", "caption", f"caption: {text}")
    answer = _verdicts(tmp_path, d).state()["items"][0]["answer"]
    assert answer == {"action": "caption", "text": text}
    # Without words, the kind alone.
    r.record({"key": "k", "action": "drop", "text": ""})
    assert Verdicts(tmp_path / "v.jsonl").by_key["k"].note == "drop"


def test_a_place_shows_each_sides_dashes_and_quotes_as_written(tmp_path):
    folded = Disagreement(
        "k",
        "nu'",
        "dan'",
        "Ik moet —",
        "zei hij",
        17,
        (24, 24),
        written=("nu\u2019", "dan'", "Ik moet \u2013", "zei hij"),
    )
    r = _verdicts(tmp_path, folded)
    ours, theirs = r.state()["items"][0]["readings"]
    assert ours["text"] == "Ik moet \u2013 nu\u2019 zei hij"
    assert theirs["text"] == "Ik moet \u2013 dan' zei hij"
    # Choosing our reading records our words as printed; it reads back as chosen.
    r.record({"key": "k", "text": ours["text"]})
    assert r.golden.verdicts.by_key["k"].truth == "nu\u2019"
    assert r.golden.verdicts.by_key["k"].category == "edition"
    assert r.state()["items"][0]["answer"]["text"] == ours["text"]


def test_answers_saved_at_once_each_keep_their_line(tmp_path):
    r = _verdicts(tmp_path, _place("geld", "geId"))
    answer = {"key": "k", "text": "Hij was zo stom geweest zijn geld niet op een"}
    threads = [
        threading.Thread(target=lambda: [r.record(answer) for _ in range(50)]) for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    lines = (tmp_path / "v.jsonl").read_text().splitlines()
    assert len(lines) == 400 and all(json.loads(line)["key"] == "k" for line in lines)


def test_a_lost_lines_white_space_is_outlined_clear_of_the_lines_around_it(tmp_path):
    import pymupdf

    from roboscriptorium.pdf import Line, PageText

    doc = pymupdf.open()
    doc.new_page(width=300, height=300)
    doc.save(tmp_path / "s.pdf")
    lines = [
        Line("je eten en je drinken", 40, 196.5, 200, 205.3),
        Line("En, vergeef", 40, 221.3, 190, 230.2),
    ]
    scan = review.Scan(tmp_path / "s.pdf", [PageText(1, 300, 300, lines)])
    gap = scan._gap(1, (40, 205.3, 200, 221.3))
    # Below the descenders of the line above (its box ends at the baseline), above the next.
    assert gap.y0 >= 205.3 + 0.35 * 8.8 and gap.y1 < 221.3


def test_a_lost_lines_draft_is_read_below_the_descenders_of_the_line_above(tmp_path, monkeypatch):
    import pymupdf

    from roboscriptorium.pdf import Line, PageText

    doc = pymupdf.open()
    doc.new_page(width=300, height=300)
    doc.save(tmp_path / "s.pdf")
    lines = [Line("retrohelmpje op", 40, 372.8, 280, 382.0), Line("wel op", 40, 397.6, 280, 407.0)]
    scan = review.Scan(tmp_path / "s.pdf", [PageText(1, 300, 300, lines)])
    tops = []

    def read(page, box, lang, **_):
        tops.append(round(box[1], 2))
        # The crop from the baseline takes in the descenders above and reads as noise.
        return "es + u u ee" if box[1] < 383 else "en\n\nzijn moderne cilindervormige kop, en dan"

    monkeypatch.setattr(scan, "read_box", read)
    assert scan.read_gap(1, (40, 382.0, 280, 397.6), "nld") == (
        "zijn moderne cilindervormige kop, en dan"
    )
    assert tops[0] == 382.0 and len(tops) == len(review.GAP_STEPS)


def test_readings_differing_only_in_a_double_quote_set_as_two_singles_are_one_option():
    line = "echt waar! {} Ze was"
    got = review.merged(
        [
            {"text": line.format("“Een nachtwaker’’!’"), "votes": ["text layer"]},
            {"text": line.format("‘‘Een nachtwaker’’!’"), "votes": ["OCR check"]},
            {"text": line.format("“Een nachtwaker”’!"), "votes": ["Qwen"]},
            # Two closing marks before a letter are an apostrophe read twice: kept apart.
            {"text": "zei ’’m", "votes": ["glm-ocr"]},
            {"text": "zei ”m", "votes": ["tesseract"]},
        ]
    )
    assert [g["votes"] for g in got] == [
        ["text layer", "OCR check"],
        ["Qwen"],
        ["glm-ocr"],
        ["tesseract"],
    ]
    assert got[0]["text"] == line.format("“Een nachtwaker’’!’")


def test_readings_differing_at_separate_places_offer_every_combination_and_accept_them():
    a = "Paganini: “Ga jij nu"
    b = "Paganini: ‘Gajij nu"
    assert review.combinations([a, b], 6) == [
        a,
        b,
        "Paganini: “Gajij nu",
        "Paganini: ‘Ga jij nu",
    ]
    readings = [{"text": a, "votes": ["text layer"]}, {"text": b, "votes": ["glm-ocr"]}]
    assert review.doubtful(a, readings, "text", "Paganini: ‘Ga jij nu") == ""
    # A letter no reading has is still a stranger.
    assert "none of the readings" in review.doubtful(a, readings, "text", "Paganini: ‘Ga jij nn")
    shown = review.with_combinations(readings)
    assert [g["votes"] for g in shown] == [["text layer"], ["glm-ocr"], ["combined"], ["combined"]]


def test_combinations_keep_insertions_at_their_place_and_stop_past_the_limit():
    assert review.combinations(["ab cd", "aXb cd", "ab cYd"], 6) == [
        "ab cd",
        "aXb cd",
        "ab cYd",
        "aXb cYd",
    ]
    many = ["abcdef", "Abcdef", "aBcdef", "abCdef"]
    assert review.combinations(many, 6) == []  # eight lines would be more than six
    assert review.with_combinations([{"text": t, "votes": []} for t in many]) == [
        {"text": t, "votes": []} for t in many
    ]


def test_a_typed_line_is_checked_against_the_one_reading_a_heading_has():
    qwen = [{"text": "HOOFDSTUK EEN", "votes": ["text layer", "Qwen"]}]
    assert review.doubtful("HOOFDSTUK EEN", qwen, "heading", "HOOFDSTUK EEN") == ""
    assert review.doubtful("HOOFDSTUK EEN", qwen, "heading", "HOOFDSTUK EN")


def test_a_place_where_one_side_has_nothing_says_what_the_other_has(tmp_path):
    verdicts = Verdicts(tmp_path / "v.jsonl")
    extra = Disagreement("e", "", ">", "de tunnel", "in", 61, (3, 3))
    lost = Disagreement("l", "en", "", "zei hij", "toen", 61, (4, 4))
    both = _place("geld", "geId")
    items = {i["key"]: i for i in review.GoldenQuestions([extra, lost, both], verdicts).state()}
    assert items["e"]["reasons"] == ["the publisher's e-book has “>” here, our text nothing"]
    assert items["l"]["reasons"] == ["our text has “en” here, the publisher's e-book nothing"]
    assert items["k"]["reasons"] == [review.GoldenQuestions.REASON]
