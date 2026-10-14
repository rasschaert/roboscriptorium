"""The page readers' readings of every page the trust data and the tuning and validation
benches build, read ahead into each book's stage caches (`pagereader.page_readings`), so
the builds after it only judge. Scans only; a page read already is skipped. Never the
test set.

    uv run python experiments/read_pages.py [book …]
"""

import sys
from pathlib import Path

from roboscriptorium import bench, ocrcheck, pagereader
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.trustdata import SPECS


def ranges() -> dict[str, set[int]]:
    """Each book's pages: its trust-data slice and its bench slice together."""
    out: dict[str, set[int]] = {}
    specs = [f"{n}:{s}" if s else n for n, s in SPECS.items() if s != "answers"]
    for spec in specs + bench.SETS["tuning"] + bench.SETS["validation"]:
        name, *rest = spec.split(":")
        book = Book.load(Path("work") / name)
        lo, hi = scoring.page_range(rest[0]) if rest and rest[0] else book.body_pages
        out.setdefault(name, set()).update(range(lo, hi + 1))
    return out


if __name__ == "__main__":
    settings = Settings.from_env()
    chosen = sys.argv[1:]
    for name, pages in ranges().items():
        if chosen and name not in chosen:
            continue
        book = Book.load(Path("work") / name)
        if not ocrcheck.scanned(book.source):
            continue
        for reader, model in (("glm-page", settings.ocr_model), ("qwen-page", settings.read_model)):
            cache = book.stages / f"page-reading-{reader}.json"
            pagereader.page_readings(book.source, sorted(pages), model, settings.ollama_url, cache)
            print(f"{name[:40]:40} {reader:9} {len(pages):4} pages", flush=True)
