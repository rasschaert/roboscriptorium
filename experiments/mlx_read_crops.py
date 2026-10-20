"""Reads every crop under work/probes/olmocr-suspects/<book>/ with an MLX OCR model, the
first line of its reading, resumable.

    work/models/mlx-env/bin/python -I experiments/mlx_read_crops.py <model dir> <label> [book …]

Writes work/probes/olmocr-suspects/<book>/<label>.json: {"<page>_<line>": reading}.
"""

import json
import sys
import time
from pathlib import Path

from mlx_vlm import generate, load
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

ROOT = Path("work/probes/olmocr-suspects")
PROMPT = "Transcribe the text in this image exactly as printed. Return only the text, on one line."
path, label = sys.argv[1], sys.argv[2]
books = sys.argv[3:] or sorted(d.name for d in ROOT.iterdir() if d.is_dir())

model, processor = load(path)
config = load_config(path)
text = apply_chat_template(processor, config, PROMPT, num_images=1)
start = time.time()
for book in books:
    out = ROOT / book / f"{label}.json"
    done = json.loads(out.read_text()) if out.exists() else {}
    pngs = sorted((ROOT / book).glob("*.png"))
    for n, png in enumerate(pngs, 1):
        if png.stem in done:
            continue
        result = generate(
            model, processor, text, image=[str(png)], max_tokens=200, temperature=0.0, verbose=False
        )
        done[png.stem] = str(getattr(result, "text", result)).strip().split("\n")[0].strip()
        if n % 50 == 0:
            out.write_text(json.dumps(done, ensure_ascii=False))
            print(f"{book[:30]} {n}/{len(pngs)} {time.time() - start:.0f}s", flush=True)
    out.write_text(json.dumps(done, ensure_ascii=False))
    print(f"{book}: {len(done)} readings, {time.time() - start:.0f}s", flush=True)
print("done")
