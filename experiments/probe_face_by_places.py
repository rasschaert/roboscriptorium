"""Render and compare: is a book's typeface better chosen by its places than by its word
shapes (the checklist, "New tactics to make it better")? The best few text cuts of the
font match each judge a sample of the book's labelled suspects; per face, how often its
pick is the print, and three signals a build has without labels: how often it agrees
with the model judges where they are of one mind, its mean margin, and how well its
best version lies over the ink. No models.

    uv run python experiments/probe_face_by_places.py <book> [more …]
    uv run python experiments/probe_face_by_places.py --report

Reads work/probes/font-match/<book>.json (the ranking) and the trust data; writes
work/probes/face-by-places/<book>.json.
"""

import json
import random
import sys
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import ocr, pdf, rendercheck, trustdata
from roboscriptorium.book import Book
from roboscriptorium.config import Settings

OUT = Path("work/probes/face-by-places")
RANKED = Path("work/probes/font-match")
FACES = 5
PLACES = 400
MODELS = ("clef:27b", "autotrust-jev:35b-nvfp4", "d3:9b")


def candidates(name: str) -> list[dict]:
    """The match's best text cuts, one a family and weight, best first."""
    ranked = json.loads((RANKED / f"{name}.json").read_text())["ranked"]
    kept = []
    while ranked and len(kept) < FACES:
        entry = rendercheck.text_cut(ranked)
        kept.append(entry)
        ranked = [e for e in ranked if e is not entry]
        if rendercheck.text_cut([entry, *ranked]) is not entry:
            break  # only heavy or italic cuts left
    return kept


def probe(name: str) -> dict:
    book = Book.load(Path("work") / name)
    layer = pdf.cached_text_layer(
        book.source, book.stages / "textlayer.json", ocr.language(book.language)
    )
    first, last = book.body_pages
    body = [p for p in layer if first <= p.number <= last]
    texts = {p.number: p for p in body}
    library = Path(Settings.from_env().fonts)
    rows = [r for r in trustdata.load(name) if r["settled"] and sum(r["right"]) == 1]
    rows = random.Random(0).sample(rows, min(PLACES, len(rows)))
    inks = []
    with pdf.PDF_LOCK, pymupdf.open(book.source) as doc:
        for r in rows:
            s = r["suspect"]
            inks.append(rendercheck.place_ink(doc[s["page"] - 1], s["box"], texts.get(s["page"])))
    words = rendercheck.scan_words(book.source, body, 80)
    faces = []
    for entry in candidates(name):
        path = library / entry["file"]
        face = rendercheck.Face.from_file(path)
        size = rendercheck.em_size(words, face.at())
        picks = []
        for r, ink in zip(rows, inks):
            if ink is None:
                picks.append(None)
                continue
            s = r["suspect"]
            versions = [s["ours"], *s["others"]]
            scores = rendercheck.fits(face, entry["spread"], size, ink, versions)
            order = np.argsort(scores)[::-1]
            picks.append(
                {
                    "pick": int(order[0]),
                    "margin": float(scores[order[0]] - scores[order[1]]),
                    "fit": float(scores[order[0]]),
                }
            )
        faces.append({**entry, "size": size, "picks": picks})
        print(f"{name}: {entry['name']} done", flush=True)
    meta = []
    for r in rows:
        s = r["suspect"]
        versions = [s["ours"], *s["others"]]
        votes = {s["votes"].get(m) for m in MODELS}
        agreed = votes.pop() if len(votes) == 1 else None
        meta.append(
            {
                "right": r["right"].index(True),
                "agreed": versions.index(agreed) if agreed in versions else None,
            }
        )
    out = {"book": name, "rows": meta, "faces": faces}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(out))
    return out


def summary(face: dict, rows: list[dict]) -> dict:
    seen = [(p, r) for p, r in zip(face["picks"], rows) if p is not None]
    one = [(p, r) for p, r in seen if r["agreed"] is not None]
    split = [(p, r) for p, r in seen if r["agreed"] is None]

    def share(pairs, key):
        return sum(p["pick"] == r[key] for p, r in pairs) / len(pairs) if pairs else float("nan")

    return {
        "name": face["name"],
        "word fit": face["fit"],
        "right": share(seen, "right"),
        "right, judges split": share(split, "right"),
        "split": len(split),
        "agrees": share(one, "agreed"),
        "margin": float(np.mean([p["margin"] for p, _ in seen])) if seen else 0.0,
        "place fit": float(np.mean([p["fit"] for p, _ in seen])) if seen else 0.0,
    }


def report() -> None:
    totals = {k: [] for k in ("word fit", "agrees", "margin", "place fit", "best")}
    for path in sorted(OUT.glob("*.json")):
        data = json.loads(path.read_text())
        faces = [summary(f, data["rows"]) for f in data["faces"]]
        print(f"\n{data['book']} ({len(data['rows'])} places)")
        for f in faces:
            print(
                f"  {f['name'][:34]:34} words {f['word fit']:.3f}  right {f['right']:.1%}"
                f"  split {f['right, judges split']:.1%} of {f['split']:3}"
                f"  agrees {f['agrees']:.1%}  margin {f['margin']:.3f}  place {f['place fit']:.3f}"
            )
        for key in ("word fit", "agrees", "margin", "place fit"):
            totals[key].append(max(faces, key=lambda f: f[key])["right"])
        totals["best"].append(max(f["right"] for f in faces))
    print(f"\nmean share right over {len(totals['best'])} books, the face chosen by:")
    for key, shares in totals.items():
        print(f"  {key:10} {np.mean(shares):.1%}   worst book {min(shares):.1%}")


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        for name in sys.argv[1:]:
            probe(name)
