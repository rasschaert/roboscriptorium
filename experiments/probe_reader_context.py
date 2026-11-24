"""Does the line reader's memory grow less at a smaller context, and does it read the same?
The silent screen's frozen line crops (work/probes/silent-screen/crops) read by the reader,
four at a time as the build reads them, at one `num_ctx`; Ollama's size for the model
(`/api/ps`) logged every 25 lines. Run once per context, the model unloaded before each.

    uv run python experiments/probe_reader_context.py <num_ctx|default> [rounds]

Writes work/probes/reader-context/<ctx>.json (each crop's reading, the sizes) as it goes,
so a stop keeps what was read. Compare two contexts with `--compare a b`.
"""

import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from roboscriptorium.config import Settings
from roboscriptorium.files import write_atomic
from roboscriptorium.readers import MAX_LINE_TOKENS, READ_WORKERS

OUT = Path("work/probes/reader-context")
CROPS = Path("work/probes/silent-screen/crops")
OLLAMA = "http://127.0.0.1:11434"
PROMPT = (
    "Transcribe the printed text in this image exactly as printed: every letter, accent, "
    "quote mark, dash and punctuation mark. It is one line of a book. Output only the text."
)


def size(model: str) -> float:
    found = httpx.get(f"{OLLAMA}/api/ps", timeout=10).json()["models"]
    return round(sum(m["size"] for m in found if m["name"] == model) / 1e9, 1)


def read(model: str, ctx: str, png: bytes) -> str:
    options = {"num_predict": MAX_LINE_TOKENS, "temperature": 0}
    if ctx != "default":
        options["num_ctx"] = int(ctx)
    body = {"model": model, "prompt": PROMPT, "images": [base64.b64encode(png).decode()],
            "stream": False, "think": False, "options": options}  # fmt: skip
    r = httpx.post(f"{OLLAMA}/api/generate", json=body, timeout=600).raise_for_status()
    return r.json()["response"].strip().split("\n")[0].strip()


def run(ctx: str, rounds: int) -> None:
    model = Settings().read_model
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{ctx}.json"
    held = json.loads(path.read_text()) if path.exists() else {"readings": {}, "sizes": []}
    for m in httpx.get(f"{OLLAMA}/api/ps", timeout=10).json()["models"]:
        httpx.post(f"{OLLAMA}/api/generate", json={"model": m["name"], "keep_alive": 0}, timeout=60)
    crops = sorted(CROPS.glob("*.png")) * rounds
    todo = [(i, c) for i, c in enumerate(crops) if f"{i}" not in held["readings"]]
    with ThreadPoolExecutor(READ_WORKERS) as pool:
        for start in range(0, len(todo), 25):
            batch = todo[start : start + 25]
            texts = pool.map(lambda ic: read(model, ctx, ic[1].read_bytes()), batch)
            for (i, c), text in zip(batch, texts):
                held["readings"][f"{i}"] = [c.name, text]
            held["sizes"].append([len(held["readings"]), size(model), time.strftime("%H:%M:%S")])
            write_atomic(path, json.dumps(held, ensure_ascii=False))
            print(f"{ctx}: {len(held['readings'])} lines, {held['sizes'][-1][1]} GB", flush=True)


def compare(a: str, b: str) -> None:
    ra = json.loads((OUT / f"{a}.json").read_text())
    rb = json.loads((OUT / f"{b}.json").read_text())
    same = sum(ra["readings"][k][1] == rb["readings"][k][1] for k in ra["readings"] if k in rb["readings"])
    shared = len(set(ra["readings"]) & set(rb["readings"]))
    print(f"{a} against {b}: {same} of {shared} readings the same")
    for name, h in ((a, ra), (b, rb)):
        print(f"  {name} sizes (lines, GB):", [(n, s) for n, s, _ in h["sizes"]])


if __name__ == "__main__":
    if sys.argv[1] == "--compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2)
