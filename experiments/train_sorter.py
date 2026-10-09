"""The line-role model (`sorter.py`): its labelled lines, its score against the rules
leaving one book out, and with `--save` the model the pipeline uses (ROBO_SORTER=1).

Labels come from `golden.align` (body, heading, other) on the bench's tuning and
validation slices and two more golden books; features from a build with the rules'
roles (ROBO_SORTER=0), never the trees' own. Validation books are scored by trees
trained without any of them and never trained on; the test set is never touched.
Lines are cached per book in work/probes/sorter/.

    uv run python experiments/train_sorter.py [--rebuild] [--save]
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, disagreements, layout, pipeline, sorter, typestyle
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.config import Settings
from roboscriptorium.files import write_atomic
from roboscriptorium.flags import treatment
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef

EXTRA = ["monterosso-mon-amour--ia-scan", "de-aanslag--calibre-pdf"]
SPECS = bench.SETS["tuning"] + bench.SETS["validation"] + EXTRA
VALIDATION = {s.split(":")[0] for s in bench.SETS["validation"]}
OUT = Path("work/probes/sorter")
RULES = {"text": "body", "heading": "heading", "dropped": "other"}


def lines(spec: str, rebuild: bool) -> list[dict]:
    name, pages, chapters = (spec.split(":") + ["", ""])[:3]
    path = OUT / f"{name}.json"
    if path.exists() and not rebuild:
        return json.loads(path.read_text())
    os.environ["ROBO_SORTER"] = "0"
    book = Book.load(Path("work") / name)
    stages = pipeline.run(book, pages=_range(pages or None), check_ocr=False)
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if span := _range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = disagreements.patch(reference, _verdicts(book))
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


def errors(truth: list[str], pred: list[str]) -> str:
    wrong = sum(t != p for t, p in zip(truth, pred, strict=True))
    lost = sum(t == "body" and p != "body" for t, p in zip(truth, pred, strict=True))
    head = sum(t == p == "heading" for t, p in zip(truth, pred, strict=True))
    spurious = sum(p == "heading" != t for t, p in zip(truth, pred, strict=True))
    return (
        f"errors {wrong:4}  body lost {lost:3}  headings {head}/{truth.count('heading')}"
        f" (+{spurious})"
    )


def fit(rows: list[dict]) -> sorter.Sorter:
    return sorter.train([r["f"] for r in rows], [r["label"] for r in rows])


def predict(model: sorter.Sorter, rows: list[dict]) -> list[str]:
    return list(model.model.predict(sorter._matrix([r["f"] for r in rows])))


if __name__ == "__main__":
    books = {s.split(":")[0]: lines(s, "--rebuild" in sys.argv) for s in SPECS}
    trainable = [b for b in books if b not in VALIDATION]
    if "--save" in sys.argv:
        path = Path(Settings.from_env().sorter_model)
        tuning = [s.split(":")[0] for s in bench.SETS["tuning"]]
        models = [(path, fit([r for b in trainable for r in books[b]]))]
        models += [
            (sorter.without(path, held), fit([r for b in trainable if b != held for r in books[b]]))
            for held in tuning
        ]
        for out, model in models:
            sorter.save(model, out)
            print(f"saved {out}")
        sys.exit()
    total = Counter()
    for book, rows in books.items():
        truth = [r["label"] for r in rows]
        rules = [r["rules"] for r in rows]
        trees = predict(fit([r for b in trainable if b != book for r in books[b]]), rows)
        kind = "validation" if book in VALIDATION else "tuning"
        print(f"{book[:34]:34} {kind}\n   rules  {errors(truth, rules)}\n   trees  {errors(truth, trees)}")
        total[f"{kind} rules"] += sum(t != p for t, p in zip(truth, rules, strict=True))
        total[f"{kind} trees"] += sum(t != p for t, p in zip(truth, trees, strict=True))
    print("\nerrors:", dict(total))
