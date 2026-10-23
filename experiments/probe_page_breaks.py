"""Can the read model tell from the whole page image which lines start a paragraph?

The vision judge on line crops gained nothing over the reflow's geometry (2026-10-17);
this asks at page level instead. The model sees the page and the pipeline's body lines
of that page, numbered, and answers with the numbers of the lines that start a paragraph.

`prepare` (no models: each tuning slice built from its caches, Ollama pointed nowhere)
lists every page with a paragraph break set wrong and as many without, seeded, each with
its body lines, the pipeline's call per line and the reference's (only lines whose first
word aligns are scored). `ask` sends each page to the read model, thinking off, answers
appended to work/probes/page-breaks/answers-<model>.jsonl (a stopped run resumes).
`score` compares the pipeline and the model with the reference, per book.

    uv run python experiments/probe_page_breaks.py prepare
    uv run python experiments/probe_page_breaks.py ask [limit]
    uv run python experiments/probe_page_breaks.py score
"""

import base64
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

OUT = Path("work/probes/page-breaks")
PROMPT = (
    "This is a page of a printed book. Below are the lines of its running text as read from "
    "the page, numbered in reading order. Which of these lines begin a new paragraph? Judge "
    "from the page image: how the print marks a paragraph's start (an indent, a blank line, "
    "the line before ending short) and what the text says. The first line on the page begins "
    "a paragraph only if the print shows it does; otherwise it continues one from the page "
    "before.\n\n{lines}\n\nAnswer with a JSON list of the numbers of the lines that begin a "
    "paragraph and nothing else, for example [1, 4, 9]."
)


def prepare() -> None:
    os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"
    from rapidfuzz.distance import Levenshtein

    from roboscriptorium import bench
    from roboscriptorium import disagreements as D
    from roboscriptorium.evaluate import normalise
    from roboscriptorium.golden import scoring

    out_pages = []
    rng = random.Random(23)
    for spec in bench.SETS["tuning"]:
        book = spec.split(":")[0]
        run = scoring.build(f"work/{spec}", bench.unseen(scoring.Settings.from_env(), book))
        if scoring.breaks_unlike(run.book):
            continue
        doc = scoring.scored(run.book, run.stages)
        pages = {p.number: p for p in run.stages.pages}
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
        by_page: dict[int, list[dict]] = {}
        for (number, k), o in sorted(first.items()):
            if number not in pages or k >= len(pages[number].lines):
                continue
            by_page.setdefault(number, []).append(
                {
                    "line": k,
                    "text": pages[number].lines[k].text,
                    "ours": o in starts,
                    "truth": (to_ref[o] in ref_starts) if o in to_ref else None,
                }
            )
        wrong = sorted(
            n for n, ls in by_page.items()
            if any(x["truth"] is not None and x["ours"] != x["truth"] for x in ls)
        )  # fmt: skip
        right = sorted(set(by_page) - set(wrong))
        sample = set(wrong) | set(rng.sample(right, min(len(right), len(wrong))))
        for number in sorted(sample):
            out_pages.append({"book": book, "page": number, "wrong": number in wrong,
                              "lines": by_page[number]})  # fmt: skip
        print(f"{book:45} pages {len(sample):3} ({len(wrong)} with errors)", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pages.json").write_text(json.dumps(out_pages, ensure_ascii=False))
    print(f"{len(out_pages)} pages")


def _answers(model: str) -> Path:
    return OUT / f"answers-{model.replace(':', '_').replace('/', '_')}.jsonl"


def ask(limit: int | None) -> None:
    import httpx
    import pymupdf

    from roboscriptorium import pagereader
    from roboscriptorium.clients.retry import patiently
    from roboscriptorium.config import Settings

    settings = Settings.from_env()
    model = settings.read_model
    pages = json.loads((OUT / "pages.json").read_text())
    path = _answers(model)
    done = {(a["book"], a["page"]) for a in map(json.loads, path.read_text().splitlines())} \
        if path.exists() else set()  # fmt: skip
    todo = [p for p in pages if (p["book"], p["page"]) not in done][:limit]
    for n, p in enumerate(todo, 1):
        with pymupdf.open(Path("work") / p["book"] / "source.pdf") as doc:
            png = pagereader._render(doc[p["page"] - 1])
        lines = "\n".join(f"{i}. {x['text']}" for i, x in enumerate(p["lines"], 1))
        body = {
            "model": model, "prompt": PROMPT.format(lines=lines), "stream": False,
            "think": False, "images": [base64.b64encode(png).decode()],
            "options": {"temperature": 0, "num_predict": 300},
        }  # fmt: skip
        reply = patiently(
            lambda: httpx.post(f"{settings.ollama_url}/api/generate", json=body, timeout=900)
        ).json()["response"]
        found = re.search(r"\[[\d,\s]*\]", reply)
        picked = json.loads(found.group()) if found else None
        with path.open("a") as f:
            f.write(json.dumps({"book": p["book"], "page": p["page"], "reply": reply,
                                "starts": picked}) + "\n")  # fmt: skip
        print(f"{n}/{len(todo)} {p['book'][:30]} p{p['page']}: {picked}", flush=True)


def score() -> None:
    from roboscriptorium.config import Settings

    model = Settings.from_env().read_model
    pages = {(p["book"], p["page"]): p for p in json.loads((OUT / "pages.json").read_text())}
    answers = [json.loads(x) for x in _answers(model).read_text().splitlines()]
    per_book: dict[str, Counter] = {}
    unparsed = 0
    for a in answers:
        p = pages[(a["book"], a["page"])]
        if a["starts"] is None:
            unparsed += 1
            continue
        picked = set(a["starts"])
        c = per_book.setdefault(a["book"], Counter())
        for i, x in enumerate(p["lines"], 1):
            if x["truth"] is None:
                continue
            ours, model_says = x["ours"] == x["truth"], (i in picked) == x["truth"]
            c["lines"] += 1
            c["ours wrong"] += not ours
            c["model wrong"] += not model_says
            c["model fixes"] += model_says and not ours
            c["model breaks"] += ours and not model_says
    total = sum(per_book.values(), Counter())
    for book, c in sorted(per_book.items()):
        print(f"{book[:40]:40} {dict(c)}")
    print(f"all: {dict(total)}; unparsed answers {unparsed}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prepare":
        prepare()
    elif cmd == "ask":
        ask(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        score()
