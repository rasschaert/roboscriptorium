"""Probe: NuExtract reads a book's front pages (title page, colophon) into metadata.

Each page before the body goes to the model as an image with a JSON template of
the fields wanted; the answers per page are printed for comparison with what's
known of the edition (book.toml, the golden manifests).

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

MODEL = "numind/nuextract3:latest"
TEMPLATE = {
    "title": "verbatim-string",
    "subtitle": "verbatim-string",
    "authors": ["verbatim-string"],
    "translators": ["verbatim-string"],
    "original_title": "verbatim-string",
    "original_language": "string",
    "publisher": "verbatim-string",
    "place_of_publication": "verbatim-string",
    "year": "integer",
    "edition_or_printing": "verbatim-string",
    "isbn": "verbatim-string",
    "series": "verbatim-string",
}
MAX_FRONT_PAGES = 8


def extract(png: bytes) -> tuple[dict | str, float]:
    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "messages": [
            {"role": "template", "content": json.dumps(TEMPLATE)},
            {"role": "user", "content": "", "images": [base64.b64encode(png).decode()]},
        ],
    }
    t = time.time()
    resp = httpx.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=600)
    out = resp.json().get("message", {}).get("content") if resp.is_success else resp.text
    try:
        return json.loads(out), time.time() - t
    except (TypeError, json.JSONDecodeError):
        return str(out)[:300], time.time() - t


def main() -> None:
    for root in sys.argv[1:]:
        book = Book.load(Path(root))
        first = book.body_pages[0]
        pages = range(1, min(first, MAX_FRONT_PAGES + 1))
        print(f"== {book.root.name}: {book.title} / {book.author} (front pages {list(pages)})")
        for n in pages:
            found, seconds = extract(render_png(book.source, n))
            if isinstance(found, dict):
                found = {k: v for k, v in found.items() if v not in (None, "", [])}
            print(f"  p{n} ({seconds:.0f}s): {found}")


if __name__ == "__main__":
    main()
