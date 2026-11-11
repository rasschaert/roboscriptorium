"""Can a book's best reader setting be told without a reference? (the checklist, "Per-book
settings"). For each book of the frozen reader set and each resolution the read model read
it at, the lines it reads right and the lines on which it agrees with an independent
reading (glm-ocr at 300 dpi, the text layer): does the setting that agrees most score best?
No models: the readings are `read_set_dpi.py`'s.

    uv run python experiments/probe_setting_agreement.py
"""

import json
import random
from collections import defaultdict
from pathlib import Path

from roboscriptorium.evaluate import normalise as fold

ROOT = Path("work/tryout/reader-v3")
SETTINGS = {dpi: f"qwen3.8_27b-nvfp4+dpi{dpi}" for dpi in (300, 450, 600)}
WITNESS = "glm-ocr_bf16"


def readings(stem: str) -> dict[str, str]:
    return json.loads((ROOT / "readings" / f"{stem}.json").read_text())


def picked(score: dict[int, int]) -> int:
    """The setting with the highest score; a tie goes to the lowest resolution."""
    return max(sorted(score), key=lambda dpi: score[dpi])


def corr(xs: list[int], ys: list[int]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else 0.0


if __name__ == "__main__":
    items = json.loads((ROOT / "items.json").read_text())["items"]
    read = {dpi: readings(stem) for dpi, stem in SETTINGS.items()}
    glm = readings(WITNESS)
    books = defaultdict(list)
    for item in items:
        books[item["book"]].append(item)
    right, with_glm, with_layer = {}, {}, {}
    for book, lines in books.items():
        for dpi in SETTINGS:
            mine = {i["id"]: fold(read[dpi][i["id"]]) for i in lines}
            right[book, dpi] = sum(mine[i["id"]] == fold(i["truth"]) for i in lines)
            with_glm[book, dpi] = sum(mine[i["id"]] == fold(glm[i["id"]]) for i in lines)
            with_layer[book, dpi] = sum(mine[i["id"]] == fold(i["layer"]) for i in lines)
    print(f"{'book':34} right at 300/450/600   agrees with glm-ocr   with the layer   picks")
    for book in books:
        cells = [
            "/".join(f"{table[book, dpi]:2}" for dpi in SETTINGS)
            for table in (right, with_glm, with_layer)
        ]
        picks = [picked({d: t[book, d] for d in SETTINGS}) for t in (right, with_glm, with_layer)]
        print(f"{book[:34]:34} {cells[0]:22} {cells[1]:21} {cells[2]:16} "
              f"best {picks[0]}, glm {picks[1]}, layer {picks[2]}")
    total = len(items)
    print()
    for dpi in SETTINGS:
        print(f"every book at {dpi} dpi: {sum(right[b, dpi] for b in books)} of {total}")
    for name, table in (("glm-ocr", with_glm), ("the layer", with_layer)):
        chosen = {b: picked({d: table[b, d] for d in SETTINGS}) for b in books}
        best = {b: max(right[b, d] for d in SETTINGS) for b in books}
        hits = sum(right[b, chosen[b]] == best[b] for b in books)
        print(f"each book at the setting agreeing most with {name}: "
              f"{sum(right[b, chosen[b]] for b in books)} of {total}; "
              f"a best setting picked for {hits} of {len(books)} books")
    print(f"each book at its best setting (needs the reference): "
          f"{sum(max(right[b, d] for d in SETTINGS) for b in books)} of {total}")
    rng = random.Random(0)
    draws = [
        sum(right[b, rng.choice(list(SETTINGS))] for b in books) for _ in range(10000)
    ]
    draws.sort()
    print(f"each book at a setting drawn at random: median {draws[5000]}, "
          f"95% between {draws[250]} and {draws[9750]}")
    print()
    for name, table in (("glm-ocr", with_glm), ("the layer", with_layer)):
        gain = [right[b, d] - right[b, 300] for b in books for d in (450, 600)]
        more = [table[b, d] - table[b, 300] for b in books for d in (450, 600)]
        print(f"lines gained over 300 dpi against agreement with {name} gained, "
              f"{len(gain)} book-settings: r = {corr(more, gain):+.2f}")
