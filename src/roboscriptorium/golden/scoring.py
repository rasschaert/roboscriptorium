"""A golden book built and scored: what `eval`, `quality`, `review`, `bench` and the
experiments share. A spec names a golden scan and the slice scored,
`work/<book>[:pages[:chapters]]` (`work/goede-dochter--ia-scan:9-64:1-4`)."""

import json
from pathlib import Path
from typing import NamedTuple

from roboscriptorium import disagreements, flags, layout, ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.disagreements import Around, Disagreement, Verdicts
from roboscriptorium.flags import Flag
from roboscriptorium.golden import notes as golden_notes
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import Chapter, load_chapters
from roboscriptorium.ir import Document


def page_range(value: str | None) -> tuple[int, int] | None:
    """A range "7-45" or a single page "7"; ValueError for anything else."""
    if value is None:
        return None
    first, dash, last = value.replace("–", "-").partition("-")
    try:
        span = int(first), int(last if dash else first)
    except ValueError:
        raise ValueError(f"{value!r}: give a range like 7-45, or one number") from None
    if span[0] < 1:
        raise ValueError(f"{value!r}: pages and chapters count from 1")
    if span[0] > span[1]:
        raise ValueError(f"{value!r}: the range runs backwards")
    return span


def parse_spec(spec: str) -> tuple[Path, tuple[int, int] | None, tuple[int, int] | None]:
    """A spec's book directory, pages and chapters."""
    book_dir, pages, chapters = (spec.split(":") + [None, None])[:3]
    return Path(book_dir), page_range(pages or None), page_range(chapters or None)


def scored(book: Book, stages: pipeline.Stages) -> Document:
    """The document as scored: without the scan's footnotes where the reference sets
    them apart."""
    found = golden_notes.load(Golden.load(book.golden).notes_path)
    return golden_notes.scored(stages.doc, stages.pages, found)


def verdicts(book: Book) -> Verdicts:
    """The verdicts on this scan's reference."""
    scan_id = book.root.name.split("--", 1)[-1]
    return Verdicts(Golden.load(book.golden).verdicts_dir / f"{scan_id}.jsonl")


def reference(book: Book, chapters: tuple[int, int] | None) -> tuple[list[Chapter], Around]:
    """The reference's chapters scored, and the words around them."""
    chapters_text = load_chapters(Golden.load(book.golden).text_dir)
    return disagreements.slice_reference(chapters_text, chapters)


def questions(book: Book, stages: pipeline.Stages) -> list[Flag]:
    """What the review asks of this build, the golden places aside."""
    regions = None
    if layout.available():
        numbers = [p.number for p in stages.pages]
        regions = layout.detect(book.source, numbers, book.stages / "layout.json")
    return flags.find(
        stages.pages,
        stages.model_roles,
        regions,
        ocrcheck.line_doubts(stages.suspects),
        stages.quote_lines,
        stages.quote_readings,
        stages.faint_pages,
        stages.epigraph_lines,
    )


class Scored(NamedTuple):
    name: str  # the book directory's name
    book: Book
    stages: pipeline.Stages
    reference: list[Chapter]  # the slice's chapters, verdicts applied
    errors: list[Disagreement]  # where the build still differs from them
    found: list[Flag]  # the review's questions
    applied: int  # verdicts applied


def build(spec: str, settings: Settings | None = None) -> Scored:
    """Build a spec's slice and score it against its reference with verdicts applied."""
    book_dir, pages, chapters = parse_spec(spec)
    book = Book.load(book_dir)
    stages = pipeline.run(book, pages=pages, settings=settings)
    found = questions(book, stages)
    chapters_text, around = reference(book, chapters)
    patched, applied = disagreements.patch(chapters_text, verdicts(book), around)
    errors = disagreements.find(scored(book, stages), patched, stages.pages, book.language, around)
    return Scored(book_dir.name, book, stages, patched, errors, found, applied)


def italics_unlike(book: Book) -> str:
    """Why the book's reference sets italics unlike its print, or "" when it doesn't."""
    return getattr(Golden.load(book.golden).reference, "italics_unlike_print", "")


def read_via(book: Book, pages: set[int]) -> dict[str, float]:
    """Of the read model's cached readings of these pages, the share each hosted build
    read in its place (`ROBO_READ_VIA`): a bench run says which reader it measured."""
    path = book.stages / "third-reading.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    keys = {k for k in raw.get("lines", {}) if int(k.split(":")[0]) in pages}
    return {
        via: round(len(keys & set(read)) / len(keys), 3)
        for via, read in raw.get("via", {}).items()
        if keys
    }
