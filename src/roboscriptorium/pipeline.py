"""Run the stages for one book, from source PDF to EPUB."""

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pymupdf

from roboscriptorium import (
    corrections,
    epigraphs,
    faint,
    figures,
    footnotes,
    hyphens,
    italics,
    layout,
    missing,
    ocr,
    ocrcheck,
    pagereader,
    quotes,
    sorter,
    trust,
    typestyle,
    typography,
)
from roboscriptorium.book import Book
from roboscriptorium.clients import decide, llama
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections
from roboscriptorium.epub import write_epub
from roboscriptorium.files import check_source, write_atomic
from roboscriptorium.flags import treatment
from roboscriptorium.ir import Document, Paragraph, SourceRef
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import PageText, cached_text_layer, render_jpeg
from roboscriptorium.reflow import reflow
from roboscriptorium.roles import DecisionCache, LineRole, classify, with_role


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
    # Per quote-flagged line, its readings other than the layer's, by kind
    # (`quotes.readings`).
    quote_readings: dict[SourceRef, dict[str, str]] = field(default_factory=dict)
    # What settled the OCR check's suspects: "fixed rule", "trust <model hash>", or ""
    # when there was no check.
    ocr_decider: str = ""
    # Body pages scanned too faint to read (`faint.py`), on scans only.
    faint_pages: set[int] = field(default_factory=set)


