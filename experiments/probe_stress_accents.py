"""Every difference that is only a stress accent, asked or not, per Dutch tuning book: which
side has the accent. A book whose output has accents its reference lacks, again and again,
has a reference that drops the print's (check a few on the scan before believing it).

    uv run python experiments/probe_stress_accents.py [book …]
"""

import sys
import unicodedata
from collections import Counter

from roboscriptorium import bench
from roboscriptorium.cli import _questions_and_errors
from roboscriptorium.config import Settings


def plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


specs = [s for s in bench.SETS["tuning"] if not sys.argv[1:] or s.split(":")[0] in sys.argv[1:]]
for spec in specs:
    name = spec.split(":")[0]
    settings = bench.unseen(Settings.from_env(), name)
    _, _, _, _, errors, _, _ = _questions_and_errors(f"work/{spec}", settings)
    sides: Counter = Counter()
    shown = []
    for e in errors:
        if not e.got or not e.want or e.got == e.want or plain(e.got) != plain(e.want):
            continue
        side = "output" if len(unicodedata.normalize("NFD", e.got)) > len(
            unicodedata.normalize("NFD", e.want)
        ) else "reference"
        sides[side] += 1
        shown.append(f"p{e.page} {e.got}→{e.want}")
    if sides:
        print(f"{name[:34]:34} accent only in output {sides['output']:3}, only in reference {sides['reference']:3}")
        print("    " + ", ".join(shown[:14]))
