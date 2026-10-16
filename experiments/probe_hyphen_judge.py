"""Line-end hyphens the book and the word list leave undecided, asked of decision
models: is the hyphen the word's own ("half-cooked") or the break's ("halfcooked")?
Scored against the tuning books' references where they spell the word one way only,
beside `hyphens.join`'s default (the break's).

    uv run python experiments/probe_hyphen_judge.py [model …]

Answers are cached in work/probes/hyphen-judge/<model>.jsonl.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, hyphens, ocr
from roboscriptorium.book import Book
from roboscriptorium.golden import scoring
from roboscriptorium.clients.decide import DecisionClient, choice
from roboscriptorium.config import Settings
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import cached_text_layer

W = re.compile(r"[^\w-]")
OUT = Path("work/probes/hyphen-judge")
models = sys.argv[1:] or ["clef:27b", "winnow-ollama:e4b", "clef-flash:9b"]
LANG = {"nl": "Dutch", "en": "English"}

items = []
for spec in bench.SETS["tuning"]:
    name, pages, chapters = (spec.split(":") + ["", ""])[:3]
    book = Book.load(Path("work") / name)
    first, last = scoring.page_range(pages or None) or book.body_pages
    lang = ocr.language(book.language)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json", lang)
    layer = [p for p in layer if first <= p.number <= last]
    seen = hyphens.spellings(layer)
    lex = Lexicon.load(lang)
    ref = load_chapters(Golden.load(book.golden).text_dir)
    words = Counter(
        W.sub("", w).lower() for ch in ref for para in ch.paragraphs for w in para.split()
    )
    lines = [line.text for p in layer for line in p.lines]
    for i, (text, nxt) in enumerate(zip(lines, lines[1:])):
        if not (text.endswith(hyphens.HYPHENS) and len(text) > 1 and text[-2].isalpha()):
            continue
        stem = W.sub("", text.split()[-1][:-1])
        rest = W.sub("", nxt.split()[0]) if nxt.split() else ""
        if not stem or not rest or not nxt[:1].islower() or "-" in stem + rest:
            continue
        closed, hyph = stem + rest, f"{stem}-{rest}"
        if seen[hyph.lower()] != seen[closed.lower()] or lex.knows(hyph) != lex.knows(closed):
            continue
        h, c = words[hyph.lower()], words[closed.lower()]
        if bool(h) == bool(c):
            continue
        sentence = " ".join([*lines[max(0, i - 1) : i], text[:-1] + "|" + nxt, *lines[i + 2 : i + 3]])
        items.append(
            {"book": name, "lang": book.language[:2], "closed": closed, "hyphenated": hyph,
             "truth": "hyphenated" if h else "closed", "context": sentence}
        )

print(f"{len(items)} undecided line-end hyphens with a one-way reference:",
      dict(Counter((i["lang"], i["truth"]) for i in items)))

settings = Settings.from_env()
client = DecisionClient(settings.ollama_url, models[0])
OUT.mkdir(parents=True, exist_ok=True)
for model in models:
    path = OUT / f"{model.replace(':', '_').replace('/', '_')}.jsonl"
    cache = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                r = json.loads(line)
                cache[(r["closed"], r["context"])] = r
            except json.JSONDecodeError:
                pass
    score = Counter()
    with path.open("a") as f:
        for it in items:
            key = (it["closed"], it["context"])
            if key not in cache:
                q = choice(
                    f"A {LANG[it["lang"][:2]]} book breaks a word across two lines with a hyphen "
                    "at the line's end (shown as |). Is the hyphen part of the word's "
                    "spelling, or only the line break's? Answer with how the word is spelled "
                    "in running text.",
                    {"closed": f"{it['closed']}", "hyphenated": f"{it['hyphenated']}"},
                )
                a = client.decide({"language": LANG[it["lang"][:2]], "text": it["context"]},
                                  {"spelling": q}, model=model)["spelling"]
                cache[key] = {"closed": it["closed"], "context": it["context"],
                              "choice": a.value, "p_hyph": a.probabilities.get("hyphenated", 0)}
                f.write(json.dumps(cache[key], ensure_ascii=False) + "\n")
                f.flush()
            r = cache[key]
            for t in (0.5, 0.7, 0.9):
                got = "hyphenated" if r["p_hyph"] >= t else "closed"
                score[(it["lang"], t, "right" if got == it["truth"] else f"wrong {got}")] += 1
            score[(it["lang"], "default", "right" if it["truth"] == "closed" else "wrong closed")] += 1
    print(model)
    for k in sorted(score, key=str):
        print("  ", k, score[k])
