"""The learned decision on line-end hyphens the book and the word list leave undecided
(`hyphens.Learned`): trained on the breaks each tuning book's build asked its judges about
(`stages/compounds.json`, each judge's chance kept), with the book's own signs
(`hyphens.features`, from the text layer over the body, as the build has them) and the
reference's spelling as the label, where it spells the word one way only. No models.

Scored leaving each book out against the judges' mean and production (Dutch joins,
English asks clef alone); `--save` writes the decision trained on every book and a copy
without each, for the bench.

    uv run python experiments/train_hyphens.py [--cut 0.8] [--save work/models/hyphens.pkl]
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import bench, hyphens, ocr
from roboscriptorium.book import Book
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import cached_text_layer

JUDGES = ("clef:27b", "autotrust-jev:35b-nvfp4", "d3:9b", "autotrust-jev:9b-nvfp4")
W = re.compile(r"[^\w-]")


def fresh() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_depth=3, min_samples_leaf=5, class_weight="balanced", random_state=0
    )


def rows_of(spec: str) -> tuple[list[dict], int]:
    """A tuning book's labelled breaks, and how many asked breaks lacked a judge's chance."""
    name = spec.split(":")[0]
    book = Book.load(Path("work") / name)
    path = book.stages / "compounds.json"
    if not path.exists():
        return [], 0
    partial = json.loads(path.read_text()).get("partial", {})
    lang = ocr.language(book.language)
    first, last = book.body_pages
    whole = [
        p
        for p in cached_text_layer(book.source, book.stages / "textlayer.json", lang)
        if first <= p.number <= last
    ]
    signs = hyphens.book_signs(whole, book.language)
    lexicon = Lexicon.load(lang)
    known = lexicon.knows if lexicon is not None else None
    reference = load_chapters(Golden.load(book.golden).text_dir)
    words = Counter(
        W.sub("", w).lower() for ch in reference for para in ch.paragraphs for w in para.split()
    )
    # The break's own letters, case kept, from the layer's lines.
    cased = {}
    lines = [ln.text for p in whole for ln in p.lines]
    for text, nxt in zip(lines, lines[1:], strict=False):
        if text.endswith(hyphens.HYPHENS) and nxt.split():
            stem, rest = W.sub("", text.split()[-1][:-1]), W.sub("", nxt.split()[0])
            cased.setdefault(f"{stem}-{rest}".lower(), (stem, rest))
    out, unheard = [], 0
    for key, chances in partial.items():
        if not all(j in chances for j in JUDGES):
            unheard += 1
            continue
        stem, rest = cased.get(key, tuple(key.split("-", 1)))
        h, c = words[key], words[key.replace("-", "", 1)]
        if bool(h) == bool(c):
            continue
        x = hyphens.features(stem, rest, signs, known) + [chances[j] for j in JUDGES]
        out.append({"book": name, "lang": book.language[:2], "word": key, "x": x, "y": bool(h)})
    return out, unheard


def main(args: list[str]) -> None:
    cut = float(args[args.index("--cut") + 1]) if "--cut" in args else 0.8
    save = Path(args[args.index("--save") + 1]) if "--save" in args else None
    rows = []
    for spec in bench.SETS["tuning"]:
        got, unheard = rows_of(spec)
        print(f"{spec.split(':')[0]}: {len(got)} labelled breaks, {unheard} without every judge")
        rows += got
    if not rows:
        print("no labelled breaks: run a build with every judge first (ROBO_HYPHEN_JUDGES)")
        return
    X = np.array([r["x"] for r in rows])
    y = np.array([r["y"] for r in rows])
    books = np.array([r["book"] for r in rows])
    langs = np.array([r["lang"] for r in rows])
    p = np.zeros(len(rows))
    for b in sorted(set(books)):
        held = books == b
        p[held] = fresh().fit(X[~held], y[~held]).predict_proba(X[held])[:, 1]
    chances = X[:, -len(JUDGES) :]
    mean, clef = chances.mean(axis=1), chances[:, 0]
    for lang in ("nl", "en"):
        m = langs == lang
        if not m.any():
            continue
        production = (clef[m] >= 0.5) if lang == "en" else np.zeros(m.sum(), bool)
        print(
            f"{lang}: {int(m.sum())} breaks, the hyphen kept by the print in {int(y[m].sum())}; "
            f"wrong: production {int((production != y[m]).sum())}, "
            f"the judges' mean {int(((mean[m] >= 0.5) != y[m]).sum())}, "
            f"learned at {cut} {int(((p[m] >= cut) != y[m]).sum())} "
            f"(kept wrongly {int(((p[m] >= cut) & ~y[m]).sum())}, "
            f"dropped wrongly {int(((p[m] < cut) & y[m]).sum())})"
        )
    if save is None:
        return
    hyphens.save_learned(save, fresh().fit(X, y), JUDGES, cut)
    for b in sorted(set(books)):
        held = books == b
        hyphens.save_learned(
            hyphens.without(save, b), fresh().fit(X[~held], y[~held]), JUDGES, cut
        )
    print(f"saved {save} and {len(set(books))} copies without a book")


if __name__ == "__main__":
    main(sys.argv[1:])
