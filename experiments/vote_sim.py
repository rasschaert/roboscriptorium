"""Does a candidate reader help a reading vote? A plurality vote over the reader set's
readings (ties to the first reader, qwen), with and without the candidate, counting the
lines it mends and breaks. No arbiter: it weighs readers, so this is an upper bound on harm.

    uv run python experiments/vote_sim.py <candidate reading file stem> [more …]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium.evaluate import normalise as fold

ROOT = Path("work/tryout/reader-v3")
BASE = ["qwen3.8_27b-nvfp4", "glm-ocr_bf16"]


def readings(stem: str) -> dict[str, str]:
    return json.loads((ROOT / "readings" / f"{stem}.json").read_text())


def vote(votes: list[str]) -> str:
    """The most common reading; a tie goes to the earliest of the tied."""
    counts = Counter(votes)
    top = max(counts.values())
    return next(v for v in votes if counts[v] == top)


def run(names: list[str], layer: bool, items: list[dict], by: dict[str, dict]) -> dict[str, bool]:
    out = {}
    for i in items:
        votes = [fold(by[n][i["id"]]) for n in names]
        if layer:
            votes.append(fold(i["layer"]))
        out[i["id"]] = vote(votes) == fold(i["truth"])
    return out


if __name__ == "__main__":
    items = json.loads((ROOT / "items.json").read_text())["items"]
    for cand in sys.argv[1:]:
        by = {n: readings(n) for n in [*BASE, cand]}
        for layer in (False, True):
            before = run(BASE, layer, items, by)
            after = run([*BASE, cand], layer, items, by)
            mended = sum(after[k] and not before[k] for k in before)
            broken = sum(before[k] and not after[k] for k in before)
            tag = "with layer" if layer else "readers only"
            print(f"{cand} {tag}: {sum(before.values())} -> {sum(after.values())} "
                  f"(mended {mended}, broken {broken}) of {len(items)}")
        alone = run(BASE[:1], False, items, by)
        print(f"  qwen alone: {sum(alone.values())}")
