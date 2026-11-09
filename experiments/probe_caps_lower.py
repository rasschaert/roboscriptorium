"""Can the vision judges tell small capitals from lower case, where every reader agrees on
lower case? The places no reading disputes, so no suspect reaches the judges today.

    uv run python experiments/probe_caps_lower.py collect   # no models: candidates, labelled
    uv run python experiments/probe_caps_lower.py ask [N]   # the judges, N per label at most
    uv run python experiments/probe_caps_lower.py report

A candidate is a short lower-case piece of a body line in the text layer: a part of one to
four letters joined by a hyphen, apostrophe or slash ("ss-chef", "u-bocht", "usb-stick"),
or a word of two to five letters with no vowel ("ss", "cv"). Its label comes from the
book's reference: the same token with that piece in capitals there (positive), in lower
case (negative), or neither (left out). Au pair is left out: its reference keeps small
capitals in lower case. Each judge is asked the OCR check's question between the piece
as read and its capitals, on the suspect's crop and on the wide crop with its line.
"""

import json
import random
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pymupdf

from roboscriptorium import bench, ocrcheck, readers
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.roles import DecisionCache
from roboscriptorium.golden import scoring
from roboscriptorium.pdf import line_words, page_words

OUT = Path("work/probes/caps-lower")
SKIP = {"au-pair--ia-scan"}
JUDGES = ["clef:27b", "autotrust-jev:35b-nvfp4", "d3:9b"]
VOWELS = set("aeiouyàáâäèéêëìíîïòóôöùúûü")
# A token: letters joined by hyphens, apostrophes or slashes.
TOKEN = re.compile(r"[^\W\d_]+(?:[-'’/][^\W\d_]+)*")


def pieces(token: str):
    """(start, end, rule) of each piece of a token that small capitals could be read as."""
    parts = list(re.finditer(r"[^\W\d_]+", token))
    if len(parts) > 1:
        for m in parts:
            if m[0].islower() and len(m[0]) <= 4:
                yield m.start(), m.end(), "joined"
    elif token.islower() and 2 <= len(token) <= 5 and not set(token) & VOWELS:
        yield 0, len(token), "no vowel"


def label(token: str, s: int, e: int, ref: Counter) -> bool | None:
    caps = token[:s] + token[s:e].upper() + token[e:]
    up, low = ref[_norm(caps)], ref[_norm(token)]
    if up and not low:
        return True
    if low and not up:
        return False
    return None


def _norm(token: str) -> str:
    return token.replace("’", "'")


def _book(spec: str) -> list[dict]:
    """One book's candidates, built warm."""
    name = spec.split(":")[0]
    scored = scoring.build(f"work/{spec}")
    ref = Counter(
        _norm(m[0])
        for ch in scored.reference
        for p in [ch.heading, *ch.paragraphs]
        for m in TOKEN.finditer(p)
    )
    rows = []
    with pymupdf.open(scored.book.source) as doc:
        for page in scored.stages.pages:
            pdf_page = doc[page.number - 1]
            words = line_words(page_words(pdf_page, page), page)
            boxes = readers.line_boxes(pdf_page, page)
            for k, line in enumerate(page.lines):
                for m in TOKEN.finditer(line.text):
                    for s, e, rule in pieces(m[0]):
                        truth = label(m[0], s, e, ref)
                        if truth is None:
                            continue
                        a0, a1 = ocrcheck._word_span(line.text, m.start(), m.end())
                        piece = line.text[a0:a1]
                        off = m.start() - a0
                        caps = piece[: off + s] + piece[off + s : off + e].upper() + piece[off + e :]
                        box = ocrcheck._box(words[k], boxes[k], line.text, a0, a1)
                        rows.append({
                            "book": name, "page": page.number, "line": k,
                            "text": line.text, "start": a0, "end": a1, "ours": piece,
                            "caps": caps, "rule": rule, "truth": truth,
                            "box": [round(v, 2) for v in box],
                        })  # fmt: skip
    return rows


def collect():
    specs = [s for s in bench.SETS["tuning"] if s.split(":")[0] not in SKIP]
    rows = []
    with ProcessPoolExecutor(bench.workers()) as pool:
        for future in as_completed([pool.submit(_book, s) for s in specs]):
            got = future.result()
            rows += got
            print(f"{got[0]['book'] if got else '?'}: {len(got)}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "candidates.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    )
    print(Counter((r["rule"], r["truth"]) for r in rows))


