"""The reference's scene breaks the build doesn't set, where they fall on the scan, and
the breaks the build sets that the reference doesn't have.

For each tuning or validation book named (default: those whose reference records
breaks), as the bench builds it: every reference break with no output break at the same
word, with the output paragraph it falls in or before, and whether that paragraph's first
line opens a page (a break at a page's end shows no white space) or whether the break
falls inside an output paragraph (no paragraph break there at all).

    uv run python experiments/probe_missed_breaks.py [book …]
"""

import sys

from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench, evaluate
from roboscriptorium.golden import scoring
from roboscriptorium.config import Settings

BOOKS = ["reis-om-mijn-schedel", "de-eerlijke-vinder", "de-cipier", "de-tuin-van-de-avondnevel",
         "doodskleed", "de-kerk-van-de-dode-meisjes", "artemis"]  # fmt: skip
names = sys.argv[1:] or BOOKS
specs = [s for s in bench.SETS["tuning"] + bench.SETS["validation"]
         if s.split("--")[0] in names]  # fmt: skip
for spec in specs:
    name = spec.split(":")[0]
    _, book, stages, reference, _, _, _ = scoring.build(
        f"work/{spec}", bench.unseen(Settings.from_env(), name)
    )
    doc = scoring.scored(book, stages)
    paras = doc.paragraphs
    out_words, starts, owner = [], [], []
    for k, p in enumerate(paras):
        starts.append(len(out_words))
        words = evaluate.normalise(p.text).split()
        out_words += words
        owner += [k] * len(words)
    ref_paras = [p for ch in reference for p in ch.paragraphs]
    flags = [k in ch.breaks for ch in reference for k in range(len(ch.paragraphs))]
    ref_words, ref_breaks = [], []
    for para, scene in zip(ref_paras, flags, strict=True):
        if scene:
            ref_breaks.append(len(ref_words))
        ref_words += evaluate.normalise(para).split()
    ref_to_out = {}
    for op in Levenshtein.opcodes(out_words, ref_words):
        if op.tag == "equal":
            for i in range(op.src_end - op.src_start):
                ref_to_out[op.dest_start + i] = op.src_start + i
    kinds = {"page top": 0, "inside a paragraph": 0, "elsewhere": 0, "unaligned": 0}
    print(f"== {name}")
    for r in ref_breaks:
        o = ref_to_out.get(r)
        if o is None:
            kinds["unaligned"] += 1
            continue
        k = owner[o]
        if starts[k] == o and paras[k].break_before:
            continue
        p = paras[k]
        if starts[k] != o:
            kind = "inside a paragraph"
        elif p.sources and p.sources[0].line == 0:
            kind = "page top"
        else:
            kind = "elsewhere"
        kinds[kind] += 1
        where = f"p{p.sources[0].page}" if p.sources else "?"
        print(f"  {kind:18} {where:5} …{' '.join(out_words[max(0, o - 6) : o])} ¶ "
              f"{' '.join(out_words[o : o + 6])}")  # fmt: skip
    print("  " + ", ".join(f"{k} {n}" for k, n in kinds.items()))
    # The output's breaks the reference doesn't have.
    out_to_ref = {o: r for r, o in ref_to_out.items()}
    recorded = set(ref_breaks)
    for k, p in enumerate(paras):
        if p.break_before and out_to_ref.get(starts[k]) not in recorded:
            o = starts[k]
            top = "page top" if p.sources and p.sources[0].line == 0 else ""
            print(f"  extra {top:8} p{p.sources[0].page if p.sources else '?'} "
                  f"…{' '.join(out_words[max(0, o - 6) : o])} ¶ {' '.join(out_words[o : o + 6])}")
