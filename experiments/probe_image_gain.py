"""Do qwen's own token probabilities mark the lines it reads wrong, even where every reader
agrees? (the deep-research reports, 2026-10-23: Fable's image-gain, Argon's runner-up margin).

On the frozen reader set: each line read with its crop as the pipeline asks it, keeping every
token's log-probability and its runner-ups; then the same prompt without the crop, the reading
fed back token by token, for each token's log-probability from the text alone. Per line, three
signals, each the weakest token's: its log-probability with the crop, its margin over the
runner-up, and its image-gain (with the crop minus without). Scored by how well each separates
the lines qwen reads wrong from those it reads right (AUC), over all lines and over the lines
where glm-ocr reads as qwen does, where no reader disagreement flags them.

    uv run python experiments/probe_image_gain.py          # read (cached), then score

A token missing from the text-only pass's top 20 gets the 20th's log-probability, a bound.
"""

import base64
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from tryout import READER_VERSION, WORK, load_set  # noqa: E402

from roboscriptorium.clients.retry import patiently  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.readers import MAX_LINE_TOKENS  # noqa: E402
from roboscriptorium.trustdata import fold  # noqa: E402

OUT = Path("work/probes/image-gain")
TOP = 20


def post(url: str, body: dict) -> dict:
    def call() -> dict:
        resp = httpx.post(url, json=body, timeout=600)
        resp.raise_for_status()
        return resp.json()

    return patiently(call)


def with_crop(png: bytes, prompt: str, settings: Settings) -> dict:
    d = post(
        f"{settings.ollama_url}/api/generate",
        {
            "model": settings.read_model, "prompt": prompt, "stream": False, "think": False,
            "images": [base64.b64encode(png).decode()], "logprobs": True, "top_logprobs": 5,
            "options": {"num_predict": MAX_LINE_TOKENS, "temperature": 0},
        },
    )  # fmt: skip
    tokens = []
    for t in d.get("logprobs") or []:
        if "\n" in t["token"]:
            break
        tokens.append([t["token"], t["logprob"], [[a["token"], a["logprob"]] for a in t["top_logprobs"]]])
    return {"text": d["response"].strip().split("\n")[0].strip(), "tokens": tokens}


def without_crop(tokens: list, prompt: str, settings: Settings) -> list[float]:
    out = []
    prefix = ""
    for tok, _, _ in tokens:
        d = post(
            f"{settings.ollama_url}/api/chat",
            {
                "model": settings.read_model, "stream": False, "think": False,
                "messages": [{"role": "user", "content": prompt}]
                + ([{"role": "assistant", "content": prefix}] if prefix else []),
                "logprobs": True, "top_logprobs": TOP,
                "options": {"num_predict": 1, "temperature": 0},
            },
        )  # fmt: skip
        top = (d.get("logprobs") or [{}])[0].get("top_logprobs", [])
        found = [a["logprob"] for a in top if a["token"] == tok]
        out.append(found[0] if found else (top[-1]["logprob"] if top else -30.0))
        prefix += tok
    return out


def auc(scores: list[float], wrong: list[bool]) -> float:
    """P(a wrong line scores lower than a right one), ties half."""
    bad = [s for s, w in zip(scores, wrong, strict=True) if w]
    good = [s for s, w in zip(scores, wrong, strict=True) if not w]
    if not bad or not good:
        return float("nan")
    pairs = sum((b < g) + 0.5 * (b == g) for b in bad for g in good)
    return pairs / (len(bad) * len(good))


if __name__ == "__main__":
    settings = Settings.from_env()
    books, items = load_set()
    OUT.mkdir(parents=True, exist_ok=True)
    img_path, txt_path = OUT / "with-crop.json", OUT / "without-crop.json"
    img = json.loads(img_path.read_text()) if img_path.exists() else {}
    txt = json.loads(txt_path.read_text()) if txt_path.exists() else {}
    for n, i in enumerate(items, 1):
        prompt = books[i["book"]]["prompt"]
        if i["id"] not in img:
            img[i["id"]] = with_crop(i["png"], prompt, settings)
        if i["id"] not in txt:
            txt[i["id"]] = without_crop(img[i["id"]]["tokens"], prompt, settings)
        if n % 25 == 0 or n == len(items):
            img_path.write_text(json.dumps(img, ensure_ascii=False))
            txt_path.write_text(json.dumps(txt, ensure_ascii=False))
            print(f"{n}/{len(items)}", flush=True)
    glm = json.loads(
        (WORK / f"reader-v{READER_VERSION}" / "readings" / "glm-ocr_bf16.json").read_text()
    )
    rows = []
    for i in items:
        r = img[i["id"]]
        if not r["tokens"]:
            continue
        lps = [t[1] for t in r["tokens"]]
        margins = [t[1] - max((a[1] for a in t[2] if a[0] != t[0]), default=-30.0) for t in r["tokens"]]
        gains = [a - b for a, b in zip(lps, txt[i["id"]], strict=True)]
        wrong = fold(r["text"]) != fold(i["truth"])
        agree = fold(glm[i["id"]]) == fold(r["text"])
        rows.append((min(lps), min(margins), min(gains), wrong, agree, i["stratum"]))
    for name, keep in (("all lines", lambda r: True), ("glm-ocr agrees", lambda r: r[4])):
        sel = [r for r in rows if keep(r)]
        wrong = [r[3] for r in sel]
        print(f"\n{name}: {len(sel)} lines, qwen wrong on {sum(wrong)}")
        for k, signal in enumerate(("log-probability", "runner-up margin", "image-gain")):
            scores = [r[k] for r in sel]
            ranked = sorted(zip(scores, wrong, strict=True))
            caught = sum(w for _, w in ranked[: max(1, len(sel) // 10)])
            print(f"  {signal:18} AUC {auc(scores, wrong):.3f}   wrong among the lowest tenth {caught}")
