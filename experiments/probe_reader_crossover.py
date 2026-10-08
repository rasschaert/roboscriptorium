"""What a candidate line reader adds to the readings the OCR check already has.

For each body line of pages first–last (truth from the aligned reference): which of
the text layer, glm-ocr, tesseract, the read model and each candidate (a cache written
by `probe_line_reader.py`) read it exactly, typography folded. A candidate earns its
place by its unique catches (right where every current reading is wrong) and its
second opinions (right where the read model is wrong); its noise is where it is wrong
and the layer right, which the judges must then overrule.

    uv run python experiments/probe_reader_crossover.py <book dir> <first> <last> <chapters> <candidate cache> …
"""

import hashlib
import json
import sys
from pathlib import Path

import pymupdf

from roboscriptorium import ocrcheck, pdf
from roboscriptorium.book import Book
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef

book_dir, first, last, chapters = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
book = Book.load(book_dir)
layer = pdf.cached_text_layer(book.source, book.stages / "textlayer.json")
pages = [p for p in layer if first <= p.number <= last]
c0, c1 = (int(x) for x in chapters.split("-"))
truth = align(pages, load_chapters(Golden.load(book.golden).text_dir)[c0 - 1 : c1])


def lines_of(path: Path) -> dict[str, str]:
    return json.loads(path.read_text())["lines"]


cached = {
    "glm": lines_of(book.stages / "second-reading.json"),
    "qwen3.8": lines_of(book.stages / "third-reading.json"),
}
candidates = {Path(f).stem.split(f"{first}-{last}-")[-1]: lines_of(Path(f)) for f in sys.argv[5:]}
checked = {SourceRef(p.number, k) for p in pages for k in range(len(p.lines))}
lang = "nld" if book.language == "nl" else "eng"
tess = ocrcheck.tesseract_readings(book.source, pages, checked, lang, book.stages / "tesseract.json")

rows = []
with pymupdf.open(book.source) as doc:
    for p in pages:
        boxes = ocrcheck.line_boxes(doc[p.number - 1], p)
        for k, line in enumerate(p.lines):
            ref = SourceRef(p.number, k)
            t = truth[ref]
            if t.role != "body" or not 0.7 < len(t.truth) / max(1, len(line.text)) < 1.4:
                continue
            text = hashlib.sha1(line.text.encode()).hexdigest()[:10]
            key = f"{p.number}:{k}:{text}:" + ",".join(f"{v:.0f}" for v in boxes[k])
            got = {"layer": line.text, "tess": tess.get(ref, "")}
            got |= {n: c.get(key) for n, c in cached.items()}
            got |= {n: c.get(key) for n, c in candidates.items()}
            if None not in got.values():
                rows.append((t.truth, {n: normalise(v) == normalise(t.truth) for n, v in got.items()}, got))

current = ["layer", "glm", "tess", "qwen3.8"]
print(f"{len(rows)} body lines; exact per reading:",
      ", ".join(f"{n} {sum(r[1][n] for r in rows)}" for n in [*current, *candidates]))
none = [r for r in rows if not any(r[1][n] for n in current)]
print(f"no current reading exact: {len(none)} lines")
for name in candidates:
    unique = [r for r in none if r[1][name]]
    second = [r for r in rows if r[1][name] and not r[1]["qwen3.8"]]
    noise = [r for r in rows if not r[1][name] and r[1]["layer"]]
    print(f"\n{name}: unique catches {len(unique)}, right where qwen3.8 is wrong {len(second)}, "
          f"wrong where the layer is right {len(noise)}")
    for t, _, got in unique[:10]:
        print(f"  truth {t!r}\n    it  {got[name]!r}")
