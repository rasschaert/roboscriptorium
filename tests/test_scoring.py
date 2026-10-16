from types import SimpleNamespace

from roboscriptorium.flags import Flag
from roboscriptorium.golden import scoring
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText


def test_a_question_without_readings_gets_the_read_models(tmp_path, monkeypatch):
    page = PageText(
        3,
        400,
        600,
        [Line("HOOFDSTUK EEN", 40, 40, 200, 52), Line("en toen ging", 40, 60, 360, 72)],
    )
    heading = Flag("h", 3, 0, 0, "HOOFDSTUK EEN", "heading", ["like-heading"])
    folio = Flag("f", 3, 1, 1, "en toen ging", "dropped", ["page-number"])
    asked = Flag("a", 3, 1, 1, "en toen ging", "text", ["ocr-doubt"], readings=[{"text": "x"}])
    lost = Flag("m", 3, 2, 1, "", "missing", ["missing-text"], (40, 80, 360, 92))
    tall = Flag("t", 3, 2, 1, "", "missing", ["missing-text"], (40, 100, 360, 160))
    read_lines = []

    def lines(pdf, pages, refs, *args):
        read_lines.extend(sorted(refs))
        return {SourceRef(3, 0): "HOOFDSTUK ÉÉN"}

    regions = []

    def boxes(pdf, wanted, *args):
        regions.extend(wanted)
        return {w: "Een regel die ontbrak." for w in wanted}

    monkeypatch.setattr(scoring.readers, "line_readings", lines)
    monkeypatch.setattr(scoring.readers, "region_readings", boxes)
    stages = SimpleNamespace(pages=[page], read_prompt="Read the line.")
    book = SimpleNamespace(source=tmp_path / "s.pdf", stages=tmp_path)
    out = scoring._read_unread(book, stages, [heading, folio, asked, lost, tall])
    # Only the heading's line is read; the scrap to drop and the line already asked aren't.
    assert read_lines == [SourceRef(3, 0)]
    assert out[0].readings == [
        {"text": "HOOFDSTUK EEN", "votes": []},
        {"text": "HOOFDSTUK ÉÉN", "votes": ["Qwen"]},
    ]
    assert out[1] == folio and out[2] == asked
    # A missing line one line tall is read as a line; a taller region isn't.
    assert regions == [(3, (40, 80, 360, 92))]
    assert out[3].readings == [{"text": "Een regel die ontbrak.", "votes": ["Qwen"]}]
    assert out[4].readings == []


def test_nothing_is_read_for_a_build_that_read_nothing():
    flag = Flag("h", 3, 0, 0, "HOOFDSTUK EEN", "heading", [])
    stages = SimpleNamespace(pages=[], read_prompt="")
    assert scoring._read_unread(SimpleNamespace(), stages, [flag]) == [flag]


def test_a_region_is_read_once_and_then_from_its_cache(tmp_path, monkeypatch):
    import pymupdf

    from roboscriptorium import readers

    doc = pymupdf.open()
    doc.new_page(width=400, height=600).insert_text((40, 90), "Een regel", fontsize=11)
    doc.save(tmp_path / "s.pdf")
    calls = []
    monkeypatch.setattr(readers, "transcribe", lambda png, *a: calls.append(png) or "Een regel")
    wanted = [(1, (40.0, 80.0, 360.0, 92.0))]
    args = (tmp_path / "s.pdf", wanted, "qwen", "http://x", tmp_path / "q.json", "Read.")
    assert readers.region_readings(*args) == {wanted[0]: "Een regel"}
    assert readers.region_readings(*args) == {wanted[0]: "Een regel"}
    assert len(calls) == 1
