"""The user's builds come first: while one runs, the agent's runs are paused.

The agent's long runs live in `screen` sessions named `robo-*` (`experiments/detached.sh`).
A `build` or a review's build that runs outside one is the user's: for its length every
process of those sessions is stopped (SIGSTOP) and continued after (SIGCONT), and
`work/runs/user-active` names it, so a run starting meanwhile waits at the battery gate
(`experiments/battery_gate.sh`). A run paused mid-request to Ollama gets its answer when
it continues.
"""

import os
import re
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

MARKER = Path("work/runs/user-active")
_SESSION = re.compile(r"^\s*(\d+)\.(robo-[^\s]+)", re.M)


def agents_own() -> bool:
    """Whether this process is one of the agent's: inside a `robo-*` screen session, or
    told so by `ROBO_AGENT`."""
    session = os.environ.get("STY", "").split(".", 1)[-1]
    return session.startswith("robo-") or bool(os.environ.get("ROBO_AGENT"))


def sessions(listing: str) -> dict[int, str]:
    """The agent's screen sessions in `screen -ls` output: their pids and names."""
    return {int(pid): name for pid, name in _SESSION.findall(listing)}


def descendants(roots: set[int], table: list[tuple[int, int]]) -> list[int]:
    """Every process below `roots` in a (pid, parent pid) table, the roots left out."""
    children: dict[int, list[int]] = {}
    for pid, parent in table:
        children.setdefault(parent, []).append(pid)
    out, todo = [], list(roots)
    while todo:
        for child in children.get(todo.pop(), []):
            out.append(child)
            todo.append(child)
    return out


GUARD = "robo-battery-guard"


def _agent_processes(skip: str = "") -> tuple[list[int], list[str]]:
    listing = subprocess.run(["screen", "-ls"], capture_output=True, text=True).stdout
    found = {pid: name for pid, name in sessions(listing).items() if name != skip}
    if not found:
        return [], []
    ps = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True).stdout
    table = [tuple(map(int, row.split())) for row in ps.splitlines() if row.strip()]
    return descendants(set(found), table), sorted(found.values())


def _signal(pids: list[int], sig: int) -> None:
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass


@contextmanager
def first(what: str) -> Iterator[None]:
    """The user's `what` runs with the agent's runs paused; the agent's own runs pass."""
    if agents_own():
        yield
        return
    pids, names = _agent_processes()
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(f"{os.getpid()}\n")
    _signal(pids, signal.SIGSTOP)
    if names:
        print(f"Paused the agent's runs for your {what}: {', '.join(names)}", file=sys.stderr)
    try:
        yield
    finally:
        _signal(pids, signal.SIGCONT)
        MARKER.unlink(missing_ok=True)
        if names:
            print(f"Your {what} is done; the agent's runs go on.", file=sys.stderr)


FLOOR, RESUME = 30, 50


def battery() -> int | None:
    """The battery's charge in percent, or None without one."""
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    found = re.search(r"(\d+)%", out)
    return int(found.group(1)) if found else None


def hold(level: int | None, held: bool, floor: int = FLOOR, resume: int = RESUME) -> bool:
    """Whether the agent's runs stay stopped: from under `floor` until back at `resume`."""
    if level is None:
        return False
    return level < resume if held else level < floor


def guard(every: int = 60) -> None:
    """Stops the agent's runs while the battery is low, mid-run, and continues them once
    it has charged: a low-wattage charger loses ground under Ollama, and the battery gate
    only checks when a run starts. Prints each change, and the level at every 5%."""
    floor = int(os.environ.get("ROBO_BATTERY_FLOOR", FLOOR))
    resume = int(os.environ.get("ROBO_BATTERY_RESUME", RESUME))
    held, last = False, None
    while True:
        level = battery()
        now = hold(level, held, floor, resume)
        pids, names = _agent_processes(skip=GUARD)
        if now:
            _signal(pids, signal.SIGSTOP)
        if now != held:
            if not now:
                _signal(pids, signal.SIGCONT)
            verb = "stopped" if now else "continued"
            runs = ", ".join(names) or "nothing"
            print(f"{time.strftime('%H:%M')} battery {level}%: {verb} {runs}", flush=True)
        elif level is not None and last is not None and level // 5 != last // 5:
            print(f"{time.strftime('%H:%M')} battery {level}%", flush=True)
        held, last = now, level
        time.sleep(every)


if __name__ == "__main__":
    guard()
