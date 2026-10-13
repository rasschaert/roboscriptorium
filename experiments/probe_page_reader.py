"""Can a vision model read a whole page into structured text? Each chosen golden page is
read whole by each model and scored, beside the pipeline's own output for the page,
against the reference: wrong words and paragraph breaks set wrong.

A page's reference is the stretch of reference words its text-layer lines align to
(`golden.align`); the pipeline's is the stretch of its document aligned to that. Words
split over the page's edges count against every side alike. Running heads, page
numbers and a picture's garbled reading count as wrong words wherever they're kept.

    uv run python experiments/probe_page_reader.py [model …]
    PROBE_ONLY=dolittle:27 uv run python experiments/probe_page_reader.py   # one page

Readings cached in work/probes/page-reader/<model>/<book>-<page>.txt.
"""

import base64
import os
import re
import sys
import time
from pathlib import Path

import httpx
from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench, pdf
from roboscriptorium.config import Settings
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.golden.reference import unmarked
from roboscriptorium.ir import Heading, Paragraph

# Tuning books only: plain Dutch and English prose, chapter openings, scene breaks,
# running heads, Dolittle's plates and captions, old typography.
PAGES = {
    "goede-dochter--ia-scan:9-99:1-6": [9, 30, 31, 55],
    "reis-om-mijn-schedel--ia-scan:9-97:1-10": [20, 24, 40],
    "the-story-of-doctor-dolittle--stokes-1920:23-88:1-7": [27, 32, 46, 51, 70],
    "monterosso-mon-amour--ia-scan:1-88:1-22": [10, 33],
    "metro-2033--ia-scan:9-94:1-2": [20, 60],
    "the-nature-of-a-crime--doubleday-1924:1-94:1-8": [37, 53],
    "de-eerlijke-vinder--ia-scan:1-84:1-4": [30],
}
OUT = Path("work/probes/page-reader")
BREAK = "¶"

PROMPT = (
    "Transcribe this printed book page exactly as printed: the same words, spelling, "
    "accents and punctuation, including the print's own quote marks and dashes. Leave out "
    "page numbers, running heads and any text inside pictures. Write a picture's caption "
    "as its own paragraph. Join a word the print breaks over a line end with a hyphen "
    "into one word; keep a hyphen that belongs to the word. Separate paragraphs with one "
    "blank line; within a paragraph write the text as one line. Mark a chapter heading "
    "with '# '. Output only the transcription."
)


def specs() -> dict[str, list[int]]:
    """The chosen pages under the bench's own slice for each book."""
    by_name = {s.split(":")[0]: s for s in bench.SETS["tuning"]}
    out = {}
    only = os.environ.get("PROBE_ONLY", "")
    for spec, pages in PAGES.items():
        name = spec.split(":")[0]
        if only:
            book, page = only.rsplit(":", 1)
            if book not in name:
                continue
            pages = [int(page)]
        out[by_name[name]] = pages
    return out


def read_page(model: str, png: bytes, url: str) -> tuple[str, float]:
    glm = model.startswith("glm-ocr")
    payload = {
        "model": model,
        "prompt": "Text Recognition:" if glm else PROMPT,
        "images": [base64.b64encode(png).decode()],
        "stream": False,
        "think": False,
        # glm-ocr runs on llama.cpp's four slots, which share the app's 8k context: a
        # smaller image and output keep one request inside its ~2k.
        "options": {"temperature": 0, "num_predict": 900 if glm else 1500},
    }
    if glm:
        payload.pop("think")
    start = time.time()
    resp = httpx.post(f"{url}/api/generate", json=payload, timeout=900)
    resp.raise_for_status()
    return resp.json()["response"], time.time() - start


def once(text: str) -> str:
    """The text up to where it starts over: glm-ocr's Ollama template has no stop token,
    so after the page it reads it again."""
    head = text.strip()[:60]
    again = text.find(head, len(head)) if len(head) >= 20 else -1
    return text[:again] if again > 0 else text


def tokens_of_markdown(text: str) -> list[str]:
    """Words and paragraph breaks of a model's page: blank lines and headings break."""
    text = once(text)
    out: list[str] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        joined = ""
        for ln in lines:
            ln = re.sub(r"^#+\s*", "", ln)
            if joined.endswith("-") and ln[:1].islower():
                joined = joined[:-1] + ln
            else:
                joined = f"{joined} {ln}".strip()
        joined = re.sub(r"[*_]{1,2}(\S[^*_]*?)[*_]{1,2}", r"\1", joined)
        out += normalise(joined).split() + [BREAK]
    return out


def stream_of_reference(chapters) -> list[str]:
    out: list[str] = []
    for ch in chapters:
        if ch.heading.strip():
            out += normalise(ch.heading).split() + [BREAK]
        for p in ch.paragraphs:
            out += normalise(unmarked(p)).split() + [BREAK]
    return out


def stream_of_doc(doc) -> list[str]:
    out: list[str] = []
    for b in doc.blocks:
        if isinstance(b, (Paragraph, Heading)) and b.text.strip():
            out += normalise(b.text).split() + [BREAK]
    return out


