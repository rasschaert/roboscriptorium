"""The accent-zone fit as a proposer: where it says a plain word carries a mark
(`probe_missed_accents.py`), do the judges agree? Every dropped mark it placed and the
plain words whose cosine is in the top 1%, each put to the judges as the layer's word
against the marked one, as the OCR check asks them (`ocrcheck._decide`). Per judge: marked
picks among the dropped marks (right) and among the plain words (false alarms), and how
many of each every judge picks. Answers cached in work/probes/accent-judges/.

    PYTHONPATH=experiments uv run python experiments/probe_accent_judges.py [--dry]
"""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.roles import DecisionCache

OUT = Path("work/probes/accent-judges")
rows = [json.loads(line) for line in Path("work/probes/missed-accents.jsonl").read_text().splitlines()]
cut = np.quantile([r["cosine"] for r in rows if not r["print_marked"]], 0.99)
chosen = [r for r in rows if r["print_marked"] or r["cosine"] > cut]
settings = Settings.from_env()
dry = "--dry" in sys.argv
OUT.mkdir(parents=True, exist_ok=True)
cache = DecisionCache(OUT / "decisions.jsonl")
tally, placed, lines_out = Counter(), 0, []
for name in dict.fromkeys(r["book"] for r in chosen):
    book = Book.load(Path("work") / name)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json")
    pages = {p.number: p for p in layer}
    whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
    vision = None if dry else decide.for_model(settings.judge_model, settings.ollama_url)
    alarms = [] if dry else [a for spec in settings.alarm_models if (a := pipeline._alarm(spec, settings, book, whole))]
    with pymupdf.open(book.source) as doc:
        for r in (r for r in chosen if r["book"] == name):
            page = pages[r["page"]]
            x, y = (r["box"][0] + r["box"][2]) / 2, (r["box"][1] + r["box"][3]) / 2
            at = [k for k, ln in enumerate(page.lines) if ln.y0 <= y <= ln.y1 and ln.x0 <= x <= ln.x1]
            if len(at) != 1 or page.lines[at[0]].text.count(r["word"]) != 1:
                continue  # the word twice in its line, or no one line at its box: left out
            k = at[0]
            text = page.lines[k].text
            a0 = text.index(r["word"])
            placed += 1
            if dry:
                continue
            (_, _, votes), _ = ocrcheck._decide(
                doc[r["page"] - 1], r["page"], k, text, a0, a0 + len(r["word"]), [r["marked"]], r["box"],
                book.language, vision, None, cache, alarms=alarms,
            )  # fmt: skip
            kind = "dropped mark" if r["print_marked"] else "plain word"
            tally[kind] += 1
            for model, pick in votes.items():
                tally[(kind, model)] += pick == r["marked"]
            every = [v for m, v in votes.items() if m != "word list"]
            tally[(kind, "every judge")] += bool(every) and all(v == r["marked"] for v in every)
            tally[(kind, "most judges")] += sum(v == r["marked"] for v in every) * 2 > len(every)
            lines_out.append(f"  {kind:12} {name[:16]:16} PDF {r['page']:4} {r['word']!r} → {r['marked']!r}: marked by {sum(v == r['marked'] for v in every)} of {len(every)}")
    print(name, flush=True)
if dry:
    print(f"{len(chosen)} candidates ({sum(r['print_marked'] for r in chosen)} dropped marks), {placed} placed on a line; cosine cut {cut:.3f}")
else:
    for kind in ("dropped mark", "plain word"):
        print(f"{kind}s: {tally[kind]}")
        for key, n in tally.items():
            if isinstance(key, tuple) and key[0] == kind:
                print(f"    picked as marked by {key[1][:40]:40} {n}")
    print("\n".join(lines_out))
