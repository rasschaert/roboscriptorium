"""Can the vision judge tell where a paragraph starts, where the page's geometry can't?

`prepare` (no models: each bench slice built from its caches, Ollama pointed nowhere so
an uncached call fails at once) lists every body line of a sample of pages with the
pipeline's call (does an output paragraph start at its first word?) and the reference's.
The sample is every page with a break error plus as many pages without one, seeded.

`ask` (the judge, clef:27b, on Ollama) shows the judge each sampled line between the
lines above and below it, cropped across the text block's width, with their text, and
asks whether it starts a paragraph. Answers are appended to
work/probes/break-judge/answers.jsonl, so a stopped run resumes.

`score` compares, on the sampled lines, the pipeline and the judge against the reference,
and the judge where the pipeline is wrong and where it is right.

    uv run python experiments/probe_break_judge.py prepare
    uv run python experiments/probe_break_judge.py ask [limit]
    uv run python experiments/probe_break_judge.py score
"""

import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

OUT = Path("work/probes/break-judge")
JUDGE = "clef:27b"
QUESTION = {
    "start": {
        "type": "choice",
        "instructions": (
            "The image is cut from a printed book page: the line in question with the "
            "line above it and the line below it. Does the line in question start a new "
            "paragraph, or does it carry on the paragraph of the line above? Look at its "
            "indent, the white space above it and the length of the line above, and at "
            "what the words say (a new speaker, a letter's greeting, a heading of a list)."
        ),
        "criteria": {
            "starts": "the line in question starts a new paragraph",
            "continues": "the line in question carries on the paragraph of the line above",
        },
    }
}


def prepare() -> None:
    os.environ["ROBO_OLLAMA_URL"] = "http://127.0.0.1:9"
    from rapidfuzz.distance import Levenshtein

    from roboscriptorium import bench
    from roboscriptorium import disagreements as D
    from roboscriptorium.evaluate import normalise
    from roboscriptorium.golden import scoring

    rows = []
    rng = random.Random(17)
    for name in ("tuning", "validation"):
        for spec in bench.SETS[name]:
            book = spec.split(":")[0]
            if "calibre-pdf" in book:
                continue  # born-digital: its breaks are exact
            run = scoring.build(f"work/{spec}", bench.unseen(scoring.Settings.from_env(), book))
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
            lines = []
            for (number, k), o in sorted(first.items()):
                if o not in to_ref or number not in pages or k >= len(pages[number].lines):
                    continue
                lines.append((number, k, o in starts, to_ref[o] in ref_starts))
            wrong = sorted({n for n, _, ours, truth in lines if ours != truth})
            right = sorted({n for n, *_ in lines} - set(wrong))
            sample = set(wrong) | set(rng.sample(right, min(len(right), len(wrong))))
            order = sorted(pages)
            for number, k, ours, truth in lines:
                if number not in sample:
                    continue
                page = pages[number]
                above = page.lines[k - 1].text if k else ""
                if not k and order.index(number):
                    before = pages[order[order.index(number) - 1]]
                    above = before.lines[-1].text if before.lines else ""
                rows.append(
                    {
                        "book": book,
                        "spec": spec,
                        "page": number,
                        "line": k,
                        "text": page.lines[k].text,
                        "above": above,
                        "below": page.lines[k + 1].text if k + 1 < len(page.lines) else "",
                        "page_top": k == 0,
                        "ours": ours,
                        "truth": truth,
                    }
                )
            print(f"{book:45} pages {len(sample):3} ({len(wrong)} with errors)", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lines.json").write_text(json.dumps(rows, ensure_ascii=False))
    print(f"{len(rows)} lines")


def _crop(doc, page, k: int) -> bytes:
    import pymupdf

    lines = page.lines
    left = min(ln.x0 for ln in lines) - 6
    right = max(ln.x1 for ln in lines) + 6
    top = lines[max(0, k - 1)].y0 - 4
    bottom = lines[min(len(lines) - 1, k + 1)].y1 + 4
    clip = pymupdf.Rect(left, top, right, bottom)
    return doc[page.number - 1].get_pixmap(dpi=150, clip=clip).tobytes("png")


def ask(limit: int | None) -> None:
    import pymupdf

    from roboscriptorium import ocr
    from roboscriptorium.book import Book
    from roboscriptorium.clients import decide
    from roboscriptorium.config import Settings
    from roboscriptorium.pdf import cached_text_layer

    rows = json.loads((OUT / "lines.json").read_text())
    path = OUT / "answers.jsonl"
    done = set()
    if path.exists():
        for ln in path.read_text().splitlines():
            try:
                a = json.loads(ln)
            except json.JSONDecodeError:
                continue
            done.add((a["book"], a["page"], a["line"]))
    todo = [r for r in rows if (r["book"], r["page"], r["line"]) not in done]
    if limit is not None:
        todo = todo[:limit]
    client = decide.for_model(JUDGE, Settings.from_env().ollama_url)
    layers: dict[str, dict] = {}
    docs: dict[str, pymupdf.Document] = {}
    start = time.time()
    with path.open("a") as f:
        for n, r in enumerate(todo, 1):
            book = r["book"]
            if book not in layers:
                b = Book.load(Path("work") / book)
                layer = cached_text_layer(
                    b.source, b.stages / "textlayer.json", ocr.language(b.language)
                )
                layers[book] = {p.number: p for p in layer}
                docs[book] = pymupdf.open(b.source)
            page = layers[book][r["page"]]
            png = _crop(docs[book], page, r["line"])
            state = {
                "line above"
                + (" (the last line of the page before)" if r["page_top"] else ""): r["above"],
                "line in question": r["text"],
                "line below": r["below"],
            }
            answer = client.decide(state, QUESTION, image_png=png)["start"]
            f.write(
                json.dumps(
                    {
                        "book": book,
                        "page": r["page"],
                        "line": r["line"],
                        "choice": answer.value,
                        "confidence": answer.confidence,
                    }
                )
                + "\n"
            )
            f.flush()
            if n % 50 == 0 or n == len(todo):
                per = (time.time() - start) / n
                left = (len(todo) - n) * per / 60
                print(f"{n}/{len(todo)}  {per:.1f} s a line, ~{left:.0f} min left", flush=True)


def score() -> None:
    rows = {(r["book"], r["page"], r["line"]): r for r in json.loads((OUT / "lines.json").read_text())}
    answers = [json.loads(ln) for ln in (OUT / "answers.jsonl").read_text().splitlines() if ln]
    by_book: dict[str, Counter] = {}
    total = Counter()
    for a in answers:
        r = rows[(a["book"], a["page"], a["line"])]
        judge = a["choice"] == "starts"
        c = by_book.setdefault(r["book"], Counter())
        for counter in (c, total):
            counter["lines"] += 1
            counter["pipeline wrong"] += r["ours"] != r["truth"]
            counter["judge wrong"] += judge != r["truth"]
            if r["ours"] != r["truth"]:
                counter["judge fixes"] += judge == r["truth"]
            else:
                counter["judge breaks"] += judge != r["truth"]
    print(f"{'book':45} lines  pipeline wrong  judge wrong  fixes  breaks")
    for book, c in sorted(by_book.items()) + [("all", total)]:
        print(
            f"{book:45} {c['lines']:5}  {c['pipeline wrong']:14}  {c['judge wrong']:11}  "
            f"{c['judge fixes']:5}  {c['judge breaks']:6}"
        )


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "prepare":
        prepare()
    elif command == "ask":
        ask(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        score()
