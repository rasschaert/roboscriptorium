"""A word a book prints once or twice, unknown to the word list, whose OCR-folded form is
a word it prints often:
"Bérrén" beside "Berren", "aIs" beside "als". Flags on the tuning books' latest builds
(`stages/document.json`), scored against their references: a flag on a form the reference
lacks is a catch, on one it has a false alarm. No models.

    uv run python experiments/probe_consistency.py
"""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, ocr
from roboscriptorium.book import Book
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.lexicon import Lexicon

WORD = re.compile(r"\w+(?:[’']\w+)*")
RARE, COMMON = 2, 5
# Accents folded too ("--accents"): Dutch stress accents are the author's, so off by default.
ACCENTS = "--accents" in __import__("sys").argv
FOLDS = [("rn", "m"), ("cl", "d"), ("vv", "w"), ("0", "o"), ("1", "l"), ("I", "l"), ("|", "l")]


def fold(word: str) -> str:
    w = word
    if ACCENTS:
        w = "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")
    w = w[:1] + w[1:].replace("I", "l")
    w = w.lower()
    for a, b in FOLDS:
        w = w.replace(a.lower(), b)
    return w


total = Counter()
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    book = Book.load(Path("work") / name)
    doc = json.loads((book.stages / "document.json").read_text())
    text = " ".join(b.get("text") or "" for b in doc["blocks"])
    ref = " ".join(p for ch in load_chapters(Golden.load(book.golden).text_dir) for p in ch.paragraphs)
    ref_words = Counter(WORD.findall(ref))
    known = Lexicon.load(ocr.language(book.language)).knows
    counts = Counter(WORD.findall(text))
    by_fold: dict[str, list[str]] = {}
    for w in counts:
        by_fold.setdefault(fold(w), []).append(w)
    catches, alarms = [], []
    for w, n in counts.items():
        if n > RARE or len(w) < 2 or known(w):
            continue
        rivals = [v for v in by_fold[fold(w)] if v != w and counts[v] >= COMMON and v.lower() != w.lower()]
        if not rivals:
            continue
        rival = max(rivals, key=counts.get)
        (alarms if ref_words[w] else catches).append(f"{w}×{n}→{rival}×{counts[rival]}")
    total["catch"] += len(catches)
    total["alarm"] += len(alarms)
    print(f"{name[:30]:30} catches {len(catches):3}  alarms {len(alarms):3}  {catches[:6]}  | {alarms[:4]}")
print(dict(total))
