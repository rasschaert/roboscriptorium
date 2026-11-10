"""The short test of the small-capitals step on Nervous System: the book built with
`ROBO_LOWER_CAPITALS` on a copy, so its own caches and review stay as they are, against
the build it has (the copied `ocr-check.json`, the setting off).

    uv run --project ../roboscriptorium-caps python experiments/probe_caps_nervous_short.py [0]

Run from the main checkout so `work/` is reached by path. The whole book, as a page built
alone is asked other line-role questions than in its book. Prints every suspect between a
word and its capitals that is new or decided otherwise, and counts them by decision; the
places to look at are PDF 43 and 59 ("tv" unasked), 47 ("vcr" picked over "ver") and 158
("ver."/"vcr." asked). Writes `nervous-short.jsonl` beside the copy. With `0` the setting
stays off: a build from the caches alone, to check the copy.
"""

import json
import os
import shutil
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from roboscriptorium import pipeline
from roboscriptorium.book import Book
from roboscriptorium.config import Settings

SOURCE = Path("work/nervous-system")
OUT = Path("work/probes/caps-lower")
COPY = OUT / "nervous-system"


def _case(ours: str, others) -> bool:
    return any(o.lower() == ours.lower() or o.isupper() for o in others)


def main():
    if not COPY.exists():
        COPY.mkdir(parents=True)
        for name in ("source.pdf", "book.toml"):
            shutil.copy2(SOURCE / name, COPY / name)
        shutil.copytree(SOURCE / "stages", COPY / "stages")
    before = {
        (s["page"], s["line"], s["start"]): s
        for s in json.loads((SOURCE / "stages/ocr-check.json").read_text())
    }
    os.environ["ROBO_LOWER_CAPITALS"] = (sys.argv[1:] or ["1"])[0]
    stages = pipeline.run(Book.load(COPY), settings=Settings.from_env())
    text = {(p.number, k): line.text for p in stages.corrected for k, line in enumerate(p.lines)}
    rows, counts = [], Counter()
    for s in stages.suspects:
        old = before.get((s.page, s.line, s.start))
        same = old and (old["choice"], old["chosen"]) == (s.choice, s.chosen)
        if same or not (_case(s.ours, s.others) or old):
            continue
        kind = "decided otherwise" if old else "new"
        capitals = s.choice == "other" and s.chosen != s.chosen.lower()
        counts[kind, "capitals" if capitals else s.choice] += 1
        rows.append({"kind": kind, **asdict(s), "built": text.get((s.page, s.line))})
        if kind == "new" and s.choice == "ours":
            continue
        was = f" (was {old['choice']} {old['chosen'] or ''})" if old else ""
        print(
            f"PDF {s.page} line {s.line} {s.ours!r} / {list(s.others)} → {s.choice} "
            f"{s.chosen or ''}{was}\n    votes {s.votes}\n    built: {text.get((s.page, s.line))}",
            flush=True,
        )
    gone = len(before.keys() - {(s.page, s.line, s.start) for s in stages.suspects})
    print(f"{len(before)} suspects before, {len(stages.suspects)} now, {gone} gone")
    for (kind, choice), n in sorted(counts.items()):
        print(f"{kind}: {choice} ×{n}")
    path = OUT / "nervous-short.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print("done", flush=True)


if __name__ == "__main__":
    main()
