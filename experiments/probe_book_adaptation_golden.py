"""The arbiter adjusted to a book by its first answers, simulated on the golden books.

For each book with trust data and a held-out arbiter (trained without it): the suspects
it would ask (sureness under the build's threshold), in page order, are split in two;
the first half is answered (labelled from the reference), a small logistic model over
the arbiter's log-odds, "this version is the text layer's" and how many line readers
read it is fit on them, and every other suspect is decided again with it. Reported per
book and in all: the second half's questions and the unasked suspects' wrong decisions,
before and after. No models.

    uv run python experiments/probe_book_adaptation_golden.py
"""

from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from roboscriptorium import trust, trustdata
from roboscriptorium.config import Settings

ASK_BELOW = Settings().ocr_ask_below
MODEL = Path(Settings().ocr_trust_model)
LINE_READERS = ("glm", "qwen", "tess")


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def features(s, p: np.ndarray, k: int) -> list[float]:
    read = sum(bool(s.support.get(r)) and s.support[r][k] > 0 for r in LINE_READERS)
    return [logit(p)[k], float(k == 0), float(read)]


def main() -> None:
    settings = Settings.from_env()
    total = {"q_before": 0, "q_after": 0, "wrong_before": 0, "wrong_after": 0, "n": 0}
    for path in sorted(trustdata.OUT.glob("*.json")):
        name = path.stem
        if "." in name or trustdata.usable(name, settings):
            continue
        held = trust.load(trust.without(MODEL, name))
        if held is None:
            continue
        rows = trustdata.rows_of(name, settings)
        scored = []
        for r in rows:
            p = trust.probabilities(held, r["s"])
            scored.append((r["s"], p, np.array(r["right"]), trust.sureness(held, p)))
        asked = sorted(
            [x for x in scored if x[3] < ASK_BELOW], key=lambda x: (x[0].page, x[0].line)
        )
        first, second = asked[: len(asked) // 2], asked[len(asked) // 2 :]
        rest = [x for x in scored if x[3] >= ASK_BELOW]
        if len(first) < 10 or len({bool(r[0]) for *_, r, _ in first}) < 2:
            continue
        X = [features(s, p, k) for s, p, _, _ in first for k in range(len(p))]
        y = [bool(r[k]) for _, p, r, _ in first for k in range(len(p))]
        fit = LogisticRegression(max_iter=1000).fit(np.array(X), np.array(y))

        def adapted(s, p):
            q = fit.predict_proba(np.array([features(s, p, k) for k in range(len(p))]))[:, 1]
            return q / q.sum()

        q_after = sum(adapted(s, p).max() < ASK_BELOW for s, p, _, _ in second)
        wrong_second = sum(
            not r[int(adapted(s, p).argmax())]
            for s, p, r, _ in second
            if adapted(s, p).max() >= ASK_BELOW
        )
        wrong_before = sum(not r[int(p.argmax())] for _, p, r, _ in rest)
        wrong_rest = 0
        for s, p, r, _ in rest:
            q = adapted(s, p)
            # A suspect the adapted arbiter is unsure of is asked: answered, so not wrong.
            wrong_rest += q.max() >= ASK_BELOW and not r[int(q.argmax())]
            q_after += q.max() < ASK_BELOW
        wrong_after = wrong_rest + wrong_second
        print(
            f"{name[:34]:34} questions {len(second):3} → {q_after:3}   "
            f"wrong {wrong_before:3} → {wrong_after:3}   (of {len(scored)})"
        )
        total["q_before"] += len(second)
        total["q_after"] += q_after
        total["wrong_before"] += wrong_before
        total["wrong_after"] += wrong_after
        total["n"] += len(scored)
    print(
        f"{'all':34} questions {total['q_before']:3} → {total['q_after']:3}   "
        f"wrong {total['wrong_before']:3} → {total['wrong_after']:3}   (of {total['n']})"
    )


if __name__ == "__main__":
    main()
