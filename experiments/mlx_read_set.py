"""Reads the frozen reader set's crops with an MLX vision-language model, for `tryout.py`.

Run with the isolated MLX environment (it has no roboscriptorium):

    work/models/mlx-env/bin/python -I experiments/mlx_read_set.py <model dir> <label> [prompt] [limit]

Writes {id: reading} to work/tryout/reader-v2/readings/<label>.json, the cache
`tryout.py run reader <label>` scores. A reading is the model's first line.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

from mlx_vlm import generate, load
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

ROOT = Path("work/tryout/reader-v2")
path, label = sys.argv[1], sys.argv[2]
prompt = sys.argv[3] if len(sys.argv) > 3 else "OCR:"
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 0

items = json.loads((ROOT / "items.json").read_text())["items"]
if limit:
    items = items[:limit]
out_path = ROOT / "readings" / f"{label}.json"
done = json.loads(out_path.read_text()) if out_path.exists() else {}

model, processor = load(path)
config = load_config(path)
text = apply_chat_template(processor, config, prompt, num_images=1)
start = time.time()
for n, item in enumerate(items, 1):
    if item["id"] in done:
        continue
    crop = ROOT / "crops" / f"{hashlib.sha256(item['id'].encode()).hexdigest()[:16]}.png"
    result = generate(model, processor, text, image=[str(crop)], max_tokens=200, temperature=0.0, verbose=False)
    reading = getattr(result, "text", result)
    done[item["id"]] = str(reading).strip().split("\n")[0].strip()
    if n % 10 == 0 or limit:
        out_path.write_text(json.dumps(done, ensure_ascii=False))
        print(f"{n}/{len(items)} {time.time() - start:.0f}s  {item['id'][:30]!r}: {done[item['id']][:60]!r}", flush=True)
out_path.write_text(json.dumps(done, ensure_ascii=False))
print(f"done: {len(done)} readings in {time.time() - start:.0f}s")
