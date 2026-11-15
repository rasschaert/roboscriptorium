"""What each book still needs a person for: every book's `book.toml` against what `init`
and the build's scan measurements give without it. No models: page kinds come from cached
answers (`init`'s own, else `probe_init_ends.py`'s), and a book whose edge pages were never
asked says so. Title, author and translator need the read model and are left to the score
of every field `init` drafts (checklist, Starting from a PDF alone).

    uv run python experiments/setup_gaps.py [book …]
"""

import contextlib
import dataclasses
import io
import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import bookinit, pagekinds, pipeline
from roboscriptorium.book import Book
from roboscriptorium.pdf import cached_text_layer

PROBE = Path("work/probes/page-kinds")
# A golden book's body_pages is the slice it is scored on; where its text proper's ends are
# labelled, those are what `init` is held to.
LABELS = json.loads(Path("tryouts/page-kinds-v1.json").read_text())["books"]
DRAFTED = ("language", "cover_page", "body_pages", "typeface")
MEASURED = ("dash", "dash_spacing", "ellipsis", "ellipsis_space", "descent")


class Cached:
    """Stands in for the page-kind model: answers only from a cache, never asks."""

    model = "clef-flash:9b"

    def decide(self, *args, **kwargs):
        raise LookupError("not in the cache")


def kinds_of(root: Path, pages) -> dict[int, str] | None:
    """`init`'s page kinds from cached answers, or None where an edge page was never asked."""
    for cache in (
        root / "stages" / "page-kinds.json",
        PROBE / f"edges-clef-flash_9b-{root.name}.json",
        PROBE / f"edges-{root.name}.json",
    ):
        if cache.exists():
            try:
                return pagekinds.kinds(root / "source.pdf", pages, Cached(), cache)
            except LookupError:
                continue
    return None


def gaps(root: Path) -> list[tuple[str, object, object]]:
    raw = json.loads(json.dumps(__import__("tomllib").loads((root / "book.toml").read_text())))
    book = Book.load(root)
    pages = cached_text_layer(book.source, book.stages / "textlayer.json")
    out = []
    lang, _ = bookinit.language_of(pages)
    if lang[:2] != book.language[:2]:
        out.append(("language", book.language, lang))
    kinds = kinds_of(root, pages)
    if kinds is None:
        out.append(("body_pages", list(book.body_pages), "edge pages never asked"))
    else:
        first, last = pagekinds.ends(kinds)
        want, said = list(book.body_pages), "body_pages"
        if root.name in LABELS:
            labelled = {int(k): v for k, v in LABELS[root.name]["pages"].items()}
            want = list(pagekinds.ends({p.number: labelled.get(p.number, "text") for p in pages}))
            said = "text proper"
        if [first, last] != want:
            out.append((said, want, [first, last]))
        cover = next((n for n, k in sorted(kinds.items()) if k == "cover"), None) or 1
        if "cover_page" in raw and raw["cover_page"] != cover:
            out.append(("cover_page", raw["cover_page"], cover))
    held = book.stages / "typeface.json"
    if "typeface" in raw:
        got = json.loads(held.read_text()).get("file") if held.exists() else None
        if got != raw["typeface"]:
            out.append(("typeface", raw["typeface"], got or "never matched"))
    bare = dataclasses.replace(book, dash=None, dash_spacing=None, ellipsis=None, ellipsis_space=None, descent=None)
    body = [p for p in pages if book.body_pages[0] <= p.number <= book.body_pages[1]]
    with contextlib.redirect_stderr(io.StringIO()):
        dash = pipeline.dash_style(bare, body) if "dash" in raw or "dash_spacing" in raw else None
        dots = pipeline.ellipsis_style(bare, body) if "ellipsis" in raw or "ellipsis_space" in raw else None
        descent = pipeline.line_descent(bare, body) if "descent" in raw else None
    for key, got in (
        ("dash", dash and dash.dash), ("dash_spacing", dash and dash.spacing),
        ("ellipsis", dots and dots.dots), ("ellipsis_space", dots and dots.space_before),
        ("descent", descent),
    ):  # fmt: skip
        if key in raw and got != raw[key]:
            out.append((key, raw[key], got if got is not None else "not measured"))
    for key in raw:
        if key not in (*DRAFTED, *MEASURED, "title", "author", "translator", "source", "golden"):
            out.append((key, raw[key], "nothing drafts it"))
    return out


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.parent.name for p in Path("work").glob("*/book.toml"))
    kinds = Counter()
    for name in names:
        root = Path("work") / name
        if not (root / "source.pdf").exists() or not (root / "stages" / "textlayer.json").exists():
            print(f"{name}: no scan or text layer cached, skipped", flush=True)
            continue
        try:
            found = gaps(root)
        except Exception as e:
            print(f"{name}: failed: {e!r}", flush=True)
            continue
        for key, have, got in found:
            kinds[key] += 1
            print(f"{name[:40]:40} {key:15} book.toml {have!r:28} alone {got!r}", flush=True)
        if not found:
            print(f"{name[:40]:40} nothing", flush=True)
    print("by key:", dict(kinds.most_common()))
