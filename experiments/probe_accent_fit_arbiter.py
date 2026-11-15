"""What the accent-zone fit (`probe_accent_fit.py`) would add to the arbiter: on the places
where two versions differ by one letter's mark, each book's held-out arbiter's pick and
sureness beside the accent call of a logistic model fitted on the other books. Counts, at
the 0.8 line under which the build asks: the arbiter's sure and wrong picks the accent call
would right, and its sure and right ones the call would wrong. No models.

    PYTHONPATH=experiments uv run python experiments/probe_accent_fit_arbiter.py
"""

import json
from collections import Counter
from pathlib import Path

import numpy as np
from probe_accent_mark import marked_letter, strip
from probe_book_vocab import SETTINGS, scored
from sklearn.linear_model import LogisticRegression

from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable

KEYS = ("cosine", "mass", "stray")
fit = [json.loads(line) for line in Path("work/probes/accent-fit.jsonl").read_text().splitlines()]
books = {n: rows_of(n, SETTINGS) for n in SPECS if not usable(n, SETTINGS)}
tot = Counter()
for name, rows in books.items():
    mine = {(f["page"], f["marked"], f["plain"]): f for f in fit if f["book"] == name}
    others = [f for f in fit if f["book"] != name]
    if not mine or len({f["print_marked"] for f in others}) < 2:
        continue
    call = LogisticRegression(max_iter=1000).fit(
        np.array([[f[k] for k in KEYS] for f in others]), [f["print_marked"] for f in others]
    )
    probs = scored([r for m in books if m != name and trainable(m) for r in books[m]], rows, None, False)
    for r, p in zip(rows, probs, strict=True):
        s = r["s"]
        versions = [s.ours, *s.others]
        k = int(p.argmax())
        for j in range(len(versions)):
            at = marked_letter(versions[k], versions[j]) if j != k else None
            if at is None:
                continue
            a, b = versions[k], versions[j]
            marked, plain = (a, b) if strip(a[at]) != a[at] else (b, a)
            f = mine.get((s.page, marked, plain))
            if f is None:
                continue
            p_marked = float(call.predict_proba([[f[x] for x in KEYS]])[0, 1])
            says = k if (p_marked > 0.5) == (marked is a) else j
            strong = abs(p_marked - 0.5) > 0.4
            sure = float(p.max()) >= 0.8
            tot["places"] += 1
            tot["arbiter sure"] += sure
            if sure and not r["right"][k]:
                tot["sure and wrong"] += 1
                tot["  the accent call rights it"] += bool(r["right"][says])
                tot["  and is strong (over 0.9)"] += bool(r["right"][says]) and strong
            if sure and r["right"][k]:
                tot["sure and right"] += 1
                tot["  the accent call wrongs it"] += says != k and not r["right"][says]
                tot["  and is strong (over 0.9)."] += says != k and not r["right"][says] and strong
            if not sure:
                tot["asked"] += 1
                tot["  the accent call is right"] += bool(r["right"][says])
                tot["  strong and right"] += bool(r["right"][says]) and strong
                tot["  strong and wrong"] += (not r["right"][says]) and strong
            break
    print(name, flush=True)
for k, v in tot.items():
    print(f"{k:34} {v}")
