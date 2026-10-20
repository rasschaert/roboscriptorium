"""Can a read prompt keep an emphasis accent? The latest tuning bench's stress-accent errors
that sit in single layer lines with no question asked, read by the read model with the book's
own prompt and with the same prompt plus a sentence about accents. For each: whether the
reading holds the reference's word (`want`) and whether it holds the build's (`got`).

    uv run python experiments/probe_accent_prompt.py

Needs `unasked_set.py`'s crops. About a minute on a free Ollama.
"""

import hashlib
import json
from pathlib import Path

from roboscriptorium import readers
from roboscriptorium.config import Settings

RUN = "tuning-20261020T182636-f38e636-dirty"
ROOT = Path("work/probes/unasked-set")
EXTRA = (
    " Keep every accent mark exactly as printed, including an acute accent on a single "
    "letter used for emphasis (for example on an i or an o), and add none that is not printed."
)


def word_in(word: str, reading: str) -> bool:
    return word.strip("‘’'\".,;:!?") in reading


if __name__ == "__main__":
    settings = Settings.from_env()
    items = {i["id"] for i in json.loads((ROOT / "items.json").read_text())["items"]}
    rows = [json.loads(x) for x in Path(f"work/bench/{RUN}.errors.jsonl").read_text().splitlines()]
    tally = {"default": [0, 0], "accent sentence": [0, 0]}
    for r in rows:
        if r["cause"] != "stress accent" or r["asked"] or r["layer"] != "kept" or not r["lines"]:
            continue
        iid = f'{r["book"]}:{r["page"]}:{r["lines"][0]}'
        if r["lines"][0] != r["lines"][1] or iid not in items:
            continue
        png = (ROOT / "crops" / f"{hashlib.sha256(iid.encode()).hexdigest()[:16]}.png").read_bytes()
        prompt = json.loads((Path("work") / r["book"] / "stages" / "third-reading.json").read_text())["prompt"]
        out = []
        for name, p in (("default", prompt), ("accent sentence", prompt + EXTRA)):
            reading = readers.transcribe(png, settings.read_model, settings.ollama_url, p)
            has_want, has_got = word_in(r["want"], reading), word_in(r["got"], reading)
            tally[name][0] += has_want
            tally[name][1] += has_got
            out.append(f"{name}: want {int(has_want)} got {int(has_got)}")
        print(f'{r["book"][:20]:20} p{r["page"]:<4} want {r["want"]!r:12} got {r["got"]!r:12}', " | ".join(out), flush=True)
    print("holds the reference's word / the build's word:", tally)
