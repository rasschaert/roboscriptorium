"""Where does the paragraph-break judge help, and where does it hurt?

Builds every scanned bench slice from its caches twice, with the judge and without (no
models: Ollama pointed nowhere, so an uncached call fails at once), aligns both to the
reference and lists every line whose paragraph start the judge changed, with the truth,
the judge's answer and confidence, and what the page shows about the line: its indent
against the margin, the white space above it against the line pitch, how full the line
above is, how it begins, and whether it opens a page.

    uv run python experiments/probe_break_conditions.py prepare   # → work/probes/break-conditions/
    uv run python experiments/probe_break_conditions.py score
"""

import json
import os
import statistics
import sys
from collections import Counter
from pathlib import Path

OUT = Path("work/probes/break-conditions")


def _starts(doc, run, pages, D, normalise, Levenshtein) -> dict:
    """{(page, line): (ours, truth)} for each body line aligned to the reference."""
    out, _, refs = D._word_sources(doc, pages)
    starts, k = set(), 0
    for para in doc.paragraphs:
        if words := normalise(para.text).split():
            starts.add(k)
            k += len(words)
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
    return {
        key: (o in starts, to_ref[o] in ref_starts) for key, o in first.items() if o in to_ref
    }


def _features(page, k: int) -> dict:
    lines = page.lines
    xs = sorted(ln.x0 for ln in lines)
    margin = xs[len(xs) // 4]
    right = sorted(ln.x1 for ln in lines)[len(lines) * 3 // 4]
    pitch = statistics.median(
        [b.y0 - a.y0 for a, b in zip(lines, lines[1:]) if 0 < b.y0 - a.y0] or [1]
    )
    height = statistics.median([ln.y1 - ln.y0 for ln in lines] or [1])
    line = lines[k]
    up = lines[k - 1] if k else None
    return {
        "indent": round((line.x0 - margin) / height, 2),
        "gap_above": round((line.y0 - up.y0) / pitch, 2) if up else None,
        "above_fill": round((up.x1 - margin) / (right - margin), 2) if up else None,
        "first_char": line.text.lstrip()[:1],
        "lines_on_page": len(lines),
    }


def prepare() -> None:
    os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"
    from dataclasses import replace

    from rapidfuzz.distance import Levenshtein

    from roboscriptorium import bench, ocrcheck, parabreaks
    from roboscriptorium import disagreements as D
    from roboscriptorium.evaluate import normalise
    from roboscriptorium.golden import scoring

    asked: dict = {}
    real_ask = parabreaks._ask

    def recording(client, cache, state, where, image):
        answer = real_ask(client, cache, state, where, image)
        asked[(where["page"], where["line"])] = answer
        return answer

    parabreaks._ask = recording
    rows = []
    for name in ("tuning", "validation"):
        for spec in bench.SETS[name]:
            book = spec.split(":")[0]
            base = scoring.Settings.from_env()
            runs = {}
            for judge in (False, True):
                asked.clear()
                settings = bench.unseen(replace(base, break_judge=judge), book)
                run = scoring.build(f"work/{spec}", settings)
                if not ocrcheck.scanned(run.book.source):
                    break
                doc = scoring.scored(run.book, run.stages)
                pages = {p.number: p for p in run.stages.pages}
                runs[judge] = (_starts(doc, run, pages, D, normalise, Levenshtein), pages)
            if len(runs) < 2:
                continue
            answers = dict(asked)
            (off, pages), (on, _) = runs[False], runs[True]
            indented = parabreaks.indents(list(pages.values()))
            n = 0
            for key in sorted(set(off) & set(on)):
                if off[key][0] == on[key][0]:
                    continue
                number, k = key
                page = pages[number]
                a = answers.get(key, {})
                rows.append(
                    {
                        "set": name,
                        "book": book,
                        "page": number,
                        "line": k,
                        "text": page.lines[k].text,
                        "above": page.lines[k - 1].text if k else "",
                        "indented_book": indented,
                        "judge": a.get("value"),
                        "confidence": a.get("confidence"),
                        "off": off[key][0],
                        "on": on[key][0],
                        "truth": on[key][1],
                        **_features(page, k),
                    }
                )
                n += 1
            print(f"{name:10} {book:45} {n:3} lines changed", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "changes.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(f"{len(rows)} lines")


def score() -> None:
    rows = json.loads((OUT / "changes.json").read_text())
    by_book = Counter()
    for r in rows:
        r["right"] = r["on"] == r["truth"]
        by_book[(r["set"], r["book"], "fixed" if r["right"] else "broke")] += 1
    for s, b in sorted({(s, b) for s, b, _ in by_book}):
        print(f"{s:10} {b:45} fixed {by_book[(s, b, 'fixed')]:3}  broke {by_book[(s, b, 'broke')]:3}")
    for name, key in (
        ("judge says", lambda r: f"{r['judge']} (book {'indents' if r['indented_book'] else 'flush'})"),
        ("confidence", lambda r: f"{min(int((r['confidence'] or 0) * 10), 9) / 10:.1f}"),
        ("indent", lambda r: "indented" if r["indent"] > 0.5 else "flush"),
        ("gap above", lambda r: "page top" if r["gap_above"] is None else "wide" if r["gap_above"] > 1.3 else "normal"),
        ("line above", lambda r: "-" if r["above_fill"] is None else "short" if r["above_fill"] < 0.85 else "full"),
        ("begins", lambda r: "dialogue" if r["first_char"] in "'\"‘“’”—–-»«" else "other"),
    ):
        c = Counter((key(r), r["right"]) for r in rows if r["set"] == "tuning")
        v = Counter((key(r), r["right"]) for r in rows if r["set"] == "validation")
        print(f"\n{name}:   tuning fixed/broke   validation fixed/broke")
        for value in sorted({k for k, _ in c} | {k for k, _ in v}):
            print(f"  {value:28} {c[(value, True)]:4} {c[(value, False)]:4}      {v[(value, True)]:4} {v[(value, False)]:4}")


if __name__ == "__main__":
    {"prepare": prepare, "score": score}[sys.argv[1]]()
