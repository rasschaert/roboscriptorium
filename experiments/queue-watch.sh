#!/usr/bin/env zsh
# Watches the job queue (experiments/queue.sh): one line per job that starts, succeeds or fails,
# and one for a running job when neither its output (work/runs/<name>.out) nor any run's step
# log has changed for STALL minutes (default 30), so a stuck job holding its group is seen. For the Monitor tool:
#   experiments/queue-watch.sh [stall minutes]
set -uo pipefail
cd "${0:A:h}/.."
exec python3 -I -u - ${1:-30} <<'EOF'
import json, subprocess, sys, time
from pathlib import Path

stall = int(sys.argv[1]) * 60
seen, warned = {}, set()
first = True
while True:
    try:
        out = subprocess.run(["pueue", "status", "--json"], capture_output=True, text=True, timeout=30)
        tasks = json.loads(out.stdout)["tasks"]
    except Exception as e:
        print(f"{time.strftime('%H:%M')} queue unreadable: {e}", flush=True)
        time.sleep(60)
        continue
    for tid, t in tasks.items():
        kind = next(iter(t["status"]))
        state = kind
        if kind == "Done":
            result = t["status"]["Done"]["result"]
            state = "succeeded" if result == "Success" else f"failed ({json.dumps(result)})"
        label = t.get("label") or t["command"][:60]
        if seen.get(tid) != state and not first and kind in ("Running", "Done"):
            print(f"{time.strftime('%H:%M')} job {tid} {label} [{t['group']}]: {state.lower()}", flush=True)
        seen[tid] = state
        if kind == "Running":
            # A run also writes per-step logs (timed.sh's, under work/runs/ and work/probes/*/runs/):
            # the newest of those counts as output too, so a long book isn't called stuck.
            logs = [Path("work/runs") / f"{label}.out", *Path("work/runs").glob("*.log"),
                    *Path("work/probes").glob("*/runs/*.log")]
            newest = max((f.stat().st_mtime for f in logs if f.exists()), default=time.time())
            idle = time.time() - newest
            if idle > stall and tid not in warned:
                print(f"{time.strftime('%H:%M')} job {tid} {label}: no output for {int(idle // 60)} minutes", flush=True)
                warned.add(tid)
            elif idle <= stall:
                warned.discard(tid)
    first = False
    time.sleep(30)
EOF
