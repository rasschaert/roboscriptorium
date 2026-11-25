"""What the running bench has left, from its own log: the books started out of the set,
the minutes each finished book took (from the queue's start of the running job to now,
over the books done), and the time left at that rate. No guess: only the log's lines, the
queue's record and the clock.

    uv run python experiments/eta.py [log]

Without a log, the most recently written work/runs/*.log.
"""

import json
import re
import subprocess
import sys
from datetime import datetime
import time
from pathlib import Path

from roboscriptorium import bench

log = Path(sys.argv[1]) if len(sys.argv) > 1 else max(Path("work/runs").glob("*.log"), key=lambda p: p.stat().st_mtime)
text = log.read_text(errors="replace").replace("\r", "\n")
started = [m.group(1) for m in re.finditer(r"^== (\S+)", text, re.M)]
command = re.search(r"bench (tuning|validation|first-look|quick)", text) or re.search(
    r"bench (tuning|validation|first-look|quick)", log.with_suffix(".sh").read_text() if log.with_suffix(".sh").exists() else ""
)
name = command.group(1) if command else None
total = len(bench.SETS[name]) if name in bench.SETS else None
tasks = json.loads(subprocess.run(["pueue", "status", "--json"], capture_output=True, text=True).stdout)["tasks"]
running = [v["status"]["Running"]["start"] for v in tasks.values() if "Running" in v["status"]]
if not running:
    sys.exit("no job is running")
begun = datetime.fromisoformat(running[0]).timestamp()
elapsed = (time.time() - begun) / 60
done = max(0, len(started) - 1)
stage = [line for line in text.splitlines() if re.search(r"of [\d,]+ (pages|lines)", line)]
print(f"{log.name}: {len(started)} of {total or '?'} books started, {elapsed:.0f} min since the job began")
if stage:
    print(f"  now: {stage[-1].strip()}")
if done and total:
    per = elapsed / done
    left = per * (total - done)
    print(f"  {per:.1f} min a finished book → about {left:.0f} min left for the {total - done} not finished")
else:
    print("  no book finished yet: no rate to give")
