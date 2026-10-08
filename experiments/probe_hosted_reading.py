"""How often a hosted model's line readings agree with the local model's cached ones.

Reads the lines of a book's pages with the hosted model (same prompt as the local cache)
and compares, line by line, with `stages/third-reading.json`.

    OPENROUTER_API_KEY=… uv run python experiments/probe_hosted_reading.py <book dir> <first> <last> <hosted model>
"""

import json
import sys
import time
from pathlib import Path

from roboscriptorium import ocrcheck, pdf
from roboscriptorium.ir import SourceRef

book, first, last, model = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
local = json.loads((book / "stages" / "third-reading.json").read_text())
pages = [
    p
    for p in pdf.cached_text_layer(book / "source.pdf", book / "stages" / "textlayer.json")
    if first <= p.number <= last
]
checked = {SourceRef(p.number, k) for p in pages for k in range(len(p.lines))}
tag = model.rsplit("@", 1)[-1].replace("/", "-")
out = Path("work/probes/openrouter") / f"{book.name}-{first}-{last}-{tag}.json"
start = time.time()
ocrcheck.line_readings(book / "source.pdf", pages, checked, model, "", out, local["prompt"])
seconds = time.time() - start
hosted = json.loads(out.read_text())["lines"]
shared = [k for k in hosted if k in local["lines"]]
same = [k for k in shared if hosted[k] == local["lines"][k]]
print(f"{len(hosted)} lines read in {seconds:.0f} s; {len(shared)} also read locally, "
      f"{len(same)} identical ({len(same) / max(1, len(shared)):.1%})")
for k in [k for k in shared if hosted[k] != local["lines"][k]][:40]:
    print(f"  {k.split(':')[0]:>4}  local  {local['lines'][k]!r}\n        hosted {hosted[k]!r}")
