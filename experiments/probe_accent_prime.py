"""Does telling the model where to look let it see an emphasis accent? A perfect trigger is
assumed (the alphabet's flag is the next step): for each of the six real stress-accent errors,
a 600 DPI crop of just the word, read with a neutral prompt and with a primed one ("the text
layer reads X; one letter looks unusual"). Controls: other plain words of the same lines, read
with the same primed prompt, to see whether priming makes the model invent accents.

    uv run python experiments/probe_accent_prime.py

Warm builds of five books for their line boxes, then about 40 model calls.
"""

import json
import re
from dataclasses import replace
from pathlib import Path

import pymupdf

from roboscriptorium import bench, pipeline, readers
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.pdf import line_words, page_words

CASES = [
    ("vals-alarm--ia-scan", 38, "zijn", "zíjn"),
    ("vals-alarm--ia-scan", 54, "zijn", "zíjn"),
    ("de-tuin-van-de-avondnevel--ia-scan", 33, "Ik", "Ík"),
    ("het-heft-in-eigen-hand--ia-scan", 71, "niét", "níét"),
    ("het-schaduwhuis--ia-scan", 29, "mijn", "míjn"),
    ("het-schaduwhuis--ia-scan", 56, "vriénden", "vríénden"),
]
RUN = "tuning-20261020T182636-f38e636-dirty"
DPI = 600
ACCENTED = set("áàâäéèêëíìîïóòôöúùûüıİ")
NEUTRAL = "Transcribe the printed word in this image exactly as printed. Return only the word."
PRIMED = (
    "Transcribe the printed word in this image exactly as printed. The text layer reads "
    "'{word}', but one letter of it looks unusual in the print: look closely at every letter "
    "and at the marks above them. Return only the word."
)


def strip(word: str) -> str:
    return re.sub(r"^\W+|\W+$", "", word)


def crop(doc, number: int, box) -> bytes:
    em = box[3] - box[1]
    clip = pymupdf.Rect(box[0] - 0.4 * em, box[1] - 0.5 * em, box[2] + 0.4 * em, box[3] + 0.5 * em)
    return doc[number - 1].get_pixmap(dpi=DPI, clip=clip).tobytes("png")


if __name__ == "__main__":
    settings = Settings.from_env()
    rows = [json.loads(x) for x in Path(f"work/bench/{RUN}.errors.jsonl").read_text().splitlines()]
    line_of = {
        (r["book"], r["page"]): r["lines"][0]
        for r in rows
        if r["cause"] == "stress accent" and r["lines"] and r["lines"][0] == r["lines"][1]
    }
    ask = lambda png, prompt: readers.transcribe(png, settings.read_model, settings.ollama_url, prompt)  # noqa: E731
    got = {"neutral": 0, "primed": 0}
    invented = [0, 0]
    for name in dict.fromkeys(b for b, *_ in CASES):
        spec = next(x for x in bench.SETS["tuning"] if x.split(":")[0] == name)
        book = Book.load(Path("work") / name)
        stages = pipeline.run(
            book, pages=scoring.page_range((spec.split(":") + ["", ""])[1] or None),
            settings=replace(settings, ocr_trust=False),
        )
        pages = {p.number: p for p in stages.pages}
        with pymupdf.open(book.source) as doc:
            for b, number, layer_word, want in CASES:
                if b != name:
                    continue
                k = line_of[(b, number)]
                words = line_words(page_words(doc[number - 1]), pages[number])[k]
                hit = next((w for w in words if strip(w[4]).lower() == layer_word.lower()), None)
                if hit is None:
                    print(f"{name[:22]} p{number}: word {layer_word!r} not found in {[w[4] for w in words]}")
                    continue
                png = crop(doc, number, hit[:4])
                a = strip(ask(png, NEUTRAL))
                c = strip(ask(png, PRIMED.format(word=layer_word)))
                got["neutral"] += a == want
                got["primed"] += c == want
                print(f"{name[:22]:22} p{number:<4} layer {layer_word!r:11} want {want!r:11} neutral {a!r:12} primed {c!r}")
                for w in [w for w in words if w is not hit and len(strip(w[4])) >= 3 and re.search("[ioe]", w[4])][:2]:
                    plain = strip(w[4])
                    r = strip(ask(crop(doc, number, w[:4]), PRIMED.format(word=plain)))
                    added = bool(set(r) & ACCENTED - set(plain))
                    invented[0] += added
                    invented[1] += 1
                    if added:
                        print(f"    control {plain!r} primed -> {r!r}  (an accent invented)")
    print("real cases: holds the reference's word, neutral / primed:", got, "of", len(CASES))
    print("controls: accents invented under priming:", invented[0], "of", invented[1])
