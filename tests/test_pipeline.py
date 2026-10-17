"""The stages together, from a PDF to the document, with a mock model server."""

import json
from dataclasses import replace

import httpx
import pymupdf
import pytest

from roboscriptorium import errata, flags, pipeline, trust
from roboscriptorium.book import Book
from roboscriptorium.clients.decide import DecisionClient
from roboscriptorium.corrections import Corrections
from roboscriptorium.ir import SourceRef

LINES = [f"Line {i} of the story goes on and on across the page" for i in range(12)]


def _book(tmp_path, indented: tuple[int, ...] = (), lines: list[str] = LINES) -> Book:
    """A one-page book of `lines`; the `indented` lines open paragraphs."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    for i, text in enumerate(lines):
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
        answers = {"role": answer}
        for name, q in json.loads(request.content)["questions"].items():
            if name != "role":
                # Any other question gets a guess too unsure to act on.
                first = next(iter(q["criteria"]))
                answers[name] = {"type": "choice", "choice": first, "confidence": 0.4}
                answers[name]["probabilities"] = {first: 0.4}
        return httpx.Response(200, json={"answers": answers})

    def client(model, *_):
        http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
        return DecisionClient("http://test", model, client=http)

    monkeypatch.setattr(pipeline.decide, "for_model", client)


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
    monkeypatch.setattr(pipeline.missing.readers, "read_line", lambda png, model, url: "Seven")

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

    monkeypatch.setattr(pipeline.readers, "transcribe", transcribe)
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


def _checked_book(tmp_path, monkeypatch) -> tuple[Book, list[str]]:
    """A scanned one-page book whose OCR check sees one suspect, on line 3, which only
    the read model reads apart; and the prompts the read model is given."""
    import json

    def handler(request: httpx.Request) -> httpx.Response:
        names = json.loads(request.content)["questions"]
        answer = {"type": "choice", "choice": "a", "confidence": 0.9}
        answer["probabilities"] = {"a": 0.9, "b": 0.1}
        if "role" in names:
            answer = {**answer, "choice": "body", "probabilities": {"body": 0.9}}
        return httpx.Response(200, json={"answers": {n: answer for n in names}})

    def client(model, *_):
        http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
        return DecisionClient("http://test", model, client=http)

    monkeypatch.setattr(pipeline.decide, "for_model", client)
    _no_layout(monkeypatch)
    book = _book(tmp_path)
    monkeypatch.setattr(pipeline.ocrcheck, "scanned", lambda pdf: True)
    monkeypatch.setattr(pipeline, "dash_style", lambda book, body: None)
    monkeypatch.setattr(pipeline.Lexicon, "load", lambda lang: None)
    monkeypatch.setattr(pipeline.readers, "tesseract_readings", lambda *args: {})
    # glm-ocr reads every line as the layer does; only the read model reads line 3 apart.
    lines = iter(LINES)
    monkeypatch.setattr(pipeline.readers, "read_line", lambda png, model, url: next(lines))
    prompts = []

    def transcribe(png, model, url, prompt):
        prompts.append(prompt)
        return "Line 3 of the stony goes on and on across the page" if len(prompts) == 4 else ""

    monkeypatch.setattr(pipeline.readers, "transcribe", transcribe)
    monkeypatch.setattr(pipeline.readers, "READ_WORKERS", 1)
    return book, prompts


def test_the_read_models_reading_of_a_line_is_checked_like_the_others(tmp_path, monkeypatch):
    monkeypatch.setenv("ROBO_OCR_TRUST", "0")
    book, prompts = _checked_book(tmp_path, monkeypatch)
    stages = pipeline.run(book)
    assert stages.ocr_decider == "fixed rule"
    (suspect,) = stages.suspects
    assert (suspect.line, suspect.ours, suspect.others) == (3, "story", ("stony",))
    assert suspect.support["qwen"] == (False, True) and suspect.support["glm"] == (True, False)
    assert "English" in prompts[0]


def test_a_washed_out_page_is_left_to_the_reviewer_not_read_by_the_ocr_check(tmp_path, monkeypatch):
    monkeypatch.setenv("ROBO_OCR_TRUST", "0")
    book, prompts = _checked_book(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline.faint, "pages", lambda pdf, body, cache: {1})
    stages = pipeline.run(book)
    assert stages.faint_pages == {1}
    assert stages.suspects == [] and prompts == []
    assert "story" in stages.doc.blocks[0].text


def test_the_ocr_check_stops_when_its_trust_model_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ROBO_OCR_TRUST_MODEL", str(tmp_path / "none.pkl"))
    book, _ = _checked_book(tmp_path, monkeypatch)
    with pytest.raises(trust.Mismatch):
        pipeline.run(book)


def test_a_scans_spaced_ellipses_come_out_as_printed_and_a_born_digital_pdfs_as_they_are(
    tmp_path, monkeypatch
):
    _everything_is_body(monkeypatch)
    _no_layout(monkeypatch)
    book = _book(tmp_path)
    read = pipeline.cached_text_layer

    def layer(*args):
        # Half the reads keep the print's gaps; reflow's tidying would squash the rest.
        pages = read(*args)
        said = ["it went . . . on", "it went... on"]
        lines = [replace(ln, text=said[k % 2]) for k, ln in enumerate(pages[0].lines)]
        return [replace(pages[0], lines=lines)]

    monkeypatch.setattr(pipeline, "cached_text_layer", layer)
    monkeypatch.setattr(pipeline, "dash_style", lambda book, body: None)
    text = " ".join(p.text for p in pipeline.run(book, use_models=False).doc.paragraphs)
    assert "went..." in text and " " not in text
    monkeypatch.setattr(pipeline.ocrcheck, "scanned", lambda pdf: True)
    text = " ".join(p.text for p in pipeline.run(book, use_models=False).doc.paragraphs)
    assert text.count("went . . . on") == len(LINES)


def test_a_slice_is_read_with_the_whole_books_style(tmp_path, monkeypatch):
    monkeypatch.setenv("ROBO_OCR_TRUST", "0")
    book, prompts = _checked_book(tmp_path, monkeypatch)
    (tmp_path / "book.toml").write_text(
        'title = "T"\nauthor = "A"\nlanguage = "en"\nbody_pages = [1, 2]\n'
    )
    book = Book.load(tmp_path)
    read = pipeline.cached_text_layer

    def layer(*args):
        # Page 2 is set in single quotes; page 1 has none.
        (page,) = read(*args)
        quoted = [replace(ln, text="‘Yes,’ she said, ‘it was.’") for ln in page.lines]
        return [page, replace(page, number=2, lines=quoted)]

    monkeypatch.setattr(pipeline, "cached_text_layer", layer)
    # The scan has one page; the styles measured on it would look for page 2.
    monkeypatch.setattr(pipeline, "dash_style", lambda book, body: None)
    monkeypatch.setattr(pipeline.scanstyle, "measure_ellipses", lambda *a: None)
    pipeline.run(book, pages=(1, 1))
    pages = layer(book.source, book.stages / "textlayer.json")
    whole = pipeline.read_prompt(book, pages, None)
    assert prompts and set(prompts) == {whole}
    assert whole != pipeline.read_prompt(book, pages[:1], None)


def test_a_washed_out_scan_page_reaches_the_review_as_one_region(tmp_path, monkeypatch):
    _no_layout(monkeypatch)
    book = _book(tmp_path)
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    page.draw_rect(page.rect, color=None, fill=(0.61,) * 3)
    for i, text in enumerate(LINES):
        page.insert_text((40, 60 + 18 * i), text, fontsize=11, color=(0.58,) * 3)
    doc.save(book.source)
    monkeypatch.setattr(pipeline.ocrcheck, "scanned", lambda pdf: True)
    monkeypatch.setattr(pipeline, "dash_style", lambda book, body: None)
    stages = pipeline.run(book, use_models=False)
    assert stages.faint_pages == {1}
    found = flags.find(stages.pages, {}, faint=stages.faint_pages)
    assert [(f.first, f.last, f.reasons) for f in found] == [(0, len(LINES) - 1, ["washed-out"])]


def test_an_undecided_line_end_hyphen_is_the_judges_once_and_cached(tmp_path, monkeypatch):
    _no_layout(monkeypatch)
    asked = []

    def handler(request: httpx.Request) -> httpx.Response:
        questions = json.loads(request.content)["questions"]
        if "spelling" in questions:
            asked.append(questions["spelling"]["criteria"]["hyphenated"])
            answer = {"type": "choice", "choice": "hyphenated", "confidence": 0.8}
            answer["probabilities"] = {"hyphenated": 0.8, "closed": 0.2}
            return httpx.Response(200, json={"answers": {"spelling": answer}})
        answer = {"type": "choice", "choice": "body", "confidence": 0.9}
        answer["probabilities"] = {"body": 0.9, "page_number": 0.1}
        return httpx.Response(200, json={"answers": {"role": answer}})

    def client(model, *_):
        http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
        return DecisionClient("http://test", model, client=http)

    monkeypatch.setattr(pipeline.decide, "for_model", client)
    lines = [*LINES[:5], "and the zib-", "zorp went on", *LINES[7:]]
    book = _book(tmp_path, lines=lines)
    for _ in range(2):
        doc = pipeline.run(book, check_ocr=False).doc
        assert "the zib-zorp went on" in doc.blocks[0].text
    assert asked == ["zib-zorp"]


def test_a_footnote_leaves_the_running_text_and_follows_the_paragraph_with_its_mark(
    tmp_path, monkeypatch
):
    _everything_is_body(monkeypatch)
    _no_layout(monkeypatch)
    from roboscriptorium.lexicon import Lexicon

    words = {"hill", "near", "the", "town", "with", "railway", "up", "to", "top", "of", "it"}
    monkeypatch.setattr(pipeline.Lexicon, "load", lambda lang: Lexicon(words))
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    lines = [f"Line {i} of the story goes on and on across the page" for i in range(10)]
    lines[4] = "Line 4 of the story goes on up the hill* and on"
    for i, text in enumerate(lines):
        page.insert_text((40, 60 + 18 * i), text, fontsize=11)
    page.insert_text((40, 520), "* A hill near the town, with a railway up", fontsize=7)
    page.insert_text((40, 530), "to the top of it.", fontsize=7)
    doc.save(tmp_path / "source.pdf")
    (tmp_path / "book.toml").write_text(
        'title = "T"\nauthor = "A"\nlanguage = "en"\nbody_pages = [1, 1]\n'
    )
    book = Book.load(tmp_path)
    stages = pipeline.run(book)
    text = " ".join(p.text for p in stages.doc.paragraphs)
    assert "railway" not in text
    (note,) = stages.doc.notes
    assert (note.mark, note.paragraph.text, note.linked) == (
        "*",
        "A hill near the town, with a railway up to the top of it.",
        True,
    )
    assert [p.notes for p in stages.doc.paragraphs] == [[0]]
    import zipfile

    with zipfile.ZipFile(book.epub_path) as z:
        html = z.read("OEBPS/text-001.xhtml").decode()
    assert 'href="#note-1"' in html and 'id="note-1"' in html


def test_a_motto_on_a_page_of_its_own_is_set_apart_before_the_text(tmp_path, monkeypatch):
    _everything_is_body(monkeypatch)
    _no_layout(monkeypatch)
    doc = pymupdf.open()
    motto = doc.new_page(width=400, height=600)
    motto.insert_text((160, 120), "'It's closing time'", fontsize=11)
    motto.insert_text((140, 136), "(Leonard Cohen, The Future)", fontsize=11)
    for _ in range(2):
        page = doc.new_page(width=400, height=600)
        for i, text in enumerate(LINES):
            page.insert_text((40, 60 + 18 * i), text, fontsize=11)
    doc.save(tmp_path / "source.pdf")
    (tmp_path / "book.toml").write_text(
        'title = "T"\nauthor = "A"\nlanguage = "en"\nbody_pages = [1, 3]\n'
    )
    book = Book.load(tmp_path)
    stages = pipeline.run(book)
    first, second, third = stages.doc.paragraphs[:3]
    assert (first.text, first.epigraph) == ("‘It’s closing time’", True)
    assert (second.text, second.epigraph) == ("(Leonard Cohen, The Future)", True)
    assert not third.epigraph and third.text.startswith("Line 0")


def test_the_page_readers_reading_reaches_the_ocr_check_as_two_more_readers(tmp_path, monkeypatch):
    monkeypatch.setenv("ROBO_OCR_TRUST", "0")
    monkeypatch.setenv("ROBO_PAGE_READERS", "1")
    book, _ = _checked_book(tmp_path, monkeypatch)
    page = "\n".join(LINES).replace("Line 7 of the story", "Line 7 of the stary")
    monkeypatch.setattr(pipeline.pagereader, "read_page", lambda png, model, url: page)
    stages = pipeline.run(book)
    seven = [s for s in stages.suspects if s.line == 7]
    assert [(s.ours, s.others) for s in seven] == [("story", ("stary",))]
    assert seven[0].support["glm-page"] == seven[0].support["qwen-page"] == (False, True)
    assert seven[0].support["glm"] == (True, False)


def test_a_trust_model_without_the_page_readers_refuses_a_build_with_them(tmp_path, monkeypatch):
    monkeypatch.setenv("ROBO_PAGE_READERS", "1")
    path = tmp_path / "trust.pkl"
    monkeypatch.setenv("ROBO_OCR_TRUST_MODEL", str(path))
    suspects = [ocrcheck_suspect(k) for k in range(40)]
    trust.save(trust.train(suspects, [[k % 2 == 0, k % 2 == 1] for k in range(40)]), path)
    book, _ = _checked_book(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline.pagereader, "read_page", lambda png, model, url: "\n".join(LINES))
    with pytest.raises(trust.Mismatch, match="ROBO_PAGE_READERS"):
        pipeline.run(book)


def ocrcheck_suspect(k: int):
    from roboscriptorium.ocrcheck import Suspect

    return Suspect(
        1, k, "the story", 4, 9, "story", ("stony",), (0, 0, 1, 1), "review",
        votes={"clef:27b": "story"}, confidence={"clef:27b": 0.9},
        support={"glm": (k % 2 == 0, k % 2 == 1)}, known=(True, False),
    )  # fmt: skip


def test_a_printed_blank_takes_the_setting_in_book_toml(tmp_path, monkeypatch):
    _no_layout(monkeypatch)
    lines = ["Ik reed naar het __plein en stak enige brieven in de bus,", "en reed terug."]
    book = _book(tmp_path, lines=lines)
    assert "__plein" in pipeline.run(book, use_models=False).doc.blocks[0].text
    toml = (tmp_path / "book.toml").read_text() + 'blank = "..."\n'
    (tmp_path / "book.toml").write_text(toml)
    text = pipeline.run(Book.load(tmp_path), use_models=False).doc.blocks[0].text
    assert "het ...plein en" in text and "_" not in text


def test_an_erratum_corrects_the_misprint_it_names_and_an_ambiguous_one_stops_the_build(
    tmp_path, monkeypatch
):
    _no_layout(monkeypatch)
    lines = ["'Ach zo,' zeI ik, 'welk soort invalide? Fysiek? Geeste-", "lijk?' ZeI hij niets?"]
    book = _book(tmp_path, lines=lines)
    errata.save(tmp_path, errata.Erratum(1, "zo,’ zeI ik", "zo,’ zei ik"))
    errata.save(tmp_path, errata.Erratum(1, "Geestelijk", "Geestelijk"))
    text = pipeline.run(book, use_models=False).doc.blocks[0].text
    assert "zo,’ zei ik" in text and "ZeI hij" in text
    errata.save(tmp_path, errata.Erratum(1, "ZeI", "Zei"))
    errata.save(tmp_path, errata.Erratum(1, "zeI", "zei"))
    with pytest.raises(errata.Unmatched, match="page 1: 'zeI' occurs 0 times"):
        pipeline.run(book, use_models=False)


def test_a_quote_question_an_answer_elsewhere_in_its_paragraph_settled_is_not_asked(
    tmp_path, monkeypatch
):
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
    stages = pipeline.run(book)
    assert SourceRef(1, 11) in stages.quote_lines
    # The opening mark was lost on line 9, a line of its own question (an OCR doubt, say).
    line = stages.pages[0].lines[9].text
    other = flags.Flag("other", 1, 9, 9, line, "text", ["ocr-doubt"])
    Corrections(book.corrections_path).record(other, "text", "‘" + line)
    again = pipeline.run(book)
    assert SourceRef(1, 11) not in again.quote_lines


def test_a_line_answered_about_its_readings_stays_asked_when_the_arbiter_is_sure_of_it(
    tmp_path, monkeypatch
):
    import numpy as np

    class Sure:
        """Sure the text layer's version is the print."""

        def predict_proba(self, X):
            p = np.where(X[:, 0] == 1, 0.97, 0.03)
            return np.column_stack([1 - p, p])

    book, _ = _checked_book(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline.trust, "load", lambda path: trust.Trust(Sure(), {}))
    monkeypatch.setattr(pipeline.trust, "fingerprint", lambda path: "sure")
    stages = pipeline.run(book)
    (suspect,) = stages.suspects
    assert suspect.choice == "ours"  # nothing to ask
    line = stages.pages[0].lines[3].text
    question = flags.Flag("q", 1, 3, 3, line, "text", ["ocr-doubt"])
    Corrections(book.corrections_path).record(question, "text", line.replace("story", "stony"))
    again = pipeline.run(book)
    (suspect,) = again.suspects
    assert suspect.choice == "review"  # answered, so its question stays
    assert "stony" in again.doc.blocks[0].text  # and the answer sets the line


