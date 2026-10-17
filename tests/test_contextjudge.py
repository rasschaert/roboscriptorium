import json

import httpx

from roboscriptorium.clients.ollama import OllamaClient


def test_choose_reads_the_letters_probabilities_from_the_answer_token():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["think"] and body["format"]["properties"]["answer"]["enum"] == ["A", "B"]
        alts = [{"token": "B", "logprob": -0.1}, {"token": "A", "logprob": -2.4}]
        return httpx.Response(
            200,
            json={
                "message": {"content": '{"answer": "B"}', "thinking": "…"},
                "logprobs": [
                    {"token": '{"', "logprob": 0.0, "top_logprobs": []},
                    {"token": "B", "logprob": -0.1, "top_logprobs": alts},
                    {"token": '"}', "logprob": 0.0, "top_logprobs": []},
                ],
            },
        )

    http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    a, b = OllamaClient("http://test", client=http).choose("m", "which?", 2)
    assert b > 0.9 and abs(a + b - 1) < 1e-9
