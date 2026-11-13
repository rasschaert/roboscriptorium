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


def _words(line: str) -> int:
    """How many of a paragraph's words a line holds: a word broken at its end counts
    with the next line."""
    return len(line.split()) - line.rstrip().endswith("-")


def _snap(words: list[str], near: int, line: str) -> int:
    """The index in `words` where `line` starts: the place nearest `near` (a count of
    the lines before it) where the line's first words stand, `near` itself where they
    aren't found (a reading the build corrected)."""
    first = line.split()[:3]
    for n in range(len(first), 0, -1):
        hits = [k for k in range(len(words) - n + 1) if words[k : k + n] == first[:n]]
        close = [k for k in hits if abs(k - near) <= 6]
        if close:
            return min(close, key=lambda k: abs(k - near))
    return max(0, min(near, len(words)))


def _on_page(block: dict, page: int, lines: dict[int, list[str]]) -> tuple[int, int]:
    """The run of the block's words that the page prints, as (first, past the last):
    a paragraph begun on the page before or ending on the next shows whole, and only
    this run can be checked against the scan."""
    words = block["text"].split(" ")
    texts = [(s["page"], lines.get(s["page"], [])[s["line"] : s["line"] + 1]) for s in block["sources"]]
    texts = [(p, t[0]) for p, t in texts if t]
    start, end = 0, len(words)
    before = [t for p, t in texts if p < page]
    here = [t for p, t in texts if p == page]
    after = [t for p, t in texts if p > page]
    if before and here:
        start = _snap(words, sum(_words(t) for t in before), here[0])
    if after and here:
        end = _snap(words, sum(_words(t) for t in before + here), after[0])
    return start, max(start, end)


def _text(block: dict, page: int, lines: dict[int, list[str]]) -> str:
    words = block["text"].split(" ")
    italic = set(block.get("italic", []))
    out = [f"<i>{html.escape(w)}</i>" if k in italic else html.escape(w) for k, w in enumerate(words)]
    start, end = _on_page(block, page, lines) if "sources" in block else (0, len(out))
    parts = [(out[:start], True), (out[start:end], False), (out[end:], True)]
    text = " ".join(
        f'<span class="off">{" ".join(run)}</span>' if off else " ".join(run)
        for run, off in parts
        if run
    )
    if "parts" in block:
        return f"<h3>{text}</h3>"
    kind = " epigraph" if block.get("epigraph") else " dedication" if block.get("dedication") else ""
    # A scene break before the paragraph and its first line set flush, as the EPUB has them.
    rule = '<hr class="break">' if block.get("break_before") else ""
    kind += " opening" if block.get("opening") else ""
    return f'{rule}<p class="{kind.strip()}">{text}</p>'


def main(book_dir: str, n: int = PAGES) -> None:
    book = Book.load(Path(book_dir))
    doc = json.loads((book.stages / "document.json").read_text())
    layer = json.loads((book.stages / "text-layer.json").read_text())["pages"]
    lines = {p["number"]: [ln["text"] for ln in p["lines"]] for p in layer}
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
            text = "\n".join(_text(b, p, lines) for b in _paragraphs(doc, p))
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
.text {{ flex: 1; min-width: 18em; }} .text p {{ margin: 0; text-indent: 1.5em; }}
.epigraph, .dedication {{ margin: 0.6em 0 0.6em 2em; text-indent: 0; color: var(--muted); }}
.text .off {{ color: var(--muted); opacity: 0.55; }}
.text hr.break {{ border: 0; height: 1.5em; margin: 0; }} .text p.opening {{ text-indent: 0; }}
</style></head><body><header><h1>{html.escape(book.title)}: spot-check</h1>
<p>{len(chosen)} random pages of the text proper. On each, compare the scan with the
paragraphs beside it and count every wrong word (a letter, accent, mark or space), every
paragraph break that is wrong or missing, and every italic word set wrong. A blank line
here is a scene break the build set. A paragraph
begun on the page before or ending on the next is shown whole, its words from the other
page in grey: judge only the words in black. Tell me the counts per page, with a word or two about each.</p></header>
{''.join(sections)}</body></html>"""
    (out / "index.html").write_text(page)
    print(f"pages {chosen}: {out / 'index.html'}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else PAGES)
