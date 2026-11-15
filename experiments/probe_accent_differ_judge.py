"""Where readings differ only by an acute ("zijn" against "zíjn"), is the scan against
both drawings where they differ (`probe_accent_first_vowel.differ_fit`) a better judge
than the render judge's whole-word fit? Over the trust data's places of that kind: the
measure for the marked version, scored against the reference beside each judge's vote.
The measure is placed in its book by the plain words of `probe_accent_differ.py`
(work/probes/accent-differ.jsonl). No models.

    PYTHONPATH=experiments uv run python experiments/probe_accent_differ_judge.py
"""

import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from probe_accent_first_vowel import differ_fit
from sklearn.metrics import roc_auc_score

from roboscriptorium import pipeline, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.trustdata import SPECS, rows_of

ACUTES = set("áéíóúÁÉÍÓÚ")


def strip(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


def main():
    settings = Settings.from_env()
    plain = defaultdict(list)
    for line in Path("work/probes/accent-differ.jsonl").read_text().splitlines():
        r = json.loads(line)
        if not r["print_marked"] and r["differ"] is not None:
            plain[r["book"]].append(r["differ"])
    out = []
    for name in SPECS:
        try:
            rows = rows_of(name, settings)
        except Exception as e:
            print(name, "skipped:", e)
            continue
        book = Book.load(Path("work") / name)
        layer = cached_text_layer(book.source, book.stages / "textlayer.json")
        body = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
        texts = {p.number: p for p in layer}
        judge = pipeline._alarm("render", settings, book, body)
        n = 0
        with pymupdf.open(book.source) as doc:
            for r in rows:
                s = r["s"]
                versions = [s.ours, *s.others]
                if len(versions) != 2 or len({strip(v) for v in versions}) != 1 or sum(r["right"]) != 1:
                    continue
                marked = [v for v in versions if ACUTES & set(v) and strip(v) != v]
                bare = [v for v in versions if strip(v) == v]
                if len(marked) != 1 or len(bare) != 1:
                    continue
                ink = rendercheck.place_ink(doc[s.page - 1], s.box, texts.get(s.page))
                d = None if ink is None else differ_fit(judge._face, judge._match, ink, marked[0], bare[0])
                if d is None:
                    continue
                truth = versions[r["right"].index(True)]
                ranks = np.sort(plain.get(name, [0.0]))
                out.append({"book": name, "marked_right": truth == marked[0], "differ": d, "rank": float(np.searchsorted(ranks, d) / len(ranks)), "marked": marked[0], "votes": {m: v == truth for m, v in s.votes.items()}, "settled": r["settled"]})
                n += 1
        print(f"{name}: {n} accent-only places", flush=True)
    Path("work/probes/accent-differ-judge.json").write_text(json.dumps(out, ensure_ascii=False))
    y = np.array([r["marked_right"] for r in out])
    print(f"{len(out)} places, the marked version right at {int(y.sum())}")
    for key in ("differ", "rank"):
        x = np.array([r[key] for r in out])
        best = max(((((x > t) == y).mean()), t) for t in np.unique(x))
        print(f"  {key}: AUC {roc_auc_score(y, x):.3f}; right at its best cut ({best[1]:.2f}) {best[0]:.1%}")
    for cut in (0.9, 0.95, 0.99):
        print(f"  marked where its rank among the book's plain words > {cut}: right {((np.array([r['rank'] for r in out]) > cut) == y).mean():.1%}")
    votes = Counter()
    for r in out:
        for m, ok in r["votes"].items():
            votes[m, "n"] += 1
            votes[m, "right"] += ok
    for m in sorted({k[0] for k in votes}):
        print(f"  {m[:44]:44} right {votes[m, 'right']} of {votes[m, 'n']} ({votes[m, 'right'] / votes[m, 'n']:.1%})")


if __name__ == "__main__":
    main()
