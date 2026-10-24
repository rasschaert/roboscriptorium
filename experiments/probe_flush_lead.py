"""What marks a paragraph's start in a book set flush, with no indent? (the checklist, "Paragraph
starts as edge classification on a graph": synthetic unindented pages from the tuning books
would carry the short last line but not any extra lead between paragraphs, so measure it first).

Per book, every pair of consecutive body lines on a page whose second line's first word aligns
to the reference: the gap between them over the page's median line pitch, and the first line's
width over the page's widest, split by whether the second line starts a paragraph in the
reference. The unindented Bruna books beside indented tuning books. No models: each slice is
built from its caches, Ollama pointed nowhere (`probe_page_breaks.py` labels lines the same way).

    uv run python experiments/probe_flush_lead.py
"""

import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BOOKS = [
    "vuurspel--ia-scan", "de-stilte-van-de-hel--ia-scan",
    "goede-dochter--ia-scan", "vals-alarm--ia-scan", "metro-2033--ia-scan",
]  # fmt: skip


def labelled(spec: str):
    """(page, line index, starts a paragraph) for every line whose first word aligns."""
    from rapidfuzz.distance import Levenshtein

    from roboscriptorium import bench
    from roboscriptorium import disagreements as D
    from roboscriptorium.evaluate import normalise
    from roboscriptorium.golden import scoring

    book = spec.split(":")[0]
    run = scoring.build(f"work/{spec}", bench.unseen(scoring.Settings.from_env(), book))
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
        if src is not None:
            first.setdefault((src.page, src.line), o)
    truth = {key: to_ref[o] in ref_starts for key, o in first.items() if o in to_ref}
    return pages, truth


if __name__ == "__main__":
    os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"
    from roboscriptorium import bench

    specs = {s.split(":")[0]: s for kind in ("tuning", "validation") for s in bench.SETS[kind]}
    for name in BOOKS:
        pages, truth = labelled(specs[name])
        gaps = {True: [], False: []}
        widths = {True: [], False: []}
        for number, page in pages.items():
            lines = page.lines
            pitch = [b.y0 - a.y0 for a, b in zip(lines, lines[1:]) if 0 < b.y0 - a.y0 < 40]
            if len(pitch) < 5:
                continue
            step = statistics.median(pitch)
            widest = max(ln.x1 - ln.x0 for ln in lines)
            for k in range(1, len(lines)):
                start = truth.get((number, k))
                if start is None:
                    continue
                gaps[start].append((lines[k].y0 - lines[k - 1].y0) / step)
                widths[start].append((lines[k - 1].x1 - lines[k - 1].x0) / widest)
        def q(xs):
            xs = sorted(xs)
            return " ".join(f"{xs[int(p * (len(xs) - 1))]:.2f}" for p in (0.1, 0.5, 0.9)) if xs else "-"
        print(f"{name[:30]:30} starts {len(gaps[True]):5}  pitch before start (10/50/90%) {q(gaps[True])}"
              f"  within {q(gaps[False])}  |  width of line before: start {q(widths[True])}"
              f"  within {q(widths[False])}", flush=True)
