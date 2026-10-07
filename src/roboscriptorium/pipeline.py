"""Run the stages for one book, from source PDF to EPUB."""

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

from roboscriptorium import (
    corrections,
    figures,
    italics,
    layout,
    missing,
    ocr,
    ocrcheck,
    quotes,
    trust,
    typestyle,
)
from roboscriptorium.book import Book
from roboscriptorium.clients import ollaya
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections
from roboscriptorium.epub import write_epub
from roboscriptorium.flags import treatment
from roboscriptorium.ir import Document, Paragraph, SourceRef
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import PageText, cached_text_layer, render_jpeg
from roboscriptorium.reflow import reflow
from roboscriptorium.roles import DecisionCache, LineRole, classify


@dataclass
class Stages:
    """What a build decided, for review: the body pages, line roles and document.

    `pages` and `model_roles` are the text layer as read, with the printed lines it
    lacks added (`missing.py`), and the model's roles for it; the review and its
    answer keys use those. `corrected` and `roles` have a
    human's answers applied (lines typed in, text replaced) and feed the book.
    """

    pages: list[PageText]
    model_roles: dict[SourceRef, LineRole] | None
    corrected: list[PageText]
    roles: dict[SourceRef, LineRole] | None  # keyed on line positions in `corrected`
    doc: Document
    corrections_applied: int
    suspects: list[ocrcheck.Suspect]  # where a second OCR reading differs
    # Lines of `pages` where a paragraph's quotes don't pair up, found before a
    # human's answers so the review's questions stay put.
    quote_lines: set[SourceRef]


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
    regions = None
    if layout.available():
        regions = layout.detect(book.source, [p.number for p in body], book.stages / "layout.json")
    corrected = body
    if use_models:
        settings = Settings.from_env()
        if regions is not None and ocrcheck.scanned(book.source):
            found = missing.candidates(body, regions, _answered(book))
            readings = missing.read(
                book.source,
                found,
                settings.ocr_model,
                settings.ollama_url,
                book.stages / "missing-lines.json",
            )
            body = missing.add(body, found, readings)
        client = ollaya.for_model(settings.role_model, settings.ollaya_url, settings.ollama_url)
        cache = DecisionCache(book.stages / "decisions.jsonl")
        styles = typestyle.measure(book.source, body, book.stages / "type.json")
        model_roles = classify(body, client, cache, styles)
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
            readings = {
                "glm": ocrcheck.line_readings(
                    book.source,
                    body,
                    kept,
                    settings.ocr_model,
                    settings.ollama_url,
                    book.stages / "second-reading.json",
                ),
                "tess": ocrcheck.tesseract_readings(
                    book.source, body, kept, lang, book.stages / "tesseract.json"
                ),
            }
            judge = ollaya.for_model(settings.judge_model, settings.ollaya_url, settings.ollama_url)
            suspects = ocrcheck.check(
                book.source, body, readings, lang, judge, reader, cache, Lexicon.load(lang)
            )
            model = trust.load(Path(settings.ocr_trust_model)) if settings.ocr_trust else None
            if model is not None:
                budget = round(settings.ocr_questions_per_page * len(body))
                suspects = trust.decide(suspects, model, budget)
            elif settings.ocr_trust:
                print(
                    f"No trust model at {settings.ocr_trust_model}; the OCR check uses its "
                    "fixed rule (train one with experiments/train_ocr_trust.py --save).",
                    file=sys.stderr,
                )
            ocrcheck.save(suspects, book.stages / "ocr-check.json")
        corrected, roles, applied = corrections.apply(
            body, model_roles, Corrections(book.corrections_path)
        )

    unanswered = reflow(ocrcheck.apply(body, suspects), model_roles)
    quote_lines = {
        ref
        for place in quotes.unbalanced([b for b in unanswered if isinstance(b, Paragraph)])
        for ref in place.sources
    }
    text = ocrcheck.apply(corrected, suspects)
    blocks = italics.mark(
        reflow(text, roles), body, italics.detect(book.source, body, book.stages / "italics.json")
    )
    doc = Document(book.title, book.author, book.language, blocks)
    images = {}
    if regions is not None:
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
    return Stages(body, model_roles, corrected, roles, doc, applied, suspects, quote_lines)


def _answered(book: Book) -> dict[int, list[tuple[float, float, float, float]]]:
    """Per page, the boxes of regions the text layer lacked that a human typed text for."""
    out: dict[int, list[tuple[float, float, float, float]]] = {}
    for c in Corrections(book.corrections_path).by_key.values():
        if c.last < c.first and c.box and c.text:
            out.setdefault(c.page, []).append(c.box)
    return out


def build(
    book: Book,
    pages: tuple[int, int] | None = None,
    use_models: bool = True,
    check_ocr: bool = True,
) -> Document:
    return run(book, pages, use_models, check_ocr).doc
