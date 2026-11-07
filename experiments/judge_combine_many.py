"""How well clef's wrong picks are told apart from its confidence plus several other
judges' answers on judge set v2: AUC, a logistic model trained on 19 books and scored on
the 20th. No models.

    uv run python experiments/judge_combine_many.py <answers name> [more …]
"""

import json
import sys

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from judge_combine import ROOT, features, right


def main(names: list[str]) -> None:
    data = json.loads((ROOT / "items.json").read_text())
    seconds = [json.loads((ROOT / "answers" / f"{n}.json").read_text()) for n in names]
    items = [i for i in data["items"] if all(i["id"] in s for s in seconds)]

    def fx(i):
        f = [i["incumbent"]["confidence"]]
        for s in seconds:
            f += features(i, s[i["id"]])[1:]
        return f

    scores, truth = [], []
    for book in data["books"]:
        train = [i for i in items if i["book"] != book]
        test = [i for i in items if i["book"] == book]
        if not test:
            continue
        y = [int(not right(i, i["incumbent"]["value"])) for i in train]
        model = LogisticRegression(max_iter=1000).fit([fx(i) for i in train], y)
        scores += [model.predict_proba([fx(i)])[0][1] for i in test]
        truth += [int(not right(i, i["incumbent"]["value"])) for i in test]
    print(f"{' + '.join(names)}: AUC {roc_auc_score(truth, scores):.3f} on {len(items)}")


if __name__ == "__main__":
    main(sys.argv[1:])
