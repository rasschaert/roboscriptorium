"""The small-capitals versions' short test: each known small-capital error's page and its
neighbours, built and scored, the error rows printed as JSON lines.

    uv run python experiments/probe_small_caps.py <out.jsonl>
    uv run --project ../roboscriptorium-caps python experiments/probe_small_caps.py <out.jsonl>

Run from the main checkout so `work/` is reached by path; the second form builds with the
branch's code. Models run for the lines whose versions changed; decisions already cached
are reused.
"""

import json
import sys
from pathlib import Path

from roboscriptorium import errorlog
from roboscriptorium.golden import scoring

# (bench spec's book and chapters, the page of a known error)
TARGETS = [
    ("work/goede-dochter--ia-scan", "1-6", 14),
    ("work/the-story-of-doctor-dolittle--stokes-1920", "1-7", 51),
    ("work/the-story-of-doctor-dolittle--stokes-1920", "1-7", 58),
    ("work/the-story-of-doctor-dolittle--stokes-1920", "1-7", 77),
    ("work/de-tuin-van-de-avondnevel--ia-scan", "1-6", 56),
    ("work/de-eerlijke-vinder--ia-scan", None, 39),
    ("work/de-kerk-van-de-dode-meisjes--ia-scan", "1-13", 101),
    ("work/verminkt--ia-scan", None, 106),
    ("work/verminkt--ia-scan", None, 180),
    ("work/verminkt--ia-scan", None, 185),
    ("work/verminkt--ia-scan", None, 251),
    ("work/de-geruchten--ia-scan", "2-22", 73),
]

out = Path(sys.argv[1])
lines = []
for book, chapters, page in TARGETS:
    spec = f"{book}:{page - 1}-{page + 1}" + (f":{chapters}" if chapters else "")
    name, _, stages, _, errors, found, _ = scoring.build(spec)
    for r in errorlog.rows(name, errors, found, stages.pages, stages.suspects):
        if abs(r["page"] - page) <= 1:
            lines.append({"target": f"{name}:{page}", **r})
    print(f"{spec}: done", flush=True)
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in lines))
