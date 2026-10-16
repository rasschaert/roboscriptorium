"""An unknown word whose accented variant the word list knows ("intuitief" → "intuïtief"):
a lost accent every reading shares? No models: the bench's builds from cache; each such
word is an error where the reference prints the variant, right where it prints the word.

    uv run python experiments/probe_accent_variants.py
"""

import re
import unicodedata
from collections import Counter, defaultdict

from roboscriptorium import bench
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.golden.reference import unmarked
from roboscriptorium.ir import Paragraph
from roboscriptorium.lexicon import Lexicon

WORD = re.compile(r"[^\W\d_]+")


def bare(w: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", w) if not unicodedata.combining(c))


tally: Counter = Counter()
for set_name in ("tuning", "validation"):
    for spec in bench.SETS[set_name]:
        name = spec.split(":")[0]
        run = scoring.build(f"work/{spec}", bench.unseen(Settings.from_env(), name))
        lang = "nld" if run.book.language == "nl" else "eng"
        lex = Lexicon.load(lang)
        accented = defaultdict(set)
        for w in lex.words:
            if bare(w) != w:
                accented[bare(w)].add(w)
        ref = Counter(w.lower() for ch in run.reference for p in ch.paragraphs for w in WORD.findall(unmarked(p)))
        out = [w for b in run.stages.doc.blocks if isinstance(b, Paragraph) for w in WORD.findall(b.text)]
        for w in set(out):
            lw = w.lower()
            if lex.knows(lw) or bare(lw) != lw or lw not in accented:
                continue
            variants = accented[lw]
            if ref[lw]:
                tally[set_name, "right as printed"] += 1
            elif any(ref[v] for v in variants):
                tally[set_name, "ERROR (reference has the variant)"] += 1
                print(f"  {name[:22]} {w!r} → {sorted(v for v in variants if ref[v])}")
            else:
                tally[set_name, "neither"] += 1
for k in sorted(tally):
    print(f"{tally[k]:5}  {k[0]:10} {k[1]}")
