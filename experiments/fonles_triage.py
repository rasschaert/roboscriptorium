"""fonles-decision-1 as a line detector, the same question and sets as `h2o_triage.py`.

Run with an environment that has torch and transformers (no roboscriptorium):

    F=~/.cache/huggingface/models/fonles-decision-1
    ~/.cache/huggingface/envs/h2o-env/bin/python -I experiments/fonles_triage.py $F [limit] [set folder]

Writes <set folder>/triage/fonles.json: {id: P(exact)}, resumable. The model's own code
(`joint_schema_model.py`) runs in-process: no server.
"""

import base64
import hashlib
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, sys.argv[1])
from joint_schema_model import load_release_model, systemone  # noqa: E402

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
model, processor = load_release_model(sys.argv[1], device=device)
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
items = json.loads((ROOT / "items.json").read_text())["items"]
items = items[:limit] if limit else items
out = ROOT / "triage" / "fonles.json"
out.parent.mkdir(exist_ok=True)
done = json.loads(out.read_text()) if out.exists() else {}
start = time.time()
for n, item in enumerate(items, 1):
    if item["id"] in done:
        continue
    crop = ROOT / "crops" / f"{hashlib.sha256(item['id'].encode()).hexdigest()[:16]}.png"
    request = {
        "model": "fonles-decision-1",
        "state": f"transcription: {item['layer']}",
        "questions": QUESTION,
        "images": [base64.b64encode(crop.read_bytes()).decode()],
    }
    done[item["id"]] = systemone(model, processor, request)["answers"]["match"].get("noul")
    if n % 25 == 0 or limit:
        out.write_text(json.dumps(done))
        print(f"{n}/{len(items)} {time.time() - start:.0f}s {done[item['id']]}", flush=True)
out.write_text(json.dumps(done))
print(f"done in {time.time() - start:.0f}s")
