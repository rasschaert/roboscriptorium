"""Lines two whole-page readings hold that the text layer lacks, on the tuning pages that
have both readings (`pagereader.py` caches), and how many of them the bench lists as lost
text. No models.

    uv run python experiments/probe_page_inserts.py

A candidate is a run of more than `MAX_INSERTED` reading words, inserted between two layer
words by both the glm-ocr and the Qwen page reading at the same place (within `TOLERANCE` layer words). Printed per book:
candidates, those the latest tuning bench lists as lost text, and the rest by where they
sit on the page (first or last line, or inside).
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench
from roboscriptorium.evaluate import normalise
from roboscriptorium.pagereader import MAX_INSERTED, _key, _layer_words, reading_words
from roboscriptorium.pdf import cached_text_layer

TOLERANCE = 2  # layer words between the two readings' insert positions
RUN = "tuning-20261020T182636-f38e636-dirty"


def inserts(layer, reading: str) -> dict[int, list[str]]:
    """Reading words inserted at a layer word index, for runs over `MAX_INSERTED`."""
    words = reading_words(reading)
    ops = Levenshtein.opcodes(
        ["".join(_key(t) for _, t in pieces) for pieces in layer], [_key(w) for w, _ in words]
    )
    return {
        op.src_start: [w for w, _ in words[op.dest_start : op.dest_end]]
        for op in ops
        if op.tag == "insert" and op.dest_end - op.dest_start > MAX_INSERTED
    }


def flat(text: str) -> str:
    return " " + normalise(re.sub(r"[#*_]", "", text)).lower() + " "


if __name__ == "__main__":
    books = [spec.split(":")[0] for spec in bench.SETS["tuning"]]
    lost = defaultdict(list)
    for line in Path(f"work/bench/{RUN}.errors.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["cause"] == "missing text":
            lost[(r["book"], r["page"])].append(flat(r["want"]).strip())
    total = Counter()
    for book in books:
        stages = Path("work") / book / "stages"
        files = [stages / f"page-reading-{k}-page.json" for k in ("glm", "qwen")]
        if not all(f.exists() for f in files):
            continue
        glm, qwen = (json.loads(f.read_text())["pages"] for f in files)
        pages = {p.number: p for p in cached_text_layer(Path("work") / book / "source.pdf", stages / "textlayer.json")}
        row = Counter()
        for number in glm.keys() & qwen.keys():
            page = pages.get(int(number))
            if page is None or len(page.lines) < 5:
                continue
            layer = _layer_words(page)
            a, b = inserts(layer, glm[number]), inserts(layer, qwen[number])
            for at in sorted(k for k in a if any(abs(k - j) <= TOLERANCE for j in b)):
                row["candidates"] += 1
                text = flat(" ".join(a[at]))
                if any(w and w in text for w in lost[(book, int(number))]):
                    row["listed as lost text"] += 1
                else:
                    edge = at <= 1 or at >= len(layer) - 1
                    row["other, at the page's edge" if edge else "other, inside"] += 1
        total += row
        print(f"{book[:34]:34} pages {len(glm.keys() & qwen.keys()):3}  {dict(row)}")
    print("all", dict(total))
