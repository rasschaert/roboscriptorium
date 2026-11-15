"""Blank pages whose show-through the text layer reads as words pad `init`'s ends (Het
ijzige land, Reis om mijn schedel, Een Russische roman: setup_gaps.py, 2026-11-15). Does a
page's ink contrast against the book's own text pages (`faint.contrast`) tell them from
printed pages? Every page of the labelled books with words in its layer: its contrast as a
share of the book's median, by its label. No models.

    PYTHONPATH=experiments uv run python experiments/probe_showthrough.py
"""

import statistics
from pathlib import Path

import pymupdf
from setup_gaps import LABELS, kinds_of

from roboscriptorium import faint, pagekinds
from roboscriptorium.pdf import cached_text_layer

rows = []
for name, entry in sorted(LABELS.items()):
    root = Path("work") / name
    if not (root / "source.pdf").exists():
        continue
    pages = cached_text_layer(root / "source.pdf", root / "stages" / "textlayer.json")
    labelled = {int(k): v for k, v in entry["pages"].items()}
    kinds = kinds_of(root, pages) or {}
    with pymupdf.open(root / "source.pdf") as doc:
        got = {}
        for p in pages:
            try:
                got[p.number] = faint.contrast(doc[p.number - 1], p.lines)
            except ValueError:  # no line box holds a pixel: nothing printed where the layer says
                pass
    body = statistics.median(got[p.number] for p in pages if p.number in got and len(p.lines) > 20)
    for p in pages:
        if p.number in got:
            words = sum(len(ln.text.split()) for ln in p.lines)
            rows.append((name, p.number, labelled.get(p.number, "text"), kinds.get(p.number), got[p.number] / body, words))
    print(name, round(body), flush=True)
for cut in (0.2, 0.3, 0.4, 0.5):
    low = [r for r in rows if r[4] < cut]
    blank = [r for r in low if r[2] in ("blank", "endpaper", "library")]
    inbook = [r for r in low if pagekinds.fate(r[2]) == "in"]
    print(f"under {cut}: {len(low)} pages, {len(blank)} labelled blank or endpaper, {len(inbook)} labelled into the book")
    for r in inbook[:12]:
        print(f"    {r[0][:30]:30} PDF {r[1]:4} {r[2]:14} init {r[3]} contrast {r[4]:.2f} words {r[5]}")
print("labelled blank yet called into the book by init:")
for r in rows:
    if r[2] in ("blank", "endpaper") and r[3] and pagekinds.fate(r[3]) == "in":
        print(f"    {r[0][:30]:30} PDF {r[1]:4} init {r[3]:10} contrast {r[4]:.2f} words {r[5]}")
