"""Bench: each OCR reading of a golden scan's body lines against the lines' truth.

Lines are labelled by `golden.align` (verdicts patched into the reference); the
readings are the build's cached ones: the text layer, glm-ocr on the line crop,
tesseract. Reports, per reading, the character error rate over the lines all
readings cover, how many lines it gets exactly right, and its most frequent
confusions (what it reads → what is printed), with typesetting
(quote, dash and ellipsis glyphs) folded.

    uv run python experiments/bench_line_readings.py work/<book> 9-64 1-4
"""

import sys
from collections import Counter
from pathlib import Path

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
