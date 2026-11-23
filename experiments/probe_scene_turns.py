"""Can a decision model tell, from the text alone, that a new scene starts at a page turn?

The build misses scene breaks at page tops where the page before ends a sentence on a
full line and the next opens flush: the geometry of a paragraph running on, so only the
text can tell (checklist, "Scene breaks the build misses"). This collects every page turn
in the tuning books where the text before it ends a sentence, labels each by whether the
reference has a scene break there and whether the build already sets one, then asks
each model named "does a new scene start here?" on the text around the turn.

    uv run python experiments/probe_scene_turns.py collect          # no model: candidates.json
    uv run python experiments/probe_scene_turns.py ask <model>…      # answers, cached per model
    uv run python experiments/probe_scene_turns.py report <model>…

Tuning books only: validation stays unseen until a version is chosen. Answers are cached in
work/probes/scene-turns/decisions.jsonl (keyed by model, question and state), so a stop
loses the call in flight.
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path("work/probes/scene-turns")
AROUND = 6
# The text before the turn ends a sentence: a stop, ! ? or ellipsis, perhaps closing quotes.
ENDS = re.compile(r"[.!?…][’”»\"')\]]*\s*$")
INSTRUCTIONS = (
    "A page of a printed novel ends and the next page begins. Does a new scene start at "
    "the top of the next page (a jump in time, place or point of view, which the book "
    "marks with a blank line or an ornament), or does the same scene go on?"
)
CRITERIA = {
    "new_scene": "a new scene starts at the top of the next page",
    "continues": "the same scene goes on across the page turn",
}


def collect() -> None:
    from rapidfuzz.distance import Levenshtein

    from roboscriptorium import bench, evaluate, parabreaks, reflow
    from roboscriptorium.config import Settings
    from roboscriptorium.golden import scoring

    rows = []
    for spec in bench.SETS["tuning"]:
        name = spec.split(":")[0]
        os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"  # the caches only, no model
        run = scoring.build(f"work/{spec}", bench.unseen(Settings.from_env(), name))
        os.environ.pop("ROBO_OLLAMA_URL")
        doc = scoring.scored(run.book, run.stages)
        pages = {p.number: p for p in run.stages.pages}
        paras = doc.paragraphs
        out_words, starts = [], []
        for p in paras:
            starts.append(len(out_words))
            out_words += evaluate.normalise(p.text).split()
        ref_words, ref_breaks, ref_chapters = [], set(), set()
        for ch in run.reference:
            ref_chapters.add(len(ref_words))
            for k, para in enumerate(ch.paragraphs):
                if k in ch.breaks:
                    ref_breaks.add(len(ref_words))
                ref_words += evaluate.normalise(para).split()
        if not ref_breaks:
            print(f"{name:45} no breaks in the reference", flush=True)
            continue
        out_of_ref = {}
        for op in Levenshtein.opcodes(out_words, ref_words):
            if op.tag == "equal":
                for i in range(op.src_end - op.src_start):
                    out_of_ref[op.dest_start + i] = op.src_start + i
        ref_at = {out_of_ref[r] for r in ref_breaks if r in out_of_ref}
        # A chapter opening is no scene break: the build's own section starts and the
        # reference's chapter starts.
        chapter_at = {out_of_ref[r] for r in ref_chapters if r in out_of_ref}
        chapter_at |= {starts[k] for k, p in enumerate(paras) if p.opening}
        built = {starts[k] for k, p in enumerate(paras) if p.break_before}
        order = [(k, s) for k, p in enumerate(paras) for s in p.sources if not s.typed]
        text = lambda s: pages[s.page].lines[s.line].text  # noqa: E731
        right = {n: max((ln.x1 for ln in pg.lines), default=0) for n, pg in pages.items()}
        book_indents = parabreaks.indents(list(pages.values()))
        found = 0
        for i in range(1, len(order)):
            (k, s), (_, prev) = order[i], order[i - 1]
            if s.page == prev.page or not ENDS.search(text(prev)):
                continue
            if order[i - 1][0] != k:
                o = starts[k]
            else:  # the turn falls inside an output paragraph: find the line's first word
                first = evaluate.normalise(text(s)).split()[:1]
                before = sum(len(evaluate.normalise(text(t)).split())
                             for kk, t in order[:i] if kk == k)  # fmt: skip
                words = out_words[starts[k] : starts[k + 1] if k + 1 < len(starts) else None]
                near = [j for j in range(max(0, before - 4), min(len(words), before + 5))
                        if words[j : j + 1] == first]  # fmt: skip
                if not near:
                    continue
                o = starts[k] + min(near, key=lambda j: abs(j - before))
            pline = pages[prev.page].lines[prev.line]
            # The build's own test for a scene's opening: flush on the margin of a page whose
            # paragraphs indent (reflow's rule, which the page-top misses pass).
            body = [pages[s.page].lines[t.line] for _, t in order if t.page == s.page]
            at = next(j for j, ln in enumerate(body) if ln is pages[s.page].lines[s.line])
            row = {
                "book": name,
                "language": run.book.language,
                "page": s.page,
                "line": s.line,
                "scene": any(o + d in ref_at for d in (-1, 0, 1)),
                "built": o in built,
                "chapter": any(o + d in chapter_at for d in (-1, 0, 1)),
                "inside_paragraph": order[i - 1][0] == k,
                "full_line": pline.x1 >= right[prev.page] - 2,
                "flush": reflow._flush_where_paragraphs_indent(body, at),
                # The same by the book's habit, for a page of running text with no indent.
                "book_indents": book_indents,
                "x0_off": round(body[at].x0 - sorted(ln.x0 for ln in body)[len(body) // 4], 1),
                "before": [text(t) for _, t in order[max(0, i - AROUND) : i]],
                "after": [text(t) for _, t in order[i : i + AROUND]],
            }
            found += row["scene"]
            rows.append(row)
        print(f"{name:45} {sum(r['book'] == name for r in rows):4} turns, {found:3} scenes", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "candidates.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    scenes = [r for r in rows if r["scene"]]
    print(f"\n{len(rows)} turns ending a sentence; {len(scenes)} with a scene break, "
          f"{sum(r['built'] for r in scenes)} of them set by the build; "
          f"{sum(r['built'] and not r['scene'] for r in rows)} set where the reference has none")  # fmt: skip


def state(row: dict) -> dict:
    return {
        "language of the book": row["language"],
        "end of the page before": "\n".join(row["before"]),
        "start of the next page": "\n".join(row["after"]),
    }


def ask(models: list[str]) -> None:
    from roboscriptorium.clients import decide
    from roboscriptorium.config import Settings
    from roboscriptorium.roles import DecisionCache

    rows = json.loads((OUT / "candidates.json").read_text())
    questions = {"scene": decide.choice(INSTRUCTIONS, CRITERIA)}
    cache = DecisionCache(OUT / "decisions.jsonl")
    settings = Settings.from_env()
    for model in models:
        client = decide.for_model(model, settings.ollama_url)
        for n, row in enumerate(rows, 1):
            st = state(row)
            key = cache.key(client.model, questions, st)
            if cache.get(key) is None:
                answer = client.decide(st, questions)["scene"]
                cache.put(key, {"value": answer.value, "probabilities": answer.probabilities})
            if n % 100 == 0:
                print(f"{model}: {n} of {len(rows)}", flush=True)


def report(models: list[str]) -> None:
    from sklearn.metrics import roc_auc_score

    from roboscriptorium.clients import decide
    from roboscriptorium.roles import DecisionCache

    rows = json.loads((OUT / "candidates.json").read_text())
    questions = {"scene": decide.choice(INSTRUCTIONS, CRITERIA)}
    cache = DecisionCache(OUT / "decisions.jsonl")
    # What the build doesn't already settle: no break set, no chapter opening there.
    open_ = [r for r in rows if not r["built"] and not r.get("chapter")]
    if "--flush" in sys.argv:  # only where the page opens flush and its paragraphs indent
        open_ = [r for r in open_ if r.get("flush")]
    if "--book-flush" in sys.argv:  # flush on the margin of a book that indents
        open_ = [r for r in open_ if r.get("book_indents") and -2.5 <= r.get("x0_off", 99) <= 3.5]
    missed = [r for r in open_ if r["scene"]]
    print(f"{len(open_)} turns the build sets no break or chapter at; "
          f"{len(missed)} of them scene breaks")
    for model in models:
        client = decide.for_model(model, "http://127.0.0.1:9")
        p = []
        for r in open_:
            got = cache.get(cache.key(client.model, questions, state(r)))
            p.append(None if got is None else got["probabilities"].get("new_scene", 0.0))
        have = [(r, x) for r, x in zip(open_, p, strict=True) if x is not None]
        if len({r["scene"] for r, _ in have}) < 2:
            print(f"{model}: {len(have)} answered, too few to score")
            continue
        auc = roc_auc_score([r["scene"] for r, _ in have], [x for _, x in have])
        print(f"\n{model}: {len(have)} answered, AUC {auc:.3f}")
        for cut in (0.5, 0.7, 0.9):
            hit = [r for r, x in have if x >= cut and r["scene"]]
            false = [r for r, x in have if x >= cut and not r["scene"]]
            print(f"  ≥ {cut}: finds {len(hit)} of {len(missed)} missed breaks, "
                  f"{len(false)} false breaks")  # fmt: skip
        by_book = defaultdict(lambda: [0, 0])
        for r, x in have:
            if r["scene"]:
                by_book[r["book"]][0] += 1
                by_book[r["book"]][1] += x >= 0.5
        print("  missed breaks found at 0.5, by book: "
              + ", ".join(f"{b.split('--')[0]} {f}/{n}" for b, (n, f) in sorted(by_book.items())))  # fmt: skip


if __name__ == "__main__":
    what, *models = [a for a in sys.argv[1:] if not a.startswith("--")] or ["collect"]
    {"collect": lambda: collect(), "ask": lambda: ask(models), "report": lambda: report(models)}[what]()
