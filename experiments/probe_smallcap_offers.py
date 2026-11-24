"""Small capitals every reader reads in lower case: would the ink offer the capitals? On the
tuning books' pages, every text-layer word with lower-case letters is tried as small
capitals (the whole word, and its part before a hyphen or apostrophe), each laid across
the word's ink by the book's face and measured letter by letter against the page
(probe_case_fit2.py). No models.

    uv run python experiments/probe_smallcap_offers.py <bench errors.jsonl> [--random 10]

Pages: those holding a case error in the given bench run, and --random body pages a book
for the false offers. A word is a true offer where the bench's error wants that word in
capitals on that page; every other offer is counted false (the print in lower case).
Prints, by the margin the capitals win by, how many true and false offers it would make;
writes work/probes/smallcap-offers/rows.json.
"""

import json
import random
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from probe_case_fit import lines_of  # noqa: E402
from probe_case_fit2 import Line, advances, expect, face, table_of  # noqa: E402

from roboscriptorium import bench  # noqa: E402
from roboscriptorium import pdf as pdflayer  # noqa: E402
from roboscriptorium.book import Book  # noqa: E402
from roboscriptorium.pdf import cached_text_layer  # noqa: E402

OUT = Path("work/probes/smallcap-offers")
SPLIT = re.compile(r"[-’']")


def capitalised(word: str) -> list[str]:
    """The small-capital versions to try: the whole word's letters, and its first part."""
    out = []
    if any(c.islower() for c in word):
        out.append(word.upper())
        m = SPLIT.search(word)
        if m and m.start() > 0 and any(c.islower() for c in word[: m.start()]):
            out.append(word[: m.start()].upper() + word[m.start():])
    return [v for v in dict.fromkeys(out) if v != word]


def misfit(line, span, font, text, table) -> float | None:
    got = line.letters(span, advances(font, text))
    if not got:
        return None
    errs = []
    for c, small, h, d in got:
        e = expect(c, small, table)
        if e is None:
            return None
        errs.append(abs(h - e[0]) + abs(d - e[1]))
    return float(np.mean(errs))


def page_offers(args) -> list[dict]:
    name, number, wanted = args
    d = Path("work") / name
    font = face(name)
    pages = {p.number: p for p in cached_text_layer(d / "source.pdf", d / "stages/textlayer.json")}
    out = []
    with pymupdf.open(d / "source.pdf") as doc:
        page = doc[number - 1]
        words = pdflayer.page_words(page, pages.get(number))
        table = table_of(page, words, font)
        for ws in lines_of(words):
            if len(ws) < 4:
                continue
            line = Line(page, ws)
            if not line.ok:
                continue
            for w in ws:
                tries = capitalised(w[4])
                if not tries:
                    continue
                span = line.extent(w)
                if span is None:
                    continue
                base = misfit(line, span, font, w[4], table)
                if base is None:
                    continue
                for v in tries:
                    f = misfit(line, span, font, v, table)
                    if f is None:
                        continue
                    out.append({
                        "book": name, "page": number, "word": w[4], "offer": v,
                        "margin": round(base - f, 3),
                        "true": any(v.strip(".,;:!?’'“”\"(") in x for x in wanted),
                    })
    return out


if __name__ == "__main__":
    errors = [json.loads(x) for x in open(sys.argv[1])]
    n_random = int(sys.argv[sys.argv.index("--random") + 1]) if "--random" in sys.argv else 10
    rng = random.Random(20261124)
    jobs = []
    for spec in bench.SETS["tuning"]:
        name = spec.split(":")[0]
        first, last = Book.load(Path("work") / name).body_pages
        if ":" in spec:
            first, last = map(int, spec.split(":")[1].split("-"))
        caps = {}
        for e in errors:
            if e["book"] == name and e["cause"] == "case" and e["want"] != e["want"].lower():
                caps.setdefault(e["page"], []).append(e["want"])
        pages = set(caps) | set(rng.sample(range(first, last + 1), min(n_random, last - first + 1)))
        jobs += [(name, p, caps.get(p, [])) for p in sorted(pages)]
    rows = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for found in pool.map(page_offers, jobs):
            rows += found
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"{len(jobs)} pages, {len(rows)} tries, {sum(r['true'] for r in rows)} true")
    for m in (0.0, 0.03, 0.06, 0.1, 0.15, 0.2):
        sel = [r for r in rows if r["margin"] > m]
        print(f"margin > {m}: {len(sel)} offers, true {sum(r['true'] for r in sel)}")
