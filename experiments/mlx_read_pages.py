"""Reads whole page images with an MLX OCR model, as Markdown, one file per page.

Run with the isolated MLX environment (it has no roboscriptorium):

    work/models/mlx-env/bin/python -I experiments/mlx_read_pages.py <model dir> <label> [limit]

Reads work/probes/olmocr-pages/*.png (`probe_page_ocr_pages.py`), writes
work/probes/olmocr-pages/<label>/<page>.md.
"""

import sys
import time
from pathlib import Path

from mlx_vlm import generate, load
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

PROMPT = (
    "Attached is one page of a document that you must process. Just return the plain "
    "text representation of this document as if you were reading it naturally."
)
ROOT = Path("work/probes/olmocr-pages")
path, label = sys.argv[1], sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 0

pngs = sorted(ROOT.glob("*.png"))
if limit:
    pngs = pngs[:limit]
out = ROOT / label
out.mkdir(exist_ok=True)
model, processor = load(path)
config = load_config(path)
text = apply_chat_template(processor, config, PROMPT, num_images=1)
start = time.time()
for n, png in enumerate(pngs, 1):
    target = out / f"{png.stem}.md"
    if target.exists():
        continue
    result = generate(
        model, processor, text, image=[str(png)], max_tokens=2500, temperature=0.0, verbose=False
    )
    target.write_text(str(getattr(result, "text", result)).strip())
    print(f"{n}/{len(pngs)} {time.time() - start:.0f}s", flush=True)
print(f"done in {time.time() - start:.0f}s")
