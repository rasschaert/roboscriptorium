"""Does a book's other places with the same two versions say which one a place prints?
From the arbiter's training data (work/probes/ocr-trust/, no models): every settled
two-version place whose pair of words (the build's, the other) the same book raises at
two or more other places; the judges' votes at this place alone against their votes
pooled over those other places, each scored on which version is the print. Stress
accents apart: an author marks them at one place and not the next.

    uv run python experiments/probe_same_pair.py
"""

import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


def plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))


groups = defaultdict(list)
for f in sorted(Path("work/probes/ocr-trust").glob("*.json")):
    for r in json.loads(f.read_text()):
        s = r["suspect"]
        if not r["settled"] or len(s["others"]) != 1 or not s["votes"]:
            continue
        if sum(r["right"]) != 1:
            continue
        share = sum(v == s["others"][0] for v in s["votes"].values()) / len(s["votes"])
        groups[f.stem, s["ours"], s["others"][0]].append((share, bool(r["right"][1]), s))

tally = Counter()
shown = []
for (book, ours, other), rows in groups.items():
    if len(rows) < 3:
        continue
    kind = "accent" if plain(ours) == plain(other) and ours != other else "other"
    truths = {right for _, right, _ in rows}
    tally[kind, "pairs"] += 1
    tally[kind, "pairs with one answer everywhere"] += len(truths) == 1
    for i, (share, right, _) in enumerate(rows):
        rest = [x for j, (x, _, _) in enumerate(rows) if j != i]
        pooled = sum(rest) / len(rest)
        tally[kind, "places"] += 1
        tally[kind, "alone: judges split 2-4 of 6"] += 0.3 < share < 0.7
        tally[kind, "alone right"] += (share > 0.5) == right
        tally[kind, "pooled right"] += (pooled > 0.5) == right
        if 0.3 < share < 0.7:
            tally[kind, "split places, pooled clear (under 0.3 or over 0.7)"] += not 0.3 <= pooled <= 0.7
            tally[kind, "split places, pooled clear and right"] += (
                not 0.3 <= pooled <= 0.7 and (pooled > 0.5) == right
            )
    shown.append((len(rows), book, ours, other, kind, sum(r for _, r, _ in rows)))
for (kind, what), n in sorted(tally.items()):
    print(f"{kind:7} {what:52} {n}")
print("the largest groups (places, book, build's, other, places where the other is the print):")
for n, book, ours, other, kind, right in sorted(shown, reverse=True)[:25]:
    print(f"  {n:3} {book[:24]:24} {ours!r} / {other!r}  {kind}  {right}")
