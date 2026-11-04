"""The learned italic decision (`italics.Trees`): its training data, its score against the
cuts, and its saved models.

Collecting builds each book's slice from its caches (as `bench` does; no models), aligns
the body pages' layer words to the reference's words, and writes one row per aligned word
(`italics.features`, the reference's mark, the cuts' decision) to
work/probes/italic-words/<book>.jsonl. `--train` fits trees leaving each book out and
compares their errors with the cuts' on the same words, at several chances. `--save`
writes the model trained on every tuning book and one without each of them (`bench`
scores a tuning book with the copy that never saw it).

    uv run python experiments/italic_words.py [tuning|validation]
    uv run python experiments/italic_words.py --train tuning
    uv run python experiments/italic_words.py --save
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench, evaluate, italics
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.ir import SourceRef

OUT = Path("work/probes/italic-words")


def book(spec: str) -> str:
    name = spec.split(":")[0]
    settings = bench.unseen(Settings.from_env(), name)
    run = scoring.build(f"work/{spec}", settings)
    if scoring.italics_unlike(run.book):
        return f"{name}: italics unlike print, skipped"
    pages = run.stages.pages
    done = italics.measure(run.book.source, pages, run.book.stages / "italics.json")
    cut = italics._cut(pages, done)
    rows = italics.features(pages, done)

    ref_paras = [p for ch in run.reference for p in ch.paragraphs]
    ref_marks = [
        ch.italic[k] if k < len(ch.italic) else ()
        for ch in run.reference
        for k in range(len(ch.paragraphs))
    ]
    ref_words, _ = evaluate._words_with_breaks(ref_paras)
    ref_italic = evaluate._italic_words(ref_paras, ref_marks)

    words, where = [], []
    for p in pages:
        for k, ln in enumerate(p.lines):
            for i, w in enumerate(ln.text.split(" ")):
                if w:
                    words.append(evaluate.normalise(w))
                    where.append((SourceRef(p.number, k), i))
    to_ref = {}
    for op in Levenshtein.opcodes(words, ref_words):
        if op.tag == "equal":
            for d in range(op.src_end - op.src_start):
                to_ref[op.src_start + d] = op.dest_start + d

    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(OUT / f"{name}.jsonl", "w") as fh:
        for w, (ref, i) in enumerate(where):
            if w not in to_ref:
                continue
            row = dict(rows[ref][i])
            row |= {
                "book": name,
                "page": ref.page,
                "line": ref.line,
                "i": i,
                "word": words[w],
                "label": to_ref[w] in ref_italic,
                "rule": i in cut.get(ref, frozenset()),
            }
            fh.write(json.dumps(row) + "\n")
            n += 1
    return f"{name}: {n} words, {len(ref_italic)} italic in reference"


def _load(books: list[str]) -> dict[str, list[dict]]:
    return {
        b: [json.loads(line) for line in open(OUT / f"{b}.jsonl")]
        for b in books
        if (OUT / f"{b}.jsonl").exists()
    }


def _fit(data: dict[str, list[dict]]) -> italics.Trees:
    rows = [r for rs in data.values() for r in rs]
    return italics.train(rows, [r["label"] for r in rows], [r["book"] for r in rows])


def _p(trees: italics.Trees, rows: list[dict]) -> np.ndarray:
    X = np.array([[r[k] for k in trees.features] for r in rows], dtype=float)
    return trees.model.predict_proba(X)[:, 1]


def train(books: list[str], cuts=(0.4, 0.5, 0.6, 0.7)) -> None:
    data = _load(books)
    total = {"rule": [0, 0]} | {c: [0, 0] for c in cuts}
    print(f"{'book':30} {'italic':>7} {'rule':>10} " + " ".join(f"{c:>10}" for c in cuts))
    for held in data:
        trees = _fit({b: rs for b, rs in data.items() if b != held})
        test = data[held]
        p = _p(trees, test)
        lab = np.array([r["label"] for r in test])
        cells = []
        for key, pred in [("rule", np.array([r["rule"] for r in test]))] + [
            (c, p >= c) for c in cuts
        ]:
            m, f = int((lab & ~pred).sum()), int((pred & ~lab).sum())
            total[key][0] += m
            total[key][1] += f
            cells.append(f"{m:>5}/{f:<4}")
        print(f"{held[:30]:30} {int(lab.sum()):7} " + " ".join(cells))
    for k, (m, f) in total.items():
        print(f"{k}: missed {m}, false {f}, errors {m + f}")


def validate(tuning: list[str], validation: list[str]) -> None:
    """The model trained on every tuning book, scored on the validation books."""
    trees = _fit(_load(tuning))
    total = {"rule": [0, 0], "trees": [0, 0]}
    for b, test in _load(validation).items():
        lab = np.array([r["label"] for r in test])
        cells = []
        for key, pred in (
            ("rule", np.array([r["rule"] for r in test])),
            ("trees", _p(trees, test) >= italics.ITALIC_P),
        ):
            m, f = int((lab & ~pred).sum()), int((pred & ~lab).sum())
            total[key][0] += m
            total[key][1] += f
            cells.append(f"{m:>5}/{f:<4}")
        print(f"{b[:30]:30} {int(lab.sum()):7} " + " ".join(cells))
    for k, (m, f) in total.items():
        print(f"{k}: missed {m}, false {f}, errors {m + f}")


def save(tuning: list[str]) -> None:
    data = _load(tuning)
    path = Path(Settings().italic_model)
    italics.save(_fit(data), path)
    print("saved", path)
    for held in tuning:
        # A tuning book with no rows (its italics unlike its print) never trained it.
        copy = italics.without(path, held)
        italics.save(_fit({b: rs for b, rs in data.items() if b != held}), copy)
        print("saved", copy)


def _names(set_name: str) -> list[str]:
    return [s.split(":")[0] for s in bench.SETS[set_name]]


def main() -> None:
    args = sys.argv[1:]
    if args[:1] == ["--train"]:
        train([b for s in (args[1:] or ["tuning"]) for b in _names(s)])
    elif args[:1] == ["--validate"]:
        validate(_names("tuning"), _names("validation"))
    elif args[:1] == ["--save"]:
        save(_names("tuning"))
    else:
        specs = [s for name in (args or ["tuning"]) for s in bench.SETS[name]]
        with ProcessPoolExecutor(bench.workers()) as pool:
            for line in pool.map(book, specs):
                print(line, flush=True)


if __name__ == "__main__":
    main()
