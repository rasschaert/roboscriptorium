"""Surya OCR 2's layout as columns of the line-role trees: the trees fitted leaving each
book out, with and without the label of the Surya block each line lies in
(`probe_surya_layout.py` keeps the layouts in work/probes/surya-layout/; a page without
one has none, as the build of a book Surya was never asked about would). Errors as
`train_sorter.py` counts them, then the lines each set gets right that the other gets
wrong. No models.

    uv run python experiments/probe_surya_roles.py
"""

import json
from collections import Counter

import numpy as np
from probe_surya_layout import OUT, label_at
from train_sorter import errors

from roboscriptorium import sorter
from roboscriptorium.sorterdata import BODY_WEIGHT, SPECS, VALIDATION, lines

# Surya's labels, grouped; each a column, 1 where the line lies in such a block.
GROUPS = {
    "surya_heading": {"Section-Header"},
    "surya_page_header": {"Page-Header"},
    "surya_page_footer": {"Page-Footer"},
    "surya_text": {"Text", "List-Group", "Complex-Block"},
    "surya_note": {"Footnote", "Caption"},
    "surya_picture": {"Image", "Figure", "Diagram", "Table"},
}
COLUMNS = ("surya_asked", "surya_none", *GROUPS)


def with_surya(name: str, rows: list[dict]) -> int:
    """Each row's features with Surya's columns added; how many pages had a layout."""
    pages: dict[int, list | None] = {}
    for r in rows:
        if r["page"] not in pages:
            path = OUT / name / f"{r['page']}.json"
            pages[r["page"]] = json.loads(path.read_text()) if path.exists() else None
        blocks = pages[r["page"]]
        f = r["f"]
        if blocks is None:
            r["f"] = f | dict.fromkeys(COLUMNS, np.nan)
            continue
        label = label_at(blocks, 0.5 + f["centre_offset"], min(1.0, f["y"] + 0.006))
        r["f"] = f | {
            "surya_asked": 1.0,
            "surya_none": float(label is None),
            **{c: float(label in group) for c, group in GROUPS.items()},
        }
    return sum(b is not None for b in pages.values())


def fit(rows: list[dict], names: tuple) -> object:
    from sklearn.ensemble import HistGradientBoostingClassifier

    labels = [r["label"] for r in rows]
    counts = Counter(labels)
    weight = {c: len(labels) / (len(counts) * n) for c, n in counts.items()}
    weight["body"] *= BODY_WEIGHT
    model = HistGradientBoostingClassifier(
        max_depth=4, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )
    X = np.array([[r["f"][k] for k in names] for r in rows], dtype=float)
    return model.fit(X, labels, sample_weight=[weight[c] for c in labels])


def predict(model, rows: list[dict], names: tuple) -> list[str]:
    return list(model.predict(np.array([[r["f"][k] for k in names] for r in rows], dtype=float)))


if __name__ == "__main__":
    books = {s.split(":")[0]: lines(s) for s in SPECS}
    for name, rows in books.items():
        print(f"{name}: {with_surya(name, rows)} pages with a layout", flush=True)
    trainable = [b for b in books if b not in VALIDATION]
    sets = {"without": sorter.FEATURES, "with Surya": sorter.FEATURES + COLUMNS}
    total: Counter = Counter()
    changed: Counter = Counter()
    examples = []
    for book, rows in books.items():
        truth = [r["label"] for r in rows]
        train = [r for b in trainable if b != book for r in books[b]]
        said = {k: predict(fit(train, names), rows, names) for k, names in sets.items()}
        kind = "validation" if book in VALIDATION else "tuning"
        print(f"{book[:34]:34} {kind}")
        for k, pred in said.items():
            print(f"   {k:11} {errors(truth, pred)}")
            total[(kind, k)] += sum(t != p for t, p in zip(truth, pred, strict=True))
        for r, t, a, b in zip(rows, truth, said["without"], said["with Surya"], strict=True):
            if a != b:
                changed[("right with Surya" if b == t else "wrong with Surya", t)] += 1
                if b == t and len(examples) < 30:
                    examples.append(f"{book} p{r['page']} l{r['line']}: {t}, without {a}")
    print("\nerrors:", {f"{k} {s}": v for (k, s), v in total.items()})
    print("lines the two sets call differently:", dict(changed))
    for e in examples:
        print("  " + e)
