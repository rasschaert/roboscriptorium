"""Does qwen read better when a crop fits its vision grid exactly? (Argon's idea, 2026-10-23).
Qwen3.8's encoder takes 16-pixel patches merged two by two, and its image processor rounds
each side to a multiple of 32 by resampling: the frozen reader set's line crops (56–339 px
high) are scaled by 0.8 to 1.2 on the way in. Here each crop is padded with its paper colour
to the next multiple of 32 instead, read again with the pipeline's prompt, and compared with
qwen's reading of the crop as it is, per stratum and per band of that scale.

    uv run python experiments/probe_grid_pad.py          # read (cached), re-read where they differ, score
"""

import io
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps
from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).parent))
from tryout import WORK, READER_VERSION, load_set  # noqa: E402

from roboscriptorium import readers  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.trustdata import fold  # noqa: E402

GRID = 32
OUT = Path("work/probes/grid-pad")


def paper(im: Image.Image) -> tuple:
    """The crop's paper colour: the commonest colour of its border pixels."""
    w, h = im.size
    px = im.load()
    border = [px[x, y] for x in range(w) for y in (0, h - 1)]
    border += [px[x, y] for y in range(h) for x in (0, w - 1)]
    return Counter(border).most_common(1)[0][0]


def padded(png: bytes) -> bytes:
    im = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = im.size
    dw, dh = -w % GRID, -h % GRID
    im = ImageOps.expand(im, (dw // 2, dh // 2, dw - dw // 2, dh - dh // 2), fill=paper(im))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def scale(png: bytes) -> float:
    h = Image.open(io.BytesIO(png)).size[1]
    return max(GRID, round(h / GRID) * GRID) / h


if __name__ == "__main__":
    settings = Settings.from_env()
    books, items = load_set()
    base = json.loads(
        (WORK / f"reader-v{READER_VERSION}" / "readings" / "qwen3.8_27b-nvfp4.json").read_text()
    )
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / "qwen.json"
    done = json.loads(cache.read_text()) if cache.exists() else {}
    todo = [i for i in items if i["id"] not in done]
    for n, i in enumerate(todo, 1):
        done[i["id"]] = readers.transcribe(
            padded(i["png"]), settings.read_model, settings.ollama_url, books[i["book"]]["prompt"]
        )
        if n % 25 == 0 or n == len(todo):
            cache.write_text(json.dumps(done, ensure_ascii=False))
            print(f"{n}/{len(todo)}", flush=True)
    # Run-to-run noise: where the padded reading differs, the crop as it is read again.
    again_path = OUT / "qwen-again.json"
    again = json.loads(again_path.read_text()) if again_path.exists() else {}
    differ = [i for i in items if done[i["id"]] != base[i["id"]] and i["id"] not in again]
    for n, i in enumerate(differ, 1):
        again[i["id"]] = readers.transcribe(
            i["png"], settings.read_model, settings.ollama_url, books[i["book"]]["prompt"]
        )
        if n % 25 == 0 or n == len(differ):
            again_path.write_text(json.dumps(again, ensure_ascii=False))
            print(f"again {n}/{len(differ)}", flush=True)
    rows: dict[str, Counter] = {}
    for i in items:
        t = fold(i["truth"])
        s = scale(i["png"])
        band = "squashed ≤0.85" if s <= 0.85 else "stretched ≥1.15" if s >= 1.15 else "near 1"
        for key in (i["stratum"], band):
            c = rows.setdefault(key, Counter())
            c["lines"] += 1
            for name, text in (("as is", base[i["id"]]), ("padded", done[i["id"]])):
                r = fold(text)
                c[f"{name} right"] += r == t
                c[f"{name} edits"] += Levenshtein.distance(r, t)
            c["fixed"] += fold(done[i["id"]]) == t != fold(base[i["id"]])
            c["broken"] += fold(base[i["id"]]) == t != fold(done[i["id"]])
            if i["id"] in again:
                c["as is, read again, differs"] += again[i["id"]] != base[i["id"]]
                c["as is, read again, right"] += fold(again[i["id"]]) == t
    for key, c in rows.items():
        print(f"{key:18} {dict(c)}")
