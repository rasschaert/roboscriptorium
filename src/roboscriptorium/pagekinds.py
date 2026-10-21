"""What kind of page each page of a scan is, for `init`: where the text proper starts and ends.

Signals first, without a model: a page's words, number-only lines, centred lines and the name
its first lines carry ("Inhoud", "Woord vooraf", ©/ISBN). They call 95% of the labelled pages
right (docs/decisions.md, 2026-10-21) but take a long advert or appendix page for text, which
pads an end by a page or two. So the model (a decision model asked `QUESTION` with the page
image) answers every page at either edge of the book (`EDGE`), and the signals the middle.
The text proper's two ends are then the first and last page whose kind goes into the EPUB
(`fate`). A person confirms them: a padded blank is mild, a cut page is not.

A page is always named by both its numbers (`page_label`): the PDF's own page, which
`book.toml` and every `--pages` use, and the number the page prints.
"""

# ruff: noqa: E501 - the names are one regex a line

import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

from roboscriptorium.clients import decide
from roboscriptorium.files import write_atomic
from roboscriptorium.page import folio, page_offset
from roboscriptorium.pdf import PageText, render_png

# The pages at each edge of the book the model answers for.
EDGE = 8

# Words that name a page's kind in its first lines, Dutch and English.
NAMES = {
    "contents": r"^(inhoud|inhoudsopgave|contents|table of contents)$",
    "foreword": r"^(woord vooraf|voorwoord|ten geleide|inleiding|preface|foreword|introduction|vooraf)$",
    "afterword": r"^(nawoord|naschrift|verantwoording|afterword|author'?s note|noot van de (auteur|schrijver|vertaler))$",
    "acknowledgements": r"^(dankwoord|dankbetuiging|woord van dank|acknowledge?ments?)$",
    "about-author": r"^(over de (auteur|schrijver|schrijfster)|about the author)$",
    "also-by": r"^(van dezelfde (auteur|schrijver|schrijfster)|ook (van|verschenen)|eerder verschenen|(also|other books) by)\b",
    "notes": r"^(noten|aantekeningen|notes)$",
    "appendix": r"^(bijlage|appendix|bibliografie|bibliography|bronnen|literatuur)\b",
    "index": r"^(register|index|personenregister)$",
    "dramatis-personae": r"^(personages|personen|dramatis personae|cast of characters|de personages)$",
    "part-title": r"^(deel|part|boek|book)\s+([ivxlc]+|\d+|een|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|one|two|three|four|five|six|seven|eight|nine|ten|first|second|third)\b",
    "text": r"^(proloog|prologue|epiloog|epilogue|hoofdstuk|chapter)\b",
}
COLOPHON = re.compile(
    r"©|\bisbn\b|\bnur\b|copyright|oorspronkelijke titel|original title|omslagontwerp|typografie|\bdruk\b|all rights reserved|alle rechten voorbehouden",
    re.I,
)


# What becomes of each kind of page (docs/decisions.md, 2026-10-11, What goes into the EPUB).
IN = {
    "dedication",
    "motto",
    "dramatis-personae",
    "foreword",
    "part-title",
    "text",
    "afterword",
    "notes",
    "appendix",
    "acknowledgements",
    "about-author",
    "index",
    "plate",
}
DETAILS = {"cover", "half-title", "title", "colophon", "contents", "back-cover"}


def fate(kind: str) -> str:
    return "in" if kind in IN else "details" if kind in DETAILS else "out"


@dataclass
class Clues:
    page: int
    words: int
    lines: int
    size: float  # median line height against the book's body median
    centred: float  # share of lines set centred and short
    numbered: bool  # a line holding only a number, at the top or foot
    named: str  # the kind the first lines name, or ""
    colophon: int  # colophon words on the page


def clues(pages: list[PageText]) -> list[Clues]:
    heights = [ln.y1 - ln.y0 for p in pages for ln in p.lines if len(p.lines) > 20]
    body = statistics.median(heights) if heights else 1.0
    out = []
    for p in pages:
        lines = [ln for ln in p.lines if ln.text.strip()]
        words = sum(len(ln.text.split()) for ln in lines)
        if lines:
            left, right = min(ln.x0 for ln in lines), max(ln.x1 for ln in lines)
            mid, width = (left + right) / 2, max(1.0, right - left)
            centred = sum(
                abs((ln.x0 + ln.x1) / 2 - mid) < 0.04 * width and ln.x1 - ln.x0 < 0.8 * width
                for ln in lines
            ) / len(lines)
            size = statistics.median(ln.y1 - ln.y0 for ln in lines) / body
        else:
            centred, size = 0.0, 0.0
        edge = lines[:2] + lines[-2:]
        numbered = any(re.fullmatch(r"\d{1,3}", ln.text.strip()) for ln in edge)
        named = ""
        for ln in lines[:4]:
            t = re.sub(r"[^\w' ]", "", ln.text.strip().lower()).strip()
            hit = next((k for k, rx in NAMES.items() if re.search(rx, t)), "")
            if hit:
                named = hit
                break
        colophon = sum(len(COLOPHON.findall(ln.text)) for ln in lines)
        out.append(
            Clues(
                p.number,
                words,
                len(lines),
                round(size, 2),
                round(centred, 2),
                numbered,
                named,
                colophon,
            )
        )
    return out


