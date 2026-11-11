"""The short test of doubts raised on lower-case small capitals (`ROBO_LOWER_CAPITALS`):
the pages of `probe_caps_lower.py`'s places, built without and with them, each place's
errors compared.

    uv run --project ../roboscriptorium-caps python experiments/probe_caps_lower_short.py
    uv run --project ../roboscriptorium-caps python experiments/probe_caps_lower_short.py compare

Run from the main checkout so `work/` is reached by path. Every small capital the probe
asked about, and the lower-case places on 40 pages of its sample; one worker a book, so
two builds never write one book's caches at once. Writes `short.jsonl` beside the answers,
a book at a time; `compare` prints what the setting fixed, made, and moved between asked
and unasked, a place being a book, page and the words got and wanted.
"""

import json
import os
import random
import sys
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
    with ProcessPoolExecutor(bench.workers()) as pool, (OUT / "short.jsonl").open("w") as out:
        jobs = [pool.submit(_book, b, _ranges(p)) for b, p in pages.items()]
        for job in as_completed(jobs):
            got = job.result()
            out.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in got))
            out.flush()
            print(f"{got[0]['book']}: {len(got)} rows", flush=True)


def compare():
    rows = [json.loads(x) for x in (OUT / "short.jsonl").read_text().splitlines()]
    place = lambda r: (r["book"], r["page"], r["got"], r["want"])  # noqa: E731
    off = {place(r): r for r in rows if r["flag"] == "0" and "key" in r}
    on = {place(r): r for r in rows if r["flag"] == "1" and "key" in r}
    for flag in "01":
        n = sum(r["case_suspects"] for r in rows if r["flag"] == flag and "key" not in r)
        print(f"setting {flag}: {n} suspects between a word and its capitals")
    groups = {
        "fixed": [off[k] for k in off.keys() - on.keys()],
        "made": [on[k] for k in on.keys() - off.keys()],
        "unasked, now asked": [on[k] for k in off.keys() & on.keys() if on[k]["asked"] > off[k]["asked"]],
        "asked, now unasked": [on[k] for k in off.keys() & on.keys() if on[k]["asked"] < off[k]["asked"]],
    }  # fmt: skip
    for name, group in groups.items():
        unasked = sum(not r["asked"] for r in group)
        print(f"\n{name}: {len(group)} ({unasked} unasked)")
        for r in sorted(group, key=place):
            asked = "asked" if r["asked"] else "unasked"
            print(f"  {r['book']} p{r['page']} {r['got']!r} for {r['want']!r} ({r['kind']}, {asked})")


if __name__ == "__main__":
    compare() if sys.argv[1:] == ["compare"] else main()
