"""Nemotron-3.5-Bolt-74B-A9B (IQ2_XXS, vision, thinking) on samples of the frozen sets.

    uv run python experiments/probe_nemotron.py [model]

Two parts, each capped in minutes, so there is an answer whatever its pace:

reader: a seeded sample of the reader set (`tryouts/reader-v2.json`) read as the pipeline
  reads a line (`readers.transcribe`, told the book's style, thinking off), against the text
  layer and the readings the book caches hold for qwen3.8 and glm-ocr on the same crops.
judge:  the context judge's prompt (`work/probes/context-judge/items.json`: the lines around an
  OCR suspect, the versions) on a seeded sample of the 100 items qwen3.8 answered locally,
  thinking off, one token read for the letter, against qwen3.8's pick and the arbiter's.

Readings and answers are kept in work/probes/nemotron/ (they quote the books).
"""

import base64
import json
import math
import random
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import tryout  # noqa: E402

from roboscriptorium import readers  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "hf.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF"
OUT = Path("work/probes/nemotron")
READER_EACH, JUDGE_EACH, CAP_MINUTES = 25, 20, 25
settings = Settings.from_env()
OUT.mkdir(parents=True, exist_ok=True)


def sample(items: list[dict], each: int, seed: int = 1) -> list[dict]:
    out = []
    for stratum in ("hard", "control"):
        pool = sorted((i for i in items if i["stratum"] == stratum), key=lambda i: i["id"])
        out += random.Random(seed).sample(pool, min(each, len(pool)))
    return out


def reader_part() -> None:
    books, items = tryout.load_set()
    incumbents = {}
    for label, stage, prompt_of in (
        (settings.read_model, "third-reading.json", lambda n: books[n]["prompt"]),
        (settings.ocr_model, "second-reading.json", None),
    ):
        seeded = tryout.stage_readings(items, stage, prompt_of)
        incumbents[label] = {k: t for k, (t, via) in seeded.items() if not via}
    items = [i for i in items if all(i["id"] in r for r in incumbents.values())]
    sub = sample(items, READER_EACH)
    path = OUT / "reader-readings.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    start, seconds = time.time(), []
    for n, i in enumerate(sub, 1):
        if i["id"] in done:
            continue
        if time.time() - start > CAP_MINUTES * 60:
            print(f"reader: time cap after {n - 1} of {len(sub)} lines")
            break
        t0 = time.time()
        done[i["id"]] = readers.transcribe(i["png"], MODEL, settings.ollama_url, books[i["book"]]["prompt"])
        seconds.append(time.time() - t0)
        path.write_text(json.dumps(done, ensure_ascii=False))
        if n % 10 == 0:
            print(f"  reader {n}/{len(sub)}, {statistics.median(seconds):.1f} s a line", flush=True)
    sub = [i for i in sub if i["id"] in done]
    layer = {i["id"]: i["layer"] for i in sub}
    rows = [tryout.score("text layer", layer, sub, incumbents)]
    rows += [
        tryout.score(n, r, sub, {k: v for k, v in incumbents.items() if k != n})
        for n, r in incumbents.items()
    ]
    rows.append(tryout.score("nemotron", done, sub, incumbents))
    print(f"\nreader sample: {len(sub)} lines ({sum(i['stratum'] == 'hard' for i in sub)} hard)")
    for r in rows:
        h, c = r["hard"], r["control"]
        print(
            f"  {r['model'][:30]:30} hard right {h['right']}/{h['lines']} CER {h['cer']:.2%}   "
            f"control right {c['right']}/{c['lines']} CER {c['cer']:.2%}   quote lines wrong "
            f"{h['quote_lines_wrong']}/{c['quote_lines_wrong']}"
        )
    if seconds:
        print(f"  nemotron: {statistics.median(seconds):.1f} s a line (median of {len(seconds)})")


