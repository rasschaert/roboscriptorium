"""Which hand-written line-role rules (`roles.py`) do the trees still need? No models: one
rule at a time is switched off for the trees' features (`train_sorter.lines`), and the
trees, trained leaving one book out, are scored against the golden labels beside the
baseline with every rule on. A rule whose removal costs no errors can be retired; the
bench confirms.

    uv run python experiments/probe_retire_rules.py [rule …]   # default: every rule

Lines per rule cached in work/probes/retire-rules/<rule>/.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from roboscriptorium import sorterdata as T  # noqa: E402

from roboscriptorium import pipeline, roles  # noqa: E402

OFF = {
    "finishes-sentence": [(roles, "_finishes_sentence", lambda *a: False)],
    "section-number": [(roles, "_section_number", lambda *a: False)],
    "heading-label": [(roles, "_heading_label", lambda *a: False)],
    "subtitle": [(roles, "_subtitles", lambda *a: None)],
    "numeral-slot": [(roles, "_numeral_slots", lambda *a: None)],
    "heading-style": [(roles, "_heading_styles", lambda *a: None)],
    "running-text": [(pipeline, "running_text", lambda pages, model_roles, known: model_roles)],
}


# Several rules off at once: "rule+rule".
def off(rule: str | None) -> list:
    return [p for r in (rule or "").split("+") if r for p in OFF[r]]


def score(books: dict[str, list[dict]]) -> Counter:
    trainable = [b for b in books if b not in T.VALIDATION]
    total: Counter = Counter()
    for book, rows in books.items():
        truth = [r["label"] for r in rows]
        trees = T.predict(T.fit([r for b in trainable if b != book for r in books[b]]), rows)
        kind = "validation" if book in T.VALIDATION else "tuning"
        for t, p in zip(truth, trees, strict=True):
            total[f"{kind} errors"] += t != p
            total[f"{kind} body lost"] += t == "body" != p
            total[f"{kind} heading wrong"] += (t == "heading") != (p == "heading")
    return total


def run(rule: str | None) -> Counter:
    saved = []
    for module, name, replacement in off(rule):
        saved.append((module, name, getattr(module, name)))
        setattr(module, name, replacement)
    T.OUT = Path("work/probes/retire-rules") / (rule or "baseline")
    T.OUT.mkdir(parents=True, exist_ok=True)
    try:
        books = {s.split(":")[0]: T.lines(s, False) for s in T.SPECS}
    finally:
        for module, name, original in saved:
            setattr(module, name, original)
    return score(books)


base = run(None)
print(f"{'baseline':18} {dict(base)}", flush=True)
for rule in sys.argv[1:] or OFF:
    got = run(rule)
    delta = {k: got[k] - base[k] for k in base}
    print(f"{rule:18} {dict(got)}\n{'':18} change {delta}", flush=True)
