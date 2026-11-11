"""Nervous System's small-capital acronyms (TV, RCMP, CBC, VCR, …) as a test of the
small-capitals step: which of them a build reads right, asks about or gets wrong unasked,
and which the lower-case doubt (`ocrcheck.capitals_doubts`) would raise or a disputed
span would get in capitals (`capitals_versions`). No models: the
build's stage caches and the second scan's own text layer.

    uv run --project ../roboscriptorium-caps python experiments/probe_caps_nervous.py

Run from the main checkout so `work/` is reached by path. The second scan (the US
edition, same setting, ABBYY layer) writes every small-capital acronym in lower case,
which finds the places; each is matched to the build's line by the words around it.
The build's scan is the UK edition, which prints "police" for the US "RCMP".
Writes `nervous.jsonl` under `work/probes/caps-lower/`.
"""

import difflib
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf

from roboscriptorium import ocrcheck

BOOK = Path("work/nervous-system")
SECOND = Path("work/nervous-system--scan2/source.pdf")
OUT = Path("work/probes/caps-lower/nervous.jsonl")
# The acronyms the book sets in small capitals, as the second scan's layer writes them.
ACRONYMS = {"tv", "rcmp", "cbc", "vcr", "gp", "er", "oj", "fbi", "id", "cd", "cnn"}
# The build's scan runs this many PDF pages behind the second, give or take.
SHIFT, SLACK = 4, 3
CONTEXT = 4

_STRIP = ".,;:!?…“”‘’'\"()[]«»—–-"


def _fold(word: str) -> str:
    return word.strip(_STRIP).lower()


def places(pdf: Path) -> list[dict]:
    """Each acronym of the second scan's layer with the words either side of it."""
    out = []
    with pymupdf.open(pdf) as doc:
        for number, page in enumerate(doc, 1):
            words = page.get_text().split()
            for i, w in enumerate(words):
                if _fold(w) in ACRONYMS and w.strip(_STRIP).islower():
                    before = [_fold(x) for x in words[max(0, i - CONTEXT) : i]]
                    after = [_fold(x) for x in words[i + 1 : i + 1 + CONTEXT]]
                    out.append({"scan2_page": number, "acronym": _fold(w).upper(),
                                "before": before, "after": after})  # fmt: skip
    return out


def find(place: dict, pages: dict[int, list[dict]]):
    """(page, line index, word index) in the build's layer where the place's words stand,
    or None. A line-end hyphen or a misread word around it costs a little of the match."""
    want = [*place["before"], "", *place["after"]]
    at = len(place["before"])
    best = (0.0, None)
    for number in range(place["scan2_page"] + SHIFT - SLACK, place["scan2_page"] + SHIFT + SLACK + 1):
        stream = [
            (k, j, _fold(w))
            for k, line in enumerate(pages.get(number, []))
            for j, w in enumerate(line["text"].split())
        ]
        for i in range(len(stream)):
            window = stream[max(0, i - at) : i + len(place["after"]) + 1]
            got = [w if n != min(i, at) else "" for n, (_, _, w) in enumerate(window)]
            score = difflib.SequenceMatcher(None, want, got, autojunk=False).ratio()
            if score > best[0]:
                best = (score, (number, stream[i][0], stream[i][1]))
    return best[1] if best[0] >= 0.7 else None


def main():
    layer = json.loads((BOOK / "stages/textlayer.json").read_text())
    pages = {p["number"]: p["lines"] for p in layer["pages"]}
    suspects = json.loads((BOOK / "stages/ocr-check.json").read_text())
    by_line = {}
    for s in suspects:
        by_line.setdefault((s["page"], s["original"]), []).append(s)
    counts = Counter(
        t
        for lines in pages.values()
        for line in lines
        for t in (w.strip(_STRIP) for w in line["text"].split())
        if t.isalpha()
    )
    rows = []
    for place in places(SECOND):
        where = find(place, pages)
        if where is None:
            rows.append({**place, "state": "not placed"})
            continue
        number, k, j = where
        text = pages[number][k]["text"]
        spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
        s0, s1 = spans[j]
        read = text[s0:s1]
        hit = [s for s in by_line.get((number, text), []) if s["start"] < s1 and s0 < s["end"]]
        built = hit[0]["chosen"] if hit and hit[0]["choice"] == "other" else read
        asked = bool(hit) and hit[0]["choice"] == "review"
        right = place["acronym"] in built.strip(_STRIP)
        doubts = ocrcheck.capitals_doubts(text, [], counts)
        raised = [v for d0, d1, v in doubts if d0 < s1 and s0 < d1]
        more = [v for s in hit for v in ocrcheck.capitals_versions(s["ours"], s["others"], counts)]
        folded = _fold(read)
        other_word = not right and (
            difflib.SequenceMatcher(None, folded, place["acronym"].lower()).ratio() < 0.6
        )
        rows.append({
            **place, "page": number, "line": k, "layer": read, "built": built,
            "suspect": [[s["ours"], s["others"], s["choice"]] for s in hit],
            "state": "right" if right else "another word in this edition" if other_word
            else "asked" if asked else "wrong, unasked",
            "doubt": raised[0] if raised else None,
            "doubt_has_capitals": any(place["acronym"] in v for vs in raised for v in vs),
            "version_has_capitals": any(place["acronym"] in v for v in more),
        })  # fmt: skip
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"{len(rows)} places; by state: {dict(Counter(r['state'] for r in rows))}")
    table = Counter()
    for r in rows:
        if r["state"] in ("not placed", "another word in this edition"):
            continue
        reach = (
            "doubt with capitals" if r["doubt_has_capitals"]
            else "capitals a new version" if r["version_has_capitals"]
            else "not reached"
        )  # fmt: skip
        table[r["acronym"], r["layer"].strip(_STRIP), r["state"], reach] += 1
    for (acronym, read, state, reach), n in sorted(table.items()):
        print(f"{acronym:5} layer {read!r:10} {state:15} {reach:20} ×{n}")


if __name__ == "__main__":
    main()
