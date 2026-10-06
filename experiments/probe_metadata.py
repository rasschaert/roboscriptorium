"""Probe: NuExtract reads a book's front pages (cover, title page, colophon) into metadata.

All pages before the body go to the model in one request, with a JSON template
of the fields wanted and an instruction to ignore library stamps and
handwriting and to describe this edition rather than the original.

    uv run python experiments/probe_metadata.py work/stella work/lady-into-fox--chatto-1922
"""

import base64
import json
import sys
import time
from pathlib import Path

import httpx

from roboscriptorium.book import Book
from roboscriptorium.pdf import render_png

MODEL = "numind/nuextract3:q6_k"
TEMPLATE = {
    "title": "verbatim-string",
    "authors": ["verbatim-string"],
    "illustrators": ["verbatim-string"],
    "translators": ["verbatim-string"],
    "publisher": "verbatim-string",
    "place_of_publication": "verbatim-string",
    "year": "integer",
    "printing": "verbatim-string",
    "isbn": "verbatim-string",
    "original_title": "verbatim-string",
    "original_language": "string",
    "original_publisher": "verbatim-string",
    "original_year": "integer",
}
INSTRUCTIONS = (
    "These are the first pages of a printed book, in order: perhaps a cover, library stamps, "
    "handwritten inscriptions, a title page and a colophon. Take the book's details from its "
    "printed title page and colophon; ignore library stamps, barcodes and handwriting. publisher, "
    "place_of_publication, year and printing describe this edition (for a translation: the "
    "translation); the original_* fields describe the original edition, if this is a translation."
)
MAX_FRONT_PAGES = 24
PAGE_PIXELS = 500_000


def extract(pngs: list[bytes]) -> tuple[dict | str, float]:
    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.2},
        "messages": [
            {"role": "template", "content": json.dumps(TEMPLATE, indent=4)},
            {"role": "instructions", "content": INSTRUCTIONS},
            {"role": "user", "content": "", "images": [base64.b64encode(p).decode() for p in pngs]},
        ],
    }
    t = time.time()
    resp = httpx.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=900)
    out = resp.json().get("message", {}).get("content") if resp.is_success else resp.text
    try:
        found = json.loads(out)
        return {k: v for k, v in found.items() if v not in (None, "", [])}, time.time() - t
    except (TypeError, json.JSONDecodeError):
        return str(out)[:300], time.time() - t


def main() -> None:
    for root in sys.argv[1:]:
        book = Book.load(Path(root))
        pages = range(1, min(book.body_pages[0], MAX_FRONT_PAGES + 1))
        pngs = [render_png(book.source, n, max_pixels=PAGE_PIXELS) for n in pages]
        found, seconds = extract(pngs)
        print(f"{book.root.name} (pages {pages.start}-{pages.stop - 1}, {seconds:.0f}s): {found}")


if __name__ == "__main__":
    main()
