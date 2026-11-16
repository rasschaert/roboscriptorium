"""The arbiter's chance for each quote-mark offer no reader has, in the nested run's trust
data, by the copy of the arbiter trained without that book: how near the right offers come
to being taken or asked. No models.

    uv run python experiments/probe_quote_offer_chance.py
"""

import glob
import json
import os
from pathlib import Path

from roboscriptorium import trust, trustdata

Q = set("‘’“”'\"")
DATA, MODEL, BELOW = "work/probes/ocr-trust-nested", "work/models/ocr-trust-nested", 0.93


def bare(text):
    return "".join(c for c in text if c not in Q)


out = {True: [], False: []}
for f in sorted(glob.glob(f"{DATA}/*.json")):
    book = os.path.basename(f)[:-5]
    path = Path(f"{MODEL}-without-{book}.pkl")
    model = trust.load(path if path.exists() else Path(f"{MODEL}.pkl"))
    for r in json.load(open(f)):
        s = trustdata.suspect(r)
        for k, o in enumerate(s.others, 1):
            if any(len(h) > k and h[k] for h in s.support.values()) or bare(o) != bare(s.ours):
                continue
            if r["right"][0] == r["right"][k]:
                continue
            p = trust.probabilities(model, s)
            sure = trust.sureness(model, p)
            d3 = s.votes.get("d3:9b") == o
            out[bool(r["right"][k])].append((float(p[k]), sure, int(p.argmax()) == k, d3, book[:18], s.page, s.ours, o))
for ok in (True, False):
    rows = sorted(out[ok], reverse=True)
    taken = sum(r[2] and r[1] >= BELOW for r in rows)
    asked = sum(r[1] < BELOW for r in rows)
    print(f'{"offer is the print" if ok else "offer is wrong"}: {len(rows)}; would take {taken}, would ask {asked} (before the page budget)')
    for cut in (0.5, 0.2, 0.1, 0.05):
        print(f"   chance of the offer ≥ {cut}: {sum(r[0] >= cut for r in rows)}")
    for r in rows[:8] if ok else rows[:4]:
        print(f"   {r[0]:.2f} sure {r[1]:.2f} d3 {'offer' if r[3] else 'ours '} {r[4]} p{r[5]}: {r[6]!r} → {r[7]!r}")
