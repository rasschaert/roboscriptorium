"""Probe: do the readers read the same with a small context, and with requests in parallel?

Reads the same line crops (a golden book's body lines) with each reader three ways:
at a 128k context one at a time, at 8k one at a time, and at 8k four at a time, and
counts the lines whose reading differs from the first. Readings at a context size
must be the same before a smaller context or parallel requests go into a build.

    uv run python experiments/probe_num_ctx.py [book] [first page] [lines]
"""

import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pymupdf

from roboscriptorium import ocrcheck, quotes
from roboscriptorium.pdf import cached_text_layer

URL = "http://127.0.0.1:11434/api/generate"
book = Path("work") / (sys.argv[1] if len(sys.argv) > 1 else "koning-wilders--ia-scan")
first = int(sys.argv[2]) if len(sys.argv) > 2 else 20
want = int(sys.argv[3]) if len(sys.argv) > 3 else 100
PROMPT = quotes.style_prompt("nl", True, "...", "–")

pages = cached_text_layer(book / "source.pdf", book / "stages" / "text-layer.json")
crops = []
with pymupdf.open(book / "source.pdf") as doc:
    for page in pages[first - 1 :]:
        for line in page.lines:
            if len(line.text.split()) >= 5:
                crops.append(ocrcheck._crop(doc[page.number - 1], (line.x0, line.y0, line.x1, line.y1)))
        if len(crops) >= want:
            break
crops = crops[:want]


def read(model: str, png: bytes, ctx: int) -> str:
    glm = model.startswith("glm-ocr")
    body = {
        "model": model,
        "prompt": "Text Recognition:" if glm else PROMPT,
        "images": [base64.b64encode(png).decode()],
        "stream": False,
        "options": {"num_predict": ocrcheck.MAX_LINE_TOKENS, "num_ctx": ctx}
        | ({} if glm else {"temperature": 0}),
    }
    if not glm:
        body["think"] = False
    text = httpx.post(URL, json=body, timeout=600).json()["response"]
    return text.strip().split("\n")[0].strip()


results = {}
for model in ("qwen3.8:27b-nvfp4", "glm-ocr:bf16"):
    runs = {}
    for name, ctx, workers in (("128k", 131072, 1), ("8k", 8192, 1), ("8k ×4", 8192, 4)):
        read(model, crops[0], ctx)  # load at this context before timing
        start = time.time()
        with ThreadPoolExecutor(workers) as pool:
            runs[name] = list(pool.map(lambda png: read(model, png, ctx), crops))
        took = time.time() - start
        differ = sum(a != b for a, b in zip(runs["128k"], runs[name], strict=True))
        print(f"{model:20} {name:6} {took / len(crops):5.2f} s a line, {differ} of {len(crops)} differ from 128k", flush=True)
    results[model] = runs
out = Path("work/probes/num-ctx.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(results, ensure_ascii=False, indent=1))
