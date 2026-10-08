import json

import httpx
import pytest

from roboscriptorium.clients import openrouter


def test_a_hosted_reading_is_pinned_to_one_provider_thinking_off(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    sent = []

    def answer(request):
        sent.append(json.loads(request.content))
        if len(sent) == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"choices": [{"message": {"content": "keek.’\nagain"}}]})

    monkeypatch.setattr(openrouter.time, "sleep", lambda s: None)
    client = httpx.Client(transport=httpx.MockTransport(answer))
    model = "openrouter:qwen/qwen3.8-27b@darkbloom/fp4"
    assert openrouter.transcribe(b"png", model, "Read it.", 120, client) == "keek.’\nagain"
    body = sent[-1]
    assert body["model"] == "qwen/qwen3.8-27b"
    assert body["provider"] == {
        "only": ["darkbloom/fp4"],
        "allow_fallbacks": False,
        "data_collection": "deny",
    }
    assert body["temperature"] == 0 and body["reasoning"] == {"enabled": False}
    assert body["messages"][0]["content"][0]["type"] == "image_url"


def test_a_hosted_name_must_name_its_provider():
    assert not openrouter.hosted("qwen3.8:27b-nvfp4")
    with pytest.raises(ValueError):
        openrouter.parse("openrouter:qwen/qwen3.8-27b")