KINDS = {
    "cover": "the front cover",
    "back-cover": "the back cover, with or without a blurb",
    "blank": "an empty page, maybe with show-through or a lone page number",
    "scan-noise": "a digitisation notice (Internet Archive's stamp page) or a colour card",
    "library": "library stamps, barcode, due-date slip, card pocket, handwriting only",
    "endpaper": "an endpaper, the inside of a cover or a jacket flap",
    "half-title": "the book's title alone, before the title page",
    "title": "the title page: title, author, publisher",
    "colophon": "the copyright page: ©, ISBN, printer, original title, translator credit",
    "contents": "a table of contents",
    "also-by": "a list of the author's other books",
    "ads": "advertisements for other books or products, praise for other books",
    "praise": "praise for this book: quotes from reviews",
    "dedication": "a dedication ('Voor ...', 'For ...')",
    "motto": "a motto or epigraph: a short quotation set apart, with its source",
    "dramatis-personae": "a list of characters, a map, a family tree",
    "foreword": "a foreword, preface or introduction before the text",
    "part-title": "a page with only a part heading ('Deel een', 'Part II', a lone numeral)",
    "text": "running text: a chapter, prologue or epilogue, its opening or its last lines",
    "plate": "a full-page picture, a frontispiece or plate",
    "afterword": "an afterword or author's note after the text",
    "notes": "endnotes",
    "appendix": "an appendix, bibliography or list of sources",
    "acknowledgements": "acknowledgements, thanks",
    "about-author": "about the author: a short biography, an author photo",
    "index": "a back-of-book index",
}
QUESTION = {
    "kind": decide.choice(
        "This is a scanned page of a printed book. What kind of page is it? Use the page "
        "image first; the text layer may be missing or garbled.",
        KINDS,
    )
}


def state(book: str, n: int, total: int, page) -> dict:
    lines = [ln.text for ln in page.lines if ln.text.strip()]
    return {
        "book": book,
        "page": f"{n} of {total}",
        "words_on_page": sum(len(t.split()) for t in lines),
        "first_lines": lines[:6],
        "last_lines": lines[-2:] if len(lines) > 6 else [],
    }


def guess(c: Clues, at: float) -> str:
    """A page's kind from its clues alone; `at` is its place in the book, 0 to 1."""
    if at == 0:
        return "cover"
    if at == 1:
        return "back-cover"
    if c.named:
        return c.named
    if c.colophon >= 2:
        return "colophon"
    if c.words == 0:
        return "blank"
    if c.words >= 120:
        return "text"
    if c.numbered and c.words >= 40:
        return "text"
    return "?"


def ends(kinds: dict[int, str]) -> tuple[int, int]:
    """The first and last page whose kind goes into the EPUB."""
    inside = [p for p, k in sorted(kinds.items()) if fate(k) == "in"]
    return inside[0], inside[-1]


def edge_pages(total: int) -> set[int]:
    """The pages at either edge of a book of `total` pages, which the model answers for."""
    return set(range(1, min(EDGE, total) + 1)) | set(range(max(1, total - EDGE + 1), total + 1))


def kinds(pdf: Path, pages: list[PageText], client, cache: Path) -> dict[int, str]:
    """Each page's kind: the model's for the pages at either edge (`edge_pages`), the signals'
    for the rest, a page they can't tell counting as text. The model's answers are kept in
    `cache` by page, so a rerun asks only what is new."""
    total = len(pages)
    answers = json.loads(cache.read_text()) if cache.exists() else {}
    edge = edge_pages(total)
    by = {c.page: c for c in clues(pages)}
    out = {}
    for page in pages:
        n = page.number
        if n in edge:
            if str(n) not in answers:
                answer = client.decide(
                    state(pdf.parent.name, n, total, page), QUESTION, image_png=render_png(pdf, n)
                )["kind"]
                answers[str(n)] = [answer.value, round(answer.confidence, 3)]
                write_atomic(cache, json.dumps(answers))
            out[n] = answers[str(n)][0]
        else:
            g = guess(by[n], (n - 1) / max(1, total - 1))
            out[n] = "text" if g == "?" else g
    return out


def page_label(number: int, offset: int | None) -> str:
    """A page named by both its numbers, never one alone: "PDF page 9 (the page prints 7)",
    or "(the page prints no number)" where the book's offset gives none above zero. The PDF's
    page is the one `book.toml` and `--pages` take."""
    printed = folio(number, offset)
    if printed is None or printed < 1:
        return f"PDF page {number} (the page prints no number)"
    return f"PDF page {number} (the page prints {printed})"


def printed_offset(pages: list[PageText]) -> int | None:
    """How far the printed numbers lag the PDF's pages (`page.page_offset`), None where the
    book prints too few numbers to say."""
    return page_offset(pages)
