"""The book's own vocabulary as an arbiter feature (the user's idea, 2026-11-08): for each
version of a suspect, how often the book prints its words elsewhere. Two arbiters trained
side by side on the same held-out folds as `train_ocr_trust.py` (each book scored by trees
trained on the other trainable books), today's features against today's plus the vocabulary
columns; silent errors at the fixed rule's number of questions, per book and in total.
No models; reads the trust data (`ROBO_TRUST_DATA`) and each book's cached text layer.

    PYTHONPATH=experiments uv run python experiments/probe_book_vocab.py
"""

import json
import math
import os
import re
import unicodedata
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import trust
from roboscriptorium.config import Settings
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.trustdata import SPECS, rows_of, seats, trainable, usable, weighed

SETTINGS = Settings.from_env()
READINGS, SEATS = weighed(SETTINGS), seats(SETTINGS)
_TOKEN = re.compile(r"[^\w'’-]+")
# VOCAB_WORDS=1: the columns only where the versions are different words, not the same word
# with other accents, case or marks ("zíjn" against "zijn" stays blank).
WORDS_ONLY = os.environ.get("VOCAB_WORDS") == "1"
# VOCAB_CONTROL=1: random columns in their place, the churn any three extra columns cause.
CONTROL = os.environ.get("VOCAB_CONTROL") == "1"
# VOCAB_KNOWN=1: one column instead, whether every word of the version is known to the word
# list or printed at least BOOK_KNOWN times by the book ("Númenor", "Mikael"); blank where
# the versions are the same word with other accents, case or marks.
KNOWN = os.environ.get("VOCAB_KNOWN") == "1"
BOOK_KNOWN = 3
_LEXICON = {}


def _folded(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in plain if c.isalpha())


def vocabulary(book: str) -> Counter:
    """How often the book's text layer prints each word, lower-cased, edge marks off."""
    path = Path("work") / book / "stages" / "text-layer.json"
    counts: Counter = Counter()
    for page in json.loads(path.read_text())["pages"]:
        for line in page["lines"]:
            for w in _TOKEN.split(line["text"].lower()):
                if w := w.strip("'’-"):
                    counts[w] += 1
    return counts


def vocab_features(s, k: int, counts: Counter) -> list[float]:
    """For version k: its rarest word's count in the book (log), the same for the text
    layer's version, and the difference: a version whose words the book prints often."""
    versions = [s.ours, *s.others]
    if WORDS_ONLY and len({_folded(v) for v in versions}) == 1:
        return [math.nan] * 3

    def rarest(text: str) -> float:
        words = [w.strip("'’-") for w in _TOKEN.split(text.lower())]
        words = [w for w in words if w]
        return min((math.log1p(counts[w]) for w in words), default=0.0)

    if KNOWN:
        if len({_folded(v) for v in versions}) == 1:
            return [math.nan]
        lang = "nld" if s_lang(counts) == "nl" else "eng"
        if lang not in _LEXICON:
            _LEXICON[lang] = Lexicon.load(lang)
        words = [w for w in _TOKEN.split(versions[k]) if w.strip("'’-") and _folded(w)]
        return [float(all(_LEXICON[lang].knows(w) or counts[w.lower().strip("'’-")] >= BOOK_KNOWN for w in words))]
    if CONTROL:
        rng = np.random.default_rng(zlib.crc32(f"{versions[0]}|{versions[k]}|{k}".encode()))
        mine, layer = rng.uniform(0, 8, 2)
        return [mine, layer, mine - layer]
    mine, layer = rarest(versions[k]), rarest(versions[0])
    return [mine, layer, mine - layer]


def s_lang(counts: Counter) -> str:
    """The book's language from its commonest words."""
    return "nl" if counts["de"] + counts["het"] > counts["the"] + counts["and"] else "en"


def silent_at(rows, ps, n: int) -> int:
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
    return sum(wrong for _, wrong in order[n:])


def rule(rows) -> tuple[int, int]:
    silent = asked = 0
    for r in rows:
        s = r["s"]
        if s.choice == "review":
            asked += 1
        else:
            k = 0 if s.choice == "ours" else 1 + s.others.index(s.chosen)
            silent += not r["right"][k]
    return silent, asked


def train_matrix(train_rows, vocab, extra: bool):
    suspects = [r["s"] for r in train_rows]
    right = [r["right"] for r in train_rows]
    names = [r["book"] for r in train_rows]
    X, y = trust.training_matrix(suspects, right, names, READINGS, SEATS)
    if not extra:
        return X, y
    cols = []
    for book in dict.fromkeys(names):
        for r in train_rows:
            if r["book"] == book:
                cols += [vocab_features(r["s"], k, vocab[book]) for k in range(len(r["right"]))]
    return np.hstack([X, np.array(cols)]), y


def scored(train_rows, rows, vocab, extra: bool):
    X, y = train_matrix(train_rows, vocab, extra)
    pairs = trust.pairs_table([r["s"] for r in train_rows], [r["right"] for r in train_rows],
                              [r["book"] for r in train_rows])  # fmt: skip
    Xt, owner = [], []
    for i, r in enumerate(rows):
        for k in range(len(r["right"])):
            f = trust.features(r["s"], k, pairs, READINGS, SEATS)
            Xt.append(f + (vocab_features(r["s"], k, vocab[r["book"]]) if extra else []))
            owner.append(i)
    model = HistGradientBoostingClassifier(max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0)
    probs = model.fit(X, y).predict_proba(np.array(Xt))[:, 1]
    out = [[] for _ in rows]
    for p, i in zip(probs, owner, strict=True):
        out[i].append(p)
    return [np.array(p) / max(sum(p), 1e-9) for p in out]


def main():
    books = {n: rows_of(n, SETTINGS) for n in SPECS if not usable(n, SETTINGS)}
    vocab = {n: vocabulary(n) for n in books}
    totals = Counter()
    changed = []
    print(f"{'book':34} {'rule':>9}  today/+vocab at: the rule's questions, none, half the rule's")
    for name, rows in books.items():
        silent, asked = rule(rows)
        train_rows = [r for n in books if n != name and trainable(n) for r in books[n]]
        pa, pb = scored(train_rows, rows, vocab, False), scored(train_rows, rows, vocab, True)
        cells = []
        for label, n in (("rule's", asked), ("none", 0), ("half", asked // 2)):
            a, b = silent_at(rows, pa, n), silent_at(rows, pb, n)
            totals[f"today@{label}"] += a
            totals[f"+vocab@{label}"] += b
            cells.append(f"{a}/{b}")
        totals["rule"] += silent
        print(f"{name[:34]:34} {silent:4}/{asked:<4}  " + "  ".join(cells))
        for r, x, y in zip(rows, pa, pb, strict=True):
            if int(x.argmax()) != int(y.argmax()):
                v = [r["s"].ours, *r["s"].others]
                changed.append((name, v, v[int(x.argmax())], v[int(y.argmax())], r["right"][int(y.argmax())]))
    print("totals:", dict(totals))
    fixed = [c for c in changed if c[4]]
    print(f"best version changed on {len(changed)} suspects: right now on {len(fixed)}, wrong now on {len(changed) - len(fixed)}")
    for c in changed[:60]:
        print(f"  {'FIXED' if c[4] else 'BROKE'} {c[0][:16]:16} {c[1]}  {c[2]!r} → {c[3]!r}")


if __name__ == "__main__":
    main()
