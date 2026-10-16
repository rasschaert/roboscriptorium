"""Probe: glm-ocr's throughput with 1, 4 and 8 requests at a time, as the pipeline sends
them (`readers.read_line`), on disjoint fresh sets of body lines; then the first set
again at the widest setting, counting readings that differ from one at a time.
Results in work/probes/glm-parallel.json.

    uv run python experiments/probe_glm_parallel.py [lines per set]
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


sys.path.insert(0, "experiments")
from probe_qwen_speed import crops_from  # noqa: E402
from roboscriptorium import readers  # noqa: E402

URL = "http://127.0.0.1:11434"
MODEL = "glm-ocr:bf16"
OUT = Path("work/probes/glm-parallel.json")


def read_set(crops: list[bytes], workers: int) -> tuple[list[str], float]:
    start = time.time()
    with ThreadPoolExecutor(workers) as pool:
        out = list(pool.map(lambda png: readers.read_line(png, MODEL, URL), crops))
    return out, time.time() - start


per_set = int(sys.argv[1]) if len(sys.argv) > 1 else 64
settings = (1, 4, 8)
lines = crops_from(60, per_set * len(settings))
sets = [lines[i * per_set : (i + 1) * per_set] for i in range(len(settings))]
assert all(len(s) == per_set for s in sets), f"only {len(lines)} lines"
readers.read_line(sets[0][0][1], MODEL, URL)  # load before timing
results = {}
for workers, crops in zip(settings, sets):
    readings, took = read_set([png for _, png in crops], workers)
    results[f"x{workers}"] = {"s_per_line": took / per_set, "readings": readings,
                              "layer": [t for t, _ in crops]}
    print(f"{workers:2} at a time: {took / per_set:5.2f} s a line  (a fresh set of {per_set})", flush=True)
again, _ = read_set([png for _, png in sets[0]], settings[-1])
base = results["x1"]["readings"]
differ = sum(a != b for a, b in zip(base, again, strict=True))
results[f"set1 x{settings[-1]}"] = {"differ": differ, "readings": again}
print(f"set 1 again, {settings[-1]} at a time: {differ} of {per_set} differ from 1 at a time")
for a, b in zip(base, again):
    if a != b:
        print(f"   x1 {a!r} -> x{settings[-1]} {b!r}")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
