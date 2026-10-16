"""Which lines change role when a slice's statistics count the whole body, and with which
line-role trees? Builds a bench slice four ways (whole body or slice, current or earlier
trees) and prints each line whose role differs from the slice-and-earlier-trees build,
with the errors left unasked. Warm caches; a line whose role changes may be read anew.

    uv run python experiments/probe_whole_body.py youre-never-weird-on-the-internet--ia-scan:13-94:1-16
"""

import sys
from dataclasses import replace

from roboscriptorium import pipeline, quality
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring

OLD_TREES = "work/models/line-roles.before-whole-body.pkl"


def sliced(monkey: bool):
    names = {
        "classify": (pipeline, 4),
        "measure": (pipeline.typestyle, 3),
        "apply": (pipeline.sorter, 5),
        "candidates": (pipeline.missing, 3),
    }
    saved = {}
    for name, (mod, keep) in names.items():
        orig = getattr(mod, name)
        saved[name] = (mod, orig)
        if monkey:
            setattr(mod, name, lambda *a, _o=orig, _k=keep: _o(*a[:_k]))
    return saved


def build(spec: str, trees: str, whole: bool):
    saved = sliced(not whole)
    try:
        settings = replace(Settings.from_env(), sorter_model=trees)
        return scoring.build(f"work/{spec}", settings)
    finally:
        for name, (mod, orig) in saved.items():
            setattr(mod, name, orig)


def main(spec: str) -> None:
    runs = {}
    for label, trees, whole in (
        ("slice+old", OLD_TREES, False),
        ("slice+new", Settings().sorter_model, False),
        ("whole+old", OLD_TREES, True),
        ("whole+new", Settings().sorter_model, True),
    ):
        run = build(spec, trees, whole)
        numbers = [p.number for p in run.stages.pages if p.lines]
        rep = quality.report(numbers, run.errors, run.found, {})
        runs[label] = run
        print(
            f"{label:10} wrong {rep['wrong words'].mean:.3f}  "
            f"questions {rep['questions'].mean:.3f}  "
            f"unasked {rep['unasked, all questions'].mean:.3f}",
            flush=True,
        )
    base = runs["slice+old"].stages
    text = {(p.number, i): ln.text for p in base.pages for i, ln in enumerate(p.lines)}
    for label, run in runs.items():
        if label == "slice+old":
            continue
        moved = [
            (ref, base.model_roles.get(ref), role)
            for ref, role in run.stages.model_roles.items()
            if base.model_roles.get(ref) is None or base.model_roles[ref].role != role.role
        ]
        print(f"\n{label}: {len(moved)} lines change role")
        for ref, was, now in sorted(moved, key=lambda m: (m[0].page, m[0].line))[:40]:
            was_role = was.role if was else "-"
            print(
                f"  p{ref.page} l{ref.line} {was_role} → {now.role}  "
                f"{text.get((ref.page, ref.line), '?')[:70]!r}"
            )


if __name__ == "__main__":
    main(sys.argv[1])
