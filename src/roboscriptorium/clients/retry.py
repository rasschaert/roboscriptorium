"""A local model call that timed out or lost its connection, tried again: with several
books running, Ollama queues requests and drops connections while it swaps models, and
one such answer shouldn't end an hour-long run."""

import time
from collections.abc import Callable

import httpx

ATTEMPTS = 3
WAIT = 10.0  # seconds before the first retry, more before each next one


def patiently[T](call: Callable[[], T], attempts: int = ATTEMPTS, wait: float = WAIT) -> T:
    """`call()`, tried again after a timeout or a dropped connection, up to `attempts`
    times in all. An answer from the server (a 4xx or 5xx) is not retried."""
    for attempt in range(attempts):
        try:
            return call()
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
            if attempt == attempts - 1:
                raise
            time.sleep(wait * (attempt + 1))
    raise AssertionError("unreachable")
