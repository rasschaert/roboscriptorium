"""A model reading the finished text for technical flaws, scored against the reference.

Builds a golden slice from its caches (fixed rule), asks `model` about the output's
paragraphs a window at a time, and checks each flag: its quote must be in the text
verbatim (else it was invented), and it lands on a remaining difference from the
reference (a catch) or on text that matches it (an editorial urge).

    ROBO_OCR_TRUST=0 uv run python experiments/probe_text_reader.py <spec> <model> [windows]
"""

import json
import re
import sys

import httpx

from roboscriptorium.cli import _questions_and_errors
from roboscriptorium.config import Settings
from roboscriptorium.ir import Paragraph
from roboscriptorium.golden.reference import unmarked

spec, model = sys.argv[1], sys.argv[2]
windows = int(sys.argv[3]) if len(sys.argv) > 3 else 10
WINDOW = 20
KINDS = ["misspelling", "punctuation", "broken sentence", "stray text", "other"]
PROMPT = """Here is part of a chapter of a book, one paragraph per line. See if you can find any \
flaws. We're not asking you to act as an editor and review the prose. We're looking for \
technical errors left by scanning and OCR, such as obvious misspellings (old styles of \
spelling are allowed and should not be treated as an error) or technical mistakes in \
punctuation, a sentence that breaks off, or text that doesn't belong (a page number, a \
running head).

Answer with one flaw per line, as: "<the exact words from the text>" | <kind>
where <kind> is one of: {kinds}. Quote only a few words, exactly as they appear. If there \
are no flaws, answer: none

{text}"""

name, book, stages, reference, errors, found, applied = _questions_and_errors(f"work/{spec}")
paragraphs = [unmarked(b.text) for b in stages.doc.blocks if isinstance(b, Paragraph)]
url = Settings.from_env().ollama_url
flags, invented, catches, urges, caught = 0, [], [], [], set()
for w in range(min(windows, -(-len(paragraphs) // WINDOW))):
    text = "\n".join(paragraphs[w * WINDOW : (w + 1) * WINDOW])
    prompt = PROMPT.format(kinds=", ".join(KINDS), text=text)
    resp = httpx.post(f"{url}/api/generate", timeout=600, json={
        "model": model, "prompt": prompt, "stream": False, "think": False,
        "options": {"temperature": 0, "num_predict": 800}})
    resp.raise_for_status()
    for line in resp.json()["response"].splitlines():
        m = re.match(r'\s*[-*\d.]*\s*"?(.+?)"?\s*\|\s*(.+)', line)
        if not m:
            continue
        flags += 1
        quote, kind = m.group(1), m.group(2).strip()
        at = text.find(quote)
        if at < 0:
            invented.append(quote)
            continue
        hits = [i for i, e in enumerate(errors) if e.got and e.got in text
                and abs(text.find(e.got) - at) < len(quote) + len(e.got)]
        if hits:
            catches.append((quote, kind, errors[hits[0]].got, errors[hits[0]].want))
            caught.update(hits)
        else:
            urges.append((quote, kind))
    print(f"window {w + 1}: {flags} flags so far", file=sys.stderr)

read = min(len(paragraphs), windows * WINDOW)
print(f"{model} on {name}: {read} paragraphs read; {flags} flags: {len(catches)} on a remaining "
      f"difference, {len(urges)} on text that matches the reference, {len(invented)} quoting "
      f"text that isn't there")
print("catches:"); [print(f"  {q!r} ({k}): output {g!r}, reference {w!r}") for q, k, g, w in catches[:15]]
print("editorial urges:"); [print(f"  {q!r} ({k})") for q, k in urges[:25]]
print("invented:"); [print(f"  {q!r}") for q in invented[:10]]
