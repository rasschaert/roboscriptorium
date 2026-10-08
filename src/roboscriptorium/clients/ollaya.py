"""Client for decision models behind a Jev-compatible API: Ollaya's
`/api/decide`, or Ollama's `/v1/systemone` (e.g. clef-flash).

Use it for questions whose possible answers are known in advance. A bare string
is ambiguous to a decision model, so pass a dict state with context (position on
the page, neighbouring lines, page type) whenever possible.
"""

import base64
import json
from dataclasses import dataclass
from typing import Any

import httpx

from roboscriptorium.clients import openrouter
from roboscriptorium.clients.retry import patiently

# Decision models with these name prefixes are served by Ollama's /v1/systemone.
OLLAMA_PREFIXES = ("clef",)


def choice(instructions: str, criteria: dict[str, str]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score(instructions: str, levels: list[str]) -> dict[str, Any]:
    return {"type": "score", "instructions": instructions, "criteria": levels}


def noul(instructions: str) -> dict[str, Any]:
    return {"type": "noul", "instructions": instructions}


@dataclass(frozen=True)
class Answer:
    """One answered question.

    `value` is the chosen option for `choice`, the expected level (a float index
    into the levels) for `score`, and the probability of "true" for `noul`.
    """

    type: str
    value: Any
    confidence: float
    probabilities: dict[str, float]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Answer":
        kind = data["type"]
        if kind == "noul":
            p = data["noul"]
            return cls(kind, p, max(p, 1 - p), {"true": p, "false": 1 - p})
        return cls(kind, data[kind], data["confidence"], data["probabilities"])


class OllayaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        client: httpx.Client | None = None,
        endpoint: str = "/api/decide",
    ):
        self.model = model
        self.endpoint = endpoint
        self._http = client or httpx.Client(base_url=base_url, timeout=300)

    def models(self) -> list[str]:
        resp = self._http.get("/v1/models")
        resp.raise_for_status()
        return [m["name"] for m in resp.json()["models"]]

    def decide(
        self,
        state: str | dict[str, Any],
        questions: dict[str, dict[str, Any]],
        model: str | None = None,
        image_png: bytes | None = None,
    ) -> dict[str, Answer]:
        """Answer questions about a state; vision models also take one PNG (at most ~1 MP)."""
        if not isinstance(state, str):
            state = json.dumps(state, ensure_ascii=False)
        payload: dict[str, Any] = {
            "model": model or self.model,
            "state": state,
            "questions": questions,
        }
        if image_png is not None:
            payload["images"] = [base64.b64encode(image_png).decode()]
        resp = patiently(lambda: self._http.post(self.endpoint, json=payload))
        resp.raise_for_status()
        return {name: Answer.from_json(a) for name, a in resp.json()["answers"].items()}


class HostedClient:
    """A local decision model's questions answered by a hosted build of it (`via`,
    `openrouter:<model>@<provider tag>`), under the local model's name, so the
    answers cache as the local model's."""

    def __init__(self, model: str, via: str, client: httpx.Client | None = None):
        self.model = model
        self.via = via
        self._http = client or httpx.Client(timeout=300)

    def decide(
        self,
        state: str | dict[str, Any],
        questions: dict[str, dict[str, Any]],
        model: str | None = None,
        image_png: bytes | None = None,
    ) -> dict[str, Answer]:
        if not isinstance(state, str):
            state = json.dumps(state, ensure_ascii=False)
        answers = openrouter.decide(self.via, state, questions, image_png, self._http)
        return {name: Answer.from_json(a) for name, a in answers.items()}


def for_model(
    model: str, ollaya_url: str, ollama_url: str, via: str = ""
) -> "OllayaClient | HostedClient":
    """A client on whichever runtime serves this decision model, or on its hosted
    build `via`."""
    if via:
        return HostedClient(model, via)
    if model.startswith(OLLAMA_PREFIXES):
        return OllayaClient(ollama_url, model, endpoint="/v1/systemone")
    return OllayaClient(ollaya_url, model)
