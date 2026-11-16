"""Stress marked on the first vowel only of a pair ("níet", "bóek", "zóu": 41 of the 136
accents Ex-minnaar's text layer lacks, a form `accentmarks.stressed` never draws). Would
drawing it find them without offering every "die" and "niet" whose i has a dot? On a
reviewed book: the mark's fit for that form at the places the built book has it, and at
a sample of plain words with a vowel pair. No models.

    uv run python experiments/probe_accent_first_vowel.py <book dir name> [plain sample]
"""

import json
import random
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pymupdf

from roboscriptorium import accentmarks, ocrcheck, pipeline, readers, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer, page_words
from roboscriptorium.readers import line_words

WORD = re.compile(r"[^\W\d_]+")
PAIR = re.compile(r"(?!ij)[aeiou]{2}", re.I)
ACUTE = "́"


def strip(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


def first_only(word: str) -> list[str]:
    return [
        unicodedata.normalize("NFC", word[: m.start() + 1] + ACUTE + word[m.start() + 1 :])
        for m in PAIR.finditer(word)
    ]


def differ_fit(face, found, ink, marked: str, plain: str) -> float | None:
    """`rendercheck.mark_fit` reworked for a mark that replaces ink (an acute where the i
    has its dot): the scan's cosine with the marked drawing less its cosine with the
    plain one, over the zone where the two drawings differ either way."""
    from scipy.ndimage import binary_dilation
    from scipy.signal import fftconvolve

    from roboscriptorium import rendercheck as rc

    drawn = rc._pair(face, marked, plain)
    if drawn is None:
        return None
    strip_ = np.asarray(rc._picture(ink).filter(rc._BLUR), np.float32)
    best = None
    for stretch in rc.STRETCHES:
        high = max(4, round(drawn[0].shape[0] * found.size / rc.RENDER_PX))
        wide = max(4, round(drawn[0].shape[1] * found.size / rc.RENDER_PX * stretch))
        sized = [np.asarray(rc._spread(rc._picture(g).resize((wide, high)), found.spread).filter(rc._BLUR), np.float32) for g in drawn]
        pad_y, pad_x = max(6, high - strip_.shape[0] + 6), max(6, wide - strip_.shape[1] + 6)
        canvas = np.pad(strip_, ((pad_y, pad_y), (pad_x, pad_x)))
        shared = np.minimum(*sized)
        over = fftconvolve(canvas, shared[::-1, ::-1], mode="valid")
        y, x = np.unravel_index(int(over.argmax()), over.shape)
        score = float(over.max()) / (float((shared * shared).sum()) ** 0.5 + 1e-6)
        if best is None or score > best[0]:
            best = (score, canvas[y : y + high, x : x + wide], sized)
    _, under, (with_mark, without) = best
    zone = np.abs(with_mark - without) > 0.15 * 255
    if zone.sum() < 6 or under.shape != zone.shape:
        return None
    zone = binary_dilation(zone, iterations=3)

    def cos(a, b):
        return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))

    return cos(under[zone], with_mark[zone]) - cos(under[zone], without[zone])


