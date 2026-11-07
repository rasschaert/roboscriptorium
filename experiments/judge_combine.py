"""Whether a second answer to the vision judge's question (another wording or crop) earns a
place beside the first: a small model, trained on every book but one, says when to take
the second's pick; scored on the book left out, weighted back to the judge's real error
share, as `tryout.py`'s judge score is. No models.

    uv run python experiments/judge_combine.py <answers name>   # e.g. clef_27b+wide
"""

import json
import sys
from pathlib import Path

from sklearn.linear_model import LogisticRegression

ROOT = Path("work/tryout/judge-v2")
L = "abcdefg"


def right(item: dict, value: str) -> bool:
    return value in L and item["right"][L.index(value)]


def features(item: dict, second: dict) -> list[float]:
    first = item["incumbent"]
    differ = float(first["value"] != second["value"])
    return [first["confidence"], second["confidence"], differ, differ * second["confidence"]]


def main(name: str) -> None:
    data = json.loads((ROOT / "items.json").read_text())
    books = data["books"]
    second = json.loads((ROOT / "answers" / f"{name}.json").read_text())
    items = [i for i in data["items"] if i["id"] in second]
    rows = {"first": [], "second": [], "combined": []}
    for book, info in books.items():
        train = [i for i in items if i["book"] != book]
        test = [i for i in items if i["book"] == book]
        hard = [i for i in test if i["stratum"] == "hard"]
        control = [i for i in test if i["stratum"] == "control"]
        if not hard or not control:
            continue
        # The label: the second's pick is right where the first's is wrong.
        x = [features(i, second[i["id"]]) for i in train]
        y = [int(right(i, second[i["id"]]["value"]) and not right(i, i["incumbent"]["value"])) for i in train]
        # Train weighted back to the real mix of hard and control suspects.
        share = sum(b["wrong"] for b in books.values()) / sum(b["settled"] for b in books.values())
        n_hard = sum(i["stratum"] == "hard" for i in train)
        w = [share / n_hard if i["stratum"] == "hard" else (1 - share) / (len(train) - n_hard) for i in train]
        model = LogisticRegression().fit(x, y, sample_weight=w)

        def combined(i):
            s = second[i["id"]]
            take = model.predict_proba([features(i, s)])[0][1] > 0.5
            return s["value"] if take else i["incumbent"]["value"]

        b_share = info["wrong"] / info["settled"]
        for key, pick in (
            ("first", lambda i: i["incumbent"]["value"]),
            ("second", lambda i: second[i["id"]]["value"]),
            ("combined", combined),
        ):
            h = sum(right(i, pick(i)) for i in hard) / len(hard)
            c = sum(right(i, pick(i)) for i in control) / len(control)
            rows[key].append(b_share * h + (1 - b_share) * c)
    for key, accs in rows.items():
        print(f"{key:9} weighted {sum(accs) / len(accs):.4f} over {len(accs)} held-out books")
    # Telling the first's wrong picks apart, which decides what the arbiter asks: AUC of
    # P(first wrong) from its confidence alone against with the second answer too, each
    # held out by book.
    from sklearn.metrics import roc_auc_score

    for label, cols in (("first's confidence", [0]), ("with the second", [0, 1, 2, 3])):
        scores, truth = [], []
        for book in books:
            train = [i for i in items if i["book"] != book]
            test = [i for i in items if i["book"] == book]
            if not test:
                continue
            fx = lambda i: [features(i, second[i["id"]])[c] for c in cols]  # noqa: E731
            y = [int(not right(i, i["incumbent"]["value"])) for i in train]
            model = LogisticRegression().fit([fx(i) for i in train], y)
            scores += [model.predict_proba([fx(i)])[0][1] for i in test]
            truth += [int(not right(i, i["incumbent"]["value"])) for i in test]
        print(f"AUC of the first's wrong picks, {label}: {roc_auc_score(truth, scores):.3f}")


if __name__ == "__main__":
    main(sys.argv[1])
