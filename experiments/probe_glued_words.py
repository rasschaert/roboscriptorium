"""Is "an unknown word that splits into two known ones" a sign of a lost space, for a
detector of errors every reading shares? No models: the bench's builds from cache; each
such word in the output is right where the reference prints it whole, an error where it
prints the two words.

    uv run python experiments/probe_glued_words.py
"""

import re
from collections import Counter

from roboscriptorium import bench
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.golden.reference import unmarked
from roboscriptorium.ir import Paragraph
from roboscriptorium.lexicon import Lexicon

WORD = re.compile(r"[^\W\d_]+(?:[’'][^\W\d_]+)?")
tally: Counter = Counter()
for set_name in ("tuning", "validation"):
    for spec in bench.SETS[set_name]:
        name = spec.split(":")[0]
        run = scoring.build(f"work/{spec}", bench.unseen(Settings.from_env(), name))
        lex = Lexicon.load("nld" if run.book.language == "nl" else "eng")
        ref = " ".join(unmarked(p) for ch in run.reference for p in ch.paragraphs).lower()
        ref_words = Counter(WORD.findall(ref))
        out = [b.text for b in run.stages.doc.blocks if isinstance(b, Paragraph)]
        seen = set()
        for text in out:
            for w in WORD.findall(text):
                lw = w.lower()
                if lw in seen or len(lw) < 5 or lex.knows(lw):
                    continue
                splits = [
                    (lw[:i], lw[i:]) for i in range(2, len(lw) - 1)
                    if lex.knows(lw[:i]) and lex.knows(lw[i:])
                ]
                if not splits:
                    continue
                seen.add(lw)
                if ref_words[lw]:
                    verdict = "right (whole in the reference)"
                elif any(f"{a} {b}" in ref for a, b in splits):
                    verdict = "ERROR (split in the reference)"
                else:
                    verdict = "neither"
                tally[set_name, verdict] += 1
                if verdict.startswith("ERROR"):
                    print(f"  {name[:22]} {w!r} → {[f'{a} {b}' for a, b in splits if f'{a} {b}' in ref]}")
for k in sorted(tally):
    print(f"{tally[k]:6}  {k[0]:10} {k[1]}")
