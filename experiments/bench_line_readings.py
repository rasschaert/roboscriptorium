"""Bench: each OCR reading of a golden scan's body lines against the lines' truth.

Lines are labelled by `golden.align` (verdicts patched into the reference); the
readings are the build's cached ones: the text layer, glm-ocr on the line crop,
tesseract. Reports, per reading, the character error rate over the lines all
readings cover, how many lines it gets exactly right, and its most frequent
confusions (what it reads → what is printed), with typesetting
(quote, dash and ellipsis glyphs) folded.

    uv run python experiments/bench_line_readings.py work/<book> 9-64 1-4 [--extra MODEL]

`--extra MODEL` adds a generative vision model's reading of each line's crop (the OCR
check's crop), cached in work/probes/line-readings/; with `--style`, its prompt tells
it the book's typesetting (`quotes.style_prompt`).
"""

import base64
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pymupdf

from rapidfuzz.distance import Levenshtein

from roboscriptorium import disagreements, ocr, ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.cli import _verdicts
from roboscriptorium.config import Settings
from roboscriptorium.evaluate import normalise
from roboscriptorium.flags import treatment
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef

book = Book.load(Path(sys.argv[1]))
first, last = map(int, sys.argv[2].split("-"))
c0, c1 = map(int, sys.argv[3].split("-"))
settings = Settings.from_env()
stages = pipeline.run(book, pages=(first, last))
pages = stages.pages
reference = load_chapters(Golden.load(book.golden).text_dir)[c0 - 1 : c1]
reference, applied = disagreements.patch(reference, _verdicts(book))
labels = align(pages, reference)
kept = {
    SourceRef(p.number, i)
    for p in pages
    for i in range(len(p.lines))
    if treatment(stages.model_roles.get(SourceRef(p.number, i))) != "dropped"
}
readings = {
    "text layer": {SourceRef(p.number, i): ln.text for p in pages for i, ln in enumerate(p.lines)},
    "glm-ocr": ocrcheck.line_readings(
        book.source, pages, kept, settings.ocr_model, settings.ollama_url,
        book.stages / "second-reading.json",
    ),
    "tesseract": ocrcheck.tesseract_readings(
        book.source, pages, kept, ocr.language(book.language), book.stages / "tesseract.json"
    ),
}
EXTRA_PROMPT = (
    "Transcribe the printed text in this image exactly as printed: every letter, accent, "
    "quote mark (‘ ’ “ ”), dash and punctuation mark. It is one line of a book. Output "
    "only the text."
)


def extra_readings(model: str, prompt: str = EXTRA_PROMPT) -> dict[SourceRef, str]:
    styled = "--styled" if prompt != EXTRA_PROMPT else ""
    cache = Path("work/probes/line-readings") / f"{book.root.name}--{model.replace(':', '_')}{styled}.json"
    done = json.loads(cache.read_text()) if cache.exists() else {}
    todo = [r for r in sorted(kept, key=lambda r: (r.page, r.line)) if f"{r.page}:{r.line}" not in done
            and len(next(p for p in pages if p.number == r.page).lines[r.line].text) >= ocrcheck.MIN_LINE_CHARS]

    def read(png: bytes) -> str:
        payload = {"model": model, "prompt": prompt, "images": [base64.b64encode(png).decode()],
                   "stream": False, "think": False, "options": {"num_predict": 160, "temperature": 0}}
        r = httpx.post(f"{settings.ollama_url}/api/generate", json=payload, timeout=600)
        r.raise_for_status()
        return r.json()["response"].strip().split("\n")[0].strip()

    by_number = {p.number: p for p in pages}
    with pymupdf.open(book.source) as pdf, ThreadPoolExecutor(2) as pool:
        boxes = {n: ocrcheck.line_boxes(pdf[n - 1], by_number[n]) for n in {r.page for r in todo}}
        for start in range(0, len(todo), 100):
            batch = todo[start : start + 100]
            crops = [ocrcheck._line_crop(pdf, r.page, boxes[r.page][r.line]) for r in batch]
            for r, text in zip(batch, pool.map(read, crops), strict=True):
                done[f"{r.page}:{r.line}"] = text
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(done, ensure_ascii=False))
            print(f"  {model}: {len(done)} lines read", flush=True)
    return {SourceRef(*map(int, k.split(":"))): v for k, v in done.items()}


