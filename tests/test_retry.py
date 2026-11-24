import httpx
import pytest

from roboscriptorium.clients import retry


def test_a_timed_out_call_is_tried_again_then_given_up(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda s: None)
    tries = []

    def slow_twice():
        tries.append(1)
        if len(tries) < 3:
            raise httpx.ReadTimeout("timed out")
        return "answer"

    assert retry.patiently(slow_twice) == "answer" and len(tries) == 3

    def always_slow():
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(httpx.ReadTimeout):
        retry.patiently(always_slow)


def test_other_errors_are_not_retried(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda s: None)
    tries = []

    def broken():
        tries.append(1)
        raise ValueError("bad answer")

    with pytest.raises(ValueError):
        retry.patiently(broken)
    assert len(tries) == 1


def test_a_dropped_connection_is_tried_again_like_a_timeout(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda s: None)
    tries = []

    def dropped_once():
        tries.append(1)
        if len(tries) == 1:
            raise httpx.RemoteProtocolError("Server disconnected")
        return "answer"

    assert retry.patiently(dropped_once) == "answer" and len(tries) == 2


def test_a_server_error_is_tried_again_and_a_refusal_is_not(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda s: None)
    request = httpx.Request("POST", "http://ollama/api/generate")

    def answering(codes):
        tries = []

        def call():
            code = codes[len(tries)]
            tries.append(code)
            return httpx.Response(code, request=request).raise_for_status()

        return call, tries

    call, tries = answering([500, 200])
    assert retry.patiently(call).status_code == 200 and tries == [500, 200]
    call, tries = answering([400, 200])
    with pytest.raises(httpx.HTTPStatusError):
        retry.patiently(call)
    assert tries == [400]
