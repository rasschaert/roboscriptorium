"""Can a learned decision beat the Dutch build's own rule on line-end hyphens? On the
tuning books' labelled Dutch breaks (`train_hyphens.rows_of`), each book left out, against
production (the hyphen kept on a vowel clash, `hyphens.vowel_clash`, else joined): the
model trained on both languages, one trained on Dutch alone, each at several cuts, and
each allowed to keep a hyphen only where both parts are in the word list and the word
starts in lower case (names and foreign words left to production). Every wrong break is
listed by what the decision does: a hyphen added the print lacks, or one dropped. No models.

    PYTHONPATH=experiments uv run python experiments/probe_hyphen_dutch.py
"""

import numpy as np
from train_hyphens import fresh, rows_of

from roboscriptorium import bench, hyphens
from roboscriptorium.lexicon import Lexicon

COL = {name: i for i, name in enumerate(hyphens.FEATURES)}


def main() -> None:
    rows = []
    for spec in bench.SETS["tuning"]:
        rows += rows_of(spec)[0]
    X = np.array([r["x"] for r in rows])
    y = np.array([r["y"] for r in rows])
    books = np.array([r["book"] for r in rows])
    dutch = np.array([r["lang"] == "nl" for r in rows])
    words = [r["word"] for r in rows]
    known = Lexicon.load("nld").knows
    clash = np.array(
        [hyphens.vowel_clash(*w.split("-", 1), "", known) if "-" in w else False for w in words]
    )
    plain = (X[:, COL["stem_known"]] == 1) & (X[:, COL["rest_known"]] == 1)
    plain &= X[:, COL["stem_capital"]] == 0

    both, alone = np.zeros(len(rows)), np.zeros(len(rows))
    for b in sorted(set(books[dutch])):
        held = books == b
        both[held] = fresh().fit(X[~held], y[~held]).predict_proba(X[held])[:, 1]
        train = ~held & dutch
        alone[held] = fresh().fit(X[train], y[train]).predict_proba(X[held])[:, 1]

    m = dutch
    print(f"{int(m.sum())} Dutch breaks, the print keeps the hyphen in {int(y[m].sum())}")

    def show(name: str, keep: np.ndarray) -> None:
        added = [words[i] for i in np.where(m & keep & ~y)[0]]
        dropped = [words[i] for i in np.where(m & ~keep & y)[0]]
        print(f"{name:44} wrong {len(added) + len(dropped):3}: adds {len(added):2}, drops {len(dropped):2}")
        if len(added) <= 12:
            print(f"    adds:  {', '.join(added)}")

    show("production (vowel clash)", clash)
    show("join every break", np.zeros(len(rows), bool))
    for cut in (0.5, 0.8, 0.9, 0.95):
        show(f"both languages at {cut}", both >= cut)
        show(f"both languages at {cut}, plain words only", clash | ((both >= cut) & plain))
        show(f"Dutch alone at {cut}", alone >= cut)
        show(f"Dutch alone at {cut}, plain words only", clash | ((alone >= cut) & plain))
    print(f"\n    production drops: {', '.join(words[i] for i in np.where(m & ~clash & y)[0])}")
    best = clash | ((both >= 0.9) & plain)
    print(f"    both languages at 0.9, plain words only, keeps: "
          f"{', '.join(words[i] for i in np.where(m & best & ~clash)[0])}")


if __name__ == "__main__":
    main()
