import math

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


def test_shisa_is_asked_in_its_makers_layout_in_the_questions_order():
    import json as _json

    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(_json.loads(request.content))
        alts = [{"token": "A", "logprob": -0.1}, {"token": "D", "logprob": -0.5},
                {"token": "B", "logprob": -2.4}]  # fmt: skip
        return httpx.Response(200, json={"response": "A", "logprobs": [{"top_logprobs": alts}]})

    client = decide.for_model("tokens:hf.co/mradermacher/shisa-de-1-GGUF:Q8_0", "http://test")
    assert isinstance(client, decide.ShisaTokenClient)
    client._http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    question = decide.choice("Which <one>?", {"b": "“later”", "a": ""})
    (answer,) = client.decide({"line": "x<y"}, {"reading": question}).values()
    (body,) = sent
    assert body["model"] == "hf.co/mradermacher/shisa-de-1-GGUF:Q8_0"
    assert body["prompt"] == (
        "<|turn>system\nApply the supplied criterion to the supplied evidence. Choose exactly "
        "one listed option. Respond with only its uppercase letter, with no explanation or "
        "reasoning.<turn|>\n<|turn>user\n"
        '{"evidence": {"line": "x<y"}, "criterion": "Which <one>?", "options": '
        '[{"letter": "A", "description": "“later”"}, {"letter": "B", "description": "a"}]}'
        "<turn|>\n<|turn>model\n<|channel>thought\n<channel|>"
    )
    # D is no option; A and B are 2.3 apart, softened by the temperature of 1.9.
    assert answer.value == "b"
    assert answer.probabilities["b"] == pytest.approx(1 / (1 + math.exp(-2.3 / 1.9)))


def test_shisa_takes_an_image_before_its_json_and_winnow_refuses_one():
    import json as _json

    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(_json.loads(request.content))
        alts = [{"token": "A", "logprob": -0.1}, {"token": "B", "logprob": -2.0}]
        return httpx.Response(200, json={"response": "A", "logprobs": [{"top_logprobs": alts}]})

    transport = httpx.MockTransport(handler)
    shisa = decide.for_model("tokens:shisa-de-1", "http://test")
    shisa._http = httpx.Client(base_url="http://test", transport=transport)
    question = decide.choice("Which text?", {"a": "één", "b": "een"})
    (answer,) = shisa.decide({"line": 3}, {"reading": question}, image_png=b"png").values()
    (body,) = sent
    assert body["images"] == ["cG5n"]
    assert '<|turn>user\n[img-0]{"evidence": {"line": 3}' in body["prompt"]
    assert answer.value == "a"
    winnow = decide.for_model("tokens:winnow", "http://test")
    with pytest.raises(ValueError):
        winnow.decide("x", {"reading": question}, image_png=b"png")


def test_selfjev_scores_each_option_by_yes_against_no():
    import json as _json

    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = _json.loads(request.content)
        sent.append(body)
        right = "Proposed answer: één" in body["prompt"]
        alts = [{"token": "yes", "logprob": -0.1 if right else -3.0},
                {"token": "no", "logprob": -2.5 if right else -0.1}]  # fmt: skip
        return httpx.Response(200, json={"response": "yes", "logprobs": [{"top_logprobs": alts}]})

    client = decide.for_model("tokens:hf.co/Jwuthrich/selfjev-4b-vision-GGUF:Q8_0", "http://test")
    assert isinstance(client, decide.SelfjevTokenClient)
    client._http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    question = decide.choice("Which text?", {"a": "één", "b": "een"})
    (answer,) = client.decide({"line": 3}, {"reading": question}, image_png=b"png").values()
    assert len(sent) == 2 and all(b["images"] == ["cG5n"] for b in sent)
    assert sent[0]["prompt"].startswith("<|im_start|>system\nJudge whether the proposed answer")
    assert (
        'Document:\n[img-0]\n{"line": 3}\nQuestion: Which text?\nProposed answer: één'
        in sent[0]["prompt"]
    )
    assert sent[0]["prompt"].endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n")
    # a: 2.4 - b: -2.9 → softmax of the two scores
    assert answer.value == "a"
    assert answer.probabilities["a"] == pytest.approx(1 / (1 + math.exp(-5.3)))


def test_shisa_de_2_keeps_de_1s_layout_with_its_own_temperature():
    two = decide.for_model("tokens:shisa-de-2:q8_0", "http://test")
    assert isinstance(two, decide.Shisa2TokenClient) and two.TEMPERATURE == 1.81
    assert isinstance(decide.for_model("tokens:shisa-de-1", "http://test"), decide.ShisaTokenClient)
    assert two.SYSTEM == decide.ShisaTokenClient.SYSTEM
