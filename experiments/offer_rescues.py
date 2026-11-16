"""What a benched source of versions rescued: the baseline run's silent errors (wrong in
the book, no question) that the new run fixed or asked about, by cause, beside the silent
errors it made. No models: it reads two bench runs' error rows.

    uv run python experiments/offer_rescues.py <baseline.errors.jsonl> <new.errors.jsonl> [examples]
"""

import json
import sys
from collections import Counter, defaultdict


def rows(path):
    return {(r["book"], r["key"]): r for r in map(json.loads, open(path))}


def main(base, new, examples=3):
    old, now = rows(base), rows(new)
    silent = {k: r for k, r in old.items() if not r["asked"]}
    fixed, asked, made = Counter(), Counter(), Counter()
    shown = defaultdict(list)
    for k, r in silent.items():
        if k not in now:
            fixed[r["cause"]] += 1
            shown[r["cause"]].append(f'fixed  {r["book"][:22]} p{r["page"]}: {r["got"]!r} → {r["want"]!r}')
        elif now[k]["asked"]:
            asked[r["cause"]] += 1
            shown[r["cause"]].append(f'asked  {r["book"][:22]} p{r["page"]}: {r["got"]!r} / {r["want"]!r}')
    for k, r in now.items():
        if not r["asked"] and (k not in old or old[k]["asked"]):
            made[r["cause"]] += 1
            shown[r["cause"]].append(f'MADE   {r["book"][:22]} p{r["page"]}: {r["got"]!r} for {r["want"]!r}')
    total = Counter(r["cause"] for r in silent.values())
    print(f"baseline silent places: {len(silent)}")
    print(f'{"cause":28} silent  fixed  asked  made silent')
    for cause in sorted(total | made, key=lambda c: -(fixed[c] + asked[c] + made[c])):
        if fixed[cause] + asked[cause] + made[cause]:
            print(f"{cause:28} {total[cause]:6} {fixed[cause]:6} {asked[cause]:6} {made[cause]:6}")
            for line in shown[cause][:examples]:
                print("    " + line)
    print(f'{"all":28} {len(silent):6} {sum(fixed.values()):6} {sum(asked.values()):6} {sum(made.values()):6}')


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
