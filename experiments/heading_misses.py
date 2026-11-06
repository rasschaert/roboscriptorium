"""The headings a warm build of bench slices sets beside the reference's, aligned, to see
which are missing, extra or not set letter for letter. No models when the caches are warm.

    uv run python experiments/heading_misses.py <book name or bench spec> [more …]

A bare book name takes its slice from `bench.SETS`.
"""

import sys
from difflib import SequenceMatcher
from pathlib import Path

from roboscriptorium import bench
from roboscriptorium.config import Settings
from roboscriptorium.evaluate import _heading_key
from roboscriptorium.golden import scoring


def spec_of(name: str) -> str:
    for spec in [s for specs in bench.SETS.values() for s in specs]:
        if spec.split(":")[0] == name:
            return spec
    return name


def show(spec: str) -> None:
    _, run, _ = bench._build_one(spec, Settings.from_env())
    doc = scoring.scored(run.book, run.stages)
    found = [(h.text, h.sources[0].page if h.sources else None) for h in doc.headings]
    expected = [ch.heading for ch in run.reference if ch.heading]
    fk = [_heading_key(t) for t, _ in found]
    ek = [_heading_key(t) for t in expected]
    print(f"\n{spec}: {len(found)} found, {len(expected)} expected")
    for tag, i0, i1, j0, j1 in SequenceMatcher(None, fk, ek, autojunk=False).get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i0, i1), range(j0, j1)):
                if found[i][0] != expected[j]:
                    print(f"  ~ p{found[i][1]} {found[i][0]!r}  ref {expected[j]!r}")
            continue
        for i in range(i0, i1):
            print(f"  + p{found[i][1]} {found[i][0]!r}")
        for j in range(j0, j1):
            print(f"  - ref {expected[j]!r}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    for name in sys.argv[1:]:
        show(spec_of(name))
