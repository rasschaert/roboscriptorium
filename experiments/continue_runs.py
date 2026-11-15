"""Continue the agent's runs a user's build paused (`priority.first`) when that build's
process ended without continuing them, and clear its marker.

    uv run python experiments/continue_runs.py
"""

import signal

from roboscriptorium import priority

pids, names = priority._agent_processes()
priority._signal(pids, signal.SIGCONT)
priority.MARKER.unlink(missing_ok=True)
print("continued:", ", ".join(names))
