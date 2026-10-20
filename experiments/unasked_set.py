"""A frozen-style set of lines for a detector: the errors the latest tuning bench's build
left in the text layer's lines with no question asked (`layer` kept, `asked` false), and
control lines of the same pages that carry no error. Crops as the line readers see them.

    uv run python experiments/unasked_set.py

Writes work/probes/unasked-set/{items.json, crops/}; items have the reader set's fields
(`id`, `stratum` hard or control, `layer`, `crop` name), so `h2o_triage.py` and
`triage_score.py` read it with that folder as their root.
"""

import hashlib
import json
import random
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import pymupdf

from roboscriptorium import pipeline, readers
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.trustdata import SPECS

RUN = "tuning-20261020T182636-f38e636-dirty"
ROOT = Path("work/probes/unasked-set")
CONTROLS_PER_ERROR = 2
MIN_LENGTH = 25


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


if __name__ == "__main__":
    rng = random.Random(7)
    rows = [json.loads(x) for x in Path(f"work/bench/{RUN}.errors.jsonl").read_text().splitlines()]
    bad = defaultdict(set)
    wanted = defaultdict(set)
    for r in rows:
        if r["lines"]:
            bad[r["book"]].update((r["page"], n) for n in range(r["lines"][0], r["lines"][1] + 1))
        if not r["asked"] and r["layer"] == "kept" and r["lines"] and r["lines"][0] == r["lines"][1]:
            wanted[r["book"]].add((r["page"], r["lines"][0]))
    (ROOT / "crops").mkdir(parents=True, exist_ok=True)
    items = []
    for book, errors in wanted.items():
        spec = SPECS.get(book, "")
        pages_arg = (spec.split(":") + [""])[0] if spec and spec != "answers" else ""
        b = Book.load(Path("work") / book)
        stages = pipeline.run(
            b, pages=scoring.page_range(pages_arg or None), settings=replace(Settings.from_env(), ocr_trust=False)
        )
        by_page = {p.number: p for p in stages.pages}
        with pymupdf.open(b.source) as doc:
            for stratum, places in (("hard", sorted(errors)), ("control", None)):
                if places is None:
                    places = []
                    for page in sorted({p for p, _ in errors}):
                        pool = [
                            (page, k)
                            for k, ln in enumerate(by_page[page].lines)
                            if (page, k) not in bad[book] and len(ln.text) >= MIN_LENGTH
                        ]
                        places += rng.sample(pool, min(len(pool), CONTROLS_PER_ERROR))
                for page, k in places:
                    p = by_page.get(page)
                    if p is None or k >= len(p.lines):
                        continue
                    boxes = readers.line_boxes(doc[page - 1], p)
                    png = readers._line_crop(doc, page, boxes[k], readers.crop_span(boxes, k))
                    item_id = f"{book}:{page}:{k}"
                    (ROOT / "crops" / f"{sha(item_id)}.png").write_bytes(png)
                    items.append({"id": item_id, "book": book, "stratum": stratum, "layer": p.lines[k].text})
        print(book, sum(i["book"] == book for i in items), flush=True)
    (ROOT / "items.json").write_text(json.dumps({"items": items}, ensure_ascii=False))
    print(len(items), "lines:", sum(i["stratum"] == "hard" for i in items), "hard")
