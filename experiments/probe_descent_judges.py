"""Are the vision judges right more often with crops that stop at the line above's
descenders (`readers.own_span`)? A sample of settled trust-data places from golden books,
each judge asked anew with the cut crop, its pick scored against the reference beside
the vote it gave on the old crop (in the trust data). Answers cached in
work/probes/descent-judges/. No arbiter.

    uv run python experiments/probe_descent_judges.py [per book] [book …]
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

import pymupdf

from roboscriptorium import ocrcheck, pipeline, readers, scanstyle
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.roles import DecisionCache
from roboscriptorium.trustdata import rows_of

OUT = Path("work/probes/descent-judges")
per_book = int(sys.argv[1]) if len(sys.argv) > 1 else 100
books = sys.argv[2:] or ["goede-dochter--ia-scan", "de-tuin-van-de-avondnevel--ia-scan", "het-heft-in-eigen-hand--ia-scan"]
settings = Settings.from_env()
OUT.mkdir(parents=True, exist_ok=True)
cache = DecisionCache(OUT / "decisions.jsonl")
right = Counter()
seen = Counter()
for name in books:
    book = Book.load(Path("work") / name)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json")
    pages = {p.number: p for p in layer}
    whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
    descent = scanstyle.measure_descent(book.source, whole, book.stages / "descent.json")
    from roboscriptorium.clients import decide

    vision = decide.for_model(settings.judge_model, settings.ollama_url)
    alarms = [a for spec in settings.alarm_models if (a := pipeline._alarm(spec, settings, book, whole))]
    rows = [r for r in rows_of(name, settings) if r["settled"]]
    random.seed(0)
    sample = random.sample(rows, min(per_book, len(rows)))
    with pymupdf.open(book.source) as doc:
        for r in sample:
            s = r["s"]
            page = pages.get(s.page)
            if page is None or s.line >= len(page.lines) or page.lines[s.line].text != s.original:
                continue
            boxes = readers.line_boxes(doc[s.page - 1], page)
            span = readers.own_span(boxes, s.line, ocrcheck.CROP_PAD, descent)
            others = list(s.others)
            (_, _, votes), _ = ocrcheck._decide(
                doc[s.page - 1], s.page, s.line, s.original, s.start, s.end, others, s.box,
                book.language, vision, None, cache, alarms=alarms, span=span,
            )  # fmt: skip
            versions = [s.ours, *others]
            for model, new in votes.items():
                if model == "word list":
                    continue
                old = s.votes.get(model)
                if old is None:
                    continue
                truth = {v for v, ok in zip(versions, r["right"], strict=True) if ok}
                seen[model] += 1
                right[(model, "old")] += old in truth
                right[(model, "new")] += new in truth
    print(f"{name}: descent {descent}", flush=True)
print(f"{'judge':40} places  old crop right  new crop right")
for model in seen:
    print(f"{model[:40]:40} {seen[model]:6}  {right[(model, 'old')]:14}  {right[(model, 'new')]:14}")
