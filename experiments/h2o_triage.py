"""H2O-Lightning-Omni-4B as a detector: for each line of the frozen reader set, the crop
and the text layer's line go in, and it says how likely the transcription is exactly what
is printed. Hard lines (the layer is wrong) should score low, control lines high.

Run with an environment that has torch and transformers (no roboscriptorium):

    H2O=~/.cache/huggingface/models/h2o-lightning-omni-4b
    ~/.cache/huggingface/envs/h2o-env/bin/python -I experiments/h2o_triage.py $H2O [limit] [set folder]

Writes <set folder>/triage/h2o.json (default work/tryout/reader-v2): {id: P(exact)}, resumable.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, sys.argv[1])
from inference import FrameBank, load_omni  # noqa: E402

ROOT = Path(sys.argv[3] if len(sys.argv) > 3 else "work/tryout/reader-v2")
QUESTION = {
    "match": {
        "type": "noul",
        "instructions": (
            "The image is one printed line of a book. Is the transcription below exactly what "
            "the line prints: every letter, accent, punctuation mark and quote mark?"
        ),
        "criteria": {
            "true": "the transcription is exactly what is printed",
            "false": "the transcription has a wrong, missing or extra character",
        },
    }
}
device = "mps" if torch.backends.mps.is_available() else "cpu"
# Images only: the audio tower isn't needed, so the tower-free attach.
runtime, _, _ = load_omni(sys.argv[1], device=device, attach=FrameBank())
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
items = json.loads((ROOT / "items.json").read_text())["items"]
items = items[:limit] if limit else items
out = ROOT / "triage" / "h2o.json"
out.parent.mkdir(exist_ok=True)
done = json.loads(out.read_text()) if out.exists() else {}
start = time.time()
for n, item in enumerate(items, 1):
    if item["id"] in done:
        continue
    crop = ROOT / "crops" / f"{hashlib.sha256(item['id'].encode()).hexdigest()[:16]}.png"
    answer = runtime.system_one_vision(
        images=[str(crop)], text=f"transcription: {item['layer']}", questions=QUESTION
    )["answers"]["match"]
    done[item["id"]] = answer.get("noul")
    if n % 25 == 0 or limit:
        out.write_text(json.dumps(done))
        print(f"{n}/{len(items)} {time.time() - start:.0f}s {done[item['id']]}", flush=True)
out.write_text(json.dumps(done))
print(f"done in {time.time() - start:.0f}s")