def run(
    book: Book,
    pages: tuple[int, int] | None = None,
    use_models: bool = True,
    check_ocr: bool = True,
    settings: Settings | None = None,
) -> Stages:
    """Build the book's EPUB. `pages` narrows the body range for quick experiments;
    `settings` default to the environment's."""
    check_source(book.source, book.stages / "source.json")
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
    answers = Corrections(book.corrections_path)
    style = dash_style(book, whole)
    dots = ellipsis_style(book, whole)
    faint_pages = set()
    # Lines printing footnotes, by position in `body` (`footnotes.lines`).
    note_lines: set[SourceRef] = set()
    # Lines of a motto set on a page of its own (`epigraphs.lines`), likewise.
    epigraph_lines: set[SourceRef] = set()
    if ocrcheck.scanned(book.source):
        faint_pages = faint.pages(book.source, body, book.stages / "contrast.json")
    if use_models:
        settings = settings or Settings.from_env()
        if regions is not None and ocrcheck.scanned(book.source):
            found = missing.candidates(body, regions, _answered(answers))
            readings = missing.read(
                book.source,
                found,
                settings.ocr_model,
                settings.ollama_url,
                book.stages / "missing-lines.json",
            )
            body = missing.add(body, found, readings)
        client = decide.for_model(settings.role_model, settings.ollama_url)
        cache = DecisionCache(book.stages / "decisions.jsonl")
        styles = typestyle.measure(book.source, body, book.stages / "type.json")
        model_roles = classify(body, client, cache, styles)
        if settings.sorter:
            trees = sorter.load(Path(settings.sorter_model))
            model_roles = sorter.apply(trees, body, model_roles, styles, regions)
        note_lines = footnotes.lines(body, model_roles, styles, known)
        epigraph_lines = epigraphs.lines(body, model_roles)
        if check_ocr and ocrcheck.scanned(book.source):
            # A washed-out page is one region for the reviewer to type; on its faint crops
            # the readers invent fluent text and the judges pick it.
            kept = {
                SourceRef(p.number, i)
                for p in body
                if p.number not in faint_pages
                for i in range(len(p.lines))
                if treatment(model_roles.get(SourceRef(p.number, i))) != "dropped"
            }
            reader = decide.for_model(settings.check_model, settings.ollama_url)
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
                    read_prompt(book, whole, style, dots),
                    settings.read_via,
                )
            if settings.page_readers:
                for name, model in (
                    ("glm-page", settings.ocr_model),
                    ("qwen-page", settings.read_model),
                ):
                    if model:
                        readings[name] = pagereader.line_readings(
                            book.source, body, kept, model, settings.ollama_url,
                            book.stages / f"page-reading-{name}.json",
                        )  # fmt: skip
            judge = decide.for_model(settings.judge_model, settings.ollama_url, settings.judge_via)
            alarm = None
            if settings.alarm_model:
                alarm = llama.ReadoutClient(settings.alarm_model, settings.llama_url)
            suspects = ocrcheck.check(
                book.source, body, readings, lang, judge, reader, cache, lexicon,
                book_style(book, whole, style, dots), alarm,
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
                paged = {r for r in readings if r in trust.PAGE_READINGS}
                if paged != {r for r in model.readings if r in trust.PAGE_READINGS}:
                    raise trust.Mismatch(
                        f"The trust model {path} weighs {', '.join(model.readings)}; this build "
                        f"reads {', '.join(readings)}. Train one with these readers or set "
                        "ROBO_PAGE_READERS to match it."
                    )
                read = len(body) - len(faint_pages)
                budget = round(settings.ocr_questions_per_page * read)
                suspects = trust.decide(suspects, model, budget, settings.ocr_ask_below)
                decider = f"trust {trust.fingerprint(path)}"
            ocrcheck.save(suspects, book.stages / "ocr-check.json")
        corrected, roles, applied = corrections.apply(body, model_roles, answers, suspects)
    if not suspects:
        # The suspects of an earlier build with the check would be taken for this one's.
        (book.stages / "ocr-check.json").unlink(missing_ok=True)

    compound = None
    if use_models and hyphens.asked(book.language):
        client = decide.for_model(settings.judge_model, settings.ollama_url, settings.judge_via)
        compound = hyphens.Compounds(
            client, settings.judge_model, book.language, book.stages / "compounds.json"
        )
    checked = ocrcheck.apply(body, suspects)
    unanswered = reflow(
        checked, _apart(checked, model_roles, note_lines, epigraph_lines), known, compound
    )
    quote_lines = {
        ref
        for place in quotes.unbalanced([b for b in unanswered if isinstance(b, Paragraph)])
        for ref in place.sources
        if ref.page not in faint_pages
    }
    quote_readings = {}
    if use_models and quote_lines and ocrcheck.scanned(book.source) and settings.read_model:
        quote_readings = proposals(book, body, whole, suspects, quote_lines, style, dots, settings)
    blocks = italics.mark(
        reflow(corrected, _apart(corrected, roles, note_lines, epigraph_lines), known, compound),
        body,
        italics.detect(book.source, body, book.stages / "italics.json"),
    )
    if compound is not None:
        compound.save()
    blocks = typography.apply(quotes.curl(blocks), style, dots, book.blank)
    notes = footnotes.collect(corrected, note_lines)
    for note, typeset in zip(
        notes,
        typography.apply(quotes.curl([n.paragraph for n in notes]), style, dots, book.blank),
        strict=True,
    ):
        note.paragraph = typeset
    doc = Document(book.title, book.author, book.language, blocks, notes, book.translator)
    images = {}
    if regions is not None:
        with pymupdf.open(book.source) as pdf:
            pictures = figures.select(pdf, body, regions, answers, lang)
            images = {p.name: figures.render(pdf, p) for p in pictures}
        doc.blocks = figures.place(doc.blocks, pictures, body)
    doc.blocks = footnotes.link(doc.blocks, doc.notes)
    write_atomic(
        book.stages / "document.json", json.dumps(asdict(doc), ensure_ascii=False, indent=1)
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
        faint_pages,
    )


def _apart(
    pages: list[PageText],
    roles: dict[SourceRef, LineRole] | None,
    note_lines: set[SourceRef],
    epigraph_lines: set[SourceRef],
) -> dict[SourceRef, LineRole] | None:
    """`roles` for reflow, keyed on positions in `pages`: footnotes and epigraphs set
    apart from the running text."""
    roles = with_role(pages, roles, note_lines, footnotes.ROLE)
    return with_role(pages, roles, epigraph_lines, epigraphs.ROLE)


def proposals(
    book: Book,
    body: list[PageText],
    whole: list[PageText],
    suspects: list[ocrcheck.Suspect],
    lines: set[SourceRef],
    style: typography.DashStyle | None,
    dots: typography.EllipsisStyle | None,
    settings: Settings,
) -> dict[SourceRef, dict[str, str]]:
    """Each quote-flagged line's other readings, by kind (`quotes.readings`): as the OCR
    check left it, with the marks the read model sees on the scan, and those combined.
    Short lines are read too: "‘Nee." is where a closing quote is most often lost."""
    read = ocrcheck.line_readings(
        book.source,
        body,
        lines,
        settings.read_model,
        settings.ollama_url,
        book.stages / "third-reading.json",
        read_prompt(book, whole, style, dots),
        settings.read_via,
    )
    texts = [ln.text for p in whole for ln in p.lines]
    ellipsis = quotes.ellipsis(" ".join(texts), dots)
    single = quotes.single_quoted_lines(texts)
    layer = {p.number: p for p in body}
    checked = {p.number: p for p in ocrcheck.apply(body, suspects)}
    out = {}
    for ref, reading in read.items():
        line = checked[ref.page].lines[ref.line].text
        found = quotes.readings(
            layer[ref.page].lines[ref.line].text, line, reading, ellipsis, single
        )
        if found:
            out[ref] = found
    return out


def _style(
    book: Book,
    body: list[PageText],
    dash: typography.DashStyle | None,
    dots: typography.EllipsisStyle | None,
) -> tuple:
    lines = [ln.text for p in body for ln in p.lines]
    return (
        book.language,
        quotes.single_quoted_lines(lines),
        quotes.ellipsis(" ".join(lines), dots),
        dash.dash if dash else None,
    )


def read_prompt(
    book: Book,
    body: list[PageText],
    dash: typography.DashStyle | None,
    dots: typography.EllipsisStyle | None = None,
) -> str:
    """The read model's prompt for a line of this book, telling it how the book is set."""
    return quotes.style_prompt(*_style(book, body, dash, dots))


def book_style(
    book: Book,
    body: list[PageText],
    dash: typography.DashStyle | None,
    dots: typography.EllipsisStyle | None = None,
) -> str:
    """How the book is set, as the OCR layer's lines show it, for a model to be told."""
    return quotes.style_note(*_style(book, body, dash, dots))


def ellipsis_style(book: Book, body: list[PageText]) -> typography.EllipsisStyle | None:
    """The book's ellipsis style: as book.toml sets it, else its gaps as measured on a scan
    and the glyph or dots as its layer reads them (said aloud). A born-digital PDF's
    ellipses are exact, so they are left as they are.
    """
    if book.ellipsis and book.ellipsis_space is not None:
        return typography.EllipsisStyle(book.ellipsis, book.ellipsis_space)
    if not ocrcheck.scanned(book.source):
        return None
    lines = [ln.text for p in body for ln in p.lines]
    layer = typography.guess_ellipsis(lines)
    scan = typography.measure_ellipses(
        book.source, [p.number for p in body], book.stages / "ellipsis.json"
    )
    guess = typography.scanned_style(layer, scan)
    if guess is None:
        return None
    space = "true" if guess.space_before else "false"
    found = f"measured on the scan: {scan.describe()}" if scan else "read in the text layer"
    print(
        f"Ellipsis style {found}: {guess.dots!r}, "
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


def _answered(answers: Corrections) -> dict[int, list[tuple[float, float, float, float]]]:
    """Per page, the boxes of regions the text layer lacked that a human typed text for."""
    out: dict[int, list[tuple[float, float, float, float]]] = {}
    for c in answers.by_key.values():
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
