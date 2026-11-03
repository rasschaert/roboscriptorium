"""Where the build's false italic words sit, by kind, on the tuning books.

A false italic is a word the build sets italic that the reference doesn't (as `eval`
counts them). Each is sorted: unaligned (the word itself differs, so it can't match),
at a run's edge (beside a word the reference sets italic: the run reaches one too far),
in a run the reference sets upright throughout, or alone among upright words. Builds
from the caches, as `bench` does; no models.

    uv run python experiments/false_italics.py > work/probes/false-italics.txt
"""

import collections
import sys
from concurrent.futures import ProcessPoolExecutor

from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench, evaluate
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring


def book(spec: str) -> list[tuple[str, str, str]]:
    settings = bench.unseen(Settings.from_env(), spec.split(":")[0])
    run = scoring.build(f"work/{spec}", settings)
    if scoring.italics_unlike(run.book):
        return []
    doc, reference = run.stages.doc, run.reference
    ref_words, _ = evaluate._words_with_breaks([p for ch in reference for p in ch.paragraphs])
    out_words, _ = evaluate._words_with_breaks([b.text for b in doc.paragraphs])
    out_to_ref = {}
    for op in Levenshtein.opcodes(out_words, ref_words):
        if op.tag == "equal":
            for k in range(op.src_end - op.src_start):
                out_to_ref[op.src_start + k] = op.dest_start + k
    ref_marks = [
        ch.italic[k] if k < len(ch.italic) else ()
        for ch in reference
        for k in range(len(ch.paragraphs))
    ]
    ref_italic = evaluate._italic_words([p for ch in reference for p in ch.paragraphs], ref_marks)
    out_italic = evaluate._italic_words(
        [b.text for b in doc.paragraphs], [b.italic for b in doc.paragraphs]
    )
    out = []
    for i in sorted(out_italic):
        j = out_to_ref.get(i)
        if j is not None and j in ref_italic:
            continue
        context = " ".join(
            f"*{w}*" if k in out_italic else w
            for k, w in enumerate(out_words[max(0, i - 4) : i + 5], start=max(0, i - 4))
        )
        if j is None:
            kind = "unaligned"
        elif j - 1 in ref_italic or j + 1 in ref_italic:
            kind = "run edge"
        elif i - 1 in out_italic or i + 1 in out_italic:
            kind = "run upright in reference"
        else:
            kind = "alone"
        out.append((spec.split(":")[0], kind, context))
    return out


def main() -> None:
    with ProcessPoolExecutor(bench.workers()) as pool:
        rows = [r for found in pool.map(book, bench.SETS[sys.argv[1] if len(sys.argv) > 1 else "tuning"]) for r in found]
    kinds = collections.Counter(k for _, k, _ in rows)
    print(f"false italics: {len(rows)}", dict(kinds.most_common()))
    per = collections.Counter((b, k) for b, k, _ in rows)
    for b in sorted({b for b, _, _ in rows}):
        print(f"  {b[:34]:34}", {k: n for (bb, k), n in per.items() if bb == b})
    for kind in kinds:
        print(f"\n== {kind}")
        for b, k, c in rows:
            if k == kind:
                print(f"  {b[:24]:24} {c}")


if __name__ == "__main__":
    main()