if "--extra" in sys.argv:
    model = sys.argv[sys.argv.index("--extra") + 1]
    readings[model] = extra_readings(model)
    if "--style" in sys.argv:
        from roboscriptorium import quotes
        from roboscriptorium.reflow import single_quoted

        paragraphs = stages.doc.paragraphs
        text = " ".join(p.text for p in paragraphs)
        dash = pipeline.dash_style(book, pages)
        prompt = quotes.style_prompt(
            book.language, single_quoted(paragraphs), quotes.ellipsis(text), dash.dash if dash else None
        )
        readings[model + " styled"] = extra_readings(model, prompt)

lines = [
    ref for ref, label in labels.items()
    if label.role == "body" and label.truth and all(ref in r for r in readings.values())
]
chars = sum(len(labels[r].truth) for r in lines)
print(f"{len(lines)} body lines, {chars} characters ({applied} verdicts applied)")


def confusions(got: str, want: str) -> list[tuple[str, str]]:
    out = []
    for op in Levenshtein.opcodes(got, want):
        if op.tag != "equal":
            out.append((got[op.src_start : op.src_end], want[op.dest_start : op.dest_end]))
    return out


for name, reading in readings.items():
    edits = sum(Levenshtein.distance(reading[r], labels[r].truth) for r in lines)
    exact = sum(reading[r] == labels[r].truth for r in lines)
    folded = [(normalise(reading[r]), normalise(labels[r].truth)) for r in lines]
    folded_edits = sum(Levenshtein.distance(g, w) for g, w in folded)
    seen = Counter(c for g, w in folded for c in confusions(g, w))
    top = ", ".join(f"{g!r}→{w!r} {n}" for (g, w), n in seen.most_common(14))
    print(
        f"\n{name:10} CER {edits / chars:.2%}, typesetting folded {folded_edits / chars:.2%}"
        f"  exact {exact}/{len(lines)}\n  folded: {top}"
    )


layer = readings["text layer"]
for name, reading in readings.items():
    if name == "text layer":
        continue
    fixes = sum(normalise(reading[r]) == normalise(labels[r].truth) != normalise(layer[r]) for r in lines)
    breaks = sum(normalise(layer[r]) == normalise(labels[r].truth) != normalise(reading[r]) for r in lines)
    print(f"{name}: right where the layer is wrong on {fixes} lines; wrong where it is right on {breaks}")


# Lines only one other reading gets right, where the layer is wrong: what that reading
# alone would add to the OCR check's versions.
others = [n for n in readings if n != "text layer"]
for name in others:
    rest = [n for n in others if n != name]
    alone = [
        r for r in lines
        if normalise(readings[name][r]) == normalise(labels[r].truth) != normalise(layer[r])
        and all(normalise(readings[n][r]) != normalise(labels[r].truth) for n in rest)
    ]
    print(f"{name}: the only reading right where the layer is wrong on {len(alone)} lines")
    for r in alone[:12]:
        print(f"    p{r.page}:{r.line} layer {layer[r]!r}\n{'':14}{name} {readings[name][r]!r}")

wrong = [r for r in lines if normalise(layer[r]) != normalise(labels[r].truth)]
nobody = [r for r in wrong if all(normalise(readings[n][r]) != normalise(labels[r].truth) for n in others)]
print(f"layer wrong on {len(wrong)} lines; no reading right on {len(nobody)}")
for r in nobody[:40]:
    print(f"    p{r.page}:{r.line} layer {layer[r]!r}\n{'':14}truth {labels[r].truth!r}")
