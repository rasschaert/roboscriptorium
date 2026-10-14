"""Fill the page readers' stage caches with the pages the probes already read, so a
build with ROBO_PAGE_READERS=1 reads only the rest. The probes read at the stage's size
with its prompts (`probe_page_reader.py`, `probe_page_joins.py`); a page the cache has
already is left as it is.

    uv run python experiments/seed_page_readings.py
"""

import json
from pathlib import Path

from roboscriptorium import pagereader
from roboscriptorium.files import write_atomic

PROBES = Path("work/probes/page-reader")
READERS = {
    "glm-page": ("glm-ocr:bf16", "glm-ocr_bf16@1600000", pagereader.GLM_PROMPT),
    "qwen-page": ("qwen3.8:27b-nvfp4", "qwen3.8_27b-nvfp4", pagereader.PROMPT),
}

if __name__ == "__main__":
    for name, (model, folder, prompt) in READERS.items():
        found: dict[str, dict[str, str]] = {}
        for f in (PROBES / folder).glob("*.txt"):
            book, page = f.stem.rsplit("-", 1)
            found.setdefault(book, {})[page] = pagereader.once(f.read_text())
        for book, pages in sorted(found.items()):
            if not (Path("work") / book).is_dir():
                continue
            cache = Path("work") / book / "stages" / f"page-reading-{name}.json"
            head = {"version": pagereader.VERSION, "model": model, "prompt": prompt}
            head["pixels"] = pagereader.PIXELS
            kept = json.loads(cache.read_text()) if cache.exists() else {}
            done = kept["pages"] if {k: kept.get(k) for k in head} == head else {}
            added = {p: t for p, t in pages.items() if p not in done}
            write_atomic(cache, json.dumps({**head, "pages": {**done, **added}}, ensure_ascii=False))
            print(f"{name:9} {book[:40]:40} {len(added):3} added, {len(done):3} there")
