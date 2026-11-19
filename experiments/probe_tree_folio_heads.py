"""A line holding its page's own printed number beside words ("The Great Journey 39") as a
column of the line-role trees: a running head that names its chapter recurs on only the
chapter's few pages, which the trees retrained on the grown slices keep as text
(Dolittle, decisions.md 2026-11-05 and 2026-11-14).

The trees are fitted on the cached lines (`sorterdata.lines`, the grown slices) leaving
each book out, with and without the column, and scored as the build keeps lines (as text
from P(body) >= `sorter.KEEP_BODY`, `sorter_keep.py`), beside production's trees from
disk. A line's text comes from the book's text-layer cache, matched by page, height on
the page and length; lines the build added (missing lines) have none and get 0. No
models, no stage cache written.

    uv run python experiments/probe_tree_folio_heads.py [--surya]

With `--surya`, also the trees with Surya OCR 2's layout columns (`probe_surya_roles.py`),
alone and beside the folio column (run with PYTHONPATH=experiments).
"""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from probe_surya_roles import COLUMNS, with_surya

from roboscriptorium import page as P
from roboscriptorium import sorter
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.sorterdata import BODY_WEIGHT, SPECS, VALIDATION, lines

COLUMN = "with_folio"
SURYA = "--surya" in sys.argv
PRODUCTION = Path("work/models")


def text_layer(name: str) -> dict[int, PageText]:
    path = Path("work") / name / "stages" / "text-layer.json"
    if not path.exists():
        return {}
    blob = json.loads(path.read_text())
    fields = set(Line.__dataclass_fields__)
    return {
        p["number"]: PageText(
            p["number"], p["width"], p["height"],
            [Line(**{k: v for k, v in ln.items() if k in fields}) for ln in p["lines"]],
        )  # fmt: skip
        for p in blob["pages"]
    }


def with_folio(name: str, rows: list[dict]) -> tuple[int, int]:
    """Each row's features with the column added; rows matched and rows marked."""
    pages = text_layer(name)
    offset = P.page_offset(list(pages.values())) if pages else None
    matched = marked = 0
    for r in rows:
        f, value = r["f"], 0.0
        page = pages.get(r["page"])
        text = None
        if page is not None:
            for ln in page.lines:
                t = ln.text.strip()
                if abs(ln.y0 / page.height - f["y"]) < 1e-4 and len(t) == f["chars"]:
                    text = t
                    break
        if text is not None:
            matched += 1
            folio = P.folio(r["page"], offset)
            plain = " ".join(text.split())
            # A misread number counts only where the page prints its number nowhere else.
            printed = folio is not None and any(
                ln.text.strip() != text and P.reads_as_folio(ln.text.strip(), folio)
                and ln.text.strip().strip(".,") == str(folio)
                for ln in page.lines
            )
            words = plain.split()
            exact = folio is not None and str(folio) in (
                words[0].strip(".,") if words else "", words[-1].strip(".,") if words else ""
            )
            if (
                folio is not None
                and any(c.isalpha() for c in text)
                and P.without_folio(plain, folio) != plain
                and (exact or not printed)
            ):
                value = 1.0
                marked += 1
        r["f"] = f | {COLUMN: value}
        r["text"] = text
    return matched, marked


def p_body(model: sorter.Sorter, rows: list[dict]) -> np.ndarray:
    body = list(model.model.classes_).index("body")
    return model.model.predict_proba(sorter._matrix([r["f"] for r in rows], model.features))[
        :, body
    ]


def fitted(rows: list[dict], names: tuple) -> sorter.Sorter:
    """Trees as `sorter.train` fits them, over the columns `names` (it keeps its own)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    labels = [r["label"] for r in rows]
    counts = Counter(labels)
    weight = {c: len(labels) / (len(counts) * n) for c, n in counts.items()}
    weight["body"] *= BODY_WEIGHT
    model = HistGradientBoostingClassifier(
        max_depth=4, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    )
    X = sorter._matrix([r["f"] for r in rows], names)
    return sorter.Sorter(model.fit(X, labels, sample_weight=[weight[c] for c in labels]), names)


if __name__ == "__main__":
    books = {s.split(":")[0]: lines(s) for s in SPECS}
    for name, rows in books.items():
        m, k = with_folio(name, rows)
        if SURYA:
            with_surya(name, rows)
        print(f"{name[:40]:40} {m:5} of {len(rows):5} lines matched, {k:3} with a folio")
    trainable = [b for b in books if b not in VALIDATION]
    sets = {"without": sorter.FEATURES, "with": sorter.FEATURES + (COLUMN,)}
    if SURYA:
        sets |= {"surya": sorter.FEATURES + COLUMNS, "surya+with": sorter.FEATURES + COLUMNS + (COLUMN,)}
    shown = ("production", *sets)
    total: Counter = Counter()
    per_book: dict[str, Counter] = {}
    examples = []
    for name, rows in books.items():
        train = [r for b in trainable if b != name for r in books[b]]
        ps = {}
        prod_path = PRODUCTION / (
            "line-roles.pkl" if name in VALIDATION else f"line-roles-without-{name}.pkl"
        )
        if prod_path.exists():
            ps["production"] = p_body(sorter.load(prod_path), rows)
        for which, names in sets.items():
            ps[which] = p_body(fitted(train, names), rows)
        c = per_book.setdefault(name, Counter())
        for which, p in ps.items():
            for r, q in zip(rows, p, strict=True):
                if r["label"] == "body" and q < sorter.KEEP_BODY:
                    c[(which, "lost")] += 1
                if r["label"] != "body" and q >= sorter.KEEP_BODY:
                    c[(which, "kept")] += 1
        for which in sets:
            if which == "without":
                continue
            for r, a, b in zip(rows, ps["without"], ps[which], strict=True):
                if (a >= sorter.KEEP_BODY) != (b >= sorter.KEEP_BODY):
                    examples.append((which, name, r["page"], r["label"], a, b, r.get("text")))
        part = "validation" if name in VALIDATION else "tuning"
        for key, n in c.items():
            total[(part, *key)] += n
        print(name, dict(c), flush=True)
    print("\nlost = body lines dropped, kept = other lines kept as text, at P(body) >= 0.25")
    for part in ("tuning", "validation"):
        print(part, {w: (total[(part, w, "lost")], total[(part, w, "kept")])
                     for w in shown})  # fmt: skip
    print("\nper book, lost/kept: " + " | ".join(shown))
    for name, c in per_book.items():
        cells = [f"{c[(w, 'lost')]:3}/{c[(w, 'kept')]:3}" for w in shown]
        print(f"  {name[:40]:40} {' | '.join(cells)}")
    for which in sets:
        mine = [e for e in examples if e[0] == which]
        print(f"\n{len(mine)} lines kept or dropped differently, without → {which}:")
        for _, name, page, label, a, b, text in mine[:60]:
            print(f"  {name[:28]:28} PDF {page:3} {label:8} {a:.2f} → {b:.2f}  {text!r}")