def _layer_words(book: str) -> Counter:
    """How often each word stands alone in the book's text layer."""
    pages = json.loads(Path(f"work/{book}/stages/text-layer.json").read_text())["pages"]
    return Counter(
        t
        for p in pages
        for line in p["lines"]
        for t in (w.strip(".,;:!?…“”‘’'\"()[]«»—–-") for w in line["text"].split())
        if t.isalpha()
    )


def keep(r: dict, words: Counter, common: int = 3) -> bool:
    """Whether a candidate passes the text cues: not a contraction's piece, and not a
    word with a vowel the book uses `common` times or more on its own."""
    o, c = r["ours"], r["caps"]
    i = next(k for k, (a, b) in enumerate(zip(o, c, strict=True)) if a != b)
    j = i
    while j < len(o) and o[j] != c[j]:
        j += 1
    p = o[i:j]
    if i and o[i - 1] in "’'":
        return False
    if re.match(r"[’'](t|re|ll|ve|d|m)\b", o[j:]) or re.match(r"n[’']t", o[j - 1 :]):
        return False
    return not (set(p) & VOWELS and len(p) > 1 and words[p] >= common)


def ask(cap: int):
    settings = Settings.from_env()
    rows = [json.loads(x) for x in (OUT / "candidates.jsonl").read_text().splitlines()]
    words = {b: _layer_words(b) for b in {r["book"] for r in rows}}
    neg = [r for r in rows if not r["truth"] and keep(r, words[r["book"]])]
    random.Random(0).shuffle(neg)
    take = [r for r in rows if r["truth"]] + neg[:cap]
    cache = DecisionCache(OUT / "decisions.jsonl")
    docs = {}
    votes = [{} for _ in take]
    for j in JUDGES:
        tight = decide.for_model(j, settings.ollama_url)
        wide = decide.Wide(tight, j + "@wide", ocrcheck.WIDE)
        for i, r in enumerate(take):
            src = scoring.parse_spec(f"work/{r['book']}")[0] / "source.pdf"
            doc = docs.setdefault(r["book"], pymupdf.open(src))
            # The OCR check's own question: the judge on the suspect's crop, and as a
            # second judge on the wide crop with its line, as the pipeline asks them.
            (_, _, v), conf = ocrcheck._decide(
                doc[r["page"] - 1], r["page"], r["line"], r["text"], r["start"], r["end"],
                [r["caps"]], tuple(r["box"]), "nl", tight, None, cache, alarms=[wide],
            )  # fmt: skip
            for name in (j, j + "@wide"):
                votes[i][name] = {"pick": v[name], "confidence": conf[name]}
        for name in (j, j + "@wide"):
            right = sum((x[name]["pick"] == r["caps"]) == r["truth"] for x, r in zip(votes, take))
            print(f"{name}: {right}/{len(take)} right", flush=True)
    out = [{**r, "votes": v, "kept": keep(r, words[r["book"]])} for r, v in zip(take, votes)]
    (OUT / "answers.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out)
    )


def report():
    rows = [json.loads(x) for x in (OUT / "answers.jsonl").read_text().splitlines()]
    names = list(rows[0]["votes"])
    for n in names:
        tp = sum(r["truth"] and r["votes"][n]["pick"] == r["caps"] for r in rows)
        fp = sum(not r["truth"] and r["votes"][n]["pick"] == r["caps"] for r in rows)
        pos = sum(r["truth"] for r in rows)
        print(f"{n:32} caps on positives {tp}/{pos}, caps on negatives {fp}/{len(rows) - pos}")
    for r in rows:
        if any((x["pick"] == r["caps"]) != r["truth"] for x in r["votes"].values()):
            wrong = [n for n, x in r["votes"].items() if (x["pick"] == r["caps"]) != r["truth"]]
            print(f"  {r['truth']!s:5} {r['book'][:14]} p{r['page']} {r['ours']!r} wrong: {wrong}")


if __name__ == "__main__":
    {"collect": collect, "report": report}.get(sys.argv[1], lambda: None)()
    if sys.argv[1] == "ask":
        ask(int(sys.argv[2]) if len(sys.argv) > 2 else 150)
