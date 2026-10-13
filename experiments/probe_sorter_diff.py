"""The disagreements a slice gains and loses when line roles come from the trees
(ROBO_SORTER=1, the copy trained without the book) instead of the rules.

    uv run python experiments/probe_sorter_diff.py <spec> [<spec> …]
"""

import sys
from dataclasses import replace

from roboscriptorium import bench
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring


def places(spec: str, settings: Settings) -> dict[str, tuple]:
    run = scoring.build(f"work/{spec}", bench.unseen(settings, spec.split(":")[0]))
    return {(d.page, d.got, d.want): d for d in run.errors}


if __name__ == "__main__":
    base = Settings.from_env()
    for spec in sys.argv[1:]:
        rules = places(spec, replace(base, sorter=False))
        trees = places(spec, replace(base, sorter=True))
        print(f"== {spec}: rules {len(rules)}, trees {len(trees)}")
        for label, a, b in (("only with trees", trees, rules), ("only with rules", rules, trees)):
            for k in sorted(set(a) - set(b), key=lambda k: (k[0] or 0, k[1])):
                d = a[k]
                print(f"  {label:16} p{d.page}: got «{d.got}» want «{d.want}»  …{d.before[-30:]}|{d.after[:30]}")
