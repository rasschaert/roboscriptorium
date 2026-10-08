"""Run the stages for one book, from source PDF to EPUB."""

import json
import sys
from dataclasses import asdict, dataclass, field
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
    typography,
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
    # Per quote-flagged line: the line as the OCR check left it, with the marks a vision
    # model reads (`quotes.proposed`), where they differ.
    quote_readings: dict[SourceRef, str] = field(default_factory=dict)
    # What settled the OCR check's suspects: "fixed rule", "trust <model hash>", or ""
    # when there was no check.
    ocr_decider: str = ""


def run(
    book: Book,
    pages: tuple[int, int] | None = None,
    use_models: bool = True,
    check_ocr: bool = True,
    settings: Settings | None = None,
) -> Stages:
    """Build the book's EPUB. `pages` narrows the body range for quick experiments;
    `settings` default to the environment's."""
    first, last = pages or book.body_pages
    lang = ocr.language(book.language)
    lexicon = Lexicon.load(lang)
    known = lexicon.knows if lexicon is not None else None
    layer = cached_text_layer(book.source, book.stages / "textlayer.json", lang)
    # How the book is set is read on its whole body, so a slice is read and set as the
    # book is, and shares its readings.
    whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
    body = [p for p in layer if first <= p.number <= last]

    roles = model_roles = None
    applied = 0
    suspects: list[ocrcheck.Suspect] = []
    decider = ""
    regions = None
    if layout.available():
        regions = layout.detect(book.source, [p.number for p in body], book.stages / "layout.json")
    corrected = body
    style = dash_style(book, whole)
    if use_models:
        settings = settings or Settings.from_env()
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
            if settings.read_model:
                readings["qwen"] = ocrcheck.line_readings(
                    book.source,
                    body,
                    kept,
                    settings.read_model,
                    settings.ollama_url,
                    book.stages / "third-reading.json",
                    read_prompt(book, whole, style),
                    settings.read_via,
                )
            judge = ollaya.for_model(
                settings.judge_model, settings.ollaya_url, settings.ollama_url, settings.judge_via
            )
            suspects = ocrcheck.check(
                book.source, body, readings, lang, judge, reader, cache, lexicon,
                book_style(book, whole, style),
            )  # fmt: skip
            decider = "fixed rule"
            if settings.ocr_trust:
                path = Path(settings.ocr_trust_model)
                model = trust.load(path)
                if model is None:
                    raise trust.Mismatch(
                        f"No trust model at {path}: train one (experiments/train_ocr_trust.py "
                        "--save) or set ROBO_OCR_TRUST=0 for the fixed rule."
                    )
                budget = round(settings.ocr_questions_per_page * len(body))
                suspects = trust.decide(suspects, model, budget)
                decider = f"trust {trust.fingerprint(path)}"
            ocrcheck.save(suspects, book.stages / "ocr-check.json")
        corrected, roles, applied = corrections.apply(
            body, model_roles, Corrections(book.corrections_path), suspects
        )

    unanswered = reflow(ocrcheck.apply(body, suspects), model_roles, known)
    quote_lines = {
        ref
        for place in quotes.unbalanced([b for b in unanswered if isinstance(b, Paragraph)])
        for ref in place.sources
    }
    quote_readings = {}
    if use_models and quote_lines and ocrcheck.scanned(book.source) and settings.read_model:
        quote_readings = proposals(book, body, whole, suspects, quote_lines, style, settings)
    blocks = italics.mark(
        reflow(corrected, roles, known),
        body,
        italics.detect(book.source, body, book.stages / "italics.json"),
    )
    blocks = typography.apply(blocks, style, ellipsis_style(book, whole))
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
    return Stages(
        body,
        model_roles,
        corrected,
        roles,
        doc,
        applied,
        suspects,
        quote_lines,
        quote_readings,
        decider,
    )


def proposals(
    book: Book,
    body: list[PageText],
    whole: list[PageText],
    suspects: list[ocrcheck.Suspect],
    lines: set[SourceRef],
    style: typography.DashStyle | None,
    settings: Settings,
) -> dict[SourceRef, str]:
    """Each quote-flagged line as the OCR check left it, with the quote marks and
    punctuation the read model sees on the scan, where they differ. Short lines are read
    too: "‘Nee." is where a closing quote is most often lost."""
    read = ocrcheck.line_readings(
        book.source,
        body,
        lines,
        settings.read_model,
        settings.ollama_url,
        book.stages / "third-reading.json",
        read_prompt(book, whole, style),
        settings.read_via,
    )
    dots = quotes.ellipsis(" ".join(ln.text for p in whole for ln in p.lines))
    checked = {p.number: p for p in ocrcheck.apply(body, suspects)}
    out = {}
    for ref, reading in read.items():
        line = checked[ref.page].lines[ref.line].text
        if (merged := quotes.proposed(line, reading, dots)) != line:
            out[ref] = merged
    return out


def read_prompt(book: Book, body: list[PageText], dash: typography.DashStyle | None) -> str:
    """The read model's prompt for a line of this book, telling it how the book is set."""
    lines = [ln.text for p in body for ln in p.lines]
    return quotes.style_prompt(
        book.language,
        quotes.single_quoted_lines(lines),
        quotes.ellipsis(" ".join(lines)),
        dash.dash if dash else None,
    )


def book_style(book: Book, body: list[PageText], dash: typography.DashStyle | None) -> str:
    """How the book is set, as the OCR layer's lines show it, for a model to be told."""
    lines = [ln.text for p in body for ln in p.lines]
    return quotes.style_note(
        book.language,
        quotes.single_quoted_lines(lines),
        quotes.ellipsis(" ".join(lines)),
        dash.dash if dash else None,
    )


def ellipsis_style(book: Book, body: list[PageText]) -> typography.EllipsisStyle | None:
    """The book's ellipsis style: as book.toml sets it, else as a scan's layer reads it
    (said aloud). A born-digital PDF's ellipses are exact, so they are left as they are.
    """
    if book.ellipsis and book.ellipsis_space is not None:
        return typography.EllipsisStyle(book.ellipsis, book.ellipsis_space)
    if not ocrcheck.scanned(book.source):
        return None
    lines = [ln.text for p in body for ln in p.lines]
    guess = typography.guess_ellipsis(lines)
    if guess is None:
        return None
    space = "true" if guess.space_before else "false"
    print(
        f"Ellipsis style read in the text layer: {guess.dots!r}, "
        f"{'a' if guess.space_before else 'no'} space before. To settle it, put "
        f'ellipsis = "{guess.dots}" and ellipsis_space = {space} in book.toml.',
        file=sys.stderr,
    )
    return guess


def dash_style(book: Book, body: list[PageText]) -> typography.DashStyle | None:
    """The book's dash style: as book.toml sets it, else as measured on a scan (said aloud).

    A born-digital PDF's dashes are exact, so they are left as they are.
    """
    if book.dash and book.dash_spacing:
        return typography.DashStyle(book.dash, book.dash_spacing)
    if not ocrcheck.scanned(book.source):
        return None
    guess = typography.guess(book.source, [p.number for p in body], book.stages / "typography.json")
    if guess is None:
        return None
    name = {"–": "en", "—": "em"}[guess.style.dash]
    print(
        f"Dash style measured on the scan: {guess.describe()}. To settle it, put "
        f'dash = "{guess.style.dash}" ({name}) and dash_spacing = "{guess.style.spacing}" '
        "in book.toml.",
        file=sys.stderr,
    )
    return guess.style


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
