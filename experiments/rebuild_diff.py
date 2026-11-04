"""Every word a rebuild changed in a book's text, each beside its scan, for a person to check
by eye: the old and the new words, the lines they sit on cropped from the scan, and a note.

The old build is a dated EPUB; the new one is the book's current `stages/document.json`
and EPUB, so build first. Each changed paragraph is split into its changed runs of words
(italic runs between asterisks, so a word set in another type counts); each run is placed
on the lines that hold it by counting words along the paragraph's source lines, with a
line either side for the slack de-hyphenation leaves. No models.

    uv run python experiments/rebuild_diff.py work/stella work/stella/epubs/<old>.epub [notes.json]

`notes.json` maps a place's number to a note shown beside it (the agent's reading of the
scan). Writes work/probes/rebuild-diff/<book>/index.html: open it in a browser.
"""

import base64
import difflib
import html
import json
import sys
from pathlib import Path

import pymupdf

from roboscriptorium import epubdiff, ocr
from roboscriptorium.book import Book
from roboscriptorium.page import folio
from roboscriptorium.pagekinds import printed_offset
from roboscriptorium.pdf import cached_text_layer

DPI = 150
CONTEXT = 6  # words shown either side of a change
PAD = 4  # points around a crop


def _plain(text: str) -> str:
    return text.replace("*", "")


def _block_for(doc: list[dict], text: str) -> dict | None:
    """The document block whose text is `text` (from the EPUB), or the likeliest one."""
    want = _plain(text)
    exact = [b for b in doc if " ".join(b["text"].split()) == want]
    if exact:
        return exact[0]
    best = max(doc, key=lambda b: difflib.SequenceMatcher(None, b["text"], want).quick_ratio())
    return best


def _runs(old: str, new: str) -> list[tuple[int, int, int, int]]:
    """The changed runs of words, as (old start, old end, new start, new end)."""
    a, b = old.split(), new.split()
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [(a0, a1, b0, b1) for op, a0, a1, b0, b1 in m.get_opcodes() if op != "equal"]


def _lines_for(block: dict, layer: dict, start: int, end: int) -> list[tuple[int, int]]:
    """The (page, line) sources holding words `start` to `end` of the block, a line either
    side."""
    refs = [(s["page"], s["line"]) for s in block.get("sources", []) if not s.get("typed")]
    if not refs:
        return []
    counts, at = [], 0
    for page, line in refs:
        lines = layer[page].lines
        n = len(lines[line].text.split()) if line < len(lines) else 0
        counts.append((at, at + n))
        at += n
    hit = [k for k, (a, b) in enumerate(counts) if a <= max(end - 1, start) and b > start]
    if not hit:
        hit = [len(refs) - 1]
    lo, hi = max(0, hit[0] - 1), min(len(refs) - 1, hit[-1] + 1)
    return refs[lo : hi + 1]


def _crops(doc: pymupdf.Document, layer: dict, refs: list[tuple[int, int]]) -> list[tuple[int, str]]:
    by_page: dict[int, list] = {}
    for page, line in refs:
        by_page.setdefault(page, []).append(layer[page].lines[line])
    out = []
    for page, lines in by_page.items():
        rect = pymupdf.Rect(
            min(ln.x0 for ln in lines) - PAD,
            min(ln.y0 for ln in lines) - PAD,
            max(ln.x1 for ln in lines) + PAD,
            max(ln.y1 for ln in lines) + PAD,
        )
        png = doc[page - 1].get_pixmap(clip=rect, dpi=DPI).tobytes("png")
        out.append((page, base64.b64encode(png).decode()))
    return out


def _snippet(words: list[str], a: int, b: int, cls: str) -> str:
    lo, hi = max(0, a - CONTEXT), min(len(words), b + CONTEXT)
    before = html.escape(" ".join(words[lo:a]))
    changed = html.escape(" ".join(words[a:b])) or "∅"
    after = html.escape(" ".join(words[b:hi]))
    return f'{"… " if lo else ""}{before} <mark class="{cls}">{changed}</mark> {after}{" …" if hi < len(words) else ""}'


def main(book_dir: str, old_epub: str, notes_file: str | None = None) -> None:
    book = Book.load(Path(book_dir))
    notes = json.loads(Path(notes_file).read_text()) if notes_file else {}
    changes = epubdiff.compare(epubdiff.blocks(Path(old_epub)), epubdiff.blocks(book.epub_path))
    doc = json.loads((book.stages / "document.json").read_text())["blocks"]
    pages = cached_text_layer(book.source, book.stages / "textlayer.json", ocr.language(book.language))
    layer = {p.number: p for p in pages}
    offset = printed_offset([p for p in pages if book.body_pages[0] <= p.number <= book.body_pages[1]])
    places = []
    with pymupdf.open(book.source) as pdf:
        for kind, was, now in changes.places:
            block = _block_for(doc, now or was)
            for a0, a1, b0, b1 in _runs(was, now) or [(0, 0, 0, 0)]:
                refs = _lines_for(block, layer, b0, b1) if block else []
                places.append(
                    {
                        "kind": kind,
                        "old": _snippet(was.split(), a0, a1, "old"),
                        "new": _snippet(now.split(), b0, b1, "new"),
                        "plain": (" ".join(was.split()[a0:a1]), " ".join(now.split()[b0:b1])),
                        "crops": _crops(pdf, layer, refs),
                    }
                )
    out = Path("work/probes/rebuild-diff") / book.root.name
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, p in enumerate(places, 1):
        where = ", ".join(
            f"PDF {page}" + (f" (printed {n})" if (n := folio(page, offset)) else "")
            for page, _ in p["crops"]
        )
        imgs = "".join(f'<img src="data:image/png;base64,{b}">' for _, b in p["crops"])
        note = html.escape(notes.get(str(k), ""))
        rows.append(
            f'<section><h2>{k}. {where or "(no place found)"}</h2>'
            f'<div class="t"><div><b>was</b> {p["old"]}</div><div><b>now</b> {p["new"]}</div>'
            f'{f"<div class=n><b>agent</b> {note}</div>" if note else ""}</div>{imgs}</section>'
        )
        print(k, where, repr(p["plain"][0]), "→", repr(p["plain"][1]))
    style = (
        "body{font:16px/1.5 Georgia,serif;max-width:1000px;margin:2em auto;padding:0 16px;"
        "background:#faf8f3;color:#222}section{border-top:1px solid #ccc;padding:1em 0}"
        "h2{font-size:1em;margin:0 0 .4em}mark.old{background:#f6c6c6}mark.new{background:#c6eac6}"
        ".t div{margin:.2em 0}.n{color:#335;font-style:italic}img{max-width:100%;display:block;"
        "margin-top:.5em;border:1px solid #ddd}"
    )
    title = f"{book.root.name}: {len(places)} changes against {Path(old_epub).name}"
    (out / "index.html").write_text(
        f"<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>"
        f"<style>{style}</style><h1>{html.escape(title)}</h1>"
        "<p>Italic runs are between asterisks. Each crop holds the changed words' lines and "
        "one either side.</p>" + "".join(rows)
    )
    print(out / "index.html")


if __name__ == "__main__":
    main(*sys.argv[1:])
