"""Run a short command while one of the agent's screen sessions stands still: every process
of that session is stopped (SIGSTOP), the command runs, and they are continued (SIGCONT),
whatever the command's end. For a probe of minutes whose answer the day's plan waits on,
ahead of a build of hours; the build loses nothing but the wait.

    uv run python experiments/slot.py <session> <command …>
"""

import signal
import subprocess
import sys

from roboscriptorium import priority

session, command = sys.argv[1], sys.argv[2:]
listing = subprocess.run(["screen", "-ls"], capture_output=True, text=True).stdout
roots = {pid for pid, name in priority.sessions(listing).items() if name == session}
ps = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True).stdout
table = [tuple(map(int, row.split())) for row in ps.splitlines() if row.strip()]
pids = priority.descendants(roots, table)
print(f"stopping {len(pids)} processes of {session}", flush=True)
priority._signal(pids, signal.SIGSTOP)
try:
    code = subprocess.run(command).returncode
finally:
    priority._signal(pids, signal.SIGCONT)
    print(f"{session} continued", flush=True)
sys.exit(code)
