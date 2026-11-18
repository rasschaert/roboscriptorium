"""How far a slow stage is: its count and the time left, printed every few minutes.

A long book's first build reads and judges for hours; each slow stage counts what it
has done against what it has to do and prints both, with an estimate from its pace so
far, to stderr. A stage that finishes within `EVERY` seconds (a cached rerun, a short
book) prints nothing.
"""

import sys
import threading
import time
from typing import TextIO

EVERY = 180.0


class Progress:
    """`what` counted to `total` in `unit`s; `add` may be called from several threads."""

    def __init__(
        self,
        what: str,
        total: int,
        unit: str,
        every: float = EVERY,
        clock=time.monotonic,
        out: TextIO | None = None,
    ):
        self.what, self.total, self.unit, self.every = what, total, unit, every
        self._clock, self._out = clock, out
        self._start = self._last = clock()
        self._done = 0
        self._lock = threading.Lock()

    def add(self, n: int = 1) -> None:
        with self._lock:
            self._done += n
            now = self._clock()
            if now - self._last < self.every or self._done >= self.total:
                return
            self._last = now
            line = self.line(now - self._start)
        print(line, file=self._out or sys.stderr, flush=True)

    def line(self, elapsed: float) -> str:
        """The count, and the time left at the pace so far."""
        left = elapsed / self._done * (self.total - self._done) if self._done else 0.0
        return (
            f"{self.what}: {self._done:,} of {self.total:,} {self.unit}, "
            f"about {duration(left)} left"
        )


def duration(seconds: float) -> str:
    """A span of time as "2 h 05 min", "12 min" or "under a minute"."""
    minutes = round(seconds / 60)
    if minutes < 1:
        return "under a minute"
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d} min"
