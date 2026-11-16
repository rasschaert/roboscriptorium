"""What the extra readers' offers were worth in a bench run: every place a version had
only extra readers behind it (the judged places kept in work/probes/extra-quick/ from a
`bench quick` with ROBO_EXTRA_READERS), labelled by the baseline run's error rows (the
offer is the print where the baseline has an error on that line whose wanted words hold
it; else the build's version is), by which readers offered it and how the judges voted.
No models.

    uv run python experiments/probe_extra_offers.py <baseline run's .errors.jsonl>
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

KEPT = Path("work/probes/extra-quick")
# The bench's rows and the judged places write quote marks and dots differently.
FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "…": "..."})


def fold(text: str) -> str:
    return text.translate(FOLD).replace(" ", "")



errors = defaultdict(list)
for line in Path(sys.argv[1]).read_text().splitlines():
    e = json.loads(line)
    for k in range(e["lines"][0], e["lines"][1] + 1):
        errors[e["book"], e["page"], k].append(e)

rows = []
for f in sorted(KEPT.glob("*.ocr-check.json")):
    book = f.name.removesuffix(".ocr-check.json")
    for s in json.loads(f.read_text()):
        versions = [s["ours"], *s["others"]]
        for i, v in enumerate(versions[1:], 1):
            behind = [r for r, has in s["support"].items() if i < len(has) and has[i]]
            if not behind or not all(r.startswith("extra-") for r in behind):
                continue
            w = fold(v)
            right = any(
                w and w in fold(e["want"]) and w not in fold(e["got"])
                for e in errors[book, s["page"], s["line"]]
            )
            votes = sum(1 for x in s["votes"].values() if x == v)
            names = "+".join("zoom" if "x2" in r else "olmOCR" for r in sorted(behind))
            did = "asked" if s["choice"] == "review" else "took it" if s["chosen"] == v else "left it"
            new = all(
                all(r.startswith("extra-") for r, has in s["support"].items() if j < len(has) and has[j])
                for j in range(1, len(versions))
            )
            rows.append((book, s, v, right, votes, len(s["votes"]), names, did, new))

print(f"{len(rows)} offers with only extra readers behind them, {sum(r[3] for r in rows)} the print")
for title, key in (
    ("by who offered", lambda r: r[6]),
    ("by judges for the offer", lambda r: f"{r[4]} of {r[5]}"),
    ("by what the arbiter did", lambda r: r[7]),
    ("by whether the place was judged without them", lambda r: "new place" if r[8] else "one more version"),
):
    c, good = Counter(map(key, rows)), Counter(key(r) for r in rows if r[3])
    print(title)
    for k in sorted(c):
        print(f"  {k:24} {c[k]:4} offers, {good[k]:3} the print")
print("offers that were the print:")
for book, s, v, right, votes, n, names, choice, _ in rows:
    if right:
        print(f"  {book[:22]:22} p{s['page']}: {s['ours']!r} → {v!r}  {names}, judges {votes}/{n}, arbiter {choice}")
print("offers the arbiter took or asked about that weren't:")
for book, s, v, right, votes, n, names, choice, _ in rows:
    if not right and choice != "left it":
        print(f"  {book[:22]:22} p{s['page']}: {s['ours']!r} → {v!r}  {names}, judges {votes}/{n}, arbiter {choice}")
