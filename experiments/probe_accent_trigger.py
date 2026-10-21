"""The accent trigger over whole books: lines flagged for an odd mark over a narrow stem, against the
lines the aligned reference says hold an accented i. No models (warm builds for the line boxes).

    uv run python experiments/probe_accent_trigger.py

Per book, each body line is cut from its PDF as the readers cut it, its marks measured as in
`probe_idot_shape.py`, the book's own distribution of marks taken from all its lines (median and
spread, so the few accents don't move it), and each line scored by its oddest mark. Reported: the
AUC, and at several thresholds the lines flagged, the accented lines among them and the share of
accented lines found.
"""

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from probe_idot_shape import marks  # noqa: E402

from roboscriptorium import bench, pipeline, readers
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.disagreements import patch
from roboscriptorium.golden import notes as golden_notes
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef

BOOKS = ["het-schaduwhuis--ia-scan", "het-heft-in-eigen-hand--ia-scan", "vals-alarm--ia-scan"]
ACCENTED = set("íìÍÌ")
THRESHOLDS = (3, 4, 5, 6, 8)


def lines_of(name: str):
    spec = next(x for x in bench.SETS["tuning"] if x.split(":")[0] == name)
    _, pages, chapters = (spec.split(":") + ["", ""])[:3]
    book = Book.load(Path("work") / name)
    stages = pipeline.run(
        book, pages=scoring.page_range(pages or None), settings=replace(Settings.from_env(), ocr_trust=False)
    )
    golden = Golden.load(book.golden)
    reference = load_chapters(golden.text_dir)
    if span := scoring.page_range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = patch(reference, scoring.verdicts(book))
    truth = align(stages.pages, reference)
    in_notes = golden_notes.note_lines(stages.pages, golden_notes.load(golden.notes_path))
    with pymupdf.open(book.source) as doc:
        for page in stages.pages:
            boxes = readers.line_boxes(doc[page.number - 1], page)
            for k in range(len(page.lines)):
                t = truth.get(SourceRef(page.number, k))
                if t is None or t.role != "body" or SourceRef(page.number, k) in in_notes:
                    continue
                png = readers._line_crop(doc, page.number, boxes[k], readers.crop_span(boxes, k))
                yield page.number, k, bool(set(t.truth) & ACCENTED), marks(png)


if __name__ == "__main__":
    for name in BOOKS:
        rows = list(lines_of(name))
        allmarks = np.array([m for _, _, _, ms in rows for m in ms])
        centre = np.median(allmarks, 0)
        spread = np.median(np.abs(allmarks - centre), 0) * 1.4826 + 1e-6
        scored = [
            (max((float(np.abs((np.array(m) - centre) / spread).max()) for m in ms), default=0.0), pos)
            for _, _, pos, ms in rows
        ]
        positives = [s for s, pos in scored if pos]
        negatives = [s for s, pos in scored if not pos]
        auc = np.mean([(p > n) + 0.5 * (p == n) for p in positives for n in negatives]) if positives else float("nan")
        print(f"{name[:30]}: {len(rows)} lines, {len(allmarks)} marks, {len(positives)} lines with an accented i; AUC {auc:.2f}")
        for t in THRESHOLDS:
            flagged = [pos for s, pos in scored if s >= t]
            hit = sum(flagged)
            print(f"   score >= {t}: {len(flagged):4} lines flagged, {hit:3} accented ({hit / max(1, len(flagged)):.0%} of them), "
                  f"{hit / max(1, len(positives)):.0%} of the accented lines found")
