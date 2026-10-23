"""A scan's PDF without its hidden text layer, the page images untouched: an image-only
scan of the same pages, to measure what the layer is worth to the build.

    uv run python experiments/strip_text_layer.py <book dir> <new book dir>

Writes <new book dir>/source.pdf and a copy of book.toml; the golden pair's verdicts for
the scan are copied to the new scan's name, since they are about the print, not the layer.
"""

import shutil
import sys
from pathlib import Path

import pymupdf

from roboscriptorium.book import Book
from roboscriptorium.golden.manifest import Golden

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=False)
with pymupdf.open(src / "source.pdf") as doc:
    for page in doc:
        page.add_redact_annot(page.rect)
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=0)
    doc.save(dst / "source.pdf", garbage=3, deflate=True)
with pymupdf.open(dst / "source.pdf") as doc:
    left = sum(len(page.get_text("words")) for page in doc)
print(f"words left in the text layer: {left}")
shutil.copy(src / "book.toml", dst / "book.toml")
verdicts = Golden.load(Book.load(src).golden).verdicts_dir
old, new = (verdicts / f"{d.name.split('--', 1)[-1]}.jsonl" for d in (src, dst))
if old.exists():
    shutil.copy(old, new)
    print(f"verdicts copied: {new}")
