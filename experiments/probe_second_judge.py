"""Another decision model as the OCR check's text judge (`check_model`) against the one in
use, on a golden slice's cached suspects: the same state and question, its answers cached
in work/probes/second-judge/. Scored against the trust data's labels: right alone, and
right where clef is wrong (what makes the second judge an alarm on the first).

    uv run python experiments/probe_second_judge.py <book> <spec> <model>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ocr_trust_data  # noqa: E402

from roboscriptorium import ocrcheck  # noqa: E402
from roboscriptorium.clients import ollaya  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.roles import DecisionCache  # noqa: E402

name, spec, model = sys.argv[1:4]
settings = Settings.from_env()
other = ollaya.for_model(model, settings.ollaya_url, settings.ollama_url)
out = Path("work/probes/second-judge") / f"{name}-{model.replace(':', '-').replace('/', '_')}.json"
out.parent.mkdir(parents=True, exist_ok=True)
answers = json.loads(out.read_text()) if out.exists() else {}
asked = {}  # (page, line, first line) -> {"judge", "check", "other"} answers
local_ask = ocrcheck._ask
last_judge = {}


def ask(client, cache, state, questions, image=None):
    local = local_ask(client, cache, state, questions, image)
    if client.model == settings.judge_model:
        last_judge["state"], last_judge["answer"] = state, local
        return local
    if client.model != settings.check_model:
        return local
    key = DecisionCache.key(model, questions, state)
    if key not in answers:
        a = other.decide(state, questions)["reading"]
        answers[key] = {"value": a.value, "confidence": a.confidence}
        if len(answers) % 25 == 0:
            out.write_text(json.dumps(answers))
            print(f"{len(answers)} answers", flush=True)
    s = last_judge["state"]
    asked[(s["page"], s["line"], tuple(s["readings"]))] = (last_judge["answer"], local, answers[key])
    return local


ocrcheck._ask = ask
rows = ocr_trust_data.build(name, spec)
out.write_text(json.dumps(answers))

letters = "abcdefg"
n = clef_wrong = 0
right = {"clef": 0, "in use": 0, model: 0}
alarm = {"in use": 0, model: 0}
for row in rows:
    s = row["suspect"]
    got = asked.get((s["page"], s["line"], (s["ours"], *s["others"])))
    if got is None or not row["settled"]:
        continue
    n += 1
    ok = [v in letters and row["right"][letters.index(v)] for v in (a["value"] for a in got)]
    for who, k in zip(right, ok, strict=True):
        right[who] += k
    if not ok[0]:
        clef_wrong += 1
        alarm["in use"] += ok[1]
        alarm[model] += ok[2]
print(f"{name}: {n} settled suspects; right: clef {right['clef']}, "
      f"{settings.check_model} {right['in use']}, {model} {right[model]}")
print(f"  where clef is wrong ({clef_wrong}): {settings.check_model} right on {alarm['in use']}, "
      f"{model} on {alarm[model]}")  # fmt: skip
