"""Both accent measures on a reviewed book of the user's, every accent form: the mark's
own fit (today's) and marked less plain (`probe_accent_first_vowel.differ_fit`), each
word's best form over `accentmarks.stressed` plus the first vowel of a pair alone
("níet"). Labels as in `probe_accent_reviewed.py`: the built book after the user's
answers. A mark counts as found where the best form is the print's and clears the cut. No
models.

    PYTHONPATH=experiments uv run python experiments/probe_accent_differ_reviewed.py <book dir name> [plain sample]
"""

import json
import random
import sys
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pymupdf
from probe_accent_first_vowel import WORD, differ_fit, first_only, strip

from roboscriptorium import accentmarks, ocrcheck, pipeline, readers, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer, page_words
from roboscriptorium.readers import line_words

ACUTES = set("áéíóúÁÉÍÓÚ")


def main():
    name = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
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
                if strip(w[4]) != w[4] or not accentmarks.stressed(w[4]):
                    continue
                if ours == w[4]:
                    plain.append((w, None))
                elif ACUTES & set(ours) and strip(ours) == w[4]:
                    marked.append((w, ours))
    random.seed(0)
    plain = random.sample(plain, min(size, len(plain)))
    rows = []
    with pymupdf.open(book.source) as doc:
        held = {}
        for w, ours in sorted(marked + plain, key=lambda x: x[0]):
            page, k, a0, a1, word = w
            if page not in held:
                held.clear()
                pdf_page = doc[page - 1]
                held[page] = (pdf_page, line_words(page_words(pdf_page, pages[page]), pages[page]), readers.line_boxes(pdf_page, pages[page]))
            pdf_page, words, boxes = held[page]
            box = ocrcheck._box(words[k], boxes[k], pages[page].lines[k].text, a0, a1)
            ink = rendercheck.place_ink(pdf_page, box, pages[page])
            if ink is None:
                continue
            forms = list(dict.fromkeys(accentmarks.stressed(word) + first_only(word)))
            row = {"word": word, "print": ours}
            for key, measure in (("mark", rendercheck.mark_fit), ("differ", differ_fit)):
                scored = [(f, form) for form in forms if (f := measure(judge._face, judge._match, ink, form, word)) is not None]
                row[key] = max(scored) if scored else None
            rows.append(row)
    Path("work/probes").mkdir(exist_ok=True)
    Path(f"work/probes/accent-differ-{name}.json").write_text(json.dumps(rows, ensure_ascii=False))
    for key in ("mark", "differ"):
        pos = [r for r in rows if r["print"] and r[key]]
        neg = np.array([r[key][0] for r in rows if not r["print"] and r[key]])
        print(f"{key}: {len(pos)} accents the layer lacks, {len(neg)} plain words")
        for share in (0.99, 0.995, 0.9975, 0.999):
            cut = float(np.quantile(neg, share))
            right = sum(r[key][0] > cut and r[key][1] == r["print"] for r in pos)
            other = sum(r[key][0] > cut and r[key][1] != r["print"] for r in pos)
            print(f"   cut at {share:.2%} of plain ({cut:.2f}): finds {right} in the print's form, {other} more in another form")


if __name__ == "__main__":
    main()
