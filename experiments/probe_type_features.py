"""Probe: do a book's heading lines stand apart from its body text by their type?

Per text-layer line on the body pages, measured on the page image: the height
from the tallest letters to the baseline (type size), the dense band's height
(x-height, or cap height in capitals), ink width per letter (letterspacing) and
stroke width (weight), each relative to the book's full-width lines. Lines are
labelled heading when their text matches a reference chapter heading, in order.

    uv run python experiments/probe_type_features.py work/<book> [--pages 9-64] [--chapters 1-4]
"""

import argparse
import json
import re
from pathlib import Path
from statistics import median

import numpy as np
import pymupdf
from rapidfuzz import fuzz

from roboscriptorium.book import Book
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.italics import ink_threshold
from roboscriptorium.page import geometry, sunk_pages
from roboscriptorium.pdf import cached_text_layer, line_words

DPI = 300
# Letters that reach above the x-height: their tops give the type size.
TALL = r"[A-Zbdhkl0-9À-Ý]"
nan = float("nan")

ap = argparse.ArgumentParser()
ap.add_argument("book")
ap.add_argument("--pages")
ap.add_argument("--chapters")
ap.add_argument("--out")
args = ap.parse_args()

book = Book.load(Path(args.book))
first, last = book.body_pages
if args.pages:
    first, last = map(int, args.pages.split("-"))
pages = [
    p
    for p in cached_text_layer(book.source, book.stages / "textlayer.json")
    if first <= p.number <= last
]
chapters = load_chapters(Golden.load(book.golden).text_dir)
if args.chapters:
    a, b = map(int, args.chapters.split("-"))
    chapters = chapters[a - 1 : b]
sunk = sunk_pages(pages)


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-zà-ÿ ]", "", s.lower()).strip()


def measure(gray: np.ndarray, threshold: int) -> dict | None:
    ink = gray < threshold
    rows = ink.sum(axis=1)
    if rows.max(initial=0) < 2:
        return None
    dense = np.nonzero(rows >= 0.4 * rows.max())[0]
    baseline = int(dense.max())
    present = np.nonzero(rows >= max(1, 0.03 * rows.max()))[0]
    top = int(present.min())
    if baseline - top < 3:
        return None
    runs = []
    for r in range(int(dense.min()), baseline + 1):
        row = ink[r].astype(np.int8)
        edges = np.diff(np.concatenate([[0], row, [0]]))
        starts, ends = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]
        runs.extend((ends - starts).tolist())
    return {
        "height": baseline - top,
        "band": len(dense),
        "stroke": float(np.mean(runs)) if runs else float("nan"),
        "inkwidth": int(np.ptp(np.nonzero(ink.any(axis=0))[0]) + 1),
    }


def part_of(t: str, target: str) -> bool:
    """The whole heading, or a line of it ("PUDDLEBY" of "THE FIRST CHAPTER PUDDLEBY")."""
    if not t:
        return False
    if fuzz.ratio(t, target) >= 85:
        return True
    return 4 <= len(t) <= len(target) + 3 and len(t) >= 0.3 * len(target) and fuzz.partial_ratio(t, target) >= 90


lines = []
zoom = DPI / 72
with pymupdf.open(book.source) as doc:
    for page in pages:
        if not page.lines:
            continue
        pdf_page = doc[page.number - 1]
        pix = pdf_page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        gray = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
        threshold = ink_threshold(gray)
        words = line_words(pdf_page.get_text("words"), page)
        full, left = geometry(page)
        for i, (ln, ws) in enumerate(zip(page.lines, words, strict=True)):
            if not ws:
                continue
            per_word = []
            for w in ws:
                x0, y0, x1, y1 = (int(round(v * zoom)) for v in w[:4])
                crop = gray[max(0, y0 - 2) : y1 + 2, max(0, x0 - 1) : x1 + 1]
                if crop.size and (m := measure(crop, threshold)):
                    m["chars"] = len(re.sub(r"\s", "", w[4]))
                    m["tall"] = bool(re.search(TALL, w[4]))
                    m["lower"] = bool(re.search(r"[a-zà-ÿ]", w[4]))
                    per_word.append(m)
            if not per_word:
                continue
            letters = [c for c in ln.text if c.isalpha()]
            chars = sum(m["chars"] for m in per_word)
            lines.append(
                {
                    "page": page.number,
                    "i": i,
                    "text": ln.text,
                    "height": median([m["height"] for m in per_word if m["tall"]] or [nan]),
                    "band": median([m["band"] for m in per_word if m["lower"]] or [nan]),
                    "capband": median(
                        [m["band"] for m in per_word if not m["lower"] and m["tall"]] or [nan]
                    ),
                    "stroke": median(m["stroke"] for m in per_word),
                    "pitch": sum(m["inkwidth"] for m in per_word) / max(1, chars),
                    "caps": sum(c.isupper() for c in letters) / len(letters) if letters else 0.0,
                    "spaced": bool(re.search(r"(?:\b\w ){3,}", ln.text + " ")),
                    "width": (ln.x1 - ln.x0) / full,
                    "y": ln.y0 / page.height,
                    "sunk": page.number in sunk,
                    "full": (ln.x1 - ln.x0) / full >= 0.9,
                }
            )

body = [ln for ln in lines if ln["full"]]
ref = {k: np.nanmedian([ln[k] for ln in body]) for k in ("height", "band", "stroke", "pitch")}
for ln in lines:
    for k in ref:
        ln[f"r_{k}"] = ln[k] / ref[k] if ref[k] else nan

# Label: each reference heading's lines are the first unlabelled lines, at or after
# the previous heading's page, whose text is part of the heading.
pos = 0
for ch in chapters:
    target = norm(ch.heading)
    if not target:
        continue
    for j in range(pos, len(lines)):
        t = norm(lines[j]["text"])
        if part_of(t, target):
            lines[j]["heading"] = ch.heading
            # Lines right below that continue the heading.
            k = j + 1
            while (
                k < len(lines)
                and lines[k]["page"] == lines[j]["page"]
                and part_of(norm(lines[k]["text"]), target)
            ):
                lines[k]["heading"] = ch.heading
                k += 1
            pos = k
            break
    else:
        print(f"  heading not found in the text layer: {ch.heading!r}")

print(f"{book.root.name}: {len(lines)} lines, {len(body)} full-width; body type {ref}")
heads = [ln for ln in lines if "heading" in ln]
print(f"{len(heads)} heading lines for {len(chapters)} reference headings")
fmt = "p{page:<4} {r_height:5.2f} cap {capband:4.0f} {r_band:5.2f} {r_stroke:5.2f} {r_pitch:5.2f} caps {caps:.2f}"
for ln in heads[:40]:
    print(fmt.format(**ln), f"y {ln['y']:.2f} sunk {ln['sunk']!s:5}", repr(ln["text"])[:50])


def distinct(ln: dict) -> bool:
    return (
        abs(ln["r_height"] - 1) > 0.15
        or abs(ln["r_band"] - 1) > 0.25
        or ln["r_stroke"] > 1.3
        or ln["r_pitch"] > 1.4
        or (ln["caps"] > 0.8 and len(ln["text"]) >= 3)
    )


others = [ln for ln in lines if "heading" not in ln and not ln["full"]]
print(
    f"distinct type: headings {sum(map(distinct, heads))}/{len(heads)}, "
    f"other short lines {sum(map(distinct, others))}/{len(others)}"
)
for ln in [o for o in others if distinct(o)][:25]:
    print("  other", fmt.format(**ln), repr(ln["text"])[:50])
if args.out:
    Path(args.out).write_text(json.dumps(lines, ensure_ascii=False))
