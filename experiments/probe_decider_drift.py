"""Does a rebuilt decision model answer as the one the caches hold? No new reading: the
line-role questions of a book's warm build, their cached answers, asked again.

    uv run python experiments/probe_decider_drift.py <book>[:pages[:chapters]] [n]

The build runs against a dead Ollama URL, so every question it reuses must be cached;
then `n` of them (default 80, spread over the book) go to the live model.
"""

import os
import random
import sys

from roboscriptorium import pipeline, roles
from roboscriptorium.book import Book
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.golden.scoring import parse_spec

folder, pages, _ = parse_spec(f"work/{sys.argv[1]}")
n = int(sys.argv[2]) if len(sys.argv) > 2 else 80
live = Settings.from_env()
states: dict[str, dict] = {}
key = roles.DecisionCache.key


def recording(model, questions, state):
    k = key(model, questions, state)
    states[k] = state
    return k


roles.DecisionCache.key = staticmethod(recording)
os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"
book = Book.load(folder)
pipeline.run(book, pages=pages, check_ocr=False, settings=Settings.from_env())
cache = roles.DecisionCache(book.stages / "decisions.jsonl")
asked = [(k, s, cache.get(k)) for k, s in states.items() if cache.get(k)]
random.Random(0).shuffle(asked)
client = decide.for_model(live.role_model, live.ollama_url)
same, gaps = 0, []
for k, st, old in asked[:n]:
    a = client.decide(st, roles.QUESTIONS)["role"]
    same += a.value == old["role"]
    gaps.append(abs(a.probabilities["body"] - old["p_body"]))
    if a.value != old["role"]:
        print(f"  {old['role']} → {a.value}: {st.get('text', '')[:60]!r}")
gaps.sort()
print(f"{live.role_model}: same role {same}/{len(gaps)}; |Δ P(body)| median "
      f"{gaps[len(gaps) // 2]:.3f}, max {gaps[-1]:.3f}")
