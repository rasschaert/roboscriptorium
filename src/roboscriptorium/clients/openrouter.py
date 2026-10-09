"""Client for OpenRouter, a hosted model served where the local machine is too slow.

A model is named `openrouter:<model>@<provider tag>` ("openrouter:qwen/qwen3.8-27b@
darkbloom/fp4"): one provider at one precision, never a fallback to another, so a
cache keyed on the name holds one model's output. Providers that keep prompts are
refused (`data_collection`). The key is `OPENROUTER_API_KEY`.

Decision models answer through `/api/alpha/decisions` (`decide`), which takes the
image inside the state and bills the model's whole context on every call.
"""

import base64
import json
import os
import time

import httpx

PREFIX = "openrouter:"
URL = "https://openrouter.ai/api/v1/chat/completions"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
RETRIES = 5
_CLIENT: httpx.Client | None = None
# Whole seconds a request may take: a stalled provider keeps the connection open with
# keep-alive bytes, so httpx's read timeout never fires.
DEADLINE = 120


class Stalled(Exception):
    pass


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
    """The response to one request; rate limits, server errors and stalls are retried."""
    http = client or _shared()
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    for attempt in range(RETRIES):
        last = attempt == RETRIES - 1
        try:
            status, content = _within_deadline(http, url, body, headers)
        except (Stalled, httpx.TimeoutException):
            if last:
                raise
            time.sleep(2**attempt)
            continue
        if status in (429, 500, 502, 503, 504) and not last:
            time.sleep(2**attempt)
            continue
        if status >= 400:
            raise httpx.HTTPStatusError(
                f"OpenRouter: {status} {content[:200]!r}",
                request=httpx.Request("POST", url),
                response=httpx.Response(status, content=content),
            )
        return json.loads(content)
    raise RuntimeError("unreachable")


def _shared() -> httpx.Client:
    """One client for every request, so hosted lines reuse a connection."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = httpx.Client(timeout=300)
    return _CLIENT


def _within_deadline(http: httpx.Client, url: str, body: dict, headers: dict) -> tuple[int, bytes]:
    start = time.monotonic()
    with http.stream("POST", url, json=body, headers=headers) as resp:
        chunks = []
        for chunk in resp.iter_bytes():
            chunks.append(chunk)
            if time.monotonic() - start > DEADLINE:
                raise Stalled(url)
        return resp.status_code, b"".join(chunks)


def decide(
    model: str, state: str, questions: dict, png: bytes | None, client: httpx.Client | None = None
) -> dict:
    """The hosted decision model's answers, as Ollama's `/v1/systemone` gives them."""
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
    choice = body["choices"][0]
    content = choice.get("message", {}).get("content")
    # A provider error can come back as a 200 with no content; caching it as an empty
    # reading would stand for the model's reading on every later run.
    if content is None or choice.get("finish_reason") == "error" or "error" in choice:
        raise RuntimeError(f"OpenRouter: no reading ({choice.get('error', choice)})")
    return content
