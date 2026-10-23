"""Line roles on the certain rows of the validation books (`laya_roles_data.py`): the
pipeline's own (the role model, its rules and the trees, as a warm build sets them) against
a trained decision model's predictions.

    uv run python experiments/laya_roles_eval.py [predictions.jsonl]

A predictions file holds {"book", "page", "line", "role", "p"} per row; without one only the
pipeline is scored. Every wrong row is listed under work/probes/laya-roles/errors-<who>.txt.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, pipeline
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.flags import treatment
from roboscriptorium.golden import scoring
from roboscriptorium.ir import SourceRef

ROOT = Path("work/probes/laya-roles")
AS_LABEL = {"text": "body", "heading": "heading", "dropped": "other"}


def rows(book: str) -> list[dict]:
    return [json.loads(x) for x in (ROOT / f"{book}.jsonl").read_text().splitlines()]


def pipeline_roles(spec: str) -> dict[tuple[int, int], str]:
    name, pages = (spec.split(":") + [""])[:2]
    stages = pipeline.run(
        Book.load(Path("work") / name),
        pages=scoring.page_range(pages or None),
        check_ocr=False,
        settings=Settings.from_env(),
    )
    return {
        (p.number, k): AS_LABEL[treatment(stages.model_roles.get(SourceRef(p.number, k)))]
        for p in stages.pages
        for k in range(len(p.lines))
    }


def score(who: str, got: dict, books: list[str]) -> None:
    confusion: Counter = Counter()
    wrong = []
    for book in books:
        n = bad = 0
        for r in rows(book):
            gold, pred = r["gold"]["role"], got.get((book, r["page"], r["line"]))
            if pred is None:
                continue
            n += 1
            confusion[(gold, pred)] += 1
            if pred != gold:
                bad += 1
                wrong.append(f"{book} p{r['page']} l{r['line']}: {gold} → {pred}  {r['state']['line']!r}")
        print(f"  {who:10} {book[:40]:40} wrong {bad:4} of {n}")
    total = sum(confusion.values())
    errors = sum(v for (g, p), v in confusion.items() if g != p)
    print(f"{who}: wrong {errors} of {total}; by (gold → predicted): "
          f"{ {f'{g}→{p}': v for (g, p), v in sorted(confusion.items()) if g != p} }")
    (ROOT / f"errors-{who}.txt").write_text("\n".join(wrong) + "\n")


if __name__ == "__main__":
    specs = [s for s in bench.SETS["validation"] if (ROOT / f"{s.split(':')[0]}.jsonl").exists()]
    books = [s.split(":")[0] for s in specs]
    base = {}
    for spec, book in zip(specs, books, strict=True):
        base.update({(book, *k): v for k, v in pipeline_roles(spec).items()})
    score("pipeline", base, books)
    if len(sys.argv) > 1:
        preds = [json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines()]
        score("model", {(p["book"], p["page"], p["line"]): p["role"] for p in preds}, books)
