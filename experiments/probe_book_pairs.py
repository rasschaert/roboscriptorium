"""Would the arbiter decide more of a book's suspects if its substitution table held the
book's own answers?

The arbiter's prior for a version is how often its substitution ("'e'→'c'") was the
print on the golden books. A book repeats its own substitutions (Ex-minnaar: "we" → "wc"
thirteen times, stress accents, elisions), which its reviewer has already settled. Here
each answered line is held out in turn and the table gets the book's other answers,
counted `WEIGHT` times each; the held-out line's suspects are scored before and after.
Then every unanswered suspect is scored with all answers in the table. No models.

    uv run python experiments/probe_book_pairs.py work/ex-minnaar [weight]
"""

import json
import sys
from collections import Counter
from pathlib import Path


from roboscriptorium import trust, trustdata
from roboscriptorium.book import Book
from roboscriptorium.config import Settings

ASK_BELOW = Settings().ocr_ask_below


def with_answers(base: trust.Pairs, labelled: list, weight: int) -> trust.Pairs:
    out = dict(base)
    for s, right in labelled:
        for k, v in enumerate(s.others, 1):
            key = trust.pair(s.ours, v)
            a, n = out.get(key, (0, 0))
            out[key] = (a + weight * int(right[k]), n + weight)
    return out


def outcome(model: trust.Trust, s, right) -> str:
    p = trust.probabilities(model, s)
    if trust.sureness(model, p) < ASK_BELOW:
        return "asked"
    return "right" if right[int(p.argmax())] else "wrong"


def main(book_dir: str, weight: int = 3) -> None:
    book = Book.load(Path(book_dir))
    raw = json.loads((book.stages / "ocr-check.json").read_text())
    suspects = [trustdata.suspect({"suspect": s}) for s in raw]
    rows = [
        r for r in trustdata.rows_from(suspects, trustdata.answered(book, suspects)) if r["settled"]
    ]
    model = trust.load(Path(Settings().ocr_trust_model))
    labelled = [(trustdata.suspect(r), r["right"]) for r in rows]
    before, after = Counter(), Counter()
    for s, right in labelled:
        others = [(t, r) for t, r in labelled if (t.page, t.line) != (s.page, s.line)]
        adapted = trust.Trust(
            model.model, with_answers(model.pairs, others, weight), model.calibration,
            model.readings,
        )  # fmt: skip
        before[outcome(model, s, right)] += 1
        after[outcome(adapted, s, right)] += 1
    print(f"answered suspects, each held out (weight {weight}):")
    for name, c in (("before", before), ("after", after)):
        print(f"  {name:6} asked {c['asked']:3}  right {c['right']:3}  wrong {c['wrong']:3}")

    adapted = trust.Trust(
        model.model, with_answers(model.pairs, labelled, weight), model.calibration,
        model.readings,
    )  # fmt: skip
    answered = {(s.page, s.line) for s, _ in labelled}
    moved = Counter()
    changed = []
    for s in suspects:
        if (s.page, s.line) in answered:
            continue
        p, q = trust.probabilities(model, s), trust.probabilities(adapted, s)
        was = "asked" if trust.sureness(model, p) < ASK_BELOW else "decided"
        now = "asked" if trust.sureness(adapted, q) < ASK_BELOW else "decided"
        moved[(was, now)] += 1
        if now == "decided" and (was == "asked" or int(p.argmax()) != int(q.argmax())):
            versions = [s.ours, *s.others]
            changed.append((s.page, versions[int(p.argmax())], versions[int(q.argmax())], was))
    print("unanswered suspects (before → after):", dict(moved))
    print(f"{len(changed)} now decided differently or newly decided:")
    for page, a, b, was in changed:
        print(f"  p{page} {a!r} → {b!r}" + (" (was asked)" if was == "asked" else ""))


if __name__ == "__main__":
    main(sys.argv[1], *(int(a) for a in sys.argv[2:]))
