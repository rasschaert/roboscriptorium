"""Client for Ollama, used for everything that generates text."""

import base64
import json
import math
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

    def choose(self, model: str, prompt: str, options: int, limit: int = 10000) -> list[float]:
        """A thinking model's answer to a question of `options` lettered answers (A, B,
        …), held to those letters: each letter's probability, from the answer token's
        alternatives (the chosen letter alone when the server gives none). Empty when
        the thinking runs past `limit` tokens before an answer."""
        letters = [chr(ord("A") + i) for i in range(options)]
        resp = self._http.post(
            "/api/chat",
            json={
                "model": model,
                "stream": False,
                "think": True,
                "logprobs": True,
                "top_logprobs": 10,
                "messages": [{"role": "user", "content": prompt}],
                "format": {
                    "type": "object",
                    "properties": {"answer": {"type": "string", "enum": letters}},
                    "required": ["answer"],
                },
                "options": {"temperature": 0, "num_predict": limit},
            },
        )
        resp.raise_for_status()
        r = resp.json()
        if r.get("done_reason") == "length" or not r["message"].get("content"):
            return []
        answer = json.loads(r["message"]["content"])["answer"]
        probs = {answer: 1.0}
        for t in reversed(r.get("logprobs") or []):
            if t["token"].strip() == answer:
                probs = {}
                for alt in t["top_logprobs"]:
                    k = alt["token"].strip()
                    if k in letters and k not in probs:
                        probs[k] = math.exp(alt["logprob"])
                break
        total = sum(probs.values())
        return [probs.get(k, 0.0) / total for k in letters]
