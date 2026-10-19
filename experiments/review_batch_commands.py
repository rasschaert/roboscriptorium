"""One `review --only` command per book that has places in a candidate list, each with the
book's tuning slice, most places first. No models.

    uv run python experiments/review_batch_commands.py work/probes/unasked/candidates-20261019.json
"""

import json
import sys
from collections import Counter

from roboscriptorium import bench

rows = json.load(open(sys.argv[1]))
slices = {}
for kind in ("tuning", "validation"):
    for spec in bench.SETS[kind]:
        name, pages, chapters = (spec.split(":") + ["", ""])[:3]
        slices[name] = (pages, chapters)
for name, n in Counter(r["book"] for r in rows).most_common():
    pages, chapters = slices.get(name, ("", ""))
    flags = f" --pages {pages}" * bool(pages) + f" --chapters {chapters}" * bool(chapters)
    print(f"# {n} places\nuv run roboscriptorium review work/{name}{flags} --only {sys.argv[1]}")
