"""Is tesseract's word confidence lower on the errors every reading shares? No Ollama:
tesseract reads each page holding one of the tuning books' unasked errors
(`unasked.py`'s work/probes/unasked/<book>.jsonl), and a word it reads as the error's
wrong word is compared with the page's other words.

    uv run python experiments/probe_tesseract_confidence.py
"""

import csv
import glob
import io
import json
import statistics
from collections import defaultdict
from pathlib import Path

import pymupdf

from roboscriptorium import ocr
from roboscriptorium.book import Book

DPI = 300
PUNCT = ".,;:!?‘’'“”()"
rows = [json.loads(line) for f in glob.glob("work/probes/unasked/*.jsonl") for line in open(f)]
rows = [r for r in rows if r["category"] in ("letters", "words") and r["got"].strip()]
by_page = defaultdict(list)
for r in rows:
    by_page[r["book"], r["page"]].append(r)
err_conf, other_conf, missed = [], [], 0
for (book, page), errors in sorted(by_page.items()):
    b = Book.load(Path("work") / book)
    lang = ocr.language(b.language)
    with pymupdf.open(b.source) as doc:
        png = doc[page - 1].get_pixmap(dpi=DPI).tobytes("png")
    table = csv.DictReader(io.StringIO(ocr.tesseract(png, lang, tsv=True)), delimiter="\t", quoting=csv.QUOTE_NONE)
    words = [(row["text"].strip(), float(row["conf"])) for row in table if (row.get("text") or "").strip() and float(row["conf"]) >= 0]
    wrong = {w.strip(PUNCT) for e in errors for w in e["got"].split()}
    hit = False
    for text, conf in words:
        if text.strip(PUNCT) in wrong:
            err_conf.append(conf)
            hit = True
        else:
            other_conf.append(conf)
    missed += not hit
    found = [c for t, c in words if t.strip(PUNCT) in wrong]
    print(f"{book[:22]} p{page}: {[(e['got'], e['want']) for e in errors]} → {found}", flush=True)
q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]  # noqa: E731
print(f"\nerror words {len(err_conf)} (pages where none was found: {missed}): median {statistics.median(err_conf):.0f}, 25% {q(err_conf, .25):.0f}")
print(f"other words {len(other_conf)}: median {statistics.median(other_conf):.0f}, 25% {q(other_conf, .25):.0f}, 10% {q(other_conf, .10):.0f}")
for t in (50, 70, 80, 90):
    e = sum(c < t for c in err_conf); o = sum(c < t for c in other_conf)
    print(f"  conf < {t}: errors {e}/{len(err_conf)}, other words {o}/{len(other_conf)} ({o / len(other_conf):.1%})")
