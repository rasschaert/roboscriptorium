"""A model reading the finished text for technical flaws, then a decision model sorting them.

Builds a golden slice from its caches (fixed rule) and asks `model` about the output's
paragraphs a window at a time (answers cached in work/probes/text-reader/). Each flag's
quote must be in its window verbatim, else it was invented. With `--judge`, a decision
model (clef) then asks of every flag whether it is a fault of scanning or layout or the
author's own text, from the paragraph alone or, with `--crop`, from the scan of the line
too. Flags are scored against the reference: on a remaining difference (a catch) or on
text that matches it (an editorial urge).

    ROBO_OCR_TRUST=0 uv run python experiments/probe_text_reader.py <spec> <model> [windows] [--judge clef:27b] [--crop]
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import httpx
import pymupdf

from roboscriptorium import ocrcheck
from roboscriptorium.cli import _questions_and_errors
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.golden.reference import unmarked
from roboscriptorium.ir import Paragraph

args = [a for a in sys.argv[1:] if not a.startswith("--")]
spec, model = args[0], args[1]
windows = int(args[2]) if len(args) > 2 else 10
judge_model = sys.argv[sys.argv.index("--judge") + 1] if "--judge" in sys.argv else ""
if judge_model in args:
    args.remove(judge_model)
crop = "--crop" in sys.argv
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
blocks = [b for b in stages.doc.blocks if isinstance(b, Paragraph)]
paragraphs = [unmarked(b.text) for b in blocks]
settings = Settings.from_env()
cache = Path("work/probes/text-reader") / f"{name}-{model.replace(':', '-')}.json"
cache.parent.mkdir(parents=True, exist_ok=True)
answers = json.loads(cache.read_text()) if cache.exists() else {}

flags = []  # (window, paragraph index, quote, kind)
invented = []
for w in range(min(windows, -(-len(paragraphs) // WINDOW))):
    text = "\n".join(paragraphs[w * WINDOW : (w + 1) * WINDOW])
    key = hashlib.sha1(text.encode()).hexdigest()[:12]
    if key not in answers:
        prompt = PROMPT.format(kinds=", ".join(KINDS), text=text)
        resp = httpx.post(f"{settings.ollama_url}/api/generate", timeout=600, json={
            "model": model, "prompt": prompt, "stream": False, "think": False,
            "options": {"temperature": 0, "num_predict": 800}})  # fmt: skip
        resp.raise_for_status()
        answers[key] = resp.json()["response"]
        cache.write_text(json.dumps(answers, ensure_ascii=False))
    for line in answers[key].splitlines():
        m = re.match(r'\s*[-*\d.]*\s*"?(.+?)"?\s*\|\s*(.+)', line)
        if not m:
            continue
        quote, kind = m.group(1), m.group(2).strip()
        para = next((i for i in range(w * WINDOW, min(len(paragraphs), (w + 1) * WINDOW))
                     if quote in paragraphs[i]), None)  # fmt: skip
        if para is None:
            invented.append(quote)
        else:
            flags.append((para, quote, kind))


def lands(para: int, quote: str):
    """The remaining difference a flag sits on, if any: one in the same paragraph whose
    output words are inside the quote or overlap it."""
    text = paragraphs[para]
    at = text.find(quote)
    for e in errors:
        if not e.got:
            continue
        g = text.find(e.got)
        while g >= 0:
            if g < at + len(quote) and at < g + len(e.got):
                return e
            g = text.find(e.got, g + 1)
    return None


doc = pymupdf.open(book.source)
pages = {p.number: p for p in stages.pages}


def line_crop(para: int, quote: str) -> bytes | None:
    """The scan of the paragraph's line holding the quote's first word."""
    first = quote.split()[0] if quote.split() else quote
    for ref in blocks[para].sources:
        page = pages.get(ref.page)
        if page and first in page.lines[ref.line].text:
            box = ocrcheck.line_boxes(doc[ref.page - 1], page)[ref.line]
            return ocrcheck._line_crop(doc, ref.page, box)
    return None


QUESTION = {
    "verdict": {
        "type": "choice",
        "instructions": (
            "A reader flagged a place in a book's text as a possible flaw. The text was "
            "made by scanning a printed book and reading it with OCR. Decide whether the "
            "flagged words are a fault of that process (a misread letter or word, a lost "
            "or wrong punctuation mark, a sentence cut off or run together, text that "
            "doesn't belong, like a page number) or the author's own text as printed, "
            "which stays as it is, however unusual: style, fragments, dialect, old "
            "spelling, names and wordplay are the author's."
            + (" The image is the printed line." if crop else "")
        ),
        "criteria": {
            "fault": "a fault of scanning or OCR: the printed book doesn't read like this",
            "authors_text": "the author's own text, as printed: not a fault",
        },
    }
}

judged = []
if judge_model:
    judge = decide.for_model(judge_model, settings.ollama_url)
    for para, quote, kind in flags:
        state = {"language": book.language, "paragraph": paragraphs[para], "flagged": quote,
                 "reader's kind": kind}  # fmt: skip
        image = line_crop(para, quote) if crop else None
        a = judge.decide(state, QUESTION, image_png=image)["verdict"]
        judged.append(a.probabilities.get("fault", 0.0))

hits = [lands(p, q) for p, q, _ in flags]
print(f"{model} on {name}: {min(len(paragraphs), windows * WINDOW)} paragraphs; "
      f"{len(flags) + len(invented)} flags, {len(invented)} quoting text that isn't there, "
      f"{sum(h is not None for h in hits)} on a remaining difference, "
      f"{sum(h is None for h in hits)} on text that matches the reference")
if judged:
    label = f"{judge_model}{' with the line crop' if crop else ''}"
    for cut in (0.3, 0.5, 0.7, 0.9):
        kept = [h for h, p in zip(hits, judged, strict=True) if p >= cut]
        print(f"  {label}, P(fault) ≥ {cut}: keeps {len(kept)}, "
              f"{sum(h is not None for h in kept)} of them on a difference")
    for (para, quote, kind), h, p in sorted(zip(flags, hits, judged, strict=True), key=lambda x: -x[2]):
        mark = "CATCH" if h else "urge "
        print(f"  {p:.2f} {mark} {quote[:70]!r} ({kind})" + (f" -> {h.want!r}" if h else ""))
