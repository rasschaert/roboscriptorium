"""The line-role model (`sorter.py`): its labelled lines, its score against the rules
leaving one book out, and with `--save` the model the pipeline uses (ROBO_SORTER=1).

Labels come from `golden.align` (body, heading, other) on the bench's tuning and
validation slices and two more golden books; features from a build with the rules'
roles (ROBO_SORTER=0), never the trees' own. Validation books are scored by trees
trained without any of them and never trained on; first-look books are never touched.
Lines are cached per book in work/probes/sorter/ (`sorterdata.lines`).

    uv run python experiments/train_sorter.py [--rebuild] [--save]
    ROBO_PAGE_ROLES=1 uv run python experiments/train_sorter.py [--without-pages]

With ROBO_PAGE_ROLES=1 the lines carry the read model's page roles (`pageroles.py`, asked
where not cached); `--without-pages` drops them again, for the same lines scored both ways.
"""

import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import sorter
from roboscriptorium.config import Settings
from roboscriptorium.sorterdata import SPECS, VALIDATION, fit, lines, models_to_save, predict


def errors(truth: list[str], pred: list[str]) -> str:
    wrong = sum(t != p for t, p in zip(truth, pred, strict=True))
    lost = sum(t == "body" and p != "body" for t, p in zip(truth, pred, strict=True))
    head = sum(t == p == "heading" for t, p in zip(truth, pred, strict=True))
    spurious = sum(p == "heading" != t for t, p in zip(truth, pred, strict=True))
    return (
        f"errors {wrong:4}  body lost {lost:3}  headings {head}/{truth.count('heading')}"
        f" (+{spurious})"
    )


if __name__ == "__main__":
    books = {s.split(":")[0]: lines(s, "--rebuild" in sys.argv) for s in SPECS}
    if "--without-pages" in sys.argv:
        for rows in books.values():
            for r in rows:
                r["f"] = {k: v for k, v in r["f"].items() if k not in sorter.PAGE_FEATURES}
    trainable = [b for b in books if b not in VALIDATION]
    if "--save" in sys.argv:
        for out, model in models_to_save(books, Path(Settings.from_env().sorter_model)):
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
