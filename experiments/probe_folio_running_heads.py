"""A line the trees call a heading that carries its page's printed number beside words and
recurs at another page's edge: a running head however few pages its chapter has? A
chapter heading appears once and never prints the page's number on its own line.

Trees fitted leaving each book out, as `probe_tree_folio_heads.py` fits them (the grown
slices; with `--surya`, Surya's layout columns too), each line's likeliest class; then
the headings the rule takes back: false ones (not headings in the reference) and true
ones. No models.

    PYTHONPATH=experiments uv run python experiments/probe_folio_running_heads.py [--surya]
"""

import sys
from collections import Counter

from probe_surya_roles import COLUMNS, with_surya
from probe_tree_folio_heads import COLUMN, fitted, with_folio

from roboscriptorium import sorter
from roboscriptorium.sorterdata import SPECS, VALIDATION, lines

SURYA = "--surya" in sys.argv
MIN_REPEATS = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--min=")), "1"))

if __name__ == "__main__":
    books = {s.split(":")[0]: lines(s) for s in SPECS}
    for name, rows in books.items():
        with_folio(name, rows)
        if SURYA:
            with_surya(name, rows)
    names = sorter.FEATURES + (COLUMNS if SURYA else ())
    trainable = [b for b in books if b not in VALIDATION]
    total: Counter = Counter()
    shown = []
    for name, rows in books.items():
        model = fitted([r for b in trainable if b != name for r in books[b]], names)
        pred = model.model.predict(sorter._matrix([r["f"] for r in rows], names))
        c: Counter = Counter()
        for r, p in zip(rows, pred, strict=True):
            if p != "heading":
                continue
            f = r["f"]
            edge = f["i_top"] < 2 or f["i_bottom"] < 2
            hit = f[COLUMN] == 1.0 and edge and f["repeats"] >= MIN_REPEATS
            truth = "true" if r["label"] == "heading" else "false"
            c[(truth, "called")] += 1
            if hit:
                c[(truth, "taken back")] += 1
                if truth == "true" or len(shown) < 40:
                    shown.append((name, r["page"], truth, f["repeats"], r.get("text")))
        part = "validation" if name in VALIDATION else "tuning"
        for k, n in c.items():
            total[(part, *k)] += n
        if c[("true", "taken back")] or c[("false", "taken back")]:
            print(f"{name[:40]:40} false headings {c[('false', 'called')]:3}, taken back "
                  f"{c[('false', 'taken back')]:3}; true taken back {c[('true', 'taken back')]}")  # fmt: skip
    for part in ("tuning", "validation"):
        print(part, {f"{t} {k}": total[(part, t, k)] for t in ("true", "false")
                     for k in ("called", "taken back")})  # fmt: skip
    print("\nlines taken back (true ones all, false ones the first 40):")
    for name, page, truth, rep, text in shown:
        print(f"  {name[:30]:30} PDF {page:3} {truth:5} repeats {rep:.0f}  {text!r}")
