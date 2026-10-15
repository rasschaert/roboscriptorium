"""Would "no page reader reads this line" fix the line roles' mistakes? No models: the
bench's builds from cache, each line's treatment (text, heading, dropped) against its
true role (`golden.align`), crossed with how many page readers have words for it
(`pagereader.split_lines`), on pages both page readers have read.

A mistake the feature could fix: a line kept as text that isn't (read by none), or a
body line dropped that both read. Run when no other build uses the same books.

    uv run python experiments/probe_unread_errors.py [tuning|validation]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, pagereader
from roboscriptorium.config import Settings
from roboscriptorium.flags import treatment
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.ir import SourceRef

settings = Settings.from_env()
tally: Counter = Counter()
examples: list[str] = []
for spec in bench.SETS[sys.argv[1] if sys.argv[1:] else "tuning"]:
    name = spec.split(":")[0]
    run = scoring.build(f"work/{spec}", bench.unseen(settings, name))
    truth = align(run.stages.pages, run.reference)
    roles = run.stages.model_roles or {}
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
            ref = SourceRef(page.number, k)
            t = truth.get(ref)
            true = "body" if t and t.role == "body" else "heading" if t and t.role == "heading" else "other"
            got = {"text": "body", "heading": "heading", "dropped": "other"}[treatment(roles.get(ref))]
            n = sum(k in s for s in splits)
            verdict = "right" if got == true else f"WRONG {got} for {true}"
            tally[verdict, n] += 1
            if got != true and len(examples) < 40:
                examples.append(f"{name[:18]} p{page.number}:{k} read by {n}: {got} for {true}: {line.text[:50]!r}")
for key in sorted(tally):
    print(f"  {tally[key]:6}  {key[0]:28} read by {key[1]} page readers")
print()
print("\n".join(examples))
