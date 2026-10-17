"""Does the paragraph-break judge do better seeing more of the page?

The judge (`parabreaks.py`, clef:27b) saw a line between the line above and below; its
wrong answers were mostly flush dialogue called a new paragraph in a book that indents
(`probe_break_conditions.py`). This asks it again with a taller crop, `--around` lines
above and below, against the three-line crop, on the lines whose start the judge
changed (`work/probes/break-conditions/changes.json`) and a seeded sample of lines the
reflow has right (`work/probes/break-judge/lines.json`), skipping `--skip` books (a
running build's). Pages come from each slice built from its caches; answers are cached
in work/probes/break-context/.

    uv run python experiments/probe_break_context.py [--around 4] [--sample 200] [--skip book,…]
"""

import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

OUT = Path("work/probes/break-context")


def main(around: int, sample: int, skip: set[str]) -> None:
    import pymupdf

    from roboscriptorium import bench, parabreaks
    from roboscriptorium.clients import decide
    from roboscriptorium.config import Settings
    from roboscriptorium.golden import scoring
    from roboscriptorium.roles import DecisionCache

    changed = json.loads(Path("work/probes/break-conditions/changes.json").read_text())
    rows = [
        {**r, "kind": "changed"}
        for r in changed
        if r["judge"] is not None and r["book"] not in skip
    ]
    lines = json.loads(Path("work/probes/break-judge/lines.json").read_text())
    right = [
        r
        for r in lines
        if r["book"] not in skip
        and r["ours"] == r["truth"]
        and parabreaks.can_start(r["above"], r["text"])
    ]
    taken = {(r["book"], r["page"], r["line"]) for r in rows}
    pool = [r for r in right if (r["book"], r["page"], r["line"]) not in taken]
    rows += [{**r, "kind": "right"} for r in random.Random(17).sample(pool, min(sample, len(pool)))]
    specs = {s.split(":")[0]: s for name in ("tuning", "validation") for s in bench.SETS[name]}
    settings = Settings.from_env()
    client = decide.for_model(settings.judge_model, settings.ollama_url, settings.judge_via)
    OUT.mkdir(parents=True, exist_ok=True)
    cache = DecisionCache(OUT / "decisions.jsonl")
    results = []
    for book in sorted({r["book"] for r in rows}):
        os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"
        run = scoring.build(f"work/{specs[book]}", bench.unseen(scoring.Settings.from_env(), book))
        os.environ.pop("ROBO_OLLAMA_URL")
        pages = {p.number: p for p in run.stages.pages}
        indented = parabreaks.indents(list(pages.values()))
        with pymupdf.open(run.book.source) as doc:
            for r in (r for r in rows if r["book"] == book):
                page = pages[r["page"]]
                k = r["line"]
                n = len(page.lines)
                state = {
                    "how the book sets paragraphs": parabreaks.STYLE[indented],
                    "line above": page.lines[k - 1].text if k else "",
                    "line in question": page.lines[k].text,
                    "line below": page.lines[k + 1].text if k + 1 < n else "",
                }
                answers = {}
                for span in (1, around):
                    rows_ = (max(0, k - span), min(n - 1, k + span))
                    where = {"page": page.number, "line": k, "crop": [span]}
                    answers[span] = parabreaks._ask(
                        client,
                        cache,
                        state,
                        where,
                        lambda p=page, rr=rows_: parabreaks._crop(doc, p, rr),
                    )
                results.append({**r, "answers": {str(s): a for s, a in answers.items()}})
        print(f"{book:45} {sum(r['book'] == book for r in rows):4} lines", flush=True)
    (OUT / f"results-{around}.json").write_text(json.dumps(results, ensure_ascii=False))
    for kind in ("changed", "right"):
        print(f"\n{kind}:  crop  fixed  broke  (sure ≥ {parabreaks.SURE})")
        for span in (1, around):
            c = Counter()
            for r in (r for r in results if r["kind"] == kind):
                a = r["answers"][str(span)]
                if a["confidence"] < parabreaks.SURE:
                    continue
                says = a["value"] == "starts"
                ours = r["off"] if kind == "changed" else r["ours"]
                if says != ours:
                    c["fixed" if says == r["truth"] else "broke"] += 1
            print(f"         ±{span}    {c['fixed']:4}   {c['broke']:4}")


if __name__ == "__main__":
    args = sys.argv[1:]

    def option(name, default):
        return type(default)(args[args.index(name) + 1]) if name in args else default

    main(option("--around", 4), option("--sample", 200), set(option("--skip", "").split(",")) - {""})
