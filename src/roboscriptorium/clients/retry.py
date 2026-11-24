"""A local model call that timed out, lost its connection or met a server error, tried
again: with several books running, Ollama queues requests, drops connections while it
swaps models, and answers 500 to the requests waiting on a model that is unloaded (the
battery guard unloads models when memory runs low); one such answer shouldn't end an
hour-long run."""

import time
from collections.abc import Callable

import httpx

ATTEMPTS = 3
WAIT = 10.0  # seconds before the first retry, more before each next one


def patiently[T](call: Callable[[], T], attempts: int = ATTEMPTS, wait: float = WAIT) -> T:
    """`call()`, tried again after a timeout, a dropped connection or a server error (5xx,
    raised inside `call` by `raise_for_status`), up to `attempts` times in all. A refusal
    of the request (4xx) is not retried."""
    for attempt in range(attempts):
        try:
            return call()
        except httpx.HTTPStatusError as e:
            if e.response.status_code < 500 or attempt == attempts - 1:
                raise
            time.sleep(wait * (attempt + 1))
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
            if attempt == attempts - 1:
                raise
            time.sleep(wait * (attempt + 1))
    raise AssertionError("unreachable")
