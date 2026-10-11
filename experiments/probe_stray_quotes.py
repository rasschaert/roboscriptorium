"""An opening quote left unclosed at a paragraph's end is excused when the next paragraph
opens with the same mark, a quotation running over paragraphs. Such a quotation starts a
sentence; one opened mid-sentence ("die erop wezen dat Green zich ‘schrap zette") is a
speck read as a quote. Counts the places the stricter excuse adds on the tuning books'
saved documents, and how many fall where the bench found an unasked quote error.

    uv run python experiments/probe_stray_quotes.py
"""

import json
import re
from pathlib import Path

from roboscriptorium import bench, quotes

MID_SENTENCE = re.compile(r"[\w,;]\s*$")

total = hits = 0
for spec in bench.SETS["tuning"]:
    name = spec.split(":")[0]
    blocks = json.loads((Path("work") / name / "stages" / "document.json").read_text())["blocks"]
    paras = [b for b in blocks if "text" in b and "level" not in b]
    errors = [json.loads(line) for line in open(f"work/probes/unasked/{name}.jsonl")]
    quote_pages = {e["page"] for e in errors if e["category"] == "quotes"}
    for k, p in enumerate(paras):
        text = p["text"]
        following = paras[k + 1]["text"][:1] if k + 1 < len(paras) else ""
        if not following or not any(c in text for c in "‘“"):
            continue
        old = quotes.problems(text, following)
        if any(why == "open at end" for _, why in old):
            continue
        # The marks left open at the end, as `problems` counts them.
        stack = []
        for i, c, kind in quotes.marks(text):
            if kind == "open":
                stack.append((i, c))
            elif stack and quotes.PAIRS.get(stack[-1][1]) == c:
                stack.pop()
        stray = [(i, c) for i, c in stack if c == following and MID_SENTENCE.search(text[:i])]
        if not stray:
            continue
        total += 1
        pages = {s["page"] for s in p["sources"]}
        hit = bool(pages & quote_pages)
        hits += hit
        i = stray[0][0]
        print(f"  {'HIT ' if hit else '    '}{name[:14]} p{min(pages)} …{text[max(0, i - 40):i + 30]!r}")
print(f"{total} new places, {hits} on a page with an unasked quote error")
