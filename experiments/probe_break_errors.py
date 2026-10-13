"""Each paragraph break a tuning book's build gets wrong, with the words around it.

As the bench builds the book (`disagreements.break_errors` counts the same): "extra",
an output paragraph starting mid-paragraph in the reference; "missing", a reference
paragraph starting mid-paragraph in the output. With the page and the line's box, to
look at on the scan.

    uv run python experiments/probe_break_errors.py <book> [limit]
"""

import sys
from collections import Counter

from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench
from roboscriptorium.golden import scoring
from roboscriptorium.config import Settings
from roboscriptorium.disagreements import _word_sources
from roboscriptorium.evaluate import normalise

name = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 40
spec = next(s for s in bench.SETS["tuning"] if s.startswith(name))
book_name = spec.split(":")[0]
_, book, stages, reference, _, _, _ = scoring.build(
    f"work/{spec}", bench.unseen(Settings.from_env(), book_name)
)
doc = scoring.scored(book, stages)
pages = {p.number: p for p in stages.pages}
out, _, refs = _word_sources(doc, pages)
starts, k = set(), 0
for para in doc.paragraphs:
    if words := normalise(para.text).split():
        starts.add(k)
        k += len(words)
ref, ref_starts = [], set()
for ch in reference:
    for para in ch.paragraphs:
        ref_starts.add(len(ref))
        ref += normalise(para).split()
to_ref = {}
for op in Levenshtein.opcodes(out, ref):
    if op.tag == "equal":
        for i in range(op.src_end - op.src_start):
            to_ref[op.src_start + i] = op.dest_start + i
to_out = {r: o for o, r in to_ref.items()}
wrong = [("extra", o) for o in starts if o in to_ref and to_ref[o] not in ref_starts]
wrong += [("missing", to_out[r]) for r in ref_starts if r in to_out and to_out[r] not in starts]
wrong.sort(key=lambda w: w[1])
print(f"{book_name}: {Counter(kind for kind, _ in wrong)}")
for kind, o in wrong[:limit]:
    src = refs[o]
    where = f"p{src.page}:{src.line}" if src is not None else "?"
    line = pages[src.page].lines[src.line] if src is not None else None
    box = f"x0 {line.x0:.0f} x1 {line.x1:.0f}" if line is not None else ""
    print(f"  {kind:7} {where:8} {box:14} …{' '.join(out[max(0, o - 6) : o])} ¶ "
          f"{' '.join(out[o : o + 6])}")  # fmt: skip
