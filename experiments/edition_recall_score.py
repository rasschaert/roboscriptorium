"""Probe (`probe_translation_check.py`'s recall): Which planted errors the edition check flagged, by kind, and what else it flagged."""
import collections, json, sys
from pathlib import Path

R = Path(sys.argv[1])
truth = {t["paragraph"]: t for t in map(json.loads, open(R / "truth.jsonl"))}
rows = {r["paragraph"]: r for r in map(json.loads, open(R / "flags.jsonl"))}
caught, total, other = collections.Counter(), collections.Counter(), 0
for k, t in sorted(truth.items()):
    if k not in rows:
        continue
    total[t["kind"]] += 1
    hit = [f for f in rows[k]["flags"] if t["planted"] in f["dutch"] or f["dutch"] in t["planted"]]
    other += len(rows[k]["flags"]) - len(hit)
    caught[t["kind"]] += bool(hit)
    fix = hit[0]["fix"] if hit else ""
    print(f"¶{k} {t['kind']:8} {t['planted']!r} (print {t['print']!r}): {'caught → ' + repr(fix) if hit else 'missed'}")
print({k: f"{caught[k]}/{total[k]}" for k in total}, f"all {sum(caught.values())}/{sum(total.values())}, other flags {other}")
