"""Probe: glm-ocr's own token probabilities as review questions.

Every body line is read by glm-ocr with logprobs (cached under work/probes/). A
word of its reading is unsure when its least likely token has probability below a
threshold. Each line holding an unsure word is a candidate question; per
threshold the probe reports questions per page and how many of the build's
wrong words (`disagreements.find`, verdicts patched in) those questions catch,
next to the review's own questions.

    uv run python experiments/probe_token_confidence.py work/<book> 9-64 1-4
"""

import base64
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pymupdf

from roboscriptorium import disagreements, flags, layout, ocrcheck, pipeline, quality
from roboscriptorium.book import Book
from roboscriptorium.cli import _verdicts
from roboscriptorium.config import Settings
from roboscriptorium.files import write_atomic
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters

book = Book.load(Path(sys.argv[1]))
first, last = map(int, sys.argv[2].split("-"))
chapters = tuple(map(int, sys.argv[3].split("-")))
settings = Settings.from_env()
out_dir = Path("work/probes/token-confidence")
out_dir.mkdir(parents=True, exist_ok=True)
cache_path = out_dir / f"{book.root.name}.json"
cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

stages = pipeline.run(book, pages=(first, last))
pages = stages.pages


def read(png: bytes) -> list[dict]:
    """The reading's tokens up to the first line break, each with its top 3."""
    payload = {
        "model": settings.ocr_model,
        "prompt": "Text Recognition:",
        "images": [base64.b64encode(png).decode()],
        "stream": False,
        "logprobs": True,
        "top_logprobs": 3,
        "options": {"num_predict": ocrcheck.MAX_LINE_TOKENS},
    }
    r = httpx.post(f"{settings.ollama_url}/api/generate", json=payload, timeout=600)
    r.raise_for_status()
    tokens = []
    for t in r.json().get("logprobs", []):
        if "\n" in t["token"]:
            break
        tokens.append(
            {"t": t["token"], "p": math.exp(t["logprob"]),
             "alt": [(a["token"], math.exp(a["logprob"])) for a in t["top_logprobs"][1:]]}
        )
    return tokens


todo = []
with pymupdf.open(book.source) as doc:
    for p in pages:
        boxes = ocrcheck.line_boxes(doc[p.number - 1], p)
        for k, line in enumerate(p.lines):
            key = f"{p.number}:{k}"
            if key not in cache and len(line.text) >= 12:
                todo.append((key, ocrcheck._line_crop(doc, p.number, boxes[k])))
print(f"{len(todo)} lines to read", flush=True)
with ThreadPoolExecutor(ocrcheck.READ_WORKERS) as pool:
    for start in range(0, len(todo), 40):
        batch = todo[start : start + 40]
        for (key, _), tokens in zip(batch, pool.map(lambda kv: read(kv[1]), batch), strict=True):
            cache[key] = tokens
        write_atomic(cache_path, json.dumps(cache, ensure_ascii=False))
        print(f"  {start + len(batch)}/{len(todo)}", flush=True)


def word_minima(tokens: list[dict]) -> list[tuple[str, float, list]]:
    """The reading's words, each with its least likely token's probability and alternatives."""
    words, text, low, alts = [], "", 1.0, []
    for t in tokens:
        if t["t"].startswith(" ") and text:
            words.append((text, low, alts))
            text, low, alts = "", 1.0, []
        text += t["t"].strip()
        if t["p"] < low:
            low, alts = t["p"], t["alt"]
    if text:
        words.append((text, low, alts))
    return words


reference = load_chapters(Golden.load(book.golden).text_dir)[chapters[0] - 1 : chapters[1]]
reference, applied = disagreements.patch(reference, _verdicts(book))
errors = disagreements.find(stages.doc, reference, stages.corrected)
regions = layout.detect(book.source, [p.number for p in pages], book.stages / "layout.json")
asked = flags.find(pages, stages.model_roles, regions, ocrcheck.doubts(stages.suspects))
numbers = [p.number for p in pages if p.lines]
total = sum(quality.size(e) for e in errors)
caught = sum(quality.size(e) for e in errors if any(quality.catches(f, e) for f in asked))
print(f"\n{len(numbers)} pages, {total} wrong words ({applied} verdicts applied)")
print(f"review now: {len(asked) / len(numbers):.2f} questions/page catch {caught}/{total}")

unsure_by_line = {}
for key, tokens in cache.items():
    page, k = map(int, key.split(":"))
    if first <= page <= last:
        unsure_by_line[(page, k)] = min((w[1] for w in word_minima(tokens)), default=1.0)
for threshold in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
    lines = [(pg, k) for (pg, k), low in unsure_by_line.items() if low < threshold]
    qs = [flags.Flag(f"{pg}:{k}", pg, k, k, "", "text", ["ocr-unsure"]) for pg, k in lines]
    hit = sum(quality.size(e) for e in errors if any(quality.catches(f, e) for f in qs))
    both = sum(quality.size(e) for e in errors if any(quality.catches(f, e) for f in qs + asked))
    print(f"unsure < {threshold:4}: {len(qs) / len(numbers):.2f} questions/page catch {hit}/{total};"
          f" with the review's: {both}/{total}")

print("\nwrong words no question catches, with the unsure words on their lines:")
for e in errors:
    if e.lines is None or any(quality.catches(f, e) for f in asked):
        continue
    words = []
    for k in range(e.lines[0], e.lines[1] + 1):
        for w, low, alts in word_minima(cache.get(f"{e.page}:{k}", [])):
            if low < 0.5:
                words.append(f"{w}({low:.2f}; {', '.join(a for a, _ in alts)})")
    print(f"  p{e.page} {e.got!r} → {e.want!r}  [{quality.category(e)}]  {' '.join(words)}")
