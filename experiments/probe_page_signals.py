"""Probe: what each page's text layer says about its kind, without a model.

For `roboscriptorium init`: the clues a page gives before any model looks at it, and
how far rules on them get against the hand labels in
work/probes/page-kinds/<book>/labels.json (`experiments/page_sheets.py`).

    uv run python experiments/probe_page_signals.py <book dir> [...]     # one table each
    uv run python experiments/probe_page_signals.py --score              # every labelled book

Clues per page: its words and lines, its type size against the book's body type, the
share of its lines set centred, whether a line holds only a number (a page number),
and the kind its first lines name ("Inhoud", "Woord vooraf", "©", "ISBN", ...).
"""

import json
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from roboscriptorium.pdf import PageText, cached_text_layer

LABELS = Path("work/probes/page-kinds")

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
COLOPHON = re.compile(r"©|\bisbn\b|\bnur\b|copyright|oorspronkelijke titel|original title|omslagontwerp|typografie|\bdruk\b|all rights reserved|alle rechten voorbehouden", re.I)


# What becomes of each kind of page (docs/decisions.md, 2026-10-11, What goes into the EPUB).
IN = {"dedication", "motto", "dramatis-personae", "foreword", "part-title", "text",
      "afterword", "notes", "appendix", "acknowledgements", "about-author", "index", "plate"}
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
        out.append(Clues(p.number, words, len(lines), round(size, 2), round(centred, 2), numbered, named, colophon))
    return out


def layer(book: Path) -> list[PageText]:
    return cached_text_layer(book / "source.pdf", book / "stages" / "text-layer.json")


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


def score() -> None:
    tally: Counter = Counter()
    fates: Counter = Counter()
    confusions: Counter = Counter()
    ends_right = Counter()
    for f in sorted(LABELS.glob("*/labels.json")):
        book = Path("work") / f.parent.name
        labels = {int(k): v for k, v in json.loads(f.read_text()).items() if k.isdigit()}
        pages = layer(book)
        # Pages the sheets left out are long pages inside the book: running text.
        labels = {p.number: labels.get(p.number, "text") for p in pages}
        by = {c.page: c for c in clues(pages)}
        guesses = {}
        for p, kind in labels.items():
            g = guess(by[p], (p - 1) / (len(pages) - 1))
            guesses[p] = g
            fates[(fate(kind), fate(g) if g != "?" else "?")] += 1
            tally["right" if g == kind else "unsure" if g == "?" else "wrong"] += 1
            if g not in (kind, "?"):
                confusions[(kind, g)] += 1
        # The ends as guessed: an unsure page counts as in, which pads rather than cuts.
        sure = {p: (g if g != "?" else "text") for p, g in guesses.items()}
        want, got = ends(labels), ends(sure)
        ends_right["first"] += want[0] == got[0]
        ends_right["last"] += want[1] == got[1]
        ends_right["books"] += 1
        if want != got:
            print(f"  {book.name}: text proper {want[0]}–{want[1]}, guessed {got[0]}–{got[1]}")
    print(dict(tally))
    print("fate (labelled, guessed):", dict(fates))
    print("ends right:", dict(ends_right))
    for (kind, g), n in confusions.most_common(25):
        print(f"  {n:4}  {kind:18} guessed {g}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--score"]:
        score()
    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            continue
        for c in clues(layer(Path(arg)))[:24]:
            print(c)
