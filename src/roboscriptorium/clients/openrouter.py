"""Client for OpenRouter, a hosted model served where the local machine is too slow.

A model is named `openrouter:<model>@<provider tag>` ("openrouter:qwen/qwen3.8-27b@
darkbloom/fp4"): one provider at one precision, never a fallback to another, so a
cache keyed on the name holds one model's output. Providers that keep prompts are
refused (`data_collection`). The key is `OPENROUTER_API_KEY`.
"""

import base64
import os
import time

import httpx

PREFIX = "openrouter:"
URL = "https://openrouter.ai/api/v1/chat/completions"
RETRIES = 5


def hosted(model: str) -> bool:
    return model.startswith(PREFIX)


def parse(model: str) -> tuple[str, str]:
    """The model and the provider tag in an `openrouter:` name."""
    name, _, provider = model.removeprefix(PREFIX).partition("@")
    if not provider:
        raise ValueError(f"{model!r} names no provider: openrouter:<model>@<provider tag>")
    return name, provider


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
        "provider": {"only": [provider], "allow_fallbacks": False, "data_collection": "deny"},
    }


def transcribe(
    png: bytes, model: str, prompt: str, max_tokens: int, client: httpx.Client | None = None
) -> str:
    """The hosted model's reply to one image; rate limits and server errors are retried."""
    http = client or httpx.Client(timeout=300)
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    for attempt in range(RETRIES):
        resp = http.post(URL, json=payload(model, prompt, png, max_tokens), headers=headers)
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < RETRIES - 1:
            time.sleep(2**attempt)
            continue
        resp.raise_for_status()
        body = resp.json()
        if "choices" not in body:
            raise RuntimeError(f"OpenRouter: {body.get('error', body)}")
        return body["choices"][0]["message"]["content"] or ""
    raise RuntimeError("unreachable")
