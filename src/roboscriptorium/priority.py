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
import shutil
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
    # screen continues a window whose own process stops, and with it the whole window.
    window = {pid for pid, parent in table if parent in found}
    return descendants(window, table), sorted(found.values())


def _stopped(pids: list[int]) -> set[int]:
    """The `pids` already stopped (held by the battery guard or paused by hand)."""
    if not pids:
        return set()
    ps = subprocess.run(
        ["ps", "-o", "pid=,stat=", "-p", ",".join(map(str, pids))], capture_output=True, text=True
    ).stdout
    return {int(pid) for pid, stat in (row.split()[:2] for row in ps.splitlines() if row.strip())
            if stat.startswith("T")}  # fmt: skip


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
    # A run already stopped stays stopped when the build ends.
    held = _stopped(pids)
    pids = [p for p in pids if p not in held]
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
# Gigabytes free on the disk that holds work/: a download filling it would fail a run
# mid-write, so the runs wait for room instead.
DISK_FLOOR, DISK_RESUME = 5, 15
# Present while the guard holds the runs, so a restarted guard holds them too.
HELD = Path("work/runs/battery-held")
# The share of memory free (macOS's memory_pressure) under which Ollama's models are
# unloaded: its MLX runner grows while it answers (qwen3.8 27B from 45 to 86 GB over two
# hours on 2026-11-24, past the 64 GB in the machine), and the swapping it causes crashes
# the user's applications. The runs are frozen first and their requests in flight given
# DRAIN seconds, so no request meets a model being unloaded; the next request reloads it.
MEMORY_FLOOR = 35
DRAIN = 60
RELIEF_GAP = 180  # seconds between two unloads at least: it regrows 27 → 77 GB in 8 minutes
OLLAMA = os.environ.get("ROBO_OLLAMA_URL", "http://127.0.0.1:11434")


def battery() -> int | None:
    """The battery's charge in percent, or None without one."""
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    found = re.search(r"(\d+)%", out)
    return int(found.group(1)) if found else None


def disk_free() -> int:
    """Whole gigabytes free on the disk that holds work/."""
    return shutil.disk_usage(HELD.parent if HELD.parent.exists() else ".").free // 10**9


def memory_free() -> int | None:
    """The share of memory free in percent, or None where it can't be read."""
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    found = re.search(r"free percentage:\s*(\d+)%", out)
    return int(found.group(1)) if found else None


def unload_models() -> list[str]:
    """Unloads every model Ollama holds; returns their names."""
    import httpx

    try:
        loaded = [m["name"] for m in httpx.get(f"{OLLAMA}/api/ps", timeout=10).json()["models"]]
        for name in loaded:
            httpx.post(f"{OLLAMA}/api/generate", json={"model": name, "keep_alive": 0}, timeout=60)
    except httpx.HTTPError:
        return []
    return loaded


def relieve(pids: list[int]) -> list[str]:
    """Frees Ollama's memory under the runs: freezes them, lets requests in flight end,
    unloads the models, and continues the runs it froze."""
    held = _stopped(pids)
    froze = [p for p in pids if p not in held]
    record = HELD.with_name("memory-frozen")
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text("".join(f"{p}\n" for p in froze))
    _signal(froze, signal.SIGSTOP)
    try:
        time.sleep(DRAIN)
        return unload_models()
    finally:
        _signal(froze, signal.SIGCONT)
        record.unlink(missing_ok=True)


def _continue_left_frozen() -> None:
    """Continues the runs a guard froze to unload models and never continued: one ended
    in the middle of `relieve` (a restart) leaves them stopped, and a new guard would take
    them for a pause by hand."""
    record = HELD.with_name("memory-frozen")
    try:
        pids = [int(p) for p in record.read_text().split()]
    except (OSError, ValueError):
        return
    _signal(pids, signal.SIGCONT)
    record.unlink(missing_ok=True)


def hold(level: int | None, held: bool, floor: int = FLOOR, resume: int = RESUME) -> bool:
    """Whether the agent's runs stay stopped: from under `floor` until back at `resume`."""
    if level is None:
        return False
    return level < resume if held else level < floor


def _is_guard(pid: int) -> bool:
    """Whether `pid` is a running guard (`python -m roboscriptorium.priority`)."""
    out = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True)
    return "roboscriptorium.priority" in out.stdout


def _replace_older_guard() -> None:
    """Ends a guard still running from before and records this one, so one guard alone
    stops and continues the runs. Quitting a guard's screen can leave its process running,
    and an older guard holding out for its own resume level keeps stopping what a new one
    continues."""
    record = HELD.with_name("battery-guard.pid")
    try:
        old = int(record.read_text().strip())
    except (OSError, ValueError):
        old = 0
    if old and old != os.getpid() and _is_guard(old):
        _signal([old], signal.SIGTERM)
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(f"{os.getpid()}\n")


def guard(every: int = 30) -> None:
    """Stops the agent's runs while the battery is low or the disk nearly full, mid-run,
    and continues them once both have recovered: a low-wattage charger loses ground under
    Ollama, a model download can fill the disk, and the battery gate only checks when a
    run starts. Prints each change, and the battery level at every 5%."""
    _replace_older_guard()
    _continue_left_frozen()
    floor = int(os.environ.get("ROBO_BATTERY_FLOOR", FLOOR))
    resume = int(os.environ.get("ROBO_BATTERY_RESUME", RESUME))
    held = HELD.exists()
    by_battery, by_disk, last = held, held, None
    relieved = 0.0
    while True:
        level, free = battery(), disk_free()
        memory = memory_free()
        if not held and memory is not None and memory < MEMORY_FLOOR:
            if time.monotonic() - relieved > RELIEF_GAP:
                pids, _ = _agent_processes(skip=GUARD)
                gone = relieve(pids)
                relieved = time.monotonic()
                names = ", ".join(gone) or "nothing"
                now_free = memory_free()
                print(f"{time.strftime('%H:%M')} memory {memory}% free: unloaded {names}, "
                      f"now {now_free}%", flush=True)  # fmt: skip
        by_battery = hold(level, by_battery, floor, resume)
        by_disk = hold(free, by_disk, DISK_FLOOR, DISK_RESUME)
        now = by_battery or by_disk
        pids, names = _agent_processes(skip=GUARD)
        if now:
            _signal(pids, signal.SIGSTOP)
        if now != held:
            if now:
                HELD.touch()
            else:
                _signal(pids, signal.SIGCONT)
                HELD.unlink(missing_ok=True)
            verb = "stopped" if now else "continued"
            runs = ", ".join(names) or "nothing"
            print(f"{time.strftime('%H:%M')} battery {level}%, {free} GB free: {verb} {runs}",
                  flush=True)  # fmt: skip
        elif level is not None and last is not None and level // 5 != last // 5:
            print(f"{time.strftime('%H:%M')} battery {level}%", flush=True)
        held, last = now, level
        time.sleep(every)


if __name__ == "__main__":
    guard()
