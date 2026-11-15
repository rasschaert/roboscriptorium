"""Line-end hyphens the book's spellings and the word list leave undecided: a learned
decision from what the book itself shows (how often it hyphenates, whether the stem opens
or the rest closes other hyphenated words in it, how often each stands alone, a vowel
clash, the word list on the parts), with and without clef's cached answer
(`probe_hyphen_judge.py`). Each tuning book decided by a model fitted on the others;
errors beside the default (the break's hyphen dropped) and clef alone. No models.

    uv run python experiments/probe_hyphen_learned.py
"""

import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import bench, hyphens, ocr
from roboscriptorium.book import Book
from roboscriptorium.golden import scoring
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import cached_text_layer

W = re.compile(r"[^\w-]")
clef = {}
path = Path("work/probes/hyphen-judge/clef_27b.jsonl")
if path.exists():
    for line in path.read_text().splitlines():
        r = json.loads(line)
        clef[(r["closed"], r["context"])] = r["p_hyph"]

items = []
for spec in bench.SETS["tuning"]:
    name, pages, _ = (spec.split(":") + ["", ""])[:3]
    book = Book.load(Path("work") / name)
    first, last = scoring.page_range(pages or None) or book.body_pages
    lang = ocr.language(book.language)
    layer = [p for p in cached_text_layer(book.source, book.stages / "textlayer.json", lang) if first <= p.number <= last]
    seen = hyphens.spellings(layer)
    lex = Lexicon.load(lang)
    ref = load_chapters(Golden.load(book.golden).text_dir)
    words = Counter(W.sub("", w).lower() for ch in ref for para in ch.paragraphs for w in para.split())
    lines = [line.text for p in layer for line in p.lines]
    tokens = [W.sub("", w).lower() for text in lines for w in text.split()[:-1]]
    alone = Counter(tokens)
    inline = [t for t in set(tokens) if "-" in t.strip("-")]
    opens = Counter(t.split("-")[0] for t in inline)
    closes = Counter(t.split("-")[-1] for t in inline)
    habit = 10_000 * sum(alone[t] for t in inline) / max(1, len(tokens))
    for i, (text, nxt) in enumerate(zip(lines, lines[1:])):
        if not (text.endswith(hyphens.HYPHENS) and len(text) > 1 and text[-2].isalpha()):
            continue
        stem = W.sub("", text.split()[-1][:-1])
        rest = W.sub("", nxt.split()[0]) if nxt.split() else ""
        if not stem or not rest or not nxt[:1].islower() or "-" in stem + rest:
            continue
        closed, hyph = stem + rest, f"{stem}-{rest}"
        if seen[hyph.lower()] != seen[closed.lower()] or lex.knows(hyph) != lex.knows(closed):
            continue
        h, c = words[hyph.lower()], words[closed.lower()]
        if bool(h) == bool(c):
            continue
        sentence = " ".join([*lines[max(0, i - 1) : i], text[:-1] + "|" + nxt, *lines[i + 2 : i + 3]])
        x = [
            float(book.language[:2] == "en"), len(stem), len(rest), float(lex.knows(stem)), float(lex.knows(rest)),
            float(lex.knows(closed)), float(hyphens.vowel_clash(stem, rest)), habit, opens[stem.lower()],
            closes[rest.lower()], np.log1p(alone[stem.lower()]), np.log1p(alone[rest.lower()]),
            float(stem.lower().endswith("s")), float(stem[:1].isupper()),
        ]  # fmt: skip
        items.append({"book": name, "lang": book.language[:2], "word": hyph, "truth": bool(h), "x": x,
                      "clef": clef.get((closed, sentence), np.nan)})  # fmt: skip
    print(name, flush=True)

y = np.array([i["truth"] for i in items])
books = np.array([i["book"] for i in items])
langs = np.array([i["lang"] for i in items])
print(f"{len(items)} undecided breaks; keep the hyphen: {dict(Counter((i['lang'], i['truth']) for i in items))}")
for label, extra in (("the book's own signs", False), ("with clef's answer", True)):
    X = np.array([i["x"] + ([i["clef"]] if extra else []) for i in items])
    p = np.zeros(len(items))
    for b in set(books):
        held = books == b
        model = HistGradientBoostingClassifier(max_depth=3, min_samples_leaf=5, class_weight="balanced", random_state=0)
        p[held] = model.fit(X[~held], y[~held]).predict_proba(X[held])[:, 1]
    for lang in ("nl", "en"):
        m = langs == lang
        for cut in (0.5, 0.8):
            keep = p[m] >= cut
            print(f"  {label:22} {lang} at {cut}: wrong {int((keep != y[m]).sum())} of {int(m.sum())} "
                  f"(kept wrongly {int((keep & ~y[m]).sum())}, dropped wrongly {int((~keep & y[m]).sum())})")  # fmt: skip
for lang in ("nl", "en"):
    m = langs == lang
    c = np.array([i["clef"] for i in items])[m]
    print(f"  default (drop) {lang}: wrong {int(y[m].sum())} of {int(m.sum())}; clef alone at 0.5: wrong {int(((c >= 0.5) != y[m]).sum())}")
