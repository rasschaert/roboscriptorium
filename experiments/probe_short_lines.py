"""Probe: what the OCR check finds on short lines (under 12 characters), once it reads them.

Compares a book's trust data built with the short-line gate (a copy in
work/probes/ocr-trust/with-gate/) and without it: the new suspects, how often the text
layer is wrong on them, and how the fixed rule and clef do there.

    uv run python experiments/probe_short_lines.py <book>
"""

import json
import sys
from collections import Counter
from pathlib import Path

name = sys.argv[1]
base = Path("work/probes/ocr-trust")
key = lambda r: (r["suspect"]["page"], r["suspect"]["line"], r["suspect"]["start"])  # noqa: E731
old = {key(r) for r in json.loads((base / "with-gate" / f"{name}.json").read_text())}
new = [r for r in json.loads((base / f"{name}.json").read_text()) if key(r) not in old]
c: Counter = Counter()
for r in new:
    s = r["suspect"]
    versions = [s["ours"], *s["others"]]
    short = len(s["original"]) < 12
    c["new", short] += 1
    if not r["settled"]:
        c["unsettled", short] += 1
        print(f"  unsettled p{s['page']}:{s['line']} {s['original']!r} {versions} truth {r['truth']!r}")
        continue
    layer_wrong = not r["right"][0]
    c["layer wrong", short] += layer_wrong
    if s["choice"] == "review":
        c["rule asks", short] += 1
    else:
        k = 0 if s["choice"] == "ours" else 1 + versions[1:].index(s["chosen"])
        c["rule silent wrong", short] += not r["right"][k]
    clef = next((v for m, v in s["votes"].items() if m != "word list"), None)
    c["clef right", short] += clef in versions and r["right"][versions.index(clef)]
    c["settled", short] += 1
    mark = "LAYER WRONG" if layer_wrong else "layer right"
    print(f"  {mark:11} p{s['page']}:{s['line']} {s['original']!r} {versions} → {r['truth']!r} rule {s['choice']}")
for short in (True, False):
    label = "short lines" if short else "longer lines (other new suspects)"
    print(f"\n{label}: " + ", ".join(f"{k} {c[k, short]}" for k in
          ("new", "unsettled", "settled", "layer wrong", "rule asks", "rule silent wrong", "clef right")))
