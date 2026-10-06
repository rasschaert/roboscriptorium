"""Run the stages for one book, from source PDF to EPUB."""

import json
from dataclasses import asdict, dataclass

from roboscriptorium import corrections, ocr, ocrcheck
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
    """What a build decided, for review: the body pages, line roles and document."""

    pages: list[PageText]
    roles: dict[SourceRef, LineRole] | None
    model_roles: dict[SourceRef, LineRole] | None  # before a human's corrections
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
    applied = 0
    suspects: list[ocrcheck.Suspect] = []
    if use_models:
        settings = Settings.from_env()
        client = ollaya.for_model(settings.role_model, settings.ollaya_url, settings.ollama_url)
        cache = DecisionCache(book.stages / "decisions.jsonl")
        roles = classify(body, client, cache)
        model_roles = dict(roles)
        if check_ocr and ocrcheck.scanned(book.source):
            kept = {
                SourceRef(p.number, i)
                for p in body
                for i in range(len(p.lines))
                if treatment(roles.get(SourceRef(p.number, i))) != "dropped"
            }
            reader = ollaya.for_model(
                settings.check_model, settings.ollaya_url, settings.ollama_url
            )
            suspects = ocrcheck.check(
                book.source,
                body,
                kept,
                ocr.language(book.language),
                client,
                reader,
                cache,
                book.stages / "tesseract.json",
            )
            ocrcheck.save(suspects, book.stages / "ocr-check.json")
        applied = corrections.apply(body, roles, Corrections(book.corrections_path))

    text = ocrcheck.apply(body, suspects)
    doc = Document(book.title, book.author, book.language, reflow(text, roles))
    (book.stages / "document.json").write_text(
        json.dumps(asdict(doc), ensure_ascii=False, indent=1)
    )

    cover = render_jpeg(book.source, book.cover_page) if book.cover_page else None
    write_epub(doc, book.epub_path, cover)
    return Stages(body, roles, model_roles, doc, applied, suspects)


def build(
    book: Book,
    pages: tuple[int, int] | None = None,
    use_models: bool = True,
    check_ocr: bool = True,
) -> Document:
    return run(book, pages, use_models, check_ocr).doc
