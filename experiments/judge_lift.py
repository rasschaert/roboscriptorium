"""What judge candidates add to a panel, on judge set v2: the places every judge of the
panel and clef get wrong that the candidate gets right (its rescues, with examples), and
its lift in telling clef's wrong picks apart, alone and with the other candidates, with a
95% interval from resampling books (`judge_panel_bootstrap.py`'s method). No models.

    PYTHONPATH=experiments uv run python experiments/judge_lift.py <candidate answers stem> [more …]

The panel is production's judges that have answers on the set (`BASE`).
"""

import json
import random
import sys

import numpy as np
from sklearn.metrics import roc_auc_score

from judge_combine import ROOT, right
from judge_panel_bootstrap import scores

BASE = ["autotrust-jev_35b-nvfp4", "d3_9b", "autotrust-jev_9b-nvfp4+text"]


def main(candidates: list[str]) -> None:
    data = json.loads((ROOT / "items.json").read_text())
    books = list(data["books"])
    names = BASE + candidates
    answers = {n: json.loads((ROOT / "answers" / f"{n}.json").read_text()) for n in names}
    items = [i for i in data["items"] if all(i["id"] in a for a in answers.values())]
    truth = {i["id"]: int(not right(i, i["incumbent"]["value"])) for i in items}
    missed = [
        i for i in items
        if truth[i["id"]] and not any(right(i, answers[n][i["id"]]["value"]) for n in BASE)
    ]
    print(f"{len(items)} suspects; clef and the panel ({', '.join(BASE)}) all wrong on {len(missed)}")
    for c in candidates:
        got = [i for i in missed if right(i, answers[c][i["id"]]["value"])]
        wrong = sum(not right(i, answers[c][i["id"]]["value"]) for i in items)
        alone = [
            i for i in items
            if right(i, answers[c][i["id"]]["value"]) and not right(i, i["incumbent"]["value"])
            and not any(right(i, answers[n][i["id"]]["value"]) for n in names if n != c)
        ]
        print(f"{c[-44:]}: rescues {len(got)} of the {len(missed)} shared misses; right where every other judge here is wrong {len(alone)}; wrong on {wrong} of {len(items)}")
        for i in got[:6]:
            readings = i["state"]["readings"]
            print("     ", i["book"][:20], "print:", [r for r, ok in zip(readings, i["right"]) if ok], "others:", [r for r, ok in zip(readings, i["right"]) if not ok])
    panels = {"base": BASE} | {f"+{c[-40:]}": BASE + [c] for c in candidates}
    if len(candidates) > 1:
        panels["+all candidates"] = names
    got = {k: scores(items, books, answers, p) for k, p in panels.items()}
    by_book = {b: [i["id"] for i in items if i["book"] == b] for b in books}
    rng = random.Random(0)
    draws = [[rng.choice(books) for _ in books] for _ in range(1000)]

    def auc(s, ids):
        return roc_auc_score([truth[k] for k in ids], [s[k] for k in ids])

    ids = [i["id"] for i in items]
    print(f"telling clef's wrong picks apart, base panel: AUC {auc(got['base'], ids):.3f}")
    for k, s in got.items():
        if k == "base":
            continue
        diffs = []
        for d in draws:
            sample = [x for b in d for x in by_book[b]]
            if len({truth[x] for x in sample}) == 2:
                diffs.append(auc(s, sample) - auc(got["base"], sample))
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        print(f" {'*' if lo > 0 else ' '} {k:44} lift {auc(s, ids) - auc(got['base'], ids):+.3f}  [{lo:+.3f}, {hi:+.3f}]")


if __name__ == "__main__":
    main(sys.argv[1:])
