"""Which readers still earn their place? The arbiter retrained without each reader in turn,
scored on each training book held out (as `train_ocr_trust.py` scores), no models.

Without a reader, a version only it read wouldn't exist: the suspect keeps the versions
another reader read, and vanishes when none is left (the layer stands). A suspect's right
version that no longer exists is an error unless the suspect is asked. Per book, the
least sure suspects are asked, one a page (`ROBO_OCR_QUESTIONS`'s default); the rest
take their likeliest version that exists. Counted: errors left unasked, and suspects.

    uv run python experiments/probe_reader_ablation.py
    ROBO_PAGE_READERS=1 ROBO_TRUST_DATA=work/probes/ocr-trust-page uv run python experiments/probe_reader_ablation.py
"""

from dataclasses import replace
from pathlib import Path

import numpy as np

from roboscriptorium import trust
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable, weighed


def pages_of(name: str) -> int:
    spec = SPECS[name]
    first, last = (
        scoring.page_range(spec.split(":")[0])
        if spec and spec != "answers"
        else Book.load(Path("work") / name).body_pages
    )
    return last - first + 1


def alive(s, kept: tuple[str, ...]) -> list[bool]:
    """Which of a suspect's versions exist with only these readers: the layer's always."""
    n = 1 + len(s.others)
    return [k == 0 or any(s.support.get(r, (False,) * n)[k] for r in kept) for k in range(n)]


def without(s, gone: set[str]):
    return replace(s, support={r: v for r, v in s.support.items() if r not in gone})


def unasked_errors(model, rows, kept, gone, budget: int) -> tuple[int, int]:
    scored = []
    for r in rows:
        s, right = r["s"], r["right"]
        live = alive(s, kept)
        if not any(live[1:]):
            scored.append((2.0, not right[0]))  # vanished: never asked, the layer stands
            continue
        p = trust.probabilities(model, without(s, gone)) * np.array(live, dtype=float)
        best = int(p.argmax())
        scored.append((float(p.max() / max(p.sum(), 1e-9)), not right[best]))
    scored.sort(key=lambda t: t[0])
    raised = sum(1 for sure, _ in scored if sure < 2.0)
    return sum(wrong for _, wrong in scored[budget:]) + sum(
        wrong for sure, wrong in scored[:budget] if sure >= 2.0
    ), raised


if __name__ == "__main__":
    settings = Settings.from_env()
    every = weighed(settings)
    books = {n: rows_of(n, settings) for n in SPECS if not usable(n, settings) and trainable(n)}
    books.pop("stella", None)
    print(f"{len(books)} books, readers {', '.join(every)}\n")
    variants = [()] + [(r,) for r in every]
    if len(every) > 3:
        variants += [tuple(r for r in every if r.endswith("-page")), ("glm", "qwen")]
    print(f"{'without':22} {'unasked errors':>14} {'suspects':>9}   per book")
    for gone in variants:
        kept = tuple(r for r in every if r not in gone)
        total = raised = 0
        per = []
        for held in books:
            train = [r for n in books if n != held for r in books[n]]
            model = trust.train(
                [without(r["s"], set(gone)) for r in train],
                [r["right"] for r in train],
                [r["book"] for r in train],
                kept,
            )
            e, n = unasked_errors(model, books[held], kept, set(gone), pages_of(held))
            total, raised = total + e, raised + n
            per.append(e)
        print(f"{', '.join(gone) or '(none)':22} {total:14} {raised:9}   {per}")
