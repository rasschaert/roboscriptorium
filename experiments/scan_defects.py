"""Pages a scan repeats or lacks, from each book's cached text layer, no models.

    uv run python experiments/scan_defects.py [book dir …]   # default: every work/*/

A repeat: a page whose text matches an earlier page's (within `WINDOW` pages) at
`SAME` or more. A gap: the printed number on a page's edge jumps by more than one
from the last page that printed one, the pages between counted.
"""

import json
import sys
from pathlib import Path

from rapidfuzz import fuzz

from roboscriptorium.page import page_number

WINDOW, SAME, MIN_CHARS, HOLD = 12, 90, 400, 3


def check(book: Path) -> None:
    layer = book / "stages" / "text-layer.json"
    if not layer.exists():
        return
    pages = json.loads(layer.read_text())["pages"]
    texts = {p["number"]: " ".join(ln["text"] for ln in p["lines"]) for p in pages}
    out = []
    for n, t in texts.items():
        if len(t) < MIN_CHARS:
            continue
        for m in range(max(1, n - WINDOW), n):
            if len(texts.get(m, "")) >= MIN_CHARS and fuzz.ratio(t, texts[m]) >= SAME:
                out.append(f"PDF {n} repeats PDF {m}")
                break
    # Each page's offset (PDF number less printed number); a gap is where the offset
    # drops and the next `HOLD` pages that print a number keep the new one.
    offsets = []
    for p in pages:
        lines = p["lines"]
        folios = [page_number(ln["text"]) for ln in (lines[:1] + lines[-1:])]
        folio = next((f for f in folios if f is not None and len(str(f)) <= 4), None)
        if folio is not None:
            offsets.append((p["number"], p["number"] - folio))
    for k in range(HOLD, len(offsets) - HOLD):
        before, (pdf, now) = offsets[k - 1][1], offsets[k]
        if now < before and all(o == now for _, o in offsets[k + 1 : k + 1 + HOLD]) and (
            all(o == before for _, o in offsets[k - HOLD : k])
        ):
            lost = before - now
            out.append(f"{lost} printed page(s) missing before PDF {pdf} (printed {pdf - now})")
    if out:
        print(book.name, *out, sep="\n  ")


if __name__ == "__main__":
    for d in [Path(a) for a in sys.argv[1:]] or sorted(Path("work").glob("*/")):
        check(d)
