"""Step two of proofreading: where a model's own reading of the crop differs from the
answer, the same model (text only) judges which of the two a carefully edited book prints.

Reads `probe_proofread.py --read` results; P(reading) against P(answer) from the first
answer token's `top_logprobs`.

    uv run python experiments/probe_proofread_judge.py MODEL [--think]

Generative models don't reliably answer with one letter. Without `--think` the answer is
read from the first token's probabilities (and how much of them fall on A or B is
shown). With `--think` the model answers freely, thinking first, and a decision model
(winnow, through Ollaya) reads that reply and answers a typed choice: A, B or unsure.
"""

import json
import math
import re
import sys
from pathlib import Path

import httpx
from probe_proofread import fold
from rapidfuzz import fuzz

from roboscriptorium.clients import ollaya
from roboscriptorium.config import Settings

OUT = Path("work/probes/proofread/stella")
ASK = (
    "Two transcriptions of the same passage from a published Dutch novel differ. One is "
    "a careful human's, one an OCR model's. Which one is what a carefully edited Dutch "
    "book prints, letter for letter, including accents, quote marks and punctuation?\n\n"
    "A: {a}\n\nB: {b}\n\nAnswer with one letter: A or B."
)


EXTRACT = ollaya.choice(
    "A model was asked which of two transcriptions, A or B, a carefully edited book "
    "prints, and replied as given. Which one did the reply settle on?",
    {"A": "transcription A", "B": "transcription B",
     "unsure": "neither, or the reply doesn't decide"},
)  # fmt: skip


def pick_thinking(model: str, a: str, b: str, url: str, extractor) -> tuple[float, str]:
    """P(B) as the decision model reads the generative model's free reply, and the reply."""
    payload = {"model": model, "prompt": ASK.format(a=a, b=b), "stream": False, "think": True,
               "options": {"temperature": 0, "num_predict": 4000}}  # fmt: skip
    r = httpx.post(f"{url}/api/generate", json=payload, timeout=1800)
    r.raise_for_status()
    reply = r.json()["response"].strip()
    answer = extractor.decide({"A": a, "B": b, "reply": reply}, {"which": EXTRACT})["which"]
    p = answer.probabilities or {}
    total = p.get("A", 0) + p.get("B", 0)
    return (p.get("B", 0) / total if total else math.nan), reply


def pick(model: str, a: str, b: str, url: str) -> float:
    """P(B) against P(A), from the first answer token."""
    payload = {"model": model, "prompt": ASK.format(a=a, b=b), "stream": False, "think": False,
               "logprobs": True, "top_logprobs": 10, "options": {"num_predict": 1, "temperature": 0}}
    r = httpx.post(f"{url}/api/generate", json=payload, timeout=900)
    r.raise_for_status()
    p = {"A": 0.0, "B": 0.0}
    for t in r.json()["logprobs"][0]["top_logprobs"]:
        if (token := t["token"].strip().upper()) in p:
            p[token] += math.exp(t["logprob"])
    if p["A"] + p["B"] < 0.5:
        print(f"  (only {p['A'] + p['B']:.2f} of the first token's probability is A or B)")
    return p["B"] / (p["A"] + p["B"]) if p["A"] + p["B"] else math.nan


def main(model: str, think: bool) -> None:
    settings = Settings.from_env()
    url = settings.ollama_url
    extractor = ollaya.for_model(settings.check_model, settings.ollaya_url, url)
    name = model.replace(":", "_").replace("/", "_")
    results = json.loads((OUT / f"{name}-read.json").read_text())
    for r in results:
        dash = lambda t: re.sub(r"\s*-\s*", "-", fold(t))  # noqa: E731
        a, full = dash(r["text"]), dash(r["reading"])
        m = fuzz.partial_ratio_alignment(a, full)
        g = full[m.dest_start : m.dest_end]
        if g == a:
            continue
        # Each order once, so the answer's position doesn't decide.
        if think:
            p1, reply = pick_thinking(model, a, g, url, extractor)
            p2, _ = pick_thinking(model, g, a, url, extractor)
            p = (p1 + 1 - p2) / 2
            print(f"  reply: {reply[:160]!r}")
        else:
            p = (pick(model, a, g, url) + 1 - pick(model, g, a, url)) / 2
        truth = dash(r["truth"])
        right = "reading" if g == truth else "answer" if a == truth else "neither"
        verdict = "reading" if p > 0.5 else "answer"
        print(f"p{r['page']:<3} P(reading) {p:.2f} → {verdict:7} truth: {right:8} "
              f"answer {a[:50]!r} | reading {g[:50]!r}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], "--think" in sys.argv)
