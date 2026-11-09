"""Pages a scan repeats, lacks or prints too poorly to read, found without a model.

A library scan can hold a page twice (Goede dochter's PDF 218–219 repeat 216–217) or
skip pages (its printed 286–287). A repeat is left out of the build; a gap can only be
reported, so a reader can look the pages up in another copy. A page the readers disagree
on line after line (De vergelding's blurred PDF 38, 34, 114) is below the quality the
build supports: it is built, named, and left out of the bench's score.
"""

from collections import Counter
from dataclasses import dataclass

from rapidfuzz import fuzz

from roboscriptorium import page as P
from roboscriptorium.pdf import PageText

# A repeat is looked for this many pages back, ...
REPEAT_WINDOW = 12
# ... matches that page's text at least this closely (`fuzz.ratio`, 0–100), ...
REPEAT_SAME = 90
# ... and both pages hold at least this many characters: a part title or a blank page
# repeats by design.
REPEAT_MIN_CHARS = 400
# A jump in the printed page numbers counts once this many numbered pages before it and
# after it agree on the offset, so one misread number is no gap, ...
GAP_HOLD = 3
# ... the old offset doesn't come back in the numbered pages after those (Steve Jobs'
# layer reads 512–514 as "912"–"914"), ...
GAP_RETURN = 12
# ... and at most this many pages are lost: a signature or two.
MAX_GAP = 32
# A page is too poor to read with at least this many OCR-check suspects a line. On all 25
# books' caches (2026-11-08) De vergelding's nine blurred pages hold 1.54–6.0 a line, the
# next page anywhere 1.24 (Verminkt's sharp Polish passages, which the readers disagree on
# for their language, not their print).
POOR_SUSPECTS = 1.5
# ... on a page of at least this many lines: a short page's rate is a handful of suspects.
POOR_MIN_LINES = 10


@dataclass(frozen=True)
class Gap:
    before: int  # the PDF page after the gap
    first: int  # the first printed page number missing
    last: int  # the last


def repeats(pages: list[PageText]) -> dict[int, int]:
    """Each page whose text repeats an earlier page's, with that earlier page."""
    texts = {p.number: " ".join(ln.text for ln in p.lines) for p in pages}
    out: dict[int, int] = {}
    for n, text in texts.items():
        if len(text) < REPEAT_MIN_CHARS:
            continue
        for m in range(n - REPEAT_WINDOW, n):
            earlier = texts.get(m, "")
            if m not in out and len(earlier) >= REPEAT_MIN_CHARS:
                if fuzz.ratio(text, earlier) >= REPEAT_SAME:
                    out[n] = m
                    break
    return out


def _folio(page: PageText) -> int | None:
    """The number printed on the page's edge: a line that is only a number, else one at
    the start or end of an edge line."""
    edges = [page.lines[i].text.strip() for i in P.edge_lines(page)]
    bare = [int(t) for t in edges if P.digits(t)]
    if bare:
        return bare[-1]
    return next((n for t in edges if (n := P.page_number(t)) is not None), None)


def gaps(pages: list[PageText]) -> list[Gap]:
    """Where the printed page numbers run ahead of the PDF's: pages the scan lacks."""
    offsets = [(p.number, p.number - f) for p in pages if (f := _folio(p)) is not None]
    out = []
    for k in range(GAP_HOLD, len(offsets) - GAP_HOLD + 1):
        pdf, now = offsets[k]
        before = offsets[k - 1][1]
        if (
            0 < before - now <= MAX_GAP
            and all(o == before for _, o in offsets[k - GAP_HOLD : k])
            and all(o == now for _, o in offsets[k : k + GAP_HOLD])
            and all(o != before for _, o in offsets[k + GAP_HOLD : k + GAP_HOLD + GAP_RETURN])
        ):
            out.append(Gap(pdf, pdf - before, pdf - now - 1))
    return out


def poor(pages: list[PageText], suspect_pages: list[int]) -> dict[int, float]:
    """Each page printed too poorly to read, with its suspects a line; `suspect_pages`
    holds the page of each of the OCR check's suspects."""
    count = Counter(suspect_pages)
    rates = {
        p.number: count[p.number] / len(p.lines) for p in pages if len(p.lines) >= POOR_MIN_LINES
    }
    return {n: r for n, r in rates.items() if r >= POOR_SUSPECTS}


def summary(
    repeated: dict[int, int], missing: list[Gap], poor: dict[int, float] | None = None
) -> str:
    """One line on what the scan repeats, lacks and prints too poorly, or "" when none."""
    parts = [f"PDF {n} repeats PDF {m}, left out" for n, m in sorted(repeated.items())]
    parts += [
        f"printed {g.first}" + (f"–{g.last}" if g.last > g.first else "")
        + f" not in the scan (before PDF {g.before})"
        for g in missing
    ]  # fmt: skip
    if poor:
        listed = ", ".join(f"{n} ({r:.1f} a line)" for n, r in sorted(poor.items()))
        parts.append(f"PDF {listed} too poor to read, out of the bench's score")
    return "scan: " + "; ".join(parts) if parts else ""
