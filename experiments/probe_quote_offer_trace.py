"""Where the right quote offers are lost between the arbiter's chance and the question:
each book's suspects of the nested run's trust data decided as a build decides them
(`trust.decide`, the arbiter trained without the book, the page budget, ask below 0.93),
then what became of each quote-mark offer no reader has. No models.

    uv run python experiments/probe_quote_offer_trace.py
"""

import glob
import json
import os
from collections import Counter
from pathlib import Path

from roboscriptorium import trust, trustdata

Q = set("‘’“”'\"")
DATA, MODEL, BELOW = "work/probes/ocr-trust-nested", "work/models/ocr-trust-nested", 0.93


def bare(text):
    return "".join(c for c in text if c not in Q)


tally = {True: Counter(), False: Counter()}
for f in sorted(glob.glob(f"{DATA}/*.json")):
    book = os.path.basename(f)[:-5]
    path = Path(f"{MODEL}-without-{book}.pkl")
    model = trust.load(path if path.exists() else Path(f"{MODEL}.pkl"))
    rows = json.load(open(f))
    suspects = [trustdata.suspect(r) for r in rows]
    pages = len({s.page for s in suspects})
    decided = trust.decide(suspects, model, pages, BELOW)
    for r, s, d in zip(rows, suspects, decided, strict=True):
        for k, o in enumerate(s.others, 1):
            if any(len(h) > k and h[k] for h in s.support.values()) or bare(o) != bare(s.ours):
                continue
            if r["right"][0] == r["right"][k]:
                continue
            p = trust.probabilities(model, s)
            ok = bool(r["right"][k])
            fate = "asked" if d.choice == "review" else "taken" if d.chosen == o else "kept ours" if d.choice == "ours" else "took another"
            tally[ok][fate] += 1
            if ok:
                print(f"{book[:20]:20} p{s.page:<4} chance {p[k]:.2f} sure {trust.sureness(model, p):.2f} → {fate}: {s.ours!r} / {o!r}")
print("right offers:", dict(tally[True]))
print("wrong offers:", dict(tally[False]))
