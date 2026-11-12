"""Render and compare: can the near-ties of a typeface match be settled without suspects,
as `init` would have to? The candidates of `probe_face_by_places.py` are ranked again by
the judge's own fit (`rendercheck.fits`: each word drawn at the book's size, laid over
its strip of the line) on plain words of the layer, and the face that wins is scored by
its share right on the labelled places (from that probe's output). No models.

    uv run python experiments/probe_face_by_words.py <book> [more …]
"""

import json
import random
import sys
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import ocr, pdf, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings

PLACES = Path("work/probes/face-by-places")
WORDS = 150

for name in sys.argv[1:]:
    data = json.loads((PLACES / f"{name}.json").read_text())
    book = Book.load(Path("work") / name)
    layer = pdf.cached_text_layer(
        book.source, book.stages / "textlayer.json", ocr.language(book.language)
    )
    first, last = book.body_pages
    body = [p for p in layer if first <= p.number <= last]
    rng = random.Random(1)
    inks = []
    with pdf.PDF_LOCK, pymupdf.open(book.source) as doc:
        for text in rng.sample(body, min(15, len(body))):
            page = doc[text.number - 1]
            words = [w for w in pdf.page_words(page, text) if len(w[4]) >= 4 and w[4].isalpha()]
            for w in rng.sample(words, min(len(words), 12)):
                ink = rendercheck.place_ink(page, w[:4], text)
                if ink is not None:
                    inks.append((w[4], ink))
    inks = inks[:WORDS]
    library = Path(Settings.from_env().fonts)
    sized = rendercheck.scan_words(book.source, body, 80)
    out = []
    for f in data["faces"]:
        face = rendercheck.Face.from_file(library / f["file"])
        size = rendercheck.em_size(sized, face.at())
        fit = np.mean([rendercheck.fits(face, f["spread"], size, ink, [w])[0] for w, ink in inks])
        seen = [(p, r) for p, r in zip(f["picks"], data["rows"]) if p is not None]
        right = np.mean([p["pick"] == r["right"] for p, r in seen])
        out.append((float(fit), float(right), f["name"]))
    best = max(out)
    print(json.dumps({"book": name, "words": len(inks), "first": out[0][1], "chosen": best[1],
                      "face": best[2], "best": max(o[1] for o in out),
                      "fits": [round(o[0], 3) for o in out]}), flush=True)
