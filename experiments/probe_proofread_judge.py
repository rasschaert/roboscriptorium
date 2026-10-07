"""Step two of proofreading: where a model's own reading of the crop differs from the
answer, the same model (text only) judges which of the two a carefully edited book prints.

Reads `probe_proofread.py --read` results; P(reading) against P(answer) from the first
answer token's `top_logprobs`.

    uv run python experiments/probe_proofread_judge.py MODEL
"""

import json
import math
import re
import sys
from pathlib import Path

import httpx
from probe_proofread import fold
from rapidfuzz import fuzz

from roboscriptorium.config import Settings

OUT = Path("work/probes/proofread/stella")
ASK = (
    "Two transcriptions of the same passage from a published Dutch novel differ. One is "
    "a careful human's, one an OCR model's. Which one is what a carefully edited Dutch "
    "book prints, letter for letter, including accents, quote marks and punctuation?\n\n"
    "A: {a}\n\nB: {b}\n\nAnswer with one letter: A or B."
)


def pick(model: str, a: str, b: str, url: str) -> float:
    """P(B) against P(A)."""
    payload = {"model": model, "prompt": ASK.format(a=a, b=b), "stream": False, "think": False,
               "logprobs": True, "top_logprobs": 10, "options": {"num_predict": 1, "temperature": 0}}
    r = httpx.post(f"{url}/api/generate", json=payload, timeout=900)
    r.raise_for_status()
    p = {"A": 0.0, "B": 0.0}
    for t in r.json()["logprobs"][0]["top_logprobs"]:
        if t["token"].strip() in p:
            p[t["token"].strip()] += math.exp(t["logprob"])
    return p["B"] / (p["A"] + p["B"]) if p["A"] + p["B"] else math.nan


def main(model: str) -> None:
    url = Settings.from_env().ollama_url
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
        p = (pick(model, a, g, url) + 1 - pick(model, g, a, url)) / 2
        truth = dash(r["truth"])
        right = "reading" if g == truth else "answer" if a == truth else "neither"
        verdict = "reading" if p > 0.5 else "answer"
        print(f"p{r['page']:<3} P(reading) {p:.2f} → {verdict:7} truth: {right:8} "
              f"answer {a[:50]!r} | reading {g[:50]!r}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
