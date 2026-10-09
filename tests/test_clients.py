import json

import httpx

from roboscriptorium.clients import decide
from roboscriptorium.clients.decide import DecisionClient
from roboscriptorium.clients.ollama import OllamaClient


def _http(handler) -> httpx.Client:
    return httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))


def test_decide_parses_all_question_types():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "answers": {
                    "role": {
                        "type": "choice",
                        "choice": "page_number",
                        "confidence": 0.86,
                        "probabilities": {"page_number": 0.9, "body": 0.1},
                    },
                    "garbled": {"type": "noul", "noul": 0.2},
                    "quality": {
                        "type": "score",
                        "score": 1.08,
                        "confidence": 0.14,
                        "probabilities": {"0": 0.25, "1": 0.43, "2": 0.32},
                    },
                }
            },
        )

    client = DecisionClient("http://test", "laya:multilingual", client=_http(handler))
    answers = client.decide(
        {"line": "Io", "note": "scène"},
        {
            "role": decide.choice("?", {"page_number": "", "body": ""}),
            "garbled": decide.noul("?"),
            "quality": decide.score("?", ["bad", "ok", "good"]),
        },
    )

    assert answers["role"].value == "page_number"
    assert answers["garbled"].value == 0.2
    assert answers["garbled"].confidence == 0.8
    assert answers["quality"].value == 1.08
    # Dict states are sent as JSON without escaping non-ASCII text.
    assert "scène" in seen["body"]


def test_generate_sends_images_and_returns_text(tmp_path):
    image = tmp_path / "page.png"
    image.write_bytes(b"png")

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.read())["images"] == ["cG5n"]
        return httpx.Response(200, json={"response": "tekst"})

    client = OllamaClient("http://test", client=_http(handler))
    assert client.generate("gemma4:latest", "OCR this", images=[image]) == "tekst"


def test_a_decision_model_is_asked_on_ollama_unless_a_hosted_build_is_named():
    local = decide.for_model("clef:27b", "http://ollama")
    assert isinstance(local, DecisionClient)
    assert local.model == "clef:27b"
    assert str(local._http.base_url) == "http://ollama"

    via = "openrouter:cloudflare/clef@cloudflare"
    hosted = decide.for_model("clef:27b", "http://ollama", via)
    assert isinstance(hosted, decide.HostedClient)
    assert (hosted.model, hosted.via) == ("clef:27b", via)
