import json

import httpx

from roboscriptorium import contextjudge
from roboscriptorium.clients.ollama import OllamaClient
from roboscriptorium.ocrcheck import Suspect
from roboscriptorium.pdf import Line, PageText


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


def test_choose_gives_no_answer_when_the_thinking_runs_out_its_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["options"]["num_predict"] == 10000
        return httpx.Response(
            200, json={"message": {"content": "", "thinking": "…"}, "done_reason": "length"}
        )

    http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    assert OllamaClient("http://test", client=http).choose("m", "which?", 2) == []


class _Judge:
    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def choose(self, model, prompt, options):
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def _suspect() -> Suspect:
    line = "Na een kwartier trofik hem nog steeds"
    return Suspect(3, 0, line, 16, 22, "trofik", ("trof ik",), (0, 0, 1, 1), "review")


def _settle(judge, tmp_path):
    pages = [PageText(3, 280, 400, [Line(_suspect().original, 10, 20, 250, 30)])]
    return contextjudge.settle(
        [_suspect()], pages, "nl", lambda s: 1, judge, "m", tmp_path / "cj.json"
    )


def test_a_judge_without_an_answer_leaves_the_suspect_asked(tmp_path):
    (s,) = _settle(_Judge([]), tmp_path)
    assert s.choice == "review"
    agreeing = _Judge([0.1, 0.9])
    (s,) = _settle(agreeing, tmp_path)
    assert s.choice == "review" and agreeing.calls == 0  # the empty answer is kept


def test_a_judge_that_times_out_leaves_the_suspect_asked_and_is_asked_again(tmp_path):
    (s,) = _settle(_Judge(httpx.ReadTimeout("slow")), tmp_path)
    assert s.choice == "review"
    (s,) = _settle(_Judge([0.1, 0.9]), tmp_path)
    assert s.choice == "other" and s.chosen == "trof ik"
