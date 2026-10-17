import httpx
import pytest

from roboscriptorium.clients import decide


def test_a_token_client_asks_in_the_trained_layout_and_reads_the_labels():
    import json as _json

    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = _json.loads(request.content)
        sent.append(body)
        alts = [{"token": "B", "logprob": -0.2}, {"token": " A", "logprob": -1.8},
                {"token": "C", "logprob": -9.0}]  # fmt: skip
        return httpx.Response(200, json={"response": "B", "logprobs": [{"top_logprobs": alts}]})

    http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    client = decide.for_model("tokens:big-judge", "http://test")
    client._http = http
    question = decide.choice("Which <one>?", {"b": "“later”", "a": "“first”"})
    (answer,) = client.decide({"line": "x<y"}, {"reading": question}).values()
    (body,) = sent
    assert body["model"] == "big-judge" and body["raw"] and body["options"]["num_predict"] == 1
    prompt = body["prompt"]
    assert prompt.startswith("<|turn>system\nYou answer classification questions")
    assert 'State:\n{"line":"x\\u003cy"}\n' in prompt
    assert 'Question: "Which \\u003cone>?"\nOptions:\nA: "a: “first”"\nB: "b: “later”"\n' in prompt
    assert prompt.endswith("Return the correct letter label.<turn|>\n<|turn>model\n"
                           "<|channel>thought\n<channel|>Answer:\n")  # fmt: skip
    assert answer.value == "b" and answer.probabilities["b"] > 0.8
    assert 0 < answer.confidence < 1
    with pytest.raises(ValueError):
        client.decide("x", {"reading": question}, image_png=b"png")
