"""Page kinds for `init`, signals first and the model where they can't tell: scored against
`tryouts/page-kinds-v1.json` on the ends of the text proper and on each page's fate.

    uv run python experiments/probe_page_kinds_combined.py [answers file]

The model's answers come from `probe_page_kinds_model.py`'s cache (the labelled pages it was
asked, edges and a few inside); a page the signals can't tell and the model wasn't asked
counts as text, as in `probe_page_signals.py`. No models run.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from probe_page_signals import clues, ends, fate, guess, layer  # noqa: E402

ANSWERS = Path(sys.argv[1] if len(sys.argv) > 1 else next(Path("work/probes/page-kinds").glob("answers-*.json")))

if __name__ == "__main__":
    labels = json.loads(Path("tryouts/page-kinds-v1.json").read_text())["books"]
    answers = json.loads(ANSWERS.read_text())
    fates, ends_right = Counter(), Counter()
    asked = unsure = 0
    for name, entry in sorted(labels.items()):
        book = Path("work") / name
        if not (book / "source.pdf").exists():
            continue
        pages = layer(book)
        want = {p.number: {int(k): v for k, v in entry["pages"].items()}.get(p.number, "text") for p in pages}
        by = {c.page: c for c in clues(pages)}
        final = {}
        for p in pages:
            g = guess(by[p.number], (p.number - 1) / (len(pages) - 1))
            if g == "?":
                unsure += 1
                a = answers.get(f"{name}:{p.number}")
                asked += a is not None
                g = a[0] if a else "text"
            final[p.number] = g
            fates[(fate(want[p.number]), fate(final[p.number]))] += 1
        w, g = ends(want), ends(final)
        ends_right["first"] += w[0] == g[0]
        ends_right["last"] += w[1] == g[1]
        ends_right["books"] += 1
        if w != g:
            print(f"  {name}: text proper {w[0]}–{w[1]}, got {g[0]}–{g[1]}")
    print(f"pages the signals couldn't tell: {unsure}, of which the model had an answer for {asked}")
    print("fate (labelled, final):", dict(fates))
    print("ends right:", dict(ends_right))
