"""Words a diaeresis would change: how the Dutch tuning books' references spell them.

    uv run python experiments/probe_diaeresis.py

For each word in a reference that the word list also knows with an "ë" or "ï" in place of
an "e", "i" or "é" after a vowel, counts the plain spelling against the diaeresis one.
A rule that prefers the diaeresis form is safe only if the references never print the
plain one.
"""

import re
from collections import Counter
from pathlib import Path

from roboscriptorium import bench
from roboscriptorium.lexicon import Lexicon

VOWELS = "aeiouAEIOU"
SWAP = {"e": "ë", "i": "ï", "é": "ë"}

lexicon = Lexicon.load("nld")


def variants(word: str) -> list[str]:
    out = []
    for i, c in enumerate(word):
        if i and c in SWAP and word[i - 1] in VOWELS:
            out.append(word[:i] + SWAP[c] + word[i + 1 :])
    return out


plain, marked, examples = Counter(), Counter(), {}
for spec in bench.SETS["tuning"]:
    name = spec.split("--")[0]
    text = Path("work/golden", name, "text")
    if not text.exists():
        continue
    words = re.findall(r"\w+", " ".join(p.read_text() for p in text.glob("chapter-*.xhtml")))
    if not any(w in {"de", "het", "een"} for w in words[:200]):
        continue
    for w in words:
        low = w.lower()
        for v in variants(low):
            if lexicon.knows(v):
                plain[name] += 1
                examples.setdefault(name, []).append(f"{w}→{v}")
        if any(c in w for c in "ëï"):
            marked[name] += 1
for name in sorted(set(plain) | set(marked)):
    print(f"{name:32} plain with a known diaeresis form {plain[name]:4}  diaeresis words {marked[name]:4}")
    print("   ", ", ".join(Counter(examples.get(name, [])).most_common(12) and f"{k} ×{n}" for k, n in Counter(examples.get(name, [])).most_common(12)))
