"""Freeze or unfreeze the agent's runs for the user, and say what changed.

    uv run python experiments/pause.py            freeze every robo- run (not the battery guard)
    uv run python experiments/pause.py resume     unfreeze what the last pause froze

A frozen run keeps its place: its processes are stopped (SIGSTOP), not killed, and go on
mid-book when continued. Every process is checked to be stopped before this reports it;
one that isn't is signalled again, and any still running is named. Ollama is left alone:
a frozen run asks it nothing, so the models it loaded unload by themselves after the
keep-alive, and a model the user loaded stays theirs.
"""

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

from roboscriptorium import priority

FROZEN = Path("work/runs/frozen.json")


def states(pids: list[int]) -> dict[int, str]:
    if not pids:
        return {}
    ps = subprocess.run(
        ["ps", "-o", "pid=,stat=", "-p", ",".join(map(str, pids))], capture_output=True, text=True
    ).stdout
    return {int(r.split()[0]): r.split()[1] for r in ps.splitlines() if r.strip()}


def pause() -> int:
    # priority's list leaves out each screen window's own process: screen continues a
    # window whose own process stops, and with it everything under it.
    pids, names = priority._agent_processes(skip=priority.GUARD)
    if not pids:
        print("nothing to freeze: no robo- run is going")
        return 0
    for _ in range(5):
        priority._signal(pids, signal.SIGSTOP)
        time.sleep(0.5)
        running = [p for p, s in states(pids).items() if not s.startswith("T")]
        if not running:
            break
    FROZEN.write_text(json.dumps({"pids": pids, "names": names, "at": time.time()}))
    if running:
        print(f"NOT frozen: {len(running)} processes still running: {running}")
        return 1
    count = len(states(pids))
    print(f"{time.strftime('%H:%M')} frozen: {', '.join(names)} ({count} processes, all stopped)")
    return 0


def resume() -> int:
    if not FROZEN.exists():
        print("nothing frozen by pause.py")
        return 0
    saved = json.loads(FROZEN.read_text())
    pids = saved["pids"]
    priority._signal(pids, signal.SIGCONT)
    time.sleep(0.5)
    still = [p for p, s in states(pids).items() if s.startswith("T")]
    if still:
        print(f"NOT continued: {still}")
        return 1
    FROZEN.unlink()
    print(f"{time.strftime('%H:%M')} continued: {', '.join(saved['names'])}")
    return 0


if __name__ == "__main__":
    sys.exit(resume() if sys.argv[1:] == ["resume"] else pause())
