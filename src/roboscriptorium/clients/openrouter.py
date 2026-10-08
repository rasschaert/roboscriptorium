"""Client for OpenRouter, a hosted model served where the local machine is too slow.

A model is named `openrouter:<model>@<provider tag>` ("openrouter:qwen/qwen3.8-27b@
darkbloom/fp4"): one provider at one precision, never a fallback to another, so a
cache keyed on the name holds one model's output. Providers that keep prompts are
refused (`data_collection`). The key is `OPENROUTER_API_KEY`.

Decision models answer through `/api/alpha/decisions` (`decide`), which takes the
image inside the state and bills the model's whole context on every call.
"""

import base64
import os
import time

import httpx

PREFIX = "openrouter:"
URL = "https://openrouter.ai/api/v1/chat/completions"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
RETRIES = 5


def hosted(model: str) -> bool:
    return model.startswith(PREFIX)


def parse(model: str) -> tuple[str, str]:
    """The model and the provider tag in an `openrouter:` name."""
    name, _, provider = model.removeprefix(PREFIX).partition("@")
    if not provider:
        raise ValueError(f"{model!r} names no provider: openrouter:<model>@<provider tag>")
    return name, provider


def _routing(provider: str) -> dict:
    return {"only": [provider], "allow_fallbacks": False, "data_collection": "deny"}


def payload(model: str, prompt: str, png: bytes, max_tokens: int) -> dict:
    """One image and its instruction, read as Ollama reads them: the image first,
    temperature 0, thinking off."""
    name, provider = parse(model)
    image = "data:image/png;base64," + base64.b64encode(png).decode()
    return {
        "model": name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning": {"enabled": False},
        "provider": _routing(provider),
    }


def decision_payload(model: str, state: str, questions: dict, png: bytes | None) -> dict:
    """A decision as Ollama's `/v1/systemone` takes it, the image first in the state."""
    name, provider = parse(model)
    parts: list[dict] = []
    if png is not None:
        image = "data:image/png;base64," + base64.b64encode(png).decode()
        parts.append({"type": "image_url", "image_url": {"url": image}})
    parts.append({"type": "text", "text": state})
    return {"model": name, "state": parts, "questions": questions, "provider": _routing(provider)}


def _post(url: str, body: dict, client: httpx.Client | None) -> dict:
    """The response to one request; rate limits and server errors are retried."""
    http = client or httpx.Client(timeout=300)
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    for attempt in range(RETRIES):
        resp = http.post(url, json=body, headers=headers)
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < RETRIES - 1:
            time.sleep(2**attempt)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("unreachable")


def decide(
    model: str, state: str, questions: dict, png: bytes | None, client: httpx.Client | None = None
) -> dict:
    """The hosted decision model's answers, as Ollaya's JSON gives them."""
    body = _post(DECISIONS_URL, decision_payload(model, state, questions, png), client)
    if "answers" not in body:
        raise RuntimeError(f"OpenRouter: {body.get('error', body)}")
    return body["answers"]


def transcribe(
    png: bytes, model: str, prompt: str, max_tokens: int, client: httpx.Client | None = None
) -> str:
    """The hosted model's reply to one image; rate limits and server errors are retried."""
    body = _post(URL, payload(model, prompt, png, max_tokens), client)
    if "choices" not in body:
        raise RuntimeError(f"OpenRouter: {body.get('error', body)}")
    return body["choices"][0]["message"]["content"] or ""
