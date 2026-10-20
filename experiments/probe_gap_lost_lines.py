"""Lost lines the mid-sentence rule can't see: a gap of about two line pitches between two
text-layer lines, whatever the line above ends in. For the lost-text errors of the latest
tuning and validation benches (asked and settled ones left out), is such a gap on the page,
and how many gaps does a page hold otherwise (scene breaks, chapter openings)?

    uv run python experiments/probe_gap_lost_lines.py

No models: the cached text layers and the benches' error lists.
"""

import json
import statistics
from pathlib import Path

RUNS = [
    "tuning-20261019T191326-6596927-dirty",
    "validation-20261019T191707-6596927-dirty",
]
LOW, HIGH = 1.6, 3.4


def gaps(page: dict) -> list[int]:
    lines = page["lines"]
    if len(lines) < 5:
        return []
    pitch = statistics.median(b["y0"] - a["y0"] for a, b in zip(lines, lines[1:], strict=False))
    return [
        k
        for k, (a, b) in enumerate(zip(lines, lines[1:], strict=False))
        if pitch > 0 and LOW * pitch <= b["y0"] - a["y0"] <= HIGH * pitch
    ]


def main() -> None:
    errors = [
        json.loads(line)
        for run in RUNS
        for line in Path(f"work/bench/{run}.errors.jsonl").read_text().splitlines()
        if line.strip()
    ]
    lost = [
        e
        for e in errors
        if e["cause"] == "missing text" and e["layer"] == "lost" and not e["asked"] and not e["auto"]
    ]
    layers = {}
    for book in {e["book"] for e in errors}:
        f = Path("work") / book / "stages" / "text-layer.json"
        if f.exists():
            data = json.loads(f.read_text())
            layers[book] = {p["number"]: p for p in (data if isinstance(data, list) else data["pages"])}
    hit = 0
    for e in lost:
        page = layers.get(e["book"], {}).get(e["page"])
        g = gaps(page) if page else None
        hit += bool(g)
        print(f"{e['book'][:14]:14} p{e['page']:<4} gaps {g}  {e['want'][:30]!r}")
    print(f"\n{hit} of {len(lost)} lost-text errors sit on a page with such a gap")
    pages = [p for book in layers.values() for p in book.values()]
    withgap = sum(bool(gaps(p)) for p in pages)
    print(f"all pages in the benches' books: {withgap} of {len(pages)} hold at least one")


if __name__ == "__main__":
    main()
