"""Probe: the decision models' time per call, one at a time against four at a time,
on Ollama's /v1/systemone with a line crop each (a choice question like the judges'),
on disjoint fresh sets. Results in work/probes/decide-parallel.json.

    uv run python experiments/probe_decide_parallel.py [calls per set]
"""

import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

sys.path.insert(0, "experiments")
from probe_qwen_speed import crops_from  # noqa: E402

URL = "http://127.0.0.1:11434/v1/systemone"
MODELS = ("clef-flash:9b", "clef:27b", "winnow-ollama:e4b")
OUT = Path("work/probes/decide-parallel.json")
QUESTIONS = {
    "reading": {
        "type": "choice",
        "instructions": "Which version of the marked words matches the print in the image?",
        "criteria": {"ours": "the first version", "other": "the second version",
                     "neither": "the image shows neither"},
    }
}


def call(model: str, text: str, png: bytes) -> dict:
    body = {"model": model, "state": json.dumps({"line": text, "versions": [text, text + "."]}),
            "questions": QUESTIONS, "images": [base64.b64encode(png).decode()]}
    r = httpx.post(URL, json=body, timeout=600).json()
    return r["answers"]["reading"] if "answers" in r else r


def run_set(model: str, items: list, workers: int) -> tuple[list, float]:
    start = time.time()
    with ThreadPoolExecutor(workers) as pool:
        out = list(pool.map(lambda it: call(model, it[0], it[1]), items))
    return out, time.time() - start


per_set = int(sys.argv[1]) if len(sys.argv) > 1 else 16
lines = crops_from(80, per_set * 3)
sets = [lines[i * per_set : (i + 1) * per_set] for i in range(3)]
results = {}
for model in MODELS:
    call(model, *sets[0][0])  # load before timing
    res = {}
    for workers, items in ((1, sets[0]), (4, sets[1])):
        answers, took = run_set(model, items, workers)
        bad = [a for a in answers if "choice" not in a]
        res[f"x{workers}"] = {"s_per_call": took / per_set, "errors": bad[:2]}
        print(f"{model:18} {workers} at a time: {took / per_set:5.2f} s a call"
              + (f"  ERRORS {bad[:1]}" if bad else ""), flush=True)
    again, _ = run_set(model, sets[0], 4)
    base, _ = run_set(model, sets[0], 1) if False else (None, 0)
    first, _ = run_set(model, sets[0], 1)
    differ = sum(a.get("choice") != b.get("choice") for a, b in zip(first, again))
    drift = max(abs(a.get("confidence", 0) - b.get("confidence", 0)) for a, b in zip(first, again))
    res["set1 x4 vs x1"] = {"choices_differ": differ, "max_confidence_drift": drift}
    print(f"{model:18} set 1 at 4 against 1 at a time: {differ} of {per_set} choices differ, "
          f"confidence drifts at most {drift:.4f}", flush=True)
    results[model] = res
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
