"""Can a vision judge settle the italic trees' disagreements? A sample of the words two
tree sets disagree on (`italic_disagree.py`), each shown as its whole line with the word
named, asked of a judge "is it italic?", scored against the reference beside both trees.
Answers are cached in work/probes/italic-judge/, so a rerun asks only new words.

    uv run python experiments/italic_judge_probe.py <old dir> <new dir> [judge] [per group]
"""

import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import bench, italics, pipeline
from roboscriptorium.book import Book
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.roles import DecisionCache

OUT = Path("work/probes/italic-judge")
WORDS = Path("work/probes/italic-words")
old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])
judge = sys.argv[3] if len(sys.argv) > 3 else "clef:27b"
per_group = int(sys.argv[4]) if len(sys.argv) > 4 else 50
settings = Settings.from_env()
client = decide.for_model(judge, settings.ollama_url)
OUT.mkdir(parents=True, exist_ok=True)
cache = DecisionCache(OUT / "decisions.jsonl")

apart = []
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    if not (WORDS / f"{name}.jsonl").exists():
        continue
    rows = [json.loads(line) for line in open(WORDS / f"{name}.jsonl")]
    picks = []
    for d in (old_dir, new_dir):
        trees = italics.load(italics.without(d / "italics.pkl", name))
        X = np.array([[r[k] for k in trees.features] for r in rows], dtype=float)
        picks.append(trees.model.predict_proba(X)[:, 1] >= italics.ITALIC_P)
    for r, o, n in zip(rows, *picks, strict=True):
        if o != n:
            apart.append((spec, r, bool(o), bool(n)))
random.seed(0)
bananen = [a for a in apart if a[0].startswith("het-geluid-van-bananen")]
others = [a for a in apart if not a[0].startswith("het-geluid-van-bananen")]
sample = random.sample(bananen, min(per_group, len(bananen))) + random.sample(
    others, min(per_group, len(others))
)

pages_of: dict[str, dict] = {}
results = []
for spec, r, old, new in sample:
    name = spec.split(":")[0]
    if name not in pages_of:
        # A copy-on-write clone of the book: a run in flight may be writing its caches.
        copy = OUT / "books" / name
        if not copy.exists():
            copy.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["cp", "-cR", f"work/{name}", str(copy)], check=True)
        book = Book.load(copy)
        st = pipeline.run(book, pages=scoring.page_range((spec.split(":") + [""])[1] or None),
                          settings=bench.unseen(settings, name))  # fmt: skip
        pages_of[name] = (book, {p.number: p for p in st.pages})
    book, pages = pages_of[name]
    line = pages[r["page"]].lines[r["line"]]
    words = line.text.split(" ")
    if r["i"] >= len(words) or not words[r["i"]]:
        continue
    with pymupdf.open(book.source) as doc:
        clip = pymupdf.Rect(line.x0 - 4, line.y0 - 4, line.x1 + 4, line.y1 + 4)
        png = doc[r["page"] - 1].get_pixmap(matrix=pymupdf.Matrix(4, 4), clip=clip).tobytes("png")
    word = words[r["i"]]
    state = {"page": r["page"], "line": r["line"], "i": r["i"], "word": word, "book": name}
    question = {
        "italic": decide.choice(
            f"The image is a line cut from a scanned printed book. Is the word ⟨{word}⟩ in "
            "it set in italic type (slanted letters), or upright like ordinary text?",
            {"italic": "the word is set in italics", "upright": "the word is set upright"},
        )
    }
    key = DecisionCache.key(judge, question, state)
    answer = cache.get(key)
    if answer is None:
        a = client.decide(state, question, image_png=png)["italic"]
        answer = {"value": a.value, "confidence": a.confidence}
        cache.put(key, answer)
    said = answer["value"] == "italic"
    results.append((name, word, r["label"], old, new, said, answer["confidence"]))

for group, keep in (
    ("bananen", lambda n: n.startswith("het-geluid")),
    ("others", lambda n: not n.startswith("het-geluid")),
):
    rs = [x for x in results if keep(x[0])]
    if not rs:
        continue
    right = lambda k: sum(x[k] == x[2] for x in rs)  # noqa: E731
    print(
        f"{group}: {len(rs)} words, right: old trees {right(3)}, new trees {right(4)}, {judge} {right(5)}"
    )
wrong = [x for x in results if x[5] != x[2]]
print(f"{judge} wrong on {len(wrong)}:")
for x in wrong[:20]:
    print(
        f"  {x[0][:22]:22} {x[1]!r:20} print {'italic' if x[2] else 'upright'}, said {'italic' if x[5] else 'upright'} ({x[6]:.2f})"
    )
