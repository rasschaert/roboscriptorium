"""Line-end hyphens inside a hyphenated chain ("geen-verandering-in-de-" / "toestand"),
over the tuning and validation books: what `hyphens.join` does with each, against how the
reference prints the chain (whole, or closed at the break). No models. Splits out the ones
where a fragment beside the break has two letters, which the joiner's `>= 3` guard joins.

    uv run --project ../roboscriptorium-chains python experiments/probe_chain_breaks.py

Writes work/probes/chain-breaks.jsonl (one line per break).
"""

import json
import re
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, hyphens, ocr
from roboscriptorium.book import Book
from roboscriptorium.golden import scoring
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import cached_text_layer

W = re.compile(r"[^\w-]")
rows = []
for kind in ("tuning", "validation"):
    for spec in bench.SETS[kind]:
        name, pages, _ = (spec.split(":") + ["", ""])[:3]
        book = Book.load(Path("work") / name)
        first, last = scoring.page_range(pages or None) or book.body_pages
        lang = ocr.language(book.language)
        layer = cached_text_layer(book.source, book.stages / "textlayer.json", lang)
        layer = [p for p in layer if first <= p.number <= last]
        seen, lex = hyphens.spellings(layer), Lexicon.load(lang)
        ref = load_chapters(Golden.load(book.golden).text_dir)
        words = Counter(
            W.sub("", w).lower() for ch in ref for para in ch.paragraphs for w in para.split()
        )
        lines = [line.text for p in layer for line in p.lines]
        for text, nxt in zip(lines, lines[1:], strict=False):
            if not (text.endswith(hyphens.HYPHENS) and len(text) > 1 and text[-2].isalpha()):
                continue
            stem = W.sub("", text.split()[-1][:-1])
            rest = W.sub("", nxt.split()[0]) if nxt.split() else ""
            if not stem or not rest or not nxt[:1].islower() or "-" not in stem + rest:
                continue
            whole, closed = f"{stem}-{rest}".lower(), f"{stem}{rest}".lower()
            h, c = words[whole], words[closed]
            if bool(h) == bool(c):
                continue
            kept = hyphens.join(text, nxt, seen=seen, known=lex.knows).split()
            before, after = stem.rsplit("-", 1)[-1], rest.split("-", 1)[0]
            rows.append(
                {
                    "book": name,
                    "chain": whole,
                    "truth": "whole" if h else "closed",
                    "join": "whole" if any(whole in w.lower() for w in kept) else "closed",
                    "short": min(len(before), len(after)) < 3,
                }
            )

out = Path("work/probes/chain-breaks.jsonl")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print(f"{len(rows)} chain breaks with a one-way reference")
tally = Counter((r["short"], r["truth"], r["join"]) for r in rows)
for k in sorted(tally, key=str):
    print("  short" if k[0] else "  long ", "truth", k[1], "join", k[2], tally[k])
for r in rows:
    if r["truth"] != r["join"]:
        print("  wrong:", r["book"][:24], r["chain"], "truth", r["truth"], "short" * r["short"])
