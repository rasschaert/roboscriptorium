"""The stages together, from a PDF to the document, with a mock model server."""

import httpx
import pymupdf

from roboscriptorium import flags, pipeline
from roboscriptorium.book import Book
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.corrections import Corrections

LINES = [f"Line {i} of the story goes on and on across the page" for i in range(12)]


def _book(tmp_path) -> Book:
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    for i, text in enumerate(LINES):
        page.insert_text((40, 60 + 18 * i), text, fontsize=11)
    doc.save(tmp_path / "source.pdf")
    (tmp_path / "book.toml").write_text(
        'title = "T"\nauthor = "A"\nlanguage = "en"\nbody_pages = [1, 1]\n'
    )
    return Book.load(tmp_path)


def _everything_is_body(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        answer = {"type": "choice", "choice": "body", "confidence": 0.9}
        answer["probabilities"] = {"body": 0.9, "page_number": 0.1}
        return httpx.Response(200, json={"answers": {"role": answer}})

    def client(model, *_):
        http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
        return OllayaClient("http://test", model, client=http)

    monkeypatch.setattr(pipeline.ollaya, "for_model", client)


def test_answers_apply_to_the_book_and_keep_their_keys_across_builds(tmp_path, monkeypatch):
    _everything_is_body(monkeypatch)
    book = _book(tmp_path)
    raw = pipeline.run(book).pages[0]
    assert [ln.text for ln in raw.lines] == LINES

    answers = Corrections(book.corrections_path)
    retyped = flags.Flag(flags.region_key(1, LINES[5]), 1, 5, 5, LINES[5], "text", ["centred"])
    answers.record(retyped, "text", "Line five, as the scan prints it")
    missing = flags.Flag("p1-gap", 1, 3, 2, "", "missing", ["missing-text"], (40, 100, 360, 110))
    answers.record(missing, "text", "A line the text layer lacks.")

    for _ in range(2):  # a rebuild must apply the same answers again
        stages = pipeline.run(book)
        assert stages.corrections_applied == 2
        text = " ".join(p.text for p in stages.doc.paragraphs)
        assert "Line five, as the scan prints it" in text
        assert "A line the text layer lacks." in text
        assert LINES[5] not in text
        # The review sees the text layer as read, so the answered region keeps its key.
        assert [ln.text for ln in stages.pages[0].lines] == LINES
        assert flags.region_key(1, stages.pages[0].lines[5].text) == retyped.key
        # The document points at text-layer lines, even below the inserted one.
        refs = [s.line for p in stages.doc.paragraphs for s in p.sources]
        assert max(refs) == len(LINES) - 1