def main():
    name = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    book = Book.load(Path("work") / name)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json")
    whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
    pages = {p.number: p for p in whole}
    judge = pipeline._alarm("render", Settings.from_env(), book, whole)
    doc_ir = json.loads((book.stages / "document.json").read_text())
    marked, plain = [], []
    for block in (b for b in doc_ir["blocks"] if "text" in b):
        scan = [
            (s["page"], s["line"], m.start(), m.end(), m.group())
            for s in block.get("sources", [])
            if s["page"] in pages and s["line"] < len(pages[s["page"]].lines)
            for m in WORD.finditer(pages[s["page"]].lines[s["line"]].text)
        ]
        built = WORD.findall(block["text"])
        match = SequenceMatcher(None, [strip(w[4]).lower() for w in scan], [strip(w).lower() for w in built], autojunk=False)
        for a, b, n in match.get_matching_blocks():
            for i in range(n):
                w, ours = scan[a + i], built[b + i]
                if strip(w[4]) != w[4] or not PAIR.search(w[4]):
                    continue
                if ours == w[4]:
                    plain.append(w)
                elif ours in first_only(w[4]):
                    marked.append((w, ours))
    random.seed(0)
    print(f"{len(plain)} plain words with a vowel pair in the book")
    plain = random.sample(plain, min(size, len(plain)))
    rows, kept = [], []
    with pymupdf.open(book.source) as doc:
        cache = {}

        def fit(w, forms):
            page, k, a0, a1, word = w
            if page not in cache:
                pdf_page = doc[page - 1]
                cache.clear()
                cache[page] = (pdf_page, line_words(page_words(pdf_page, pages[page]), pages[page]), readers.line_boxes(pdf_page, pages[page]))
            pdf_page, words, boxes = cache[page]
            box = ocrcheck._box(words[k], boxes[k], pages[page].lines[k].text, a0, a1)
            got = [f for form in forms if (f := judge.mark(pdf_page, page, box, form, word)) is not None]
            ink = rendercheck.place_ink(pdf_page, box, pages[page])
            two = [] if ink is None else [f for form in forms if (f := differ_fit(judge._face, judge._match, ink, form, word)) is not None]
            if ink is not None and forms and forms[0] in first_only(word):
                for form in forms:
                    if (f := differ_fit(judge._face, judge._match, ink, form, word)) is not None:
                        kept.append({"book": name, "page": page, "word": word, "form": form, "differ": f})
            return (max(got) if got else None, max(two) if two else None)

        for w, ours in sorted(marked):
            before = len(kept)
            rows.append((True, *fit(w, [ours]), *fit(w, accentmarks.stressed(w[4]))))
            for k in kept[before:]:
                k["printed"] = True
        for w in sorted(plain):
            rows.append((False, *fit(w, first_only(w[4])), *fit(w, accentmarks.stressed(w[4])), w[4]))
    Path("work/probes/accent-first-vowel").mkdir(parents=True, exist_ok=True)
    Path(f"work/probes/accent-first-vowel/{name}.jsonl").write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kept))
    labels = ("first vowel only, the mark's fit", "first vowel only, marked less plain", "both vowels, the mark's fit", "both vowels, marked less plain")
    for col, label in enumerate(labels, 1):
        pos = np.array([r[col] for r in rows if r[0] and r[col] is not None])
        neg = np.array([r[col] for r in rows if not r[0] and r[col] is not None])
        print(f"{label}: {len(pos)} printed 'íe'-like marks, {len(neg)} plain words with a vowel pair")
        print("   plain words' quantiles 50/99/99.75:", np.round(np.quantile(neg, [0.5, 0.99, 0.9975]), 2).tolist(), f"; {int((neg >= 0.183).sum())} at 0.183 or more")
        if len(pos):
            print("   marks' quantiles 10/25/50/75/90:", np.round(np.quantile(pos, [0.1, 0.25, 0.5, 0.75, 0.9]), 2).tolist())
            for share in (0.99, 0.9975, 1.0):
                cut = float(np.quantile(neg, share))
                print(f"   cut at {share:.2%} of plain ({cut:.2f}): finds {int((pos > cut).sum())} of {len(pos)}")
            for cut in np.sort(pos)[[0, len(pos) // 10, len(pos) // 4]]:
                print(f"   cut {cut:.3f}: finds {int((pos >= cut).sum())} of {len(pos)}, offers {int((neg >= cut).sum())} of {len(neg)} plain")
        top = sorted((r for r in rows if not r[0] and r[col] is not None), key=lambda r: -r[col])[:15]
        print("   plain words scoring highest:", [(r[-1], round(r[col], 2)) for r in top])


if __name__ == "__main__":
    main()
