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


def test_a_hosted_decision_answers_under_the_local_name(monkeypatch):
    from roboscriptorium.clients import ollaya

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    sent = []

    def answer(request):
        sent.append(json.loads(request.content))
        reading = {"type": "choice", "choice": "b", "confidence": 0.8,
                   "probabilities": {"a": 0.1, "b": 0.9}}  # fmt: skip
        return httpx.Response(200, json={"answers": {"reading": reading}})

    http = httpx.Client(transport=httpx.MockTransport(answer))
    client = ollaya.HostedClient("clef:27b", "openrouter:cloudflare/clef@primeintellect", http)
    question = {"reading": ollaya.choice("Which?", {"a": "x", "b": "y"})}
    got = client.decide({"page": 3}, question, image_png=b"png")["reading"]
    assert (client.model, got.value, got.probabilities["b"]) == ("clef:27b", "b", 0.9)
    body = sent[0]
    assert body["model"] == "cloudflare/clef"
    assert body["provider"]["only"] == ["primeintellect"]
    assert [part["type"] for part in body["state"]] == ["image_url", "text"]
    assert body["state"][1]["text"] == '{"page": 3}'