def ask_letter(prompt: str, options: int) -> tuple[int, str]:
    """The context judge's prompt put to Nemotron, thinking off: the index of the version it
    picks (-1 for none), and how it was read ("logprobs", or "text" from the first letter)."""
    labels = "ABCDEFGH"[:options]
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "logprobs": True,
        "top_logprobs": 20,
        # A batch above 16 segfaults the runner on this Ollama build (Metal); 16 runs.
        "options": {"temperature": 0, "num_predict": 4, "num_batch": 16},
    }
    resp = httpx.post(f"{settings.ollama_url}/api/chat", json=body, timeout=600)
    resp.raise_for_status()
    data = resp.json()
    top = ((data.get("logprobs") or [{}])[0] or {}).get("top_logprobs", [])
    best = {}
    for t in top:
        label = t["token"].strip()
        if label in labels and label not in best:
            best[label] = t["logprob"]
    if best:
        return labels.index(max(best, key=best.__getitem__)), "logprobs"
    text = (data.get("message", {}).get("content") or "").strip()
    for ch in text:
        if ch in labels:
            return labels.index(ch), "text"
    return -1, f"none: {text[:40]!r}"


def judge_part() -> None:
    """Nemotron as the context judge, on the 100 probe items qwen3.8 answered locally (no
    counts in the prompt): each version picked from the lines around the place."""
    cj = Path("work/probes/context-judge")
    items = {i["id"]: i for i in json.loads((cj / "items.json").read_text())}
    qwen = {}
    for line in (cj / "answers-qwen3.8_27b-nvfp4-nocounts.jsonl").read_text().splitlines():
        if line.strip():
            a = json.loads(line)
            if a["id"] in items and a.get("pick", -1) >= 0:
                qwen[a["id"]] = a["pick"]
    ids = sorted(qwen)
    ids = random.Random(1).sample(ids, min(len(ids), JUDGE_EACH * 2))
    path = OUT / "judge-answers.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    start, seconds, how = time.time(), [], {}
    for n, k in enumerate(ids, 1):
        if k in done:
            continue
        if time.time() - start > CAP_MINUTES * 60:
            print(f"judge: time cap after {n - 1} of {len(ids)} items")
            break
        t0 = time.time()
        pick, mode = ask_letter(items[k]["prompt"], len(items[k]["versions"]))
        seconds.append(time.time() - t0)
        how[mode] = how.get(mode, 0) + 1
        done[k] = pick
        path.write_text(json.dumps(done))
        if n % 10 == 0:
            print(f"  judge {n}/{len(ids)}, {statistics.median(seconds):.1f} s a question", flush=True)
    ids = [k for k in ids if k in done]

    def right(k, pick):
        return pick >= 0 and bool(items[k]["right"][pick])

    def likeliest(k):
        arb = items[k]["arbiter"]
        return max(range(len(arb)), key=arb.__getitem__)

    print(f"\njudge sample: {len(ids)} suspects the arbiter would ask; Nemotron's answers read from {how}")
    for name, pick in (
        ("nemotron", lambda k: done[k]),
        ("qwen3.8 (thinking)", lambda k: qwen[k]),
        ("the arbiter's likeliest", likeliest),
    ):
        print(f"  {name:26} right on {sum(right(k, pick(k)) for k in ids)}/{len(ids)}")
    agree = [k for k in ids if done[k] == likeliest(k)]
    print(f"  nemotron agrees with the arbiter on {len(agree)}; of those the arbiter is right on "
          f"{sum(right(k, likeliest(k)) for k in agree)}")
    if seconds:
        print(f"  nemotron: {statistics.median(seconds):.1f} s a question (median of {len(seconds)})")


if __name__ == "__main__":
    print(f"{datetime.now(UTC):%H:%M} nemotron probe: {MODEL}")
    for part in (reader_part, judge_part):
        try:
            part()
        except Exception as error:  # a failed part must not hide the other's result
            print(f"{part.__name__} failed: {type(error).__name__}: {error}")
