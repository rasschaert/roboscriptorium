"""The stages together, from a PDF to the document, with a mock model server."""

from dataclasses import replace

import httpx
import pymupdf

from roboscriptorium import flags, pipeline
from roboscriptorium.book import Book
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.corrections import Corrections

LINES = [f"Line {i} of the story goes on and on across the page" for i in range(12)]


def _book(tmp_path, indented: tuple[int, ...] = ()) -> Book:
    """A one-page book of LINES; the `indented` lines open paragraphs."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    for i, text in enumerate(LINES):
        page.insert_text((60 if i in indented else 40, 60 + 18 * i), text, fontsize=11)
    doc.save(tmp_path / "source.pdf")
    (tmp_path / "book.toml").write_text(
        'title = "T"\nauthor = "A"\nlanguage = "en"\nbody_pages = [1, 1]\n'
    )
    return Book.load(tmp_path)


def _no_layout(monkeypatch) -> None:
    monkeypatch.setattr(pipeline.layout, "available", lambda: False)


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
    _no_layout(monkeypatch)
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


def test_a_picture_goes_into_the_book_between_paragraphs_with_its_caption(tmp_path, monkeypatch):
    import zipfile

    from roboscriptorium.ir import Figure
    from roboscriptorium.layout import Region

    _everything_is_body(monkeypatch)
    book = _book(tmp_path, indented=(6,))
    picture = Region("figure", 0.9, 60, 140, 300, 200)
    monkeypatch.setattr(pipeline.layout, "available", lambda: True)
    monkeypatch.setattr(pipeline.layout, "detect", lambda pdf, numbers, cache: {1: [picture]})
    answers = Corrections(book.corrections_path)
    caption = flags.Flag("p1-cap", 1, 0, -1, "", "missing", ["caption"], (60, 202, 300, 210))
    answers.record(caption, "caption", "“The Doctor's house”")

    doc = pipeline.run(book).doc
    figure = next(b for b in doc.blocks if isinstance(b, Figure))
    assert figure.caption == "“The Doctor's house”"
    # Between the paragraph that starts above the picture and the one that starts below it.
    at = doc.blocks.index(figure)
    assert [doc.blocks[at - 1].sources[0].line, doc.blocks[at + 1].sources[0].line] == [0, 6]
    with zipfile.ZipFile(book.epub_path) as epub:
        names = epub.namelist()
        assert f"OEBPS/images/{figure.image}" in names
        text = "".join(epub.read(n).decode() for n in names if n.endswith(".xhtml"))
        assert f'<img src="images/{figure.image}"' in text
        assert "<figcaption>“The Doctor's house”</figcaption>" in text
        assert f'href="images/{figure.image}"' in epub.read("OEBPS/content.opf").decode()


def test_a_caption_inside_a_pictures_box_is_trimmed_off():
    from roboscriptorium.figures import TRIM_GAP, _without

    # A sideways caption down the right edge, and an upright one along the bottom.
    assert _without((10, 10, 300, 400), [(280, 50, 295, 350)]) == (10, 10, 280 - TRIM_GAP, 400)
    assert _without((10, 10, 300, 400), [(40, 380, 260, 395)]) == (10, 10, 300, 380 - TRIM_GAP)
    assert _without((10, 10, 300, 400), [(10, 420, 300, 440)]) == (10, 10, 300, 400)


def test_italic_words_on_the_scan_reach_the_epub(tmp_path, monkeypatch):
    _everything_is_body(monkeypatch)
    _no_layout(monkeypatch)
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    for i, text in enumerate(LINES):
        page.insert_text((40, 60 + 18 * i), text, fontsize=11)
    y = 60 + 18 * len(LINES)
    x = 40
    for text, font in (
        ("He said it was ", "tiro"),
        ("truly remarkable", "tiit"),
        (", and left.", "tiro"),
    ):
        page.insert_text((x, y), text, fontsize=11, fontname=font)
        x += pymupdf.get_text_length(text, fontname=font, fontsize=11)
    doc.save(tmp_path / "source.pdf")
    (tmp_path / "book.toml").write_text(
        'title = "T"\nauthor = "A"\nlanguage = "en"\nbody_pages = [1, 1]\n'
    )
    book = Book.load(tmp_path)

    paragraph = pipeline.run(book, check_ocr=False).doc.paragraphs[-1]
    words = paragraph.text.split()
    assert [words[k] for k in paragraph.italic] == ["truly", "remarkable,"]
    import zipfile

    with zipfile.ZipFile(book.epub_path) as z:
        xhtml = "".join(z.read(n).decode() for n in z.namelist() if n.endswith(".xhtml"))
    assert "it was <i>truly remarkable</i>, and left." in xhtml


def test_a_printed_line_the_text_layer_lacks_is_read_into_the_book(tmp_path, monkeypatch):
    from roboscriptorium.layout import Region

    _everything_is_body(monkeypatch)
    book = _book(tmp_path)
    answers = Corrections(book.corrections_path)
    retyped = flags.Flag(flags.region_key(1, LINES[5]), 1, 5, 5, LINES[5], "text", ["centred"])
    answers.record(retyped, "text", "Line five, as the scan prints it")
    number = Region("abandon", 0.6, 190, 20, 200, 32)
    monkeypatch.setattr(pipeline.layout, "available", lambda: True)
    monkeypatch.setattr(pipeline.layout, "detect", lambda pdf, numbers, cache: {1: [number]})
    monkeypatch.setattr(pipeline.ocrcheck, "scanned", lambda pdf: True)
    monkeypatch.setattr(pipeline.missing.ocrcheck, "read_line", lambda png, model, url: "Seven")

    stages = pipeline.run(book, check_ocr=False)
    assert [ln.text for ln in stages.pages[0].lines] == ["Seven"] + LINES
    text = " ".join(p.text for p in stages.doc.paragraphs)
    assert text.startswith("Seven")
    # The answer recorded before the line was added still finds its line.
    assert stages.corrections_applied == 1
    assert "Line five, as the scan prints it" in text and LINES[5] not in text


def test_a_lost_quote_becomes_a_question_that_stays_once_answered(tmp_path, monkeypatch):
    _everything_is_body(monkeypatch)
    _no_layout(monkeypatch)
    book = _book(tmp_path)
    lost = "the story goes on, he said.’ And that was that"
    read = pipeline.cached_text_layer

    def layer(*args):
        pages = read(*args)
        lines = [replace(ln, text=lost) if k == 11 else ln for k, ln in enumerate(pages[0].lines)]
        return [replace(pages[0], lines=lines)]

    monkeypatch.setattr(pipeline, "cached_text_layer", layer)

    def asked(stages) -> list[flags.Flag]:
        found = flags.find(stages.pages, stages.model_roles, quotes=stages.quote_lines)
        return [f for f in found if "quotes" in f.reasons]

    stages = pipeline.run(book)
    (question,) = asked(stages)
    assert question.first <= 11 <= question.last
    printed = question.text.replace("the story goes on, he", "‘the story goes on, he")
    Corrections(book.corrections_path).record(question, "text", printed)
    again = pipeline.run(book)
    assert again.corrections_applied == 1
    assert "‘the story" in " ".join(p.text for p in again.doc.paragraphs)
    # The question was found before the answer, so it is still asked.
    assert [f.key for f in asked(again)] == [question.key]


def test_a_quote_question_offers_the_lines_marks_as_read_on_the_scan(tmp_path, monkeypatch):
    _everything_is_body(monkeypatch)
    _no_layout(monkeypatch)
    book = _book(tmp_path)
    lost = "the story goes on, he said.’ And that was that"
    read = pipeline.cached_text_layer

    def layer(*args):
        pages = read(*args)
        lines = [replace(ln, text=lost) if k == 11 else ln for k, ln in enumerate(pages[0].lines)]
        return [replace(pages[0], lines=lines)]

    monkeypatch.setattr(pipeline, "cached_text_layer", layer)
    monkeypatch.setattr(pipeline.ocrcheck, "scanned", lambda pdf: True)
    monkeypatch.setattr(pipeline, "dash_style", lambda book, body: None)
    prompts = []

    def transcribe(png, model, url, prompt):
        prompts.append(prompt)
        return "'the story gaes on,' he said.' And that was that"

    monkeypatch.setattr(pipeline.ocrcheck, "transcribe", transcribe)
    stages = pipeline.run(book, check_ocr=False)
    found = flags.find(
        stages.pages, stages.model_roles, quotes=stages.quote_lines,
        proposed=stages.quote_readings,
    )  # fmt: skip
    (question,) = [f for f in found if "quotes" in f.reasons]
    layer_text, scan = (r["text"] for r in question.readings)
    assert layer_text == question.text
    # The scan's marks, the text layer's letters ("goes", not "gaes").
    assert "‘the story goes on,’ he said.’" in scan
    assert prompts and "English" in prompts[0]
    # A reading that is picked is the answer, applied on the next build.
    Corrections(book.corrections_path).record(question, "text", scan)
    again = pipeline.run(book, check_ocr=False)
    assert "‘the story goes on,’ he said." in " ".join(p.text for p in again.doc.paragraphs)
