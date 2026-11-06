"""Reads the quiet set (`quiet_set.py`) with a model on a local OpenAI-compatible server,
asked as the reader set asks it (`tryout.read_openai_local`), with the prompt the book's
read model was given (its `third-reading.json` cache), into
work/tryout/quiet-v1/readings/<stem>.json; then score it with `quiet_set.py score <stem>`.

    uv run python experiments/quiet_read_openai.py openai-local:<model id>[#<label>]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from quiet_set import ROOT  # noqa: E402
from tryout import read_openai_local, sha  # noqa: E402

model = sys.argv[1]
items = json.loads((ROOT / "items.json").read_text())["items"]
prompts = {
    b: json.loads((Path("work") / b / "stages" / "third-reading.json").read_text())["prompt"]
    for b in {i["book"] for i in items}
}
out = ROOT / "readings" / f"{model.replace(':', '_').replace('/', '_')}.json"
done = json.loads(out.read_text()) if out.exists() else {}
todo = [i for i in items if i["id"] not in done]
for n, i in enumerate(todo, 1):
    png = (ROOT / "crops" / f"{sha(i['id'])}.png").read_bytes()
    done[i["id"]] = read_openai_local(png, model, prompts[i["book"]])
    if n % 25 == 0 or n == len(todo):
        out.write_text(json.dumps(done, ensure_ascii=False))
        print(f"{n}/{len(todo)}", flush=True)
