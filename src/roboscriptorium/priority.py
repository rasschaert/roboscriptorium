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


def _agent_processes() -> tuple[list[int], list[str]]:
    listing = subprocess.run(["screen", "-ls"], capture_output=True, text=True).stdout
    found = sessions(listing)
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
