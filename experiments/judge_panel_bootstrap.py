"""Does adding judges to a panel really help tell clef's wrong picks apart? On judge set
v2, each panel's held-out-by-book scores (a logistic model trained on 19 books, scored on
the 20th, as `judge_combine_many.py`), then the AUC difference between a panel and the
base panel with a 95% interval from resampling books. No models.

    PYTHONPATH=experiments uv run python experiments/judge_panel_bootstrap.py
"""

import json
import random

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from judge_combine import ROOT, features, right

BASE = ["autotrust-jev_35b-nvfp4", "d3_9b", "pplx-decider_27b-nvfp4+wide"]
CANDIDATES = [
    "d1_3b", "d1-omni_2b", "autotrust-jev_9b-nvfp4+text", "pplx-decider-flash_4b-nvfp4",
    "d3_27b-nvfp4", "pplx-decider_27b-nvfp4", "clef_27b+wide",
]


def scores(items, books, answers, panel):
    """Each item's held-out P(clef wrong) from clef's confidence and the panel's answers."""
    def fx(i):
        f = [i["incumbent"]["confidence"]]
        for n in panel:
            f += features(i, answers[n][i["id"]])[1:]
        return f

    out = {}
    for book in books:
        train = [i for i in items if i["book"] != book]
        test = [i for i in items if i["book"] == book]
        y = [int(not right(i, i["incumbent"]["value"])) for i in train]
        model = LogisticRegression(max_iter=2000).fit([fx(i) for i in train], y)
        for i, p in zip(test, model.predict_proba([fx(i) for i in test])[:, 1], strict=True):
            out[i["id"]] = p
    return out


def main():
    data = json.loads((ROOT / "items.json").read_text())
    books = list(data["books"])
    names = BASE + CANDIDATES
    answers = {n: json.loads((ROOT / "answers" / f"{n}.json").read_text()) for n in names}
    items = [i for i in data["items"] if all(i["id"] in a for a in answers.values())]
    truth = {i["id"]: int(not right(i, i["incumbent"]["value"])) for i in items}
    panels = {"base": BASE}
    panels |= {f"+{c}": BASE + [c] for c in CANDIDATES}
    panels["+d1 trio"] = BASE + ["d1_3b", "d1-omni_2b", "autotrust-jev_9b-nvfp4+text"]
    panels["+all"] = names
    got = {k: scores(items, books, answers, p) for k, p in panels.items()}
    by_book = {b: [i["id"] for i in items if i["book"] == b] for b in books}
    rng = random.Random(0)
    draws = [[rng.choice(books) for _ in books] for _ in range(1000)]

    def auc(s, ids):
        return roc_auc_score([truth[k] for k in ids], [s[k] for k in ids])

    allids = [i["id"] for i in items]
    base = got["base"]
    print(f"{len(items)} suspects; base panel {', '.join(BASE)}: AUC {auc(base, allids):.3f}")
    for k, s in got.items():
        if k == "base":
            continue
        diffs = []
        for d in draws:
            ids = [x for b in d for x in by_book[b]]
            if len({truth[x] for x in ids}) < 2:
                continue
            diffs.append(auc(s, ids) - auc(base, ids))
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        mark = "*" if lo > 0 else " "
        print(f" {mark} {k:34} AUC {auc(s, allids):.3f}  lift {auc(s, allids) - auc(base, allids):+.3f}  [{lo:+.3f}, {hi:+.3f}]")


if __name__ == "__main__":
    main()
