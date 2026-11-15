"""The accent measure reworked: the scan against both drawings where they differ, either
way (`probe_accent_first_vowel.differ_fit`), beside the mark's own fit (`cosine`, today's),
on the labelled rows of `probe_missed_accents.py` (dropped marks of the tuning bench and
500 plain words a book). Results kept per row in work/probes/accent-differ.jsonl. No models.

    PYTHONPATH=experiments uv run python experiments/probe_accent_differ.py
"""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from probe_accent_first_vowel import differ_fit
from sklearn.metrics import roc_auc_score

from roboscriptorium import pipeline, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/accent-differ.jsonl")


def main():
    rows = [json.loads(line) for line in Path("work/probes/missed-accents.jsonl").read_text().splitlines()]
    done = [json.loads(line) for line in OUT.read_text().splitlines()] if OUT.exists() else []
    have = {r["book"] for r in done}
    by = defaultdict(list)
    for r in rows:
        by[r["book"]].append(r)
    settings = Settings.from_env()
    for name, mine in by.items():
        if name in have:
            continue
        book = Book.load(Path("work") / name)
        layer = cached_text_layer(book.source, book.stages / "textlayer.json")
        body = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
        texts = {p.number: p for p in layer}
        judge = pipeline._alarm("render", settings, book, body)
        out = []
        with pymupdf.open(book.source) as doc:
            for r in mine:
                ink = rendercheck.place_ink(doc[r["page"] - 1], r["box"], texts.get(r["page"]))
                d = None if ink is None else differ_fit(judge._face, judge._match, ink, r["marked"], r["word"])
                out.append({**r, "differ": d})
        with OUT.open("a") as f:
            for r in out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        done += out
        print(f"{name}: {len(out)} rows", flush=True)
    rows = [r for r in done if r["differ"] is not None]
    y = np.array([r["print_marked"] for r in rows])
    has_i = np.array(["í" in r["marked"].lower() for r in rows])
    for label, pick in (("every row", np.ones(len(rows), bool)), ("the mark on an i", has_i), ("the mark on another vowel", ~has_i)):
        print(f"{label}: {int((y & pick).sum())} dropped marks, {int((~y & pick).sum())} plain words")
        for k in ("cosine", "differ"):
            x = np.array([r[k] for r in rows])
            line = f"   {k:7} AUC {roc_auc_score(y[pick], x[pick]):.3f};"
            for rate in (0.01, 0.0025, 0.001):
                cut = np.quantile(x[~y & pick], 1 - rate)
                line += f" at {rate:.2%} false offers finds {int((x[y & pick] > cut).sum())};"
            print(line)


if __name__ == "__main__":
    main()
