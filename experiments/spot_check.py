"""A spot-check of a built book: five random pages of its text proper, each scan beside the
paragraphs the build made of it, for a person to mark every wrong word, break and italic.

The pages are drawn from the text proper, seeded by the book's name, so a rerun shows the
same ones; pages with a picture or no text are drawn past. Reads the last build's
document (`stages/document.json`), so build first. No models.

    uv run python experiments/spot_check.py work/hoe-wij-verdwijnen [pages]

Writes work/probes/spot-check/<book>/index.html: open it in a browser.
"""

import base64
import html
import json
import random
import sys
from pathlib import Path

import pymupdf

from roboscriptorium.book import Book

PAGES = 5
DPI = 110


def _paragraphs(doc: dict, page: int) -> list[dict]:
    return [b for b in doc["blocks"] if any(s["page"] == page for s in b.get("sources", []))]


def _text(block: dict) -> str:
    words = block["text"].split(" ")
    italic = set(block.get("italic", []))
    out = [f"<i>{html.escape(w)}</i>" if k in italic else html.escape(w) for k, w in enumerate(words)]
    text = " ".join(out)
    if "parts" in block:
        return f"<h3>{text}</h3>"
    kind = " epigraph" if block.get("epigraph") else " dedication" if block.get("dedication") else ""
    return f'<p class="{kind.strip()}">{text}</p>'


def main(book_dir: str, n: int = PAGES) -> None:
    book = Book.load(Path(book_dir))
    doc = json.loads((book.stages / "document.json").read_text())
    first, last = book.body_pages
    with_text = [p for p in range(first, last + 1) if _paragraphs(doc, p)]
    chosen = sorted(random.Random(book.root.name).sample(with_text, min(n, len(with_text))))
    out = Path("work/probes/spot-check") / book.root.name
    out.mkdir(parents=True, exist_ok=True)
    sections = []
    with pymupdf.open(book.source) as pdf:
        for p in chosen:
            png = pdf[p - 1].get_pixmap(dpi=DPI).tobytes("png")
            image = base64.b64encode(png).decode()
            text = "\n".join(_text(b) for b in _paragraphs(doc, p))
            sections.append(
                f'<section><h2>PDF page {p}</h2><div class="pair">'
                f'<img src="data:image/png;base64,{image}" alt="scan of PDF page {p}">'
                f'<div class="text">{text}</div></div></section>'
            )
    page = f"""<!doctype html><html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spot-check</title><style>
:root {{ --bg: #fbfaf7; --fg: #1d1d1b; --muted: #6b6b66; --line: #ddd8cc; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #1b1b19; --fg: #e8e6e0; --muted: #a09d94; --line: #3a3833; }} }}
body {{ background: var(--bg); color: var(--fg); font: 17px/1.55 Georgia, serif; margin: 0 16px; }}
header {{ max-width: 70em; margin: 1.5em auto; }} header p {{ color: var(--muted); }}
section {{ max-width: 70em; margin: 2em auto; border-top: 1px solid var(--line); }}
.pair {{ display: flex; gap: 2em; align-items: flex-start; flex-wrap: wrap; }}
.pair img {{ max-width: 100%; width: 30em; border: 1px solid var(--line); }}
.text {{ flex: 1; min-width: 18em; }} .text p {{ margin: 0 0 0.6em; }}
.epigraph, .dedication {{ margin-left: 2em; color: var(--muted); }}
</style></head><body><header><h1>{html.escape(book.title)}: spot-check</h1>
<p>{len(chosen)} random pages of the text proper. On each, compare the scan with the
paragraphs beside it and count every wrong word (a letter, accent, mark or space), every
paragraph break that is wrong or missing, and every italic word set wrong. A paragraph
shown here may run onto the next page or start on the one before: judge only the words on
this scan. Tell me the counts per page, with a word or two about each.</p></header>
{''.join(sections)}</body></html>"""
    (out / "index.html").write_text(page)
    print(f"pages {chosen}: {out / 'index.html'}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else PAGES)
