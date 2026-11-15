"""The short test of an extra reader in the build (`ROBO_EXTRA_READERS`): the pages
holding the silent errors it read right on the short test (`silent_screen.py`) and the
reader in use didn't, each built alone, without it and with it, in a copy of the book
(work/probes/extra-readers/, the book's own caches untouched). Per error: fixed
silently, asked, or still as it was; and what the reader costs on those pages in
suspects and questions.

    PYTHONPATH=experiments uv run python experiments/probe_extra_reader.py <model> [variant]
"""

import json
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from silent_screen import ROOT, answers, fold

from roboscriptorium import pipeline
from roboscriptorium.book import Book
from roboscriptorium.config import Settings

OUT = Path("work/probes/extra-readers")
IN_USE = "qwen3.8:27b-nvfp4"


def rescued(model: str, variant: str, items: list[dict]) -> set[str]:
    got = {k: fold(v) for k, v in answers(model, variant).items()}
    return {
        i["id"]
        for i in items
        if i["id"] in got and i["want"] in got[i["id"]] and (i["got"] not in got[i["id"]] or i["got"] in i["want"]) and not (i["got"] in got[i["id"]] and i["want"] in i["got"])
    }


def main():
    # "<model>@x2" is the model shown each crop at twice its size (the test's "zoom").
    spec = sys.argv[1]
    model, variant = spec.partition("@x")[0], ("zoom" if "@x" in spec else (sys.argv[2] if len(sys.argv) > 2 else "book"))
    items = [i for i in json.loads((ROOT / "items.json").read_text())["items"] if i["stratum"] == "silent"]
    new = rescued(model, variant, items) - rescued(IN_USE, "book", items)
    mine = [i for i in items if i["id"] in new]
    print(f"{spec}: {len(mine)} silent errors it reads right and {IN_USE} doesn't", flush=True)
    settings = Settings.from_env()
    tally, cost = Counter(), Counter()
    for i in mine:
        name, page, line = i["id"].rsplit(":", 2)
        page, line = int(page), int(line)
        copy = OUT / name
        if not copy.exists():
            OUT.mkdir(parents=True, exist_ok=True)
            # A clone: no bytes copied until one side changes.
            subprocess.run(["cp", "-Rc", str(Path("work") / name), str(copy)], check=True)
        book = Book.load(copy)
        seen = {}
        for mode, extra in (("without", ""), ("with", spec)):
            stages = pipeline.run(book, pages=(page, page), settings=replace(settings, extra_readers=extra))
            here = [s for s in stages.suspects if s.page == page and s.line == line and any(i["want"] in fold(v) for v in s.others)]
            seen[mode] = (
                "no suspect" if not here
                else "fixed" if any(s.choice == "other" and i["want"] in fold(s.chosen or "") for s in here)
                else "asked" if any(s.choice == "review" for s in here)
                else "kept as it was"
            )
            cost[mode, "suspects"] += len(stages.suspects)
            cost[mode, "questions"] += sum(s.choice == "review" for s in stages.suspects)
            cost[mode, "changed"] += sum(s.choice == "other" for s in stages.suspects)
        tally[seen["without"], seen["with"]] += 1
        print(f"  {name[:22]:22} p{page} [{i['got']}] → [{i['want']}] ({i['cause']}): without {seen['without']}, with {seen['with']}", flush=True)
    print("without → with:", dict(tally))
    print("on those pages:", {f"{k} {m}": cost[m, k] for k in ("suspects", "questions", "changed") for m in ("without", "with")})


if __name__ == "__main__":
    main()
