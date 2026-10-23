"""Do the OCR check's judges answer as the caches hold after an Ollama update or a pull?
`probe_decider_drift.py` does the same for the line roles. No new reading: a book's warm
build against a dead Ollama URL records every judge question it reuses from the cache,
then `n` of each judge's (default 60, shuffled) go to the live model.

    uv run python experiments/probe_judge_drift.py <book>[:pages[:chapters]] [n]
"""

import os
import random
import sys
from collections import defaultdict

from roboscriptorium import ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.golden.scoring import parse_spec

folder, pages, _ = parse_spec(f"work/{sys.argv[1]}")
n = int(sys.argv[2]) if len(sys.argv) > 2 else 60
live = Settings.from_env()
asked: dict[str, list] = defaultdict(list)
cached_ask = ocrcheck._ask


def recording(client, cache, state, questions, image=None):
    answer = cached_ask(client, cache, state, questions, image)
    png = image() if image else None
    asked[client.model].append((state, questions, png, answer))
    return answer


ocrcheck._ask = recording
os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"
pipeline.run(Book.load(folder), pages=pages, settings=Settings.from_env())
for model, items in asked.items():
    client = decide.for_model(model, live.ollama_url)
    random.Random(0).shuffle(items)
    same, gaps = 0, []
    for state, questions, png, old in items[:n]:
        a = client.decide(state, questions, image_png=png)["reading"]
        same += a.value == old["value"]
        gaps.append(abs(a.confidence - old["confidence"]))
        if a.value != old["value"]:
            print(f"  {model}: {old['value']} ({old['confidence']:.2f}) → {a.value} "
                  f"({a.confidence:.2f})")
    gaps.sort()
    print(f"{model}: same pick {same}/{len(gaps)} of {len(items)} cached; confidence gap "
          f"median {gaps[len(gaps) // 2]:.4f}, max {gaps[-1]:.4f}")
