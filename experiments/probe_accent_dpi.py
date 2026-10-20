"""Does a higher-resolution crop let the read model see an emphasis accent? The six stress-accent
errors in single layer lines that the stress-accent audit found real, cropped at several DPI
and read with the book's own prompt: does the reading hold the reference's word?

    uv run python experiments/probe_accent_dpi.py

Warm builds of five books for their line boxes, then about 20 model calls.
"""

import json
from dataclasses import replace
from pathlib import Path

import pymupdf

from roboscriptorium import bench, pipeline, readers
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring

REAL = [
    ("vals-alarm--ia-scan", 38, "zíjn"),
    ("vals-alarm--ia-scan", 54, "zíjn"),
    ("de-tuin-van-de-avondnevel--ia-scan", 33, "Ík"),
    ("het-heft-in-eigen-hand--ia-scan", 71, "níét"),
    ("het-schaduwhuis--ia-scan", 29, "míjn"),
    ("het-schaduwhuis--ia-scan", 56, "vríénden"),
]
RUN = "tuning-20261020T182636-f38e636-dirty"
DPIS = (300, 450, 600)

if __name__ == "__main__":
    settings = Settings.from_env()
    rows = [json.loads(x) for x in Path(f"work/bench/{RUN}.errors.jsonl").read_text().splitlines()]
    line_of = {
        (r["book"], r["page"]): r["lines"][0]
        for r in rows
        if r["cause"] == "stress accent" and r["lines"] and r["lines"][0] == r["lines"][1]
    }
    held = {d: 0 for d in DPIS}
    for book_name in dict.fromkeys(b for b, _, _ in REAL):
        spec = next(x for x in bench.SETS["tuning"] if x.split(":")[0] == book_name)
        book = Book.load(Path("work") / book_name)
        stages = pipeline.run(
            book, pages=scoring.page_range((spec.split(":") + ["", ""])[1] or None),
            settings=replace(settings, ocr_trust=False),
        )
        pages = {p.number: p for p in stages.pages}
        prompt = json.loads((Path("work") / book_name / "stages" / "third-reading.json").read_text())["prompt"]
        with pymupdf.open(book.source) as doc:
            for b, number, want in REAL:
                if b != book_name:
                    continue
                k = line_of[(b, number)]
                boxes = readers.line_boxes(doc[number - 1], pages[number])
                span = readers.crop_span(boxes, k)
                out = []
                for dpi in DPIS:
                    readers.DPI = dpi
                    png = readers._line_crop(doc, number, boxes[k], span)
                    reading = readers.transcribe(png, settings.read_model, settings.ollama_url, prompt)
                    held[dpi] += want in reading
                    out.append(f"{dpi}: {int(want in reading)}")
                print(f"{b[:22]:22} p{number:<4} {want!r:12}", " ".join(out), flush=True)
    print("reference's word held, of", len(REAL), held)
