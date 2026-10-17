"""Probe: what does each reader and judge of the OCR check earn? Take one away and see.

On the trust data, no models. Without a judge, its votes are gone. Without a reader,
every version only it read is gone, and a suspect left with the layer's version alone
is no suspect at all: the layer's reading stands unasked, a silent error where it was
wrong. A judge's vote for a version that is gone counts as no pick (the judge chose
among more versions than it would have been shown; a small optimism for the reader).
Each book is scored by trees trained on the other trainable books, as
`train_ocr_trust.py` scores them, at 0, 0.25, 0.5 and 1 question a page.

    uv run python experiments/probe_subtract.py [variant …]   # default: all
"""

import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.trustdata import HELD_OUT, SPECS, rows_of, trainable, usable, weighed

BUDGETS = (0.0, 0.25, 0.5, 1.0)
SETTINGS = Settings.from_env()
READINGS = weighed(SETTINGS)
VARIANTS = {
    "all": ("", ""),
    "no tesseract": ("reader", "tess"),
    "no glm-ocr": ("reader", "glm"),
    "no qwen3.8": ("reader", "qwen"),
    "no clef": ("judge", SETTINGS.judge_model),
    "no winnow": ("judge", SETTINGS.check_model),
    "no word list": ("judge", "word list"),
}


def without_judge(r: dict, judge: str) -> dict:
    s = r["s"]
    return {
        **r,
        "s": replace(
            s,
            votes={m: v for m, v in s.votes.items() if m != judge},
            confidence={m: c for m, c in s.confidence.items() if m != judge},
            judges=tuple(m for m in s.judges if m != judge),
        ),
    }


def without_reader(r: dict, reader: str) -> dict | None:
    """The row as the check would have made it without `reader`; None when no suspect
    is left (the layer's version stands)."""
    s = r["s"]
    others = [r_ for r_ in s.support if r_ != reader]
    n = 1 + len(s.others)
    keep = [0] + [
        k for k in range(1, n) if any(s.support[o][k] for o in others if s.support.get(o))
    ]
    if len(keep) == 1:
        return None
    versions = [s.ours, *s.others]
    kept = {versions[k] for k in keep}
    return {
        **r,
        "right": [r["right"][k] for k in keep],
        "s": replace(
            s,
            others=tuple(versions[k] for k in keep[1:]),
            support={o: tuple(s.support[o][k] for k in keep) for o in others if s.support.get(o)},
            known=tuple(s.known[k] for k in keep) if s.known else (),
            votes={m: (v if v in kept else "") for m, v in s.votes.items()},
        ),
    }


def pages_of(name: str) -> int:
    spec = SPECS[name]
    ranged = spec and spec != "answers"
    first, last = (
        scoring.page_range(spec.split(":")[0])
        if ranged
        else Book.load(Path("work") / name).body_pages
    )
    return last - first + 1


def silent_at(rows, ps, n: int) -> int:
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
    return sum(wrong for _, wrong in order[n:])


def scored(books, train_names, rows, readings):
    train = [r for n in train_names for r in books[n]]
    suspects, right = [r["s"] for r in train], [r["right"] for r in train]
    names = [n for n in train_names for _ in books[n]]
    pairs = trust.pairs_table(suspects, right, names)
    X, y = trust.training_matrix(suspects, right, names, readings)
    model = HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0
    ).fit(X, y)
    out = []
    for r in rows:
        Xt = np.array([trust.features(r["s"], k, pairs, readings) for k in range(len(r["right"]))])
        p = model.predict_proba(Xt)[:, 1]
        out.append(p / max(p.sum(), 1e-9))
    return out


def main(chosen: list[str]) -> None:
    base = {n: rows_of(n, SETTINGS) for n in SPECS if not usable(n, SETTINGS)}
    pages = {n: pages_of(n) for n in base}
    print(f"{sum(len(v) for v in base.values())} settled suspects over {len(base)} books, "
          f"{sum(pages.values())} pages")
    for label in chosen:
        kind, what = VARIANTS[label]
        books, vanished = {}, Counter()
        readings = READINGS
        for name, rows in base.items():
            if kind == "judge":
                books[name] = [without_judge(r, what) for r in rows]
            elif kind == "reader":
                readings = tuple(x for x in READINGS if x != what)
                out = []
                for r in rows:
                    if (t := without_reader(r, what)) is None:
                        vanished[name] += not r["right"][0]
                    else:
                        out.append(t)
                books[name] = out
            else:
                books[name] = rows
        trained = [n for n in books if trainable(n)]
        totals = {"trained": [0] * 4, "held out": [0] * 4}
        for name, rows in books.items():
            ps = scored(books, [n for n in trained if n != name], rows, readings)
            group = "held out" if name.split("--")[0] in HELD_OUT else "trained"
            for i, b in enumerate(BUDGETS):
                totals[group][i] += silent_at(rows, ps, int(b * pages[name])) + vanished[name]
        lost = sum(vanished.values())
        print(f"{label:14} silent at 0/.25/.5/1 a page: trained {totals['trained']}, "
              f"held out {totals['held out']}  (layer errors left unchecked: {lost})", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(VARIANTS))
