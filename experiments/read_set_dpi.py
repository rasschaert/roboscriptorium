"""The read model's reading of the frozen reader set from crops of another resolution, as one more
witness for the vote simulation.

    uv run python experiments/read_set_dpi.py <dpi> [limit]

Each line is cut from its PDF as the readers cut it (`readers._line_crop`, the box and the
neighbour-trimmed span in the item's cache key) but at <dpi>, then read with the book's own prompt.
Writes work/tryout/reader-v2/readings/<read model>+dpi<dpi>.json; `vote_sim.py <that stem>` scores it.
`--check` only compares the crops at 300 dpi with the frozen ones. Resumable.
"""

import json
import sys
from collections import Counter
from io import BytesIO
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import tryout  # noqa: E402

from roboscriptorium import readers  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.files import write_atomic  # noqa: E402


def crop_of(doc, item: dict, dpi: int) -> bytes:
    parts = item["cache_key"].split(":")
    page, box = int(parts[0]), [float(v) for v in parts[3].split(",")]
    span = tuple(float(v) for v in parts[4].split("-")) if len(parts) > 4 else None
    readers.DPI = dpi
    return readers._line_crop(doc, page, box, span)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dpi = int(args[0])
    limit = int(args[1]) if len(args) > 1 else 0
    settings = Settings.from_env()
    books, items = tryout.load_set()
    items = items[:limit] if limit else items
    if "--check" in sys.argv:
        close, far, shapes = 0, 0, []
        for item in items:
            with pymupdf.open(Path("work") / item["book"] / "source.pdf") as doc:
                mine = Image.open(BytesIO(crop_of(doc, item, 300))).convert("L")
            frozen = Image.open(BytesIO(item["png"])).convert("L")
            shapes.append((mine.width - frozen.width, mine.height - frozen.height))
            gap = np.abs(np.asarray(mine.resize(frozen.size), dtype=int) - np.asarray(frozen, dtype=int)).mean()
            close += gap < 10
            far += gap >= 10
        print(f"crops at 300 dpi close to the frozen ones (mean grey gap under 10): {close}, further: {far}")
        print("width and height differences in pixels, most common:", Counter(shapes).most_common(5))
        sys.exit()
    out = tryout._readings_path(f"{settings.read_model}+dpi{dpi}")
    out.parent.mkdir(parents=True, exist_ok=True)
    done = json.loads(out.read_text()) if out.exists() else {}
    asked = 0
    for item in items:
        if item["id"] in done:
            continue
        with pymupdf.open(Path("work") / item["book"] / "source.pdf") as doc:
            png = crop_of(doc, item, dpi)
        done[item["id"]] = readers.transcribe(png, settings.read_model, settings.ollama_url, books[item["book"]]["prompt"])
        asked += 1
        if asked % 25 == 0:
            write_atomic(out, json.dumps(done, ensure_ascii=False))
            print(f"{len(done)}/{len(items)}", flush=True)
    write_atomic(out, json.dumps(done, ensure_ascii=False))
    print(f"done: {len(done)} readings")
