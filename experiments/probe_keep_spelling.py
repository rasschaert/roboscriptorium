"""The read model on the frozen reader set, told to keep the author's own spelling.

Qwen standardises dialect ("wijveke" → "wijfje", "Goeienavond" → "Goedenavond"); a
sentence added to its prompt (`probe_qwen_dialect.KEEP`) stopped that on Ex-minnaar's
lines. Here the same model reads the reader set (`experiments/tryout.py`, its current
version) with the set's frozen prompts plus that sentence, cached apart, and both are
scored as `tryout.py run reader` scores them.

    uv run python experiments/probe_keep_spelling.py
"""

import json

from probe_qwen_dialect import KEEP
from tryout import READER_VERSION, WORK, _readings_path, load_set, score

from roboscriptorium.config import Settings
from roboscriptorium import readers


def main() -> None:
    settings = Settings.from_env()
    books, items = load_set()
    model = settings.read_model
    before = json.loads(_readings_path(model).read_text())
    cache = WORK / f"reader-v{READER_VERSION}" / "readings" / "keep-spelling.json"
    done = json.loads(cache.read_text()) if cache.exists() else {}
    todo = [i for i in items if i["id"] not in done]
    for n, i in enumerate(todo, 1):
        prompt = books[i["book"]]["prompt"] + KEEP
        done[i["id"]] = readers.transcribe(i["png"], model, settings.ollama_url, prompt)
        if n % 25 == 0 or n == len(todo):
            cache.write_text(json.dumps(done, ensure_ascii=False))
            print(f"  {n}/{len(todo)}", flush=True)
    for name, reading in (("as built", before), ("keep spelling", done)):
        r = score(name, reading, items, {})
        h, c = r["hard"], r["control"]
        print(
            f"{name:14} hard {h['right']}/{h['lines']} CER {h['cer']:.2%}   "
            f"control {c['right']}/{c['lines']} CER {c['cer']:.2%}"
        )
    changed = [i for i in items if before[i["id"]] != done[i["id"]]]
    print(f"{len(changed)} lines read differently:")
    for i in changed:
        print(f"  {i['book'][:20]} truth {i['truth']!r}\n    was  {before[i['id']]!r}\n    now  {done[i['id']]!r}")


if __name__ == "__main__":
    main()
