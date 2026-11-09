"""The short test of doubts raised on lower-case small capitals (`ROBO_LOWER_CAPITALS`):
the pages of `probe_caps_lower.py`'s places, built without and with them, each place's
errors compared.

    uv run --project ../roboscriptorium-caps python experiments/probe_caps_lower_short.py

Run from the main checkout so `work/` is reached by path. Every small capital the probe
asked about, and the lower-case places on 40 pages of its sample; one worker a book, so
two builds never write one book's caches at once. Writes `short.jsonl` beside the answers.
"""

import json
import os
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from roboscriptorium import bench, errorlog
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring

OUT = Path("work/probes/caps-lower")


def _ranges(pages: list[int]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for p in sorted(set(pages)):
        if out and p - out[-1][1] <= 2:
            out[-1][1] = p
        else:
            out.append([p, p])
    return [(a, b) for a, b in out]


def _book(book: str, ranges: list[tuple[int, int]]) -> list[dict]:
    rows = []
    for flag in ("0", "1"):
        os.environ["ROBO_LOWER_CAPITALS"] = flag
        settings = Settings.from_env()
        for a, b in ranges:
            name, _, stages, _, errors, found, _ = scoring.build(f"work/{book}:{a}-{b}", settings)
            for r in errorlog.rows(name, errors, found, stages.pages, stages.suspects):
                rows.append({"flag": flag, "range": [a, b], **r})
            n = sum(s.others and s.ours.lower() == s.others[0].lower() for s in stages.suspects)
            rows.append({"flag": flag, "range": [a, b], "book": name, "case_suspects": n})
    return rows


def main():
    answers = [json.loads(x) for x in (OUT / "answers.jsonl").read_text().splitlines()]
    neg = sorted({(r["book"], r["page"]) for r in answers if not r["truth"]})
    random.Random(1).shuffle(neg)
    pages = defaultdict(list)
    for r in answers:
        if r["truth"]:
            pages[r["book"]].append(r["page"])
    for book, page in neg[:40]:
        pages[book].append(page)
    out = []
    with ProcessPoolExecutor(bench.workers()) as pool:
        jobs = [pool.submit(_book, b, _ranges(p)) for b, p in pages.items()]
        for job in as_completed(jobs):
            got = job.result()
            out += got
            print(f"{got[0]['book']}: {len(got)} rows", flush=True)
    (OUT / "short.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))


if __name__ == "__main__":
    main()
