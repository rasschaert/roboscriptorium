"""The OCR check's judge (clef) answered by a hosted build against its local answers,
on a golden slice's cached suspects: the same state, question and crop, the hosted
answers cached in work/probes/hosted-judge/. Scored by agreement of picks, by which is
right against the trust data's labels, and by the shift in confidence (the trust
model's feature).

    uv run python experiments/probe_hosted_judge.py <book> <spec> <openrouter:model@provider>
"""

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ocr_trust_data  # noqa: E402

from roboscriptorium import ocrcheck  # noqa: E402
from roboscriptorium.clients import decide  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.roles import DecisionCache  # noqa: E402

name, spec, via = sys.argv[1:4]
settings = Settings.from_env()
hosted = decide.HostedClient(settings.judge_model, via)
out = Path("work/probes/hosted-judge") / f"{name}-{via.split('@')[1].replace('/', '-')}.json"
answers = json.loads(out.read_text()) if out.exists() else {}
pairs = {}  # (page, line, versions) -> (local, hosted)
local_ask = ocrcheck._ask


def ask(client, cache, state, questions, image=None):
    local = local_ask(client, cache, state, questions, image)
    if client.model != settings.judge_model or image is None:
        return local
    key = DecisionCache.key(client.model, questions, state)
    if key not in answers:
        a = hosted.decide(state, questions, image_png=image())["reading"]
        answers[key] = {"value": a.value, "confidence": a.confidence,
                        "probabilities": a.probabilities}  # fmt: skip
        if len(answers) % 25 == 0:
            out.write_text(json.dumps(answers))
            print(f"{len(answers)} hosted answers", flush=True)
    pairs[(state["page"], state["line"], tuple(state["readings"]))] = (local, answers[key])
    return local


ocrcheck._ask = ask
rows = ocr_trust_data.build(name, spec)
out.write_text(json.dumps(answers))

same, local_right, hosted_right, shifts, settled = 0, 0, 0, [], 0
letters = "abcdefg"
for row in rows:
    s = row["suspect"]
    pair = pairs.get((s["page"], s["line"], (s["ours"], *s["others"])))
    if pair is None:
        continue
    local, remote = pair
    same += local["value"] == remote["value"]
    shifts.append(abs(local["confidence"] - remote["confidence"]))
    if row["settled"]:
        settled += 1
        right = lambda v: v in letters and row["right"][letters.index(v)]  # noqa: E731
        local_right += right(local["value"])
        hosted_right += right(remote["value"])
n = len(shifts)
print(f"{name}: {n} suspects judged both ways")
print(f"  same pick: {same}/{n} ({same / n:.1%})")
print(f"  right on settled suspects: local {local_right}/{settled}, hosted {hosted_right}/{settled}")
print(f"  confidence shift: median {statistics.median(shifts):.3f}, "
      f"90th percentile {sorted(shifts)[int(0.9 * n)]:.3f}")  # fmt: skip
