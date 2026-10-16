"""Does telling the reader about small capitals help, or make it capitalize what isn't?
The frozen reader set (`tryout.py`), every line read by the read model with the book's
prompt plus `HINT`, scored beside the same model's readings with the prompt as it is.

    uv run python experiments/probe_smallcaps_prompt.py
Readings cached in work/tryout/reader-v<N>/readings/<model>+smallcaps.json.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tryout as T  # noqa: E402

from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium import readers  # noqa: E402

HINT = (
    " The book may set some words, such as abbreviations and car models, in small"
    " capitals: capital letters drawn about as small as lower-case ones. Write small"
    " capitals as capital letters."
)
settings = Settings.from_env()


def right(item: dict, text: str) -> bool:
    return T.fold(text) == T.fold(item["truth"])


books, items = T.load_set()
model = settings.read_model
plain = json.loads(T._readings_path(model).read_text())
cache = T._readings_path(model).with_name(T._readings_path(model).stem + "+smallcaps.json")
done = json.loads(cache.read_text()) if cache.exists() else {}
for n, i in enumerate([i for i in items if i["id"] not in done], 1):
    prompt = books[i["book"]]["prompt"].replace(" It is one line of a book.", " It is one line of a book." + HINT)
    done[i["id"]] = readers.transcribe(i["png"], model, settings.ollama_url, prompt)
    if n % 25 == 0:
        cache.write_text(json.dumps(done, ensure_ascii=False))
        print(f"  {n}", flush=True)
cache.write_text(json.dumps(done, ensure_ascii=False))
for label, reading in (("as now", plain), ("small caps told", done)):
    r = T.score(label, reading, items, {})
    h, c = r["hard"], r["control"]
    print(f"{label:16} hard {h['right']}/{h['lines']} CER {h['cer']:.2%}   control {c['right']}/{c['lines']} CER {c['cer']:.2%}")
fixed = [i for i in items if right(i, done[i["id"]]) and not right(i, plain[i["id"]])]
broke = [i for i in items if right(i, plain[i["id"]]) and not right(i, done[i["id"]])]
print(f"fixed {len(fixed)}, broke {len(broke)}")
for i in broke[:15]:
    print(f"  BROKE {i['book'][:16]}: {plain[i['id']]!r} → {done[i['id']]!r}")
for i in fixed[:10]:
    print(f"  fixed {i['book'][:16]}: {plain[i['id']]!r} → {done[i['id']]!r}")
