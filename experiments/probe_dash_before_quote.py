"""A dash before a closing quote ("Dud—’", "toch –’", "Granny – ’"): does the scan say
how it is spaced where the layer doesn't?

The dash styling gives such a dash the book's space on its open side only. Some books
set it closed on both sides where speech is cut off, or spaced on both; the layer's own
spacing is no guide (Goede dochter's glues 21 where its reference closes 2). For every
such dash in the given books' layers this measures the blank either side of the stroke
on the scan (`scanstyle._measure`, in letters) and pairs it with how the reference
spaces the same place, found by the two words before it.

    uv run python experiments/probe_dash_before_quote.py <book dir> …

No models. Writes work/probes/dash-before-quote.jsonl.
"""

import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import pymupdf

from roboscriptorium import scanstyle
from roboscriptorium.book import Book
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.pdf import page_words

DASH = "—–"
QUOTE = "’”'\"*"
LETTERS = re.compile(r"[^\W\d_]+")
PLACE = re.compile(rf"[{DASH}]\s?[{QUOTE}]")


def bare(text: str) -> str:
    return "".join(LETTERS.findall(text)).lower()


rows = []
for folder in sys.argv[1:]:
    book = Book.load(Path(folder))
    first, last = book.body_pages
    chapters = load_chapters(Golden.load(book.golden).text_dir)
    reference = "\n".join(p for ch in chapters for p in ch.paragraphs)
    # How the reference spaces each dash before a closing quote, by the two words before.
    spaced: dict[tuple[str, str], set[str]] = {}
    for m in re.finditer(rf"(\S+) (\S+?)(\s?)[{DASH}](\s?)[{QUOTE}]", reference):
        kind = ("sp" if m.group(3) else "gl") + "-" + ("sp" if m.group(4) else "gl")
        spaced.setdefault((bare(m.group(1)), bare(m.group(2))), set()).add(kind)
    with pymupdf.open(book.source) as pdf:
        for number in range(first, last + 1):
            page = pdf[number - 1]
            words = page_words(page, None)
            for i, w in enumerate(words):
                if not PLACE.search(w[4]):
                    continue
                before = [bare(v[4]) for v in words[max(0, i - 3) : i]]
                own = bare(re.split(rf"[{DASH}]", w[4])[0])
                context = [b for b in [*before, own] if b][-2:]
                truth = spaced.get(tuple(context), set()) if len(context) == 2 else set()
                line = [v for v in words if v[5] == w[5] and v[6] == w[6]]
                m = scanstyle._measure(page, w, line)
                if m is None or len(truth) != 1:
                    continue
                gaps = m["word_gaps"]
                rows.append(
                    {
                        "book": book.path.name if hasattr(book, "path") else Path(folder).name,
                        "page": number,
                        "layer": w[4],
                        "layer_glued": bool(own),
                        "truth": next(iter(truth)),
                        "left": m["left"],
                        "right": m["right"],
                        "word_gap": statistics.median(gaps) if gaps else None,
                    }
                )

out = Path("work/probes/dash-before-quote.jsonl")
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print(f"{len(rows)} dashes before a closing quote, measured and placed in the reference")
for name in sorted({r["book"] for r in rows}):
    mine = [r for r in rows if r["book"] == name]
    print(name)
    for truth, n in sorted(Counter(r["truth"] for r in mine).items()):
        lefts = sorted(r["left"] for r in mine if r["truth"] == truth and r["left"] is not None)
        glued = sum(r["layer_glued"] for r in mine if r["truth"] == truth)
        if lefts:
            print(
                f"  reference {truth}: {n}, layer glued {glued}; blank before the dash "
                f"{lefts[0]:.2f}–{lefts[-1]:.2f}, median {statistics.median(lefts):.2f} letters"
            )
