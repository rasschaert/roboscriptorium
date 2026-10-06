"""Probe: a second OCR reading finds suspect words, a vision decision model picks the right one.

Tesseract reads each page image with word boxes; its words are gathered into
the text layer's lines. The two readings of a line are compared character by
character, and each difference, widened to whole words, is a suspect. Its crop
goes to the role model (clef) with both readings as options. The truth for a
suspect is the reading whose version of the line is closer to the line's
best-matching stretch of the golden reference.

    uv run python experiments/probe_ocr_check.py work/the-story-of-doctor-dolittle--stokes-1920 30-49
"""

import csv
import io
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from roboscriptorium.book import Book
from roboscriptorium.clients import ollaya
from roboscriptorium.config import Settings
from roboscriptorium.evaluate import _FOLD, normalise
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.pdf import cached_text_layer

DPI = 300
CROP_ZOOM = 4
CROP_PAD = 4  # points around the suspect words
SURE = 0.8


def tesseract_words(page: pymupdf.Page) -> list[tuple[str, pymupdf.Rect]]:
    png = page.get_pixmap(dpi=DPI).tobytes("png")
    out = subprocess.run(
        ["tesseract", "-", "-", "-l", "eng", "tsv"], input=png, capture_output=True, check=True
    ).stdout.decode()
    scale = 72 / DPI
    words = []
    for row in csv.DictReader(io.StringIO(out), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        if row["level"] == "5" and text:
            x, y, w, h = (int(row[k]) * scale for k in ("left", "top", "width", "height"))
            words.append((text, pymupdf.Rect(x, y, x + w, y + h)))
    return words


def by_line(bands: list[pymupdf.Rect], words) -> list[list[tuple[str, pymupdf.Rect]]]:
    """Words per visual line: the line band (widened a little) that holds the word's centre."""
    out = [[] for _ in bands]
    for text, r in words:
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        for k, band in enumerate(bands):
            if band.x0 - 3 <= cx <= band.x1 + 3 and band.y0 - 2 <= cy <= band.y1 + 2:
                out[k].append((text, r))
                break
    return [sorted(ws, key=lambda w: w[1].x0) for ws in out]


def word_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Widen [start, end) to whole space-separated words."""
    while start > 0 and text[start - 1] != " ":
        start -= 1
    while end < len(text) and text[end] != " ":
        end += 1
    return start, end


def suspects(ours: str, theirs: str) -> list[tuple[int, int, int, int]]:
    """Differing stretches as (our start, our end, their start, their end), whole words."""
    spans = []
    for op in Levenshtein.opcodes(ours.translate(_FOLD), theirs.translate(_FOLD)):
        if op.tag == "equal":
            continue
        a = word_span(ours, op.src_start, op.src_end)
        b = word_span(theirs, op.dest_start, op.dest_end)
        if spans and a[0] <= spans[-1][1]:
            prev = spans.pop()
            a, b = (prev[0], max(prev[1], a[1])), (prev[2], max(prev[3], b[1]))
        spans.append((*a, *b))
    return [s for s in spans if ours[s[0] : s[1]].strip() != theirs[s[2] : s[3]].strip()]


def main() -> None:
    book = Book.load(Path(sys.argv[1]))
    first, last = (int(v) for v in sys.argv[2].split("-"))
    reference = normalise(
        " ".join(
            p for ch in load_chapters(Golden.load(book.golden).text_dir) for p in ch.paragraphs
        )
    )
    settings = Settings.from_env()
    client = ollaya.for_model(settings.role_model, settings.ollaya_url, settings.ollama_url)

    tally: Counter = Counter()
    seconds = []
    layer = {p.number: p for p in cached_text_layer(book.source, book.stages / "textlayer.json")}
    with pymupdf.open(book.source) as doc:
        for n in range(first, last + 1):
            page = doc[n - 1]
            bands = [pymupdf.Rect(ln.x0, ln.y0, ln.x1, ln.y1) for ln in layer[n].lines]
            ours_words = [(w[4], pymupdf.Rect(w[:4])) for w in page.get_text("words")]
            lines = by_line(bands, ours_words)
            theirs_by_line = by_line(bands, tesseract_words(page))
            for words, tess in zip(lines, theirs_by_line, strict=True):
                if not words:
                    continue
                ours = " ".join(t for t, _ in words)
                theirs = " ".join(t for t, _ in tess)
                tally["lines"] += 1
                if len(ours) < 12 or not theirs:
                    continue
                align = fuzz.partial_ratio_alignment(normalise(ours), reference)
                if align.score < 80:
                    tally["line not in reference"] += 1
                    continue
                target = reference[max(0, align.dest_start - 3) : align.dest_end + 3]
                for a0, a1, b0, b1 in suspects(ours, theirs):
                    ours_part, theirs_part = ours[a0:a1], theirs[b0:b1]
                    tally["suspects"] += 1
                    swapped = ours[:a0] + theirs_part + ours[a1:]
                    d_ours = Levenshtein.distance(normalise(ours), target)
                    d_theirs = Levenshtein.distance(normalise(swapped), target)
                    truth = "a" if d_ours < d_theirs else "b" if d_theirs < d_ours else None
                    # Boxes of our words in the span.
                    k0 = ours[:a0].count(" ")
                    k1 = k0 + ours[a0:a1].strip().count(" ") + 1
                    box = pymupdf.Rect(words[k0][1])
                    for _, r in words[k0:k1]:
                        box |= r
                    clip = box + (-CROP_PAD, -CROP_PAD, CROP_PAD, CROP_PAD)
                    png = page.get_pixmap(
                        matrix=pymupdf.Matrix(CROP_ZOOM, CROP_ZOOM), clip=clip
                    ).tobytes("png")
                    question = {
                        "reading": ollaya.choice(
                            "The image is cut from a scanned printed book. Which text does it "
                            "show, letter for letter, including quote marks, dashes and "
                            "punctuation?",
                            {
                                "a": f"exactly “{ours_part}”",
                                "b": f"exactly “{theirs_part}”",
                                "neither": "something else",
                            },
                        )
                    }
                    start = time.monotonic()
                    answer = client.decide(
                        {"readings": [ours_part, theirs_part]}, question, image_png=png
                    )["reading"]
                    seconds.append(time.monotonic() - start)
                    sure = answer.confidence >= SURE
                    if truth is None:
                        tally["no truth"] += 1
                        verdict = "?"
                    else:
                        tally["with truth"] += 1
                        tally[f"truth {'layer' if truth == 'a' else 'tesseract'}"] += 1
                        right = answer.value == truth
                        tally["clef right"] += right
                        tally["clef sure"] += sure
                        tally["clef sure and right"] += sure and right
                        verdict = "ok" if right else "WRONG"
                    print(
                        f"p{n} {ours_part!r:26} tess {theirs_part!r:26} truth {truth or '-'} "
                        f"clef {answer.value:7} {answer.confidence:.2f} {verdict}"
                    )
    print(dict(tally))
    if seconds:
        print(f"clef: {sum(seconds) / len(seconds):.2f} s per suspect, {len(seconds)} calls")


if __name__ == "__main__":
    main()
