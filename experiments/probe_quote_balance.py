"""Paragraphs whose quote marks don't pair up, as review questions: what they cost and catch.

    uv run python experiments/probe_quote_balance.py work/goede-dochter--ia-scan:9-64:1-4 …

For each book: the number of unbalanced places, how many cover a remaining error
(and how many of the book's quote errors they cover), and the places themselves.
"""

import sys
from pathlib import Path

from roboscriptorium import disagreements, pipeline, quality
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.flags import Flag
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import Paragraph
from roboscriptorium.quotes import unbalanced


def main(specs: list[str]) -> None:
    for spec in specs:
        book_dir, pages, chapters = (spec.split(":") + [None, None])[:3]
        book = Book.load(Path(book_dir))
        stages = pipeline.run(book, pages=_range(pages or None))
        reference = load_chapters(Golden.load(book.golden).text_dir)
        if (span := _range(chapters or None)) is not None:
            reference = reference[span[0] - 1 : span[1]]
        reference, _ = disagreements.patch(reference, _verdicts(book))
        errors = disagreements.find(stages.doc, reference, stages.corrected)
        paragraphs = [b for b in stages.doc.blocks if isinstance(b, Paragraph)]
        places = unbalanced(paragraphs)
        by_place = []
        for p in places:
            mine = []
            for page in sorted({r.page for r in p.sources}):
                lines = [r.line for r in p.sources if r.page == page]
                mine.append(Flag("", page, min(lines), max(lines), "", "text", ["quotes"]))
            by_place.append(mine)
        flags = [f for mine in by_place for f in mine]
        quote_errors = [e for e in errors if quality.category(e) in ("quotes", "punctuation")]
        hit = [f for f in flags if any(quality.catches(f, e) for e in errors)]
        caught = [e for e in quote_errors if any(quality.catches(f, e) for f in flags)]
        pages_n = len({p.number for p in stages.pages if p.lines})
        print(
            f"== {Path(book_dir).name}: {len(places)} places ({len(places) / pages_n:.2f}/page), "
            f"{len(hit)}/{len(flags)} flags on an error, "
            f"{len(caught)}/{len(quote_errors)} quote/punctuation errors covered"
        )
        for p, mine in zip(places, by_place, strict=True):
            ok = any(quality.catches(f, e) for f in mine for e in errors)
            print(f"  {'HIT ' if ok else 'miss'} p{p.sources[0].page} {p.why:16} {p.excerpt}")


if __name__ == "__main__":
    main(sys.argv[1:])
