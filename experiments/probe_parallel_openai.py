"""Probe: does a model on a local OpenAI-compatible server (Unsloth Studio) read the same,
and faster, with several requests at once?

Reads every eighth line of reader set v2 one at a time, then with 2 and 4 requests in
flight, and counts the readings that differ from the tryout's cached one-at-a-time
reading of the same model.

    uv run python experiments/probe_parallel_openai.py "openai-local:<id>#<label>"
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import tryout

model = sys.argv[1]
books, items = tryout.load_set()
items = items[::8]
cached = json.loads(tryout._readings_path(model).read_text())

for workers in (1, 2, 4):
    start = time.time()
    with ThreadPoolExecutor(workers) as pool:
        got = list(
            pool.map(
                lambda i: tryout.read_openai_local(i["png"], model, books[i["book"]]["prompt"]),
                items,
            )
        )
    took = (time.time() - start) / len(items)
    differ = [(i["id"], cached[i["id"]], g) for i, g in zip(items, got, strict=True) if g != cached[i["id"]]]
    print(f"{workers} at a time: {took:.2f} s a line, {len(differ)} of {len(items)} differ", flush=True)
    for d in differ[:5]:
        print("   ", d, flush=True)
