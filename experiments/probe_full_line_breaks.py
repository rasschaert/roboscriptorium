"""Where a line ends a sentence at the right margin, does the next start a paragraph?

Geometry can't tell there in a book that doesn't indent (Vuurspel, De stilte), so only
the text can. Over every bench slice, each line whose previous line reaches the margin
and ends a sentence is labelled by the reference (a paragraph starts at its first word or
not), and counted by how the previous line ends (closing quote or not) and how this one
begins (opening quote, capital, other), per book and whether the book indents. Warm
builds, no new model calls.

    uv run python experiments/probe_full_line_breaks.py > work/probes/full-line-breaks.txt
"""

import re
from collections import Counter, defaultdict
from statistics import median

from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench
from roboscriptorium import disagreements as D
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden import scoring

FULL = 0.03  # of the text width: a line ending this close to the margin is full
END = re.compile(r"[.!?…][’”'\"]?\s*$")


def kinds(prev: str, line: str) -> tuple[str, str]:
    closes = "quote" if re.search(r"[’”'\"]\s*$", prev) else "plain"
    t = line.lstrip()
    if t[:1] in "‘“'\"":
        opens = "quote"
    elif t[:1] in "–—-":
        opens = "dash"
    elif t[:1].isupper():
        opens = "capital"
    else:
        opens = "other"
    return closes, opens


def book(spec: str) -> tuple[Counter, int]:
    run = scoring.build(f"work/{spec}")
    doc = scoring.scored(run.book, run.stages)
    pages = {p.number: p for p in run.stages.pages}
    out, _, refs = D._word_sources(doc, pages)
    ref, ref_starts = [], set()
    for ch in run.reference:
        for para in ch.paragraphs:
            ref_starts.add(len(ref))
            ref += normalise(para).split()
    to_ref = {}
    for op in Levenshtein.opcodes(out, ref):
        if op.tag == "equal":
            for i in range(op.src_end - op.src_start):
                to_ref[op.src_start + i] = op.dest_start + i
    first = {}
    for o, src in enumerate(refs):
        if src is not None and (src.page, src.line) not in first:
            first[(src.page, src.line)] = o
    counts: Counter = Counter()
    indented = 0
    for number, page in pages.items():
        lines = page.lines
        if len(lines) < 5:
            continue
        left = median(ln.x0 for ln in lines)
        right = median(ln.x1 for ln in lines)
        width = right - left
        indented += sum(0.02 * width < ln.x0 - left < 0.08 * width for ln in lines)
        for k in range(1, len(lines)):
            prev, line = lines[k - 1], lines[k]
            o = first.get((number, k))
            if o is None or o not in to_ref:
                continue
            if right - prev.x1 > FULL * width or not END.search(prev.text):
                continue
            if abs(line.x0 - left) > 0.02 * width:
                continue  # indented or centred: geometry speaks
            closes, opens = kinds(prev.text, line.text)
            counts[(closes, opens, to_ref[o] in ref_starts)] += 1
    return counts, indented


def main() -> None:
    total: dict[str, Counter] = defaultdict(Counter)
    for name in ("tuning", "validation"):
        for spec in bench.SETS[name]:
            counts, indented = book(spec)
            flush = "flush" if indented < 20 else "indents"
            short = spec.split("--")[0][:22]
            row = " ".join(
                f"{c}/{o}:{counts[(c, o, True)]}/{counts[(c, o, True)] + counts[(c, o, False)]}"
                for c in ("quote", "plain")
                for o in ("quote", "capital", "dash")
                if counts[(c, o, True)] + counts[(c, o, False)]
            )
            print(f"{short:22} {flush:7} {row}", flush=True)
            total[flush] += counts
    for flush, counts in total.items():
        print(f"\n{flush}: breaks / lines, by previous line's end / this line's start")
        for c in ("quote", "plain"):
            for o in ("quote", "capital", "dash", "other"):
                n = counts[(c, o, True)] + counts[(c, o, False)]
                if n:
                    print(f"  {c:5} → {o:7} {counts[(c, o, True)]:4} / {n:4}")


if __name__ == "__main__":
    main()
