"""The accent-zone fit as a judge of any small difference: two versions of a place drawn in
the book's typeface, the scan scored only where the drawings differ (`probe_accent_fit
.measures`, both ways). On the trust data's settled places with two versions, one of them
the print, of the same length or one a single character longer at either end (a speck read
as a comma, a mark over a letter, a letter for another): a logistic model on the two
cosines and ink shares, fitted on the other books, picks a version. Its picks beside each
judge's vote there, by kind of difference, and the places every judge got wrong that it
rights. No models.

    PYTHONPATH=experiments uv run python experiments/probe_zone_judge.py
"""

import json
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import pymupdf
from probe_accent_fit import measures
from sklearn.linear_model import LogisticRegression

from roboscriptorium import pipeline, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.trustdata import SPECS, rows_of, usable

OUT = Path("work/probes/zone-judge.jsonl")


def strip(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


def kind(a: str, b: str) -> str | None:
    if len(a) == len(b):
        diff = [(x, y) for x, y in zip(a, b, strict=True) if x != y]
        if len(diff) > 2:
            return None
        if all(strip(x) == strip(y) for x, y in diff):
            return "mark"
        if all(x.lower() == y.lower() for x, y in diff):
            return "case"
        if all(not x.isalnum() and not y.isalnum() for x, y in diff):
            return "punctuation"
        return "letter"
    long, short = (a, b) if len(a) > len(b) else (b, a)
    if len(long) - len(short) == 1 and (long.startswith(short) or long.endswith(short)):
        extra = long[-1] if long.startswith(short) else long[0]
        return "punctuation added" if not extra.isalnum() else None
    return None


def main():
    settings = Settings.from_env()
    done = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            row = json.loads(line)
            done.setdefault(row["book"], []).append(row)
    for name in [n for n in SPECS if not usable(n, settings)]:
        if name in done:
            continue
        book = Book.load(Path("work") / name)
        layer = cached_text_layer(book.source, book.stages / "textlayer.json")
        body = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
        judge = pipeline._alarm("render", settings, book, body)
        if judge is None:
            continue
        texts = {p.number: p for p in layer}
        rows = []
        with pymupdf.open(book.source) as doc:
            for r in rows_of(name, settings):
                s = r["s"]
                versions = [s.ours, *s.others]
                if len(versions) != 2 or sum(r["right"]) != 1:
                    continue
                k = kind(*versions)
                if k is None or not versions[0].strip() or not versions[1].strip():
                    continue
                ink = rendercheck.place_ink(doc[s.page - 1], s.box, texts.get(s.page))
                if ink is None:
                    continue
                a = measures(judge._face, judge._match, ink, versions[0], versions[1])
                b = measures(judge._face, judge._match, ink, versions[1], versions[0])
                zero = {"cosine": 0.0, "mass": 0.0, "stray": 0.0}
                a, b = a or zero, b or zero
                votes = {m: versions.index(v) for m, v in s.votes.items() if v in versions}
                rows.append({
                    "book": name, "page": s.page, "versions": versions, "right": int(r["right"][1]), "kind": k,
                    "x": [a["cosine"], a["mass"], a["stray"], b["cosine"], b["mass"], b["stray"]], "votes": votes,
                })  # fmt: skip
        with OUT.open("a") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[name] = rows
        print(f"{name}: {len(rows)} places", flush=True)
    rows = [r for rs in done.values() for r in rs]
    X = np.array([r["x"] for r in rows])
    y = np.array([r["right"] for r in rows])
    books = np.array([r["book"] for r in rows])
    pick = np.zeros(len(rows), int)
    sure = np.zeros(len(rows))
    for b in set(books):
        held = books == b
        p = LogisticRegression(max_iter=2000).fit(X[~held], y[~held]).predict_proba(X[held])[:, 1]
        pick[held], sure[held] = p > 0.5, np.abs(p - 0.5) * 2
    judges = sorted({m for r in rows for m in r["votes"]})
    print(f"{len(rows)} places")
    print(f"{'kind':18} {'places':>6} {'zone':>6} " + " ".join(f"{m[:14]:>14}" for m in judges))
    for k in [*sorted({r["kind"] for r in rows}), None]:
        idx = [i for i, r in enumerate(rows) if k is None or r["kind"] == k]
        cells = []
        for m in judges:
            voted = [i for i in idx if m in rows[i]["votes"]]
            cells.append(f"{sum(rows[i]['votes'][m] == y[i] for i in voted):>7}/{len(voted):<6}")
        print(f"{k or 'all':18} {len(idx):>6} {int((pick[idx] == y[idx]).sum()):>6} " + " ".join(cells))
    vision = [m for m in judges if m != "word list"]
    lost = [i for i, r in enumerate(rows) if all(r["votes"].get(m, 1 - y[i]) != y[i] for m in vision)]
    print(f"every judge wrong on {len(lost)} places; the zone fit rights {int((pick[lost] == y[lost]).sum())}, by kind {dict(Counter(rows[i]['kind'] for i in lost if pick[i] == y[i]))}")
    strong = sure > 0.8
    print(f"zone fit sure (over 0.9): {int(strong.sum())} places, right on {int((pick[strong] == y[strong]).sum())}")


if __name__ == "__main__":
    main()
