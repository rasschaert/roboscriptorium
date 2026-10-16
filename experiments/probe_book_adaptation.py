"""Would the arbiter, adjusted to one book by its reviewer's answers, ask less and err less?

The arbiter is trained on the golden books, where the text layer is mostly right. A book
whose layer is worse (Ex-minnaar: right on 15% of the lines asked) needs it trusted
less. Here each answered suspect of the book is a label; a two-weight logistic model
over the arbiter's own log-odds and "this version is the text layer's" is fit on the
other answered lines (leave one line out) and rescores the held-out one. Reported: how
many of the answered suspects the arbiter asked, decided right or decided wrong, before
and after, at the build's sureness threshold. No models; reads the book's cached
suspects and review answers.

    uv run python experiments/probe_book_adaptation.py work/ex-minnaar
"""

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from roboscriptorium import trust, trustdata
from roboscriptorium.book import Book
from roboscriptorium.config import Settings

ASK_BELOW = Settings().ocr_ask_below


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def main(book_dir: str) -> None:
    book = Book.load(Path(book_dir))
    raw = json.loads((book.stages / "ocr-check.json").read_text())
    suspects = [trustdata.suspect({"suspect": s}) for s in raw]
    rows = trustdata.rows_from(suspects, trustdata.answered(book, suspects))
    model = trust.load(Path("work/models/ocr-trust.pkl"))
    if model is None:
        model = trust.load(next(Path("work/models").glob("ocr-trust*.pkl")))
    items = []
    for r in rows:
        if not r["settled"]:
            continue
        s = trustdata.suspect(r)
        p = trust.probabilities(model, s)
        items.append((s.page, s.line, s, p, np.array(r["right"])))
    print(f"{len(items)} answered suspects ({len(rows)} labelled)")

    def outcome(p: np.ndarray, right: np.ndarray, sure: float) -> str:
        if sure < ASK_BELOW:
            return "asked"
        return "right" if right[int(p.argmax())] else "wrong"

    before, after = [], []
    lines = sorted({(pg, ln) for pg, ln, *_ in items})
    for held in lines:
        train = [x for x in items if (x[0], x[1]) != held]
        X = np.array([[logit(p)[k], float(k == 0)] for *_, p, _ in train for k in range(len(p))])
        y = np.array([bool(r[k]) for *_, p, r in train for k in range(len(p))])
        fit = LogisticRegression(C=1.0).fit(X, y)
        for pg, ln, s, p, right in items:
            if (pg, ln) != held:
                continue
            before.append(outcome(p, right, trust.sureness(model, p)))
            q = fit.predict_proba(np.array([[logit(p)[k], float(k == 0)] for k in range(len(p))]))
            q = q[:, 1] / q[:, 1].sum()
            after.append(outcome(q, right, float(q.max())))
    for name, got in (("before", before), ("after", after)):
        print(f"  {name:6} asked {got.count('asked'):3}  right {got.count('right'):3}  "
              f"wrong {got.count('wrong'):3}")


if __name__ == "__main__":
    main(sys.argv[1])
