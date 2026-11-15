"""Labelled quote marks for a learned measure of them on the scan: for each word of a
golden slice's body lines that the aligner pairs with a reference word, the raised ink at
its two edges as a small picture and a few measures, labelled with the marks the
reference sets there ("" none, "s" a single mark, "d" a double one, "sd" a single then a
double as ‘“ opens a nested quotation, and so on). Every word with a mark in the layer
or the reference, and one in twenty of the others. Kept per book in
work/probes/quote-marks/. No models.

    PYTHONPATH=experiments uv run python experiments/quote_marks_data.py <tuning spec or book> …
"""

import json
import random
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from probe_nested_quotes import strip
from tryout import _beside_break, _shifted, slice_of

from roboscriptorium import bench, disagreements, rendercheck
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.pdf import cached_text_layer, line_words, page_words

OUT = Path("work/probes/quote-marks")
SINGLE, DOUBLE = "‘’'‚", "“”\"„"
STOPS = ".,;:!?…"
ROWS, COLS = 12, 30
# The picture's width, in heights of the line's letters, from the strip's edge inward.
REACH = 1.8


def marks(word: str, opening: bool) -> str:
    """The quote marks at a word's edge, outside in for the opening edge and inside out
    for the closing one, stops between them left out."""
    out = ""
    for c in word if opening else reversed(word):
        if c in SINGLE:
            out += "s"
        elif c in DOUBLE:
            out += "d"
        elif opening or c not in STOPS:
            break
    return out if opening else out[::-1]


def letters(word: str) -> str:
    return "".join(c for c in word if c.isalnum()).lower()


def edge(page: pymupdf.Page, word: tuple, opening: bool) -> dict | None:
    """The upper half of the line at a word's edge, as a picture of fixed size (the edge
    at its left), with the count and widths of its ink runs."""
    ink = strip(page, word)
    if ink is None:
        return None
    mask = ink > 0.5
    cols = np.where(mask.any(0))[0]
    if len(cols) < 4:
        return None
    lows = np.array([np.where(mask[:, c])[0][-1] for c in cols])
    tops = np.array([np.where(mask[:, c])[0][0] for c in cols])
    base, top = float(np.median(lows)), float(np.quantile(tops, 0.1))
    high = base - top
    if high < 8:
        return None
    r0, r1 = max(0, round(top - 0.15 * high)), round(top + 0.5 * high)
    wide = round(REACH * high)
    band = ink[r0:r1] if opening else ink[r0:r1, ::-1]
    band = band[:, cols[0] : cols[0] + wide] if opening else band[:, ink.shape[1] - 1 - cols[-1] :][:, :wide]
    if band.shape[1] < wide:
        band = np.pad(band, ((0, 0), (0, wide - band.shape[1])))
    low = (ink[r1:] if opening else ink[r1:, ::-1])
    low = low[:, cols[0] : cols[0] + wide] if opening else low[:, ink.shape[1] - 1 - cols[-1] :][:, :wide]
    inked = (band > 0.5).any(0)
    # Runs of raised ink from the edge, until a column with ink below the middle too.
    below = np.zeros(wide, bool)
    below[: low.shape[1]] = (low > 0.5).any(0)[:wide]
    runs, at = [], 0
    while at < wide and len(runs) < 4:
        if not inked[at]:
            at += 1
            continue
        end = at
        while end < wide and inked[end]:
            end += 1
        if below[at:end].any():
            break
        runs.append((at, end))
        at = end
    widths = [(b - a) / high for a, b in runs] + [0.0] * (4 - len(runs))
    gaps = [(runs[i + 1][0] - runs[i][1]) / high for i in range(len(runs) - 1)] + [0.0] * (4 - max(1, len(runs)))
    picture = np.asarray(Image.fromarray((band * 255).astype(np.uint8)).resize((COLS, ROWS), Image.BILINEAR), np.float32) / 255
    return {
        "runs": len(runs),
        "widths": [round(v, 3) for v in widths],
        "gaps": [round(v, 3) for v in gaps[:3]],
        "span": round((runs[-1][1] - runs[0][0]) / high, 3) if runs else 0.0,
        "ink": round(float(sum(band[:, a:b].sum() for a, b in runs)) / high**2, 4),
        "high": round(high / (rendercheck.DPI / 72), 2),
        "picture": [round(float(v), 2) for v in picture.ravel()],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[1:]:
        spec = next((s for s in bench.SETS["tuning"] + bench.SETS["validation"] if s.split(":")[0] == arg.split(":")[0]), arg)
        book, (first, last), chapters = slice_of(spec)
        name = book.root.name
        pages = [p for p in cached_text_layer(book.source, book.stages / "textlayer.json") if first <= p.number <= last]
        reference = load_chapters(Golden.load(book.golden).text_dir)
        if chapters:
            reference = reference[chapters[0] - 1 : chapters[1]]
        reference, _ = disagreements.patch(reference, scoring.verdicts(book))
        labels = align(pages, reference)
        by = {p.number: p for p in pages}
        rng = random.Random(0)
        rows = []
        with pymupdf.open(book.source) as doc:
            held = None
            for ref, lab in labels.items():
                page = by[ref.page]
                text = page.lines[ref.line].text
                if lab.role != "body" or not lab.truth or _beside_break(page.lines, ref.line) or _shifted(text, lab.truth):
                    continue
                ours, theirs = text.split(), lab.truth.split()
                if len(ours) != len(theirs) or [letters(w) for w in ours] != [letters(w) for w in theirs]:
                    continue
                if held is None or held[0] != ref.page:
                    pdf_page = doc[ref.page - 1]
                    held = (ref.page, pdf_page, line_words(page_words(pdf_page, page), page))
                words = held[2][ref.line]
                if [w[4] for w in words] != ours:
                    continue
                for i, (w, mine, want) in enumerate(zip(words, ours, theirs, strict=True)):
                    if not letters(mine):
                        continue
                    for opening in (True, False):
                        layer, truth = marks(mine, opening), marks(want, opening)
                        if not layer and not truth and rng.random() > 0.05:
                            continue
                        found = edge(held[1], w, opening)
                        if found:
                            rows.append({"page": ref.page, "line": ref.line, "word": i, "text": mine, "want": want, "opening": opening, "layer": layer, "truth": truth, **found})
        (OUT / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False))
        from collections import Counter

        print(name, len(rows), Counter((r["layer"], r["truth"]) for r in rows).most_common(14), flush=True)


if __name__ == "__main__":
    main()
