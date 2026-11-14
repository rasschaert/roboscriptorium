"""Where every vision judge picks the same version, how often is it the print, and how
often does the arbiter still ask? The trust data's settled places, each book scored by
trees trained without it (as `probe_book_vocab.py` does, today's features); asked means
its raw probability for its pick is under the build's line (`ocr_ask_below`), which the
build applies to a calibrated sureness. No models.

    PYTHONPATH=experiments uv run python experiments/probe_unanimous.py
"""

from collections import Counter

from probe_book_vocab import SETTINGS, scored
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable

VISION = ("clef:27b", "autotrust-jev:35b-nvfp4", "d3:9b", "render")

names = [n for n in SPECS if not usable(n, SETTINGS)]
books = {n: rows_of(n, SETTINGS) for n in names}
c = Counter()
examples = []
for name, rows in books.items():
    train_rows = [r for n in books if n != name and trainable(n) for r in books[n]]
    probs = scored(train_rows, rows, None, False)
    for r, p in zip(rows, probs, strict=True):
        s = r["s"]
        votes = [s.votes.get(m) for m in VISION]
        if any(v in (None, "") for v in votes) or len(set(votes)) != 1:
            continue
        versions = [s.ours, *s.others]
        k = versions.index(votes[0]) if votes[0] in versions else None
        if k is None:
            continue
        sure = float(p.max())  # raw, uncalibrated: the build calibrates it (`trust.sureness`)
        pick = int(p.argmax())
        kind = "layer" if k == 0 else "other"
        c[(kind, "places")] += 1
        c[(kind, "right")] += r["right"][k]
        c[(kind, "arbiter agrees")] += pick == k
        asked = sure < SETTINGS.ocr_ask_below
        c[(kind, "asked")] += asked
        c[(kind, "asked, judges right")] += asked and r["right"][k]
        if asked and r["right"][k] and len(examples) < 25 and kind == "other":
            examples.append((name, versions, votes[0], round(sure, 2)))
    print(name, flush=True)
for kind in ("layer", "other"):
    n = c[(kind, "places")]
    print(f"all four vision judges on the {kind}'s version: {n} places, right {c[(kind, 'right')]}, "
          f"arbiter agrees {c[(kind, 'arbiter agrees')]}, asked {c[(kind, 'asked')]} "
          f"(judges right on {c[(kind, 'asked, judges right')]} of those)")  # fmt: skip
for e in examples:
    print("  asked though every judge agreed and was right:", e)
