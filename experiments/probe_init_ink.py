"""Blank pages showing the other side's print pad `init`'s ends (the page-kind model calls
them text, unsure). Told how dark a page's ink is against the book's text pages, does it
call them blank? Every edge page of the labelled books asked again with an `ink` line in
its state (`faint.contrast` over the book's median), cached apart in
work/probes/page-kinds-ink/; the ends scored against the labels beside production's
(cached answers). Run after the mirror test failed to tell show-through from washed-out
text (decisions.md, 2026-11-15).

    PYTHONPATH=experiments uv run python experiments/probe_init_ink.py [--dry]
"""

import statistics
import sys
from pathlib import Path

import pymupdf
from setup_gaps import LABELS, kinds_of

from roboscriptorium import faint, pagekinds
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/page-kinds-ink")
plain_state = pagekinds.state
share: dict[tuple[str, int], float] = {}


def state(book: str, n: int, total: int, page) -> dict:
    out = plain_state(book, n, total, page)
    s = share.get((book, n))
    if s is not None:
        out["ink"] = (
            f"faint: {max(0, round(s * 100))}% as dark as this book's pages of text (a blank page "
            "showing the print of its other side looks like this, and so does a washed-out scan)"
            if s < 0.3
            else "as dark as this book's pages of text"
        )
    return out


def main():
    dry = "--dry" in sys.argv
    settings = Settings.from_env()
    client = decide.for_model(settings.role_model, settings.ollama_url)
    pagekinds.state = state
    OUT.mkdir(parents=True, exist_ok=True)
    right = {"first, told the ink": 0, "last, told the ink": 0, "first, production": 0, "last, production": 0, "books": 0}
    for name, entry in sorted(LABELS.items()):
        root = Path("work") / name
        if not (root / "source.pdf").exists() or not (root / "stages" / "textlayer.json").exists():
            print(f"{name}: no scan or text layer, left out", flush=True)
            continue
        pages = cached_text_layer(root / "source.pdf", root / "stages" / "textlayer.json")
        before = kinds_of(root, pages)
        if dry or before is None:
            print(f"{name}: {'ready' if before is not None else 'no cached production answers, left out'}", flush=True)
            continue
        with pymupdf.open(root / "source.pdf") as doc:
            got = {}
            for p in pages:
                try:
                    got[p.number] = faint.contrast(doc[p.number - 1], p.lines)
                except ValueError:
                    pass
        body = statistics.median(got[p.number] for p in pages if p.number in got and len(p.lines) > 20)
        share.update({(name, n): c / body for n, c in got.items()})
        kinds = pagekinds.kinds(root / "source.pdf", pages, client, OUT / f"{name}.json")
        labelled = {int(k): v for k, v in entry["pages"].items()}
        want = pagekinds.ends({p.number: labelled.get(p.number, "text") for p in pages})
        g, b = pagekinds.ends(kinds), pagekinds.ends(before)
        right["books"] += 1
        right["first, told the ink"] += g[0] == want[0]
        right["last, told the ink"] += g[1] == want[1]
        right["first, production"] += b[0] == want[0]
        right["last, production"] += b[1] == want[1]
        print(f"{name[:36]:36} labelled {want}, production {b}, told the ink {g}", flush=True)
    print("ends right:", right)


if __name__ == "__main__":
    main()
