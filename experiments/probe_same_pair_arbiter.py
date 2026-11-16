"""Does the arbiter decide better when it also weighs a book's other places with the same
two versions? Each book scored by trees trained on the other tuning books
(`train_ocr_trust.py`'s way), once with the arbiter's inputs as they are and once with
two more for each version: the judges' share of votes for it pooled over the book's
other places raising the same pair (0.5 where there are none), and how many such places
there are. Silent errors at the fixed rule's number of questions and at budgets of
questions a page. No models; each book's scores are kept in
work/probes/same-pair-arbiter.json as they come, so a stopped run goes on.

    uv run python experiments/probe_same_pair_arbiter.py
"""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from roboscriptorium import trust
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.files import write_atomic
from roboscriptorium.golden import scoring
from roboscriptorium.trustdata import SPECS, rows_of, seats, trainable, usable, weighed

SETTINGS = Settings.from_env()
READINGS, SEATS = weighed(SETTINGS), seats(SETTINGS)
BUDGETS = (0.0, 0.25, 0.5, 1.0)
SEEDS = 5
MOST = 20
MEMO = Path("work/probes/same-pair-arbiter.json")


def elsewhere(rows: list[dict]) -> list[list[tuple[float, float]]]:
    """For each version of each of a book's places: the judges' share of votes for it at
    the book's other places with the same pair of versions, and how many there are."""
    groups = defaultdict(list)

    def keys(s):
        yield (s.ours, tuple(s.others)), s.ours
        for v in s.others:
            yield (s.ours, v), v

    for i, r in enumerate(rows):
        s = r["s"]
        if not s.votes:
            continue
        for key, v in keys(s):
            groups[key, v].append((i, sum(x == v for x in s.votes.values()) / len(s.votes)))
    out = []
    for i, r in enumerate(rows):
        cells = []
        for key, v in keys(r["s"]):
            rest = [share for j, share in groups[key, v] if j != i]
            cells.append((sum(rest) / len(rest) if rest else 0.5, float(min(len(rest), MOST))))
        out.append(cells)
    return out


def columns(rows: list[dict]) -> np.ndarray:
    return np.array([c for cells in elsewhere(rows) for c in cells])


def silent_at(rows, ps, n: int) -> int:
    order = sorted((p.max(), not r["right"][int(p.argmax())]) for r, p in zip(rows, ps, strict=True))
    return int(sum(wrong for _, wrong in order[n:]))


def rule_asked(rows) -> int:
    return sum(r["s"].choice == "review" for r in rows)


def pages_of(name: str) -> int:
    spec = SPECS[name]
    ranged = spec and spec != "answers"
    first, last = scoring.page_range(spec.split(":")[0]) if ranged else Book.load(Path("work") / name).body_pages
    return last - first + 1


def score(name: str) -> dict:
    rows = books[name]
    names = [n for n in books if n != name and trainable(n)]
    train = [r for n in names for r in books[n]]
    suspects, right = [r["s"] for r in train], [r["right"] for r in train]
    owners = [n for n in names for _ in books[n]]
    X, y = trust.training_matrix(suspects, right, owners, READINGS, SEATS)
    pairs = trust.pairs_table(suspects, right, owners)
    Xt = np.array([trust.features(r["s"], k, pairs, READINGS, SEATS) for r in rows for k in range(len(r["right"]))])
    more, more_t = np.vstack([columns(books[n]) for n in names]), columns(rows)
    sizes = [len(r["right"]) for r in rows]
    often = [any(n >= 2 for _, n in cells[1:]) for cells in elsewhere(rows)]
    out = {"places": len(rows), "pages": pages_of(name), "asked by the rule": rule_asked(rows), "often": sum(often)}
    for label, A, B in (("as it is", X, Xt), ("with the pair elsewhere", np.hstack([X, more]), np.hstack([Xt, more_t]))):
        p = trust.Trees(SEEDS).fit(A, y).predict_proba(B)[:, 1]
        ps, at = [], 0
        for n in sizes:
            ps.append(p[at : at + n] / max(p[at : at + n].sum(), 1e-9))
            at += n
        sub = [(r, q) for r, q, o in zip(rows, ps, often, strict=True) if o]
        out[label] = {
            "silent at the rule's questions": silent_at(rows, ps, out["asked by the rule"]),
            "silent by budget": [silent_at(rows, ps, int(b * out["pages"])) for b in BUDGETS],
            "wrong picks": int(sum(not r["right"][int(q.argmax())] for r, q in zip(rows, ps, strict=True))),
            # At pairs raised three times or more: picks wrong, and places under 0.9 sure.
            "often: wrong picks": int(sum(not r["right"][int(q.argmax())] for r, q in sub)),
            "often: under 0.9": int(sum(q.max() < 0.9 for _, q in sub)),
        }
    return out


books: dict = {}

if __name__ == "__main__":
    books.update({name: rows_of(name, SETTINGS) for name in SPECS if not usable(name, SETTINGS)})
    memo = json.loads(MEMO.read_text()) if MEMO.exists() else {}
    for name in books:
        if name not in memo:
            memo[name] = score(name)
            write_atomic(MEMO, json.dumps(memo))
        m = memo[name]
        a, b = m["as it is"], m["with the pair elsewhere"]
        print(
            f"{name[:30]:30} places {m['places']:5} (often {m['often']:4})  silent at rule's questions "
            f"{a['silent at the rule\'s questions']:3} → {b['silent at the rule\'s questions']:3}  by budget "
            f"{'/'.join(map(str, a['silent by budget']))} → {'/'.join(map(str, b['silent by budget']))}  "
            f"often: wrong {a['often: wrong picks']} → {b['often: wrong picks']}, unsure "
            f"{a['often: under 0.9']} → {b['often: under 0.9']}",
            flush=True,
        )
    for label in ("as it is", "with the pair elsewhere"):
        rows = [m[label] for m in memo.values()]
        print(
            f"{label:24} silent at the rule's questions {sum(r['silent at the rule\'s questions'] for r in rows)}, by budget "
            f"{[sum(r['silent by budget'][i] for r in rows) for i in range(len(BUDGETS))]}, wrong picks "
            f"{sum(r['wrong picks'] for r in rows)}; at pairs raised often: wrong {sum(r['often: wrong picks'] for r in rows)}, "
            f"under 0.9 sure {sum(r['often: under 0.9'] for r in rows)}"
        )
