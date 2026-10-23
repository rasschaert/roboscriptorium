"""Line crops and their printed text from the tuning books' bench slices, for training a
character recogniser with no language model (Kraken) as a witness that fails differently
(the deep-research reports, 2026-10-23). No models: warm text layers and the references.

    uv run python experiments/kraken_lines.py [book …]

Each body line whose reference words align to it, not broken over a line end and close to
what the text layer reads (so the crop shows the truth), is written as
~/models/roboscriptorium/kraken/lines/<book>/<page>_<line>.png with <page>_<line>.gt.txt
beside it (out of the project: ~1.4 GB, and the project folder is backed up hourly), cut
as the OCR check cuts it (`readers._line_crop`). Lines of the frozen reader set are written
too; `kraken_eval.py` keeps them out of training by book.
"""

import sys
from pathlib import Path

import pymupdf
from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).parent))
from tryout import _beside_break, _shifted, fold, slice_of  # noqa: E402

from roboscriptorium import bench, disagreements, readers  # noqa: E402
from roboscriptorium.golden import scoring  # noqa: E402
from roboscriptorium.golden.align import align  # noqa: E402
from roboscriptorium.golden.manifest import Golden  # noqa: E402
from roboscriptorium.golden.reference import load_chapters  # noqa: E402
from roboscriptorium.pdf import cached_text_layer  # noqa: E402

OUT = Path.home() / "models/roboscriptorium/kraken/lines"
CLOSE = 0.85

if __name__ == "__main__":
    wanted = set(sys.argv[1:])
    for spec in bench.SETS["tuning"]:
        book, (first, last), chapters = slice_of(spec)
        name = book.root.name
        if wanted and name not in wanted:
            continue
        pages = [
            p
            for p in cached_text_layer(book.source, book.stages / "textlayer.json")
            if first <= p.number <= last
        ]
        reference = load_chapters(Golden.load(book.golden).text_dir)
        if chapters:
            reference = reference[chapters[0] - 1 : chapters[1]]
        reference, _ = disagreements.patch(reference, scoring.verdicts(book))
        labels = align(pages, reference)
        out = OUT / name
        out.mkdir(parents=True, exist_ok=True)
        made = 0
        with pymupdf.open(book.source) as doc:
            for page in pages:
                boxes = None
                for k, line in enumerate(page.lines):
                    lab = labels.get(readers.SourceRef(page.number, k))
                    if lab is None or lab.role != "body" or not lab.truth.strip():
                        continue
                    if _beside_break(page.lines, k) or _shifted(line.text, lab.truth):
                        continue
                    if Levenshtein.normalized_similarity(fold(line.text), fold(lab.truth)) < CLOSE:
                        continue
                    if boxes is None:
                        boxes = readers.line_boxes(doc[page.number - 1], page)
                    png = readers._line_crop(
                        doc, page.number, boxes[k], readers.crop_span(boxes, k)
                    )
                    stem = out / f"{page.number}_{k}"
                    stem.with_suffix(".png").write_bytes(png)
                    stem.with_suffix(".gt.txt").write_text(lab.truth.strip() + "\n")
                    made += 1
        print(f"{name[:40]:40} {made:5} lines", flush=True)
