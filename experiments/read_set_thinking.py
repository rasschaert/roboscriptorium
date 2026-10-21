"""The read model's reading of the frozen reader set with its thinking on, for `tryout.py`.

    uv run python experiments/read_set_thinking.py [limit]

Asks the read model (`Settings.read_model`) each line as the pipeline does, the book's own
prompt and the crop, but with `think` on and room to think; the reading is the answer's
first line. Writes work/tryout/reader-v2/readings/<model>+think.json, which
`tryout.py run reader <model>+think` scores. Resumable.
"""

import base64
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import tryout  # noqa: E402

from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.files import write_atomic  # noqa: E402

THINK_TOKENS = 6000

if __name__ == "__main__":
    settings = Settings.from_env()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    books, items = tryout.load_set()
    items = items[:limit] if limit else items
    out = tryout._readings_path(f"{settings.read_model}+think")
    out.parent.mkdir(parents=True, exist_ok=True)
    done = json.loads(out.read_text()) if out.exists() else {}
    start, asked, tokens = time.time(), 0, 0
    for item in items:
        if item["id"] in done:
            continue
        payload = {
            "model": settings.read_model,
            "prompt": books[item["book"]]["prompt"],
            "images": [base64.b64encode(item["png"]).decode()],
            "stream": False,
            "think": True,
            "options": {"num_predict": THINK_TOKENS, "temperature": 0.6},
        }
        resp = httpx.post(f"{settings.ollama_url}/api/generate", json=payload, timeout=1800)
        resp.raise_for_status()
        body = resp.json()
        done[item["id"]] = body["response"].strip().split("\n")[0].strip()
        asked += 1
        tokens += body.get("eval_count", 0)
        if asked % 10 == 0 or limit:
            write_atomic(out, json.dumps(done, ensure_ascii=False))
            print(
                f"{len(done)}/{len(items)} {(time.time() - start) / asked:.1f} s a line, "
                f"{tokens // asked} tokens a line",
                flush=True,
            )
    write_atomic(out, json.dumps(done, ensure_ascii=False))
    print(f"done: {len(done)} readings in {time.time() - start:.0f}s")
