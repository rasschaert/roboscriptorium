"""Client for Ollama, used for everything that generates text."""

import base64
from pathlib import Path

import httpx


class OllamaClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None):
        # Vision models on full book pages can take minutes per call.
        self._http = client or httpx.Client(base_url=base_url, timeout=600)

    def models(self) -> list[str]:
        resp = self._http.get("/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json()["models"]]

    def generate(
        self,
        model: str,
        prompt: str,
        images: list[Path] | None = None,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if images:
            payload["images"] = [base64.b64encode(p.read_bytes()).decode() for p in images]
        resp = self._http.post("/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json()["response"]
