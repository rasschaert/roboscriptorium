"""What the accent offers (`accentmarks.py`) were worth, and what training on them did to
the arbiter: every settled place of the accent run's trust data (work/probes/
ocr-trust-accents/) where a version adds a stress accent to the build's, split by whether
a reader has that version or only the scan's accent measure offered it, with what the
arbiter in use and the one trained with the offers each do there (each book by the model
trained without it; asked below the build's sureness, the question budget left out).
No models.

    ROBO_TRUST_DATA=work/probes/ocr-trust-accents uv run python experiments/probe_accent_offers.py
"""

import unicodedata
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, trust, trustdata
from roboscriptorium.config import Settings

OLD, NEW = Path("work/models/ocr-trust-text.pkl"), Path("work/models/ocr-trust-accents.pkl")
ACUTE = "́"


def acutes(text: str) -> int:
    return unicodedata.normalize("NFD", text).count(ACUTE)


def bare(text: str) -> str:
    return unicodedata.normalize("NFD", text).replace(ACUTE, "")


settings = Settings.from_env()
tally: dict[tuple[str, str], Counter] = {}
moved = []
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    # `rows_of` would build a missing book's data with the models.
    if not (trustdata.OUT / f"{name}.json").exists():
        continue
    rows = trustdata.rows_of(name, settings)
    arbiters = {}
    for label, path in (("in use", OLD), ("trained with offers", NEW)):
        arbiters[label] = trust.load(trust.without(path, name))
    if None in arbiters.values():
        print(f"{name}: no arbiter trained without it, left out")
        continue
    picks = {}
    for label, arbiter in arbiters.items():
        ps = trust.all_probabilities(arbiter, [r["s"] for r in rows])
        picks[label] = [(int(p.argmax()), trust.sureness(arbiter, p)) for p in ps]
    for n, r in enumerate(rows):
        s = r["s"]
        versions = [s.ours, *s.others]
        for i, v in enumerate(versions[1:], 1):
            if not (acutes(v) > acutes(s.ours) and bare(v) == bare(s.ours)):
                continue
            read = any(i < len(has) and has[i] for has in s.support.values())
            group = "a reader has it" if read else "only the scan's measure"
            printed = "print has the accent" if r["right"][i] else "print has none"
            did = {}
            for label in arbiters:
                best, sure = picks[label][n]
                if sure < settings.ocr_ask_below:
                    did[label] = "asks"
                elif r["right"][best]:
                    did[label] = "right, no question"
                else:
                    did[label] = "wrong, no question"
                tally.setdefault((group, printed), Counter())[label, did[label]] += 1
            tally[group, printed]["places"] += 1
            if did["in use"] != did["trained with offers"]:
                moved.append((group, printed, did["in use"], did["trained with offers"], name, s.ours, v))
            break

for (group, printed), c in sorted(tally.items()):
    print(f"{group}, {printed}: {c['places']} places")
    for label in ("in use", "trained with offers"):
        parts = ", ".join(
            f"{what} {c[label, what]}"
            for what in ("right, no question", "asks", "wrong, no question")
        )
        print(f"  arbiter {label:20} {parts}")
print("\nwhere the two arbiters differ:")
for key, n in Counter(m[:4] for m in moved).most_common():
    print(f"  {n:4}  {key[0]}, {key[1]}: {key[2]} → {key[3]}")
