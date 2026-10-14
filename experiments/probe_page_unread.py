"""Lines the page readers have no words for, by their true role (the golden alignment):
is "no page reader reads it" a sign that a line isn't running text, for the line-role
trees? No models; tuning pages both page readers have read (`pagereader.split_lines`).

    uv run python experiments/probe_page_unread.py
"""
import json
from collections import Counter
from pathlib import Path
from roboscriptorium import bench, pagereader
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.ir import SourceRef

settings = Settings.from_env()
tally, examples = Counter(), []
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    run = scoring.build(f"work/{spec}", bench.unseen(settings, name))
    truth = align(run.stages.pages, run.reference)
    read = {}
    for r in ("glm-page", "qwen-page"):
        f = Path("work") / name / "stages" / f"page-reading-{r}.json"
        read[r] = json.loads(f.read_text())["pages"] if f.exists() else {}
    for page in run.stages.pages:
        if not all(str(page.number) in read[r] for r in read):
            continue
        splits = [pagereader.split_lines(page, read[r][str(page.number)]) for r in read]
        if not all(splits):
            continue
        for k, line in enumerate(page.lines):
            t = truth.get(SourceRef(page.number, k))
            role = t.role if t else "unaligned"
            n = sum(k in s for s in splits)
            tally[role, n] += 1
            if n == 0 and role == "body":
                examples.append(f"{name[:18]} p{page.number}:{k} {line.text!r}")
for key in sorted(tally):
    print(f"  {tally[key]:6}  role {key[0]:12} read by {key[1]} page readers")
print("\nbody lines no page reader reads:")
for e in examples[:25]:
    print(" ", e)
