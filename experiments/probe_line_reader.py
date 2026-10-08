"""A candidate line reader against the local reading model, on a golden book's pages.

Reads every line of pages first–last with the candidate (local on Ollama, or hosted as
`openrouter:…`), with the prompt the book's `stages/third-reading.json` was read with,
and prints its speed, how often it reads a line as the local model did, and each
reading's CER, exact lines and lines with quote marks wrong against the aligned
reference (body lines whose truth is about the line's length).

    uv run python experiments/probe_line_reader.py <book dir> <first> <last> <model> [<chapters>]
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium import ocrcheck, pdf
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef

book_dir, first, last, model = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
chapters = sys.argv[5] if len(sys.argv) > 5 else ""
book = Book.load(book_dir)
local = json.loads((book.stages / "third-reading.json").read_text())
layer = pdf.cached_text_layer(book.source, book.stages / "textlayer.json")
pages = [p for p in layer if first <= p.number <= last]
checked = {SourceRef(p.number, k) for p in pages for k in range(len(p.lines))}
slug = model.replace("/", "-").replace(":", "-").replace("@", "-")
out = Path("work/probes/line-readers") / f"{book_dir.name}-{first}-{last}-{slug}.json"
url = Settings.from_env().ollama_url
start = time.time()
ocrcheck.line_readings(book.source, pages, checked, model, url, out, local["prompt"])
seconds = time.time() - start
theirs = json.loads(out.read_text())["lines"]
shared = [k for k in theirs if k in local["lines"]]
same = sum(theirs[k] == local["lines"][k] for k in shared)
print(f"{model}: {len(theirs)} lines in {seconds:.0f} s ({seconds / max(1, len(theirs)):.2f} s a line, "
      f"cached lines count as 0); the same as {local['model']} on {same}/{len(shared)}")

reference = load_chapters(Golden.load(book.golden).text_dir)
if chapters:
    c0, c1 = (int(x) for x in chapters.split("-"))
    reference = reference[c0 - 1 : c1]
truth = align(pages, reference)
rows = []
with pymupdf.open(book.source) as doc:
    for p in pages:
        boxes = ocrcheck.line_boxes(doc[p.number - 1], p)
        for k, line in enumerate(p.lines):
            t = truth[SourceRef(p.number, k)]
            if t.role != "body" or not 0.7 < len(t.truth) / max(1, len(line.text)) < 1.4:
                continue
            text = hashlib.sha1(line.text.encode()).hexdigest()[:10]
            key = f"{p.number}:{k}:{text}:" + ",".join(f"{v:.0f}" for v in boxes[k])
            if key in local["lines"] and key in theirs:
                rows.append((t.truth, line.text, local["lines"][key], theirs[key]))


def quotes(s: str) -> int:
    return sum(s.count(c) for c in "‘’“”")


chars = sum(len(normalise(r[0])) for r in rows)
print(f"against the reference, {len(rows)} body lines:")
for i, name in ((1, "text layer"), (2, local["model"]), (3, model)):
    d = [Levenshtein.distance(normalise(r[i]), normalise(r[0])) for r in rows]
    q = sum(quotes(r[i]) != quotes(r[0]) for r in rows)
    print(f"  {name:45} CER {sum(d) / max(1, chars):.2%}  exact {d.count(0)}  quote marks wrong {q}")
