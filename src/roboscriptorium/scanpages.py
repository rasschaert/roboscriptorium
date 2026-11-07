"""Pages a scan repeats or lacks, found from the text layer without a model.

A library scan can hold a page twice (Goede dochter's PDF 218–219 repeat 216–217) or
skip pages (its printed 286–287). A repeat is left out of the build; a gap can only be
reported, so a reader can look the pages up in another copy.
"""

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


def summary(repeated: dict[int, int], missing: list[Gap]) -> str:
    """One line on what the scan repeats and lacks, or "" when neither."""
    parts = [f"PDF {n} repeats PDF {m}, left out" for n, m in sorted(repeated.items())]
    parts += [
        f"printed {g.first}" + (f"–{g.last}" if g.last > g.first else "")
        + f" not in the scan (before PDF {g.before})"
        for g in missing
    ]  # fmt: skip
    return "scan: " + "; ".join(parts) if parts else ""
