"""Does the OCR check's text judge do better with the lines around the suspect?

Runs `eval` on a golden book with `ocrcheck._ask` wrapped: each text-judge
question is also asked without the surrounding lines (the old state and
question). Where the vision judge is sure (>= 0.8), its pick stands in for the
truth; reports how often the text judge agrees with it, both ways.

    uv run python experiments/probe_reader_context.py work/<book> [--pages 11-60 --chapters 1-10]
"""

import sys

from roboscriptorium import ocrcheck
from roboscriptorium.cli import app

real_ask = ocrcheck._ask
rows = []
last_vision = {}


def ask(client, cache, state, questions, image=None):
    answer = real_ask(client, cache, state, questions, image)
    if image is not None:
        last_vision.update(answer)
        return answer
    old_state = {k: v for k, v in state.items() if k not in ("line before", "line after")}
    q = questions["reading"]
    old_q = {
        "reading": {
            **q,
            "instructions": q["instructions"].replace(
                ", read between the line before and the line after?", "?"
            ),
        }
    }
    old = real_ask(client, cache, old_state, old_q)
    rows.append((dict(last_vision), answer, old))
    return answer


ocrcheck._ask = ask
sys.argv = ["roboscriptorium", "eval", *sys.argv[1:]]
try:
    app()
except SystemExit:
    pass

sure = [(v, new, old) for v, new, old in rows if v.get("confidence", 0) >= 0.8]
print(f"{len(rows)} text-judge questions; vision judge sure on {len(sure)}")
print(f"  with context:    agrees {sum(n['value'] == v['value'] for v, n, _ in sure)}")
print(f"  without context: agrees {sum(o['value'] == v['value'] for v, _, o in sure)}")
changed = sum(n["value"] != o["value"] for _, n, o in rows)
print(f"  answers that changed: {changed}")
