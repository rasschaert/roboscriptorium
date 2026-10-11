"""Every wrong word no question asks about, per tuning book, as the bench builds it (each
book with its leave-one-out models): what the output has, what the reference has, the
context, its category and whether the OCR check raised a suspect on that line.

    uv run python experiments/unasked.py [book …]   # default: every tuning book

Writes work/probes/unasked/<book>.jsonl and prints the commonest kinds with examples.
Warm caches make no model calls; run it when no other run builds the same books.
"""

import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from roboscriptorium import bench, quality
from roboscriptorium.cli import _questions_and_errors
from roboscriptorium.config import Settings

OUT = Path("work/probes/unasked")
specs = [s for s in bench.SETS["tuning"] if not sys.argv[1:] or s.split(":")[0] in sys.argv[1:]]
OUT.mkdir(parents=True, exist_ok=True)
examples = defaultdict(list)
sizes = Counter()
for spec in specs:
    name = spec.split(":")[0]
    settings = bench.unseen(Settings.from_env(), name)
    _, book, stages, reference, errors, found, _ = _questions_and_errors(f"work/{spec}", settings)
    suspect_lines = {(s.page, s.line) for s in stages.suspects}
    rows = []
    for e in errors:
        if any(quality.catches(f, e) for f in found):
            continue
        first = e.lines[0] if e.lines else None
        row = asdict(e) | {
            "book": name,
            "category": quality.category(e),
            "size": quality.size(e),
            "suspect_on_line": (e.page, first) in suspect_lines,
        }
        rows.append(row)
        sizes[row["category"]] += row["size"]
        examples[row["category"]].append(row)
    (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"{name}: {len(rows)} unasked differences", flush=True)

print()
for category, n in sizes.most_common():
    rows = examples[category]
    raised = sum(r["suspect_on_line"] for r in rows)
    print(f"{category}: {n} words, {len(rows)} places, {raised} on a line with a suspect")
    for r in rows[:: max(1, len(rows) // 12)][:12]:
        print(f"   {r['book'][:14]:14} p{r['page']}  {r['got']!r} ≠ {r['want']!r}   …{r['before'][-30:]}|{r['after'][:30]}…")