def test_a_paragraph_starts_where_the_judge_is_sure_one_does(tmp_path, monkeypatch):
    _no_layout(monkeypatch)
    lines = list(LINES)
    lines[5] = "Line 5 of the story goes on and on across the page."
    lines[6] = "Then line 6 of the story goes on and on across the page"
    book = _book(tmp_path, lines=lines)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "start" in body["questions"]:
            line = json.loads(body["state"])["line in question"]
            value = "starts" if line == lines[6] else "continues"
            answer = {"type": "choice", "choice": value, "confidence": 0.9}
            answer["probabilities"] = {value: 0.9}
            return httpx.Response(200, json={"answers": {"start": answer}})
        answer = {"type": "choice", "choice": "body", "confidence": 0.9}
        answer["probabilities"] = {"body": 0.9, "page_number": 0.1}
        return httpx.Response(200, json={"answers": {"role": answer}})

    def client(model, *_):
        http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
        return DecisionClient("http://test", model, client=http)

    monkeypatch.setattr(pipeline.decide, "for_model", client)
    monkeypatch.setattr(pipeline.ocrcheck, "scanned", lambda pdf: True)
    monkeypatch.setenv("ROBO_BREAK_JUDGE", "1")
    paragraphs = pipeline.run(book, check_ocr=False).doc.paragraphs
    assert [p.text.split()[:2] for p in paragraphs] == [["Line", "0"], ["Then", "line"]]
    monkeypatch.setenv("ROBO_BREAK_JUDGE", "0")
    assert len(pipeline.run(book, check_ocr=False).doc.paragraphs) == 1
