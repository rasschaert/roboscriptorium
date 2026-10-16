"""Put the break-judge probe's answers into each book's decision cache, keyed as
`parabreaks.judged` asks them, so a build doesn't ask the judge those lines again.

The probe and the stage ask the same question with the same state; the stage's key adds
the line's page and index and the crop settings (`parabreaks._ask`). A line whose text
the build changed (an OCR fix) has another state, and is asked anew.

    uv run python experiments/seed_break_answers.py [model]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import parabreaks
from roboscriptorium.roles import DecisionCache

OUT = Path("work/probes/break-judge")


def main(model: str = "clef:27b") -> None:
    rows = {(r["book"], r["page"], r["line"]): r for r in json.loads((OUT / "lines.json").read_text())}
    name = "answers.jsonl" if model == "clef:27b" else f"answers-{model.replace(':', '_')}.jsonl"
    caches: dict[str, DecisionCache] = {}
    added = Counter()
    for ln in (OUT / name).read_text().splitlines():
        a = json.loads(ln)
        r = rows[(a["book"], a["page"], a["line"])]
        state = {
            "line above"
            + (" (the last line of the page before)" if r["page_top"] else ""): r["above"],
            "line in question": r["text"],
            "line below": r["below"],
        }
        where = {
            "page": r["page"],
            "line": r["line"],
            "crop": [parabreaks.DPI, parabreaks.PAD, parabreaks.GAP],
        }
        key = DecisionCache.key(model, parabreaks.QUESTION, {**state, **where})
        cache = caches.setdefault(
            r["book"], DecisionCache(Path("work") / r["book"] / "stages" / "decisions.jsonl")
        )
        if cache.get(key) is None:
            cache.put(key, {"value": a["choice"], "confidence": a["confidence"]})
            added[r["book"]] += 1
    for book, n in sorted(added.items()):
        print(f"{book:45} {n}")
    print(f"{sum(added.values())} answers added")


if __name__ == "__main__":
    main(*sys.argv[1:])
