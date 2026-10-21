"""`init`'s page kinds through the package code (`pagekinds.kinds`): the model on the edge pages,
the signals in the middle, scored against `tryouts/page-kinds-v1.json` on the text proper's two
ends. The model's earlier answers (`probe_page_kinds_model.py`'s cache) seed the per-book
caches, so only edge pages never asked before cost a call (about 4 s each on clef-flash).

    uv run python experiments/probe_init_ends.py [model]
"""

import json
import sys
from pathlib import Path

from roboscriptorium import pagekinds
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.pagekinds import ends
from roboscriptorium.pdf import cached_text_layer

OLD = Path("work/probes/page-kinds")

if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "clef-flash:9b"
    client = decide.for_model(model, Settings.from_env().ollama_url)
    old = {}
    for f in OLD.glob("answers-*.json"):
        old |= json.loads(f.read_text())
    labels = json.loads(Path("tryouts/page-kinds-v1.json").read_text())["books"]
    right = {"first": 0, "last": 0, "books": 0}
    for name, entry in sorted(labels.items()):
        book = Path("work") / name
        if not (book / "source.pdf").exists():
            continue
        pages = cached_text_layer(book / "source.pdf", book / "stages" / "textlayer.json")
        cache = OLD / f"edges-{name}.json"
        if not cache.exists():
            seed = {k.split(":")[1]: v for k, v in old.items() if k.startswith(name + ":")}
            cache.write_text(json.dumps(seed))
        kinds = pagekinds.kinds(book / "source.pdf", pages, client, cache)
        want = {int(k): v for k, v in entry["pages"].items()}
        want = {p.number: want.get(p.number, "text") for p in pages}
        w, g = ends(want), ends(kinds)
        right["first"] += w[0] == g[0]
        right["last"] += w[1] == g[1]
        right["books"] += 1
        off = pagekinds.printed_offset(pages)
        mark = "" if w == g else f"  <- labelled {pagekinds.page_label(w[0], off)} to {pagekinds.page_label(w[1], off)}"
        print(f"{name[:34]:34} got {pagekinds.page_label(g[0], off)} to {pagekinds.page_label(g[1], off)}{mark}", flush=True)
    print("ends right:", right)
