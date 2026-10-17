"""The line-role model's labelled lines and the models the pipeline uses (`sorter.py`).

Labels come from `golden.align` (body, heading, other) on the bench's tuning and
validation slices and a few training-only slices; features from a build with the
rules' roles (the trees off), never the trees' own. Lines are cached per book in
work/probes/sorter/. Scored and saved by `experiments/train_sorter.py`.
"""

import json
import os
from dataclasses import replace
from pathlib import Path

from roboscriptorium import bench, disagreements, layout, pipeline, sorter, typestyle
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.files import write_atomic
from roboscriptorium.flags import treatment
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters

# Training-only slices, never scored: De aanslag's exact text (born-digital, not a scan);
# De tunnels' chapter 12, its photos and captions (an OCR-made reference, close enough for
# role labels); Steve Jobs' photo insert, captions against the retail EPUB.
EXTRA = [
    "de-aanslag--calibre-pdf",
    "de-tunnels--ia-scan:238-270:14-14",
    "steve-jobs--ia-scan:387-402:43-43",
]
SPECS = bench.SETS["tuning"] + bench.SETS["validation"] + EXTRA
# Scored by trees trained without any of them, and never trained on.
VALIDATION = {s.split(":")[0] for s in bench.SETS["validation"]}
OUT = Path("work/probes/sorter")
# The rules' treatment of a line as the trees' label for it.
RULES = {"text": "body", "heading": "heading", "dropped": "other"}
# How much more a body line weighs than its class's balanced share (SORTER_BODY_WEIGHT).
BODY_WEIGHT = float(os.environ.get("SORTER_BODY_WEIGHT", "10"))


def lines(spec: str, rebuild: bool = False) -> list[dict]:
    """A slice's lines, each with its features, its label and the rules' role, cached."""
    name, pages, chapters = (spec.split(":") + ["", ""])[:3]
    path = OUT / f"{name}.json"
    if path.exists() and not rebuild:
        return json.loads(path.read_text())
    book = Book.load(Path("work") / name)
    settings = replace(Settings.from_env(), sorter=False)
    stages = pipeline.run(
        book, pages=scoring.page_range(pages or None), check_ocr=False, settings=settings
    )
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if span := scoring.page_range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = disagreements.patch(reference, scoring.verdicts(book))
    labels = align(stages.pages, reference)
    styles = typestyle.measure(book.source, stages.pages, book.stages / "type.json")
    regions = None
    if layout.available():
        numbers = [p.number for p in stages.pages]
        regions = layout.detect(book.source, numbers, book.stages / "layout.json")
    found = sorter.features(stages.pages, stages.model_roles, styles, regions)
    rows = [
        {
            "page": ref.page,
            "line": ref.line,
            "f": f,
            "label": labels[ref].role,
            "rules": RULES[treatment(stages.model_roles.get(ref))],
        }
        for ref, f in found.items()
    ]
    write_atomic(path, json.dumps(rows))
    return rows


def fit(rows: list[dict]) -> sorter.Sorter:
    return sorter.train([r["f"] for r in rows], [r["label"] for r in rows], BODY_WEIGHT)


def predict(model: sorter.Sorter, rows: list[dict]) -> list[str]:
    return list(model.model.predict(sorter._matrix([r["f"] for r in rows])))


def models_to_save(books: dict[str, list[dict]], path: Path) -> list[tuple[Path, sorter.Sorter]]:
    """The trees the pipeline uses, trained on every book but the validation ones, and a
    copy without each tuning book, which `bench` scores that book with."""
    trainable = [b for b in books if b not in VALIDATION]
    tuning = [s.split(":")[0] for s in bench.SETS["tuning"]]
    out = [(path, fit([r for b in trainable for r in books[b]]))]
    out += [
        (sorter.without(path, held), fit([r for b in trainable if b != held for r in books[b]]))
        for held in tuning
    ]
    return out
