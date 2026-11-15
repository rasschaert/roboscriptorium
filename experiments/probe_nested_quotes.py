"""The outer mark of a nested quotation every reader drops (the print's ‘“Lucy … kind,”’
built as “Lucy … kind,”: 21 of tuning's 460 unasked errors, 2026-11-15). Does the render
judge's fit on that one mark (`rendercheck.mark_fit`) find them? Positives: the bench's
unasked quote errors whose reference has one mark more at the word's edge, placed on
their page by the word the build has. Negatives: the same books' other layer words that
open or close on a double mark, where the reference sets that word so and never nested.
Prints the AUC and what a cut finds. No models.

    uv run python experiments/probe_nested_quotes.py <bench errors.jsonl> [book …]
"""

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from sklearn.metrics import roc_auc_score

from roboscriptorium import pdf as pdflayer
from roboscriptorium import pipeline, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/nested-quotes.jsonl")
STRAIGHT = str.maketrans("‘’“”", "''\"\"")
STOPS = ".,;:!?"


def versions(word: str) -> tuple[str, str] | None:
    """A layer word opening or closing on a double mark, and it with the single mark a
    nested quotation sets outside it; None for any other word."""
    if word[:1] == "“" and len(word) > 1:
        return "‘" + word, word
    bare = word.rstrip(STOPS)
    if bare[-1:] == "”" and len(bare) > 1:
        return word + "’", word
    return None


def gapped(marked: str, plain: str, gap: str) -> str:
    """The marked version with the gap a print may set between nested marks."""
    return marked[0] + gap + plain if marked.endswith(plain) else plain + gap + marked[-1]


def strip(page: pymupdf.Page, word: tuple) -> np.ndarray | None:
    """The ink of a layer word out to the blanks around it, and on over raised marks
    beyond them (quote marks set off by a gap, which the layer's box leaves out)."""
    high = word[3] - word[1]
    clip = pymupdf.Rect(word[0] - high * 3, word[1] - high * 0.3, word[2] + high * 3, word[3] + high * 0.3)
    clip &= page.rect
    grey = rendercheck._clip_ink(page, clip)
    if grey is None:
        return None
    scale = rendercheck.DPI / 72
    mask = grey > 0.5
    cols = mask.any(0)
    gap = max(4, round(high * scale * rendercheck.WORD_GAP))
    middle = round((word[1] + high * 0.55 - clip.y0) * scale)
    a, b = round((word[0] - clip.x0) * scale), round((word[2] - clip.x0) * scale)
    a, b = min(a + gap, b), max(b - gap, a)

    def raised(c0: int, c1: int) -> bool:
        rows = np.where(mask[:, c0:c1].any(1))[0]
        return len(rows) > 0 and rows[-1] < middle and c1 - c0 <= high * scale * 0.5

    for _ in range(4):
        while a > 0 and cols[max(0, a - gap) : a].any():
            a -= 1
        c1 = a - gap
        while c1 > 0 and not cols[c1 - 1] and a - c1 < high * scale * 0.6:
            c1 -= 1
        c0 = c1
        while c0 > 0 and cols[c0 - 1]:
            c0 -= 1
        if c1 > c0 and raised(c0, c1):
            a = c0
        else:
            break
    for _ in range(4):
        while b < len(cols) and cols[b : b + gap].any():
            b += 1
        c0 = b + gap
        while c0 < len(cols) and not cols[c0] and c0 - b < high * scale * 0.6:
            c0 += 1
        c1 = c0
        while c1 < len(cols) and cols[c1]:
            c1 += 1
        if c1 > c0 and raised(c0, c1):
            b = c1
        else:
            break
    return grey[:, a:b] if b - a > 8 else None


def main():
    errors = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
    names = sys.argv[2:] or list(dict.fromkeys(e["book"] for e in errors))
    settings = Settings.from_env()
    rows = []
    for name in names:
        book = Book.load(Path("work") / name)
        layer = cached_text_layer(book.source, book.stages / "textlayer.json")
        body = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
        mine = [e for e in errors if e["book"] == name]
        pages = {e["page"] for e in mine}
        if not pages:
            continue
        lost = {}
        for e in mine:
            g, w = e["got"], e["want"]
            if not e["asked"] and e["kind"] == "quotes" and w in ("'" + g, g + "'") and '"' in g:
                lost.setdefault((e["page"], g), []).append(e)
        golden = name.split("--")[0]
        reference = " ".join(Path(f).read_text() for f in glob.glob(f"work/golden/{golden}/text/*.xhtml"))
        judge = pipeline._alarm("render", settings, book, body)
        if judge is None:
            continue
        n = {True: 0, False: 0}
        with pymupdf.open(book.source) as doc:
            for p in body:
                if not min(pages) <= p.number <= max(pages):
                    continue
                every = pdflayer.page_words(doc[p.number - 1], p)
                for i, w in enumerate(every):
                    pair = versions(w[4])
                    if pair is None:
                        continue
                    marked, plain = pair
                    positive = (p.number, plain.translate(STRAIGHT)) in lost
                    # The layer often reads a single mark as a double one: only words the
                    # reference sets with the double mark, and never nested, are plain.
                    if not positive and (marked in reference or plain not in reference):
                        continue
                    ink = strip(doc[p.number - 1], w)
                    fits = [] if ink is None else [
                        f
                        for gap in ("", "\u2009")
                        if (f := rendercheck.mark_fit(judge._face, judge._match, ink, gapped(marked, plain, gap), plain)) is not None
                    ]
                    fit = max(fits) if fits else None
                    if fit is None:
                        continue
                    n[positive] += 1
                    rows.append({"book": name, "page": p.number, "word": plain, "marked": marked, "lost": positive, "fit": fit})
        print(f"{name}: {n[True]} lost outer marks placed of {len(lost)}, {n[False]} plain double marks", flush=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    y = np.array([r["lost"] for r in rows])
    x = np.array([r["fit"] for r in rows])
    if y.any() and not y.all():
        print(f"{int(y.sum())} lost marks, {int((~y).sum())} plain; AUC {roc_auc_score(y, x):.3f}")
        print("  lost marks' fits:", np.round(np.sort(x[y]), 2).tolist())
        print("  plain, quantiles 50/90/99/max:", np.round(np.quantile(x[~y], [0.5, 0.9, 0.99, 1]), 2).tolist())
        for cut in (0.5, 0.6, 0.7, 0.79, 0.85):
            print(f"  cut {cut}: found {int((x[y] >= cut).sum())} of {int(y.sum())}, offered among plain {int((x[~y] >= cut).sum())} of {int((~y).sum())}")
        top = sorted((r for r in rows if not r["lost"]), key=lambda r: -r["fit"])[:12]
        print("  plain that look most nested:", [(r["book"][:8], r["page"], r["word"], round(r["fit"], 2)) for r in top])


if __name__ == "__main__":
    main()