def words_only(stream: list[str]) -> tuple[list[str], list[int]]:
    """The stream's words and each one's position in it."""
    pos = [i for i, t in enumerate(stream) if t != BREAK]
    return [stream[i] for i in pos], pos


def trim(tokens: list[str]) -> list[str]:
    while tokens and tokens[0] == BREAK:
        tokens = tokens[1:]
    while tokens and tokens[-1] == BREAK:
        tokens = tokens[:-1]
    return tokens


def score(got: list[str], want: list[str]) -> tuple[int, int]:
    """Wrong words and paragraph breaks set wrong, `got` against `want`."""
    words = breaks = 0
    for op in Levenshtein.opcodes(got, want):
        if op.tag == "equal":
            continue
        a, b = got[op.src_start : op.src_end], want[op.dest_start : op.dest_end]
        breaks += abs(a.count(BREAK) - b.count(BREAK))
        words += max(len(a) - a.count(BREAK), len(b) - b.count(BREAK))
    return words, breaks


def page_spans(stages, reference_words: list[str]) -> dict[int, tuple[int, int]]:
    """Each page's first and last reference word (indices into `reference_words`)."""
    labels = align(stages.pages, scoring_chapters[0])
    words, owner = [], []
    for page in stages.pages:
        for k, _ in enumerate(page.lines):
            t = labels.get(_ref(page.number, k))
            if t is None or t.role == "other":
                continue
            for w in normalise(t.truth).split():
                words.append(w)
                owner.append(page.number)
    spans: dict[int, list[int]] = {}
    for op in Levenshtein.opcodes(words, reference_words):
        if op.tag != "equal":
            continue
        for k in range(op.src_end - op.src_start):
            p = owner[op.src_start + k]
            j = op.dest_start + k
            lo, hi = spans.get(p, (j, j))
            spans[p] = (min(lo, j), max(hi, j))
    return spans


def _ref(page, line):
    from roboscriptorium.ir import SourceRef

    return SourceRef(page, line)


scoring_chapters: list = [None]

if __name__ == "__main__":
    models = sys.argv[1:] or ["qwen3.8:27b-nvfp4", "glm-ocr:bf16"]
    settings = Settings.from_env()
    totals = {m: [0, 0, 0.0, 0] for m in ["pipeline", *models]}
    for spec, pages in specs().items():
        name = spec.split(":")[0]
        run = scoring.build(f"work/{spec}", bench.unseen(settings, name))
        scoring_chapters[0] = run.reference
        ref_stream = stream_of_reference(run.reference)
        ref_words, ref_pos = words_only(ref_stream)
        doc_stream = stream_of_doc(scoring.scored(run.book, run.stages))
        doc_words, doc_pos = words_only(doc_stream)
        # Reference word index → pipeline word index, through their equal stretches.
        to_doc: dict[int, int] = {}
        for op in Levenshtein.opcodes(ref_words, doc_words):
            if op.tag == "equal":
                for k in range(op.src_end - op.src_start):
                    to_doc[op.src_start + k] = op.dest_start + k
        spans = page_spans(run.stages, ref_words)
        for page in pages:
            if page not in spans:
                print(f"{name[:28]} p{page}: no reference stretch")
                continue
            lo, hi = spans[page]
            want = trim(ref_stream[ref_pos[lo] : ref_pos[hi] + 1])
            d_lo = next((to_doc[j] for j in range(lo, hi + 1) if j in to_doc), None)
            d_hi = next((to_doc[j] for j in range(hi, lo - 1, -1) if j in to_doc), None)
            row = [f"{name[:28]:28} p{page:<4} ref {len(want):4}"]
            if d_lo is not None and d_hi is not None:
                got = trim(doc_stream[doc_pos[d_lo] : doc_pos[d_hi] + 1])
                w, b = score(got, want)
                totals["pipeline"][0] += w
                totals["pipeline"][1] += b
                totals["pipeline"][3] += 1
                row.append(f"pipeline {w:3}w {b:2}b")
            for m in models:
                pixels = 700_000 if m.startswith("glm-ocr") else 1_600_000
                png = pdf.render_png(run.book.source, page, max_pixels=pixels)
                cache = OUT / m.replace(":", "_") / f"{name}-{page}.txt"
                if cache.exists():
                    text, secs = cache.read_text(), 0.0
                else:
                    try:
                        text, secs = read_page(m, png, settings.ollama_url)
                    except httpx.HTTPError as e:
                        row.append(f"{m.split(':')[0]} failed ({e.__class__.__name__})")
                        continue
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text(text)
                w, b = score(trim(tokens_of_markdown(text)), want)
                totals[m][0] += w
                totals[m][1] += b
                totals[m][2] += secs
                totals[m][3] += 1
                row.append(f"{m.split(':')[0]} {w:3}w {b:2}b {secs:4.0f}s")
            print("  ".join(row), flush=True)
    print()
    for m, (w, b, secs, n) in totals.items():
        print(f"{m:22} pages {n:3}  wrong words {w:5}  breaks wrong {b:4}  {secs / max(1, n):5.0f} s/page")
