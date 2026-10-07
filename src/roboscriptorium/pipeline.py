"""Run the stages for one book, from source PDF to EPUB."""

import json
from dataclasses import asdict, dataclass

import pymupdf

from roboscriptorium import corrections, figures, italics, layout, ocr, ocrcheck
from roboscriptorium.book import Book
from roboscriptorium.clients import ollaya
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections
from roboscriptorium.epub import write_epub
from roboscriptorium.flags import treatment
from roboscriptorium.ir import Document, SourceRef
from roboscriptorium.pdf import PageText, cached_text_layer, render_jpeg
from roboscriptorium.reflow import reflow
from roboscriptorium.roles import DecisionCache, LineRole, classify


@dataclass
class Stages:
    """What a build decided, for review: the body pages, line roles and document.

    `pages` and `model_roles` are the text layer as read and the model's roles for
    it; the review and its answer keys use those. `corrected` and `roles` have a
    human's answers applied (lines typed in, text replaced) and feed the book.
    """

    pages: list[PageText]
    model_roles: dict[SourceRef, LineRole] | None
    corrected: list[PageText]
    roles: dict[SourceRef, LineRole] | None  # keyed on line positions in `corrected`
    doc: Document
    corrections_applied: int
    suspects: list[ocrcheck.Suspect]  # where a second OCR reading differs


def run(
    book: Book,
    pages: tuple[int, int] | None = None,
    use_models: bool = True,
    check_ocr: bool = True,
) -> Stages:
    """Build the book's EPUB. `pages` narrows the body range for quick experiments."""
    first, last = pages or book.body_pages
    body = [
        p
        for p in cached_text_layer(book.source, book.stages / "textlayer.json")
        if first <= p.number <= last
    ]

    roles = model_roles = None
    corrected = body
    applied = 0
    suspects: list[ocrcheck.Suspect] = []
    if use_models:
        settings = Settings.from_env()
        client = ollaya.for_model(settings.role_model, settings.ollaya_url, settings.ollama_url)
        cache = DecisionCache(book.stages / "decisions.jsonl")
        model_roles = classify(body, client, cache)
        if check_ocr and ocrcheck.scanned(book.source):
            kept = {
                SourceRef(p.number, i)
                for p in body
                for i in range(len(p.lines))
                if treatment(model_roles.get(SourceRef(p.number, i))) != "dropped"
            }
            reader = ollaya.for_model(
                settings.check_model, settings.ollaya_url, settings.ollama_url
            )
            lang = ocr.language(book.language)
            readings = [
                ocrcheck.line_readings(
                    book.source,
                    body,
                    kept,
                    settings.ocr_model,
                    settings.ollama_url,
                    book.stages / "second-reading.json",
                ),
                ocrcheck.tesseract_readings(
                    book.source, body, kept, lang, book.stages / "tesseract.json"
                ),
            ]
            judge = ollaya.for_model(settings.judge_model, settings.ollaya_url, settings.ollama_url)
            suspects = ocrcheck.check(book.source, body, readings, lang, judge, reader, cache)
            ocrcheck.save(suspects, book.stages / "ocr-check.json")
        corrected, roles, applied = corrections.apply(
            body, model_roles, Corrections(book.corrections_path)
        )

    text = ocrcheck.apply(corrected, suspects)
    blocks = italics.mark(
        reflow(text, roles), body, italics.detect(book.source, body, book.stages / "italics.json")
    )
    doc = Document(book.title, book.author, book.language, blocks)
    images = {}
    if layout.available():
        regions = layout.detect(book.source, [p.number for p in body], book.stages / "layout.json")
        with pymupdf.open(book.source) as pdf:
            pictures = figures.select(
                pdf, body, regions, Corrections(book.corrections_path), ocr.language(book.language)
            )
            images = {p.name: figures.render(pdf, p) for p in pictures}
        doc.blocks = figures.place(doc.blocks, pictures, body)
    (book.stages / "document.json").write_text(
        json.dumps(asdict(doc), ensure_ascii=False, indent=1)
    )

    cover = render_jpeg(book.source, book.cover_page) if book.cover_page else None
    write_epub(doc, book.epub_path, cover, images)
    return Stages(body, model_roles, corrected, roles, doc, applied, suspects)


def build(
    book: Book,
    pages: tuple[int, int] | None = None,
    use_models: bool = True,
    check_ocr: bool = True,
) -> Document:
    return run(book, pages, use_models, check_ocr).doc
