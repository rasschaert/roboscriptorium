"""A golden book built and scored: what `eval`, `quality`, `review`, `bench` and the
experiments share. A spec names a golden scan and the slice scored,
`work/<book>[:pages[:chapters]]` (`work/goede-dochter--ia-scan:9-64:1-4`)."""

import json
from dataclasses import replace
from pathlib import Path
from typing import NamedTuple

from roboscriptorium import disagreements, flags, layout, ocrcheck, ocrdoubts, pipeline, readers
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections
from roboscriptorium.disagreements import Around, Disagreement, Verdicts
from roboscriptorium.evaluate import normalise
from roboscriptorium.flags import Flag
from roboscriptorium.golden import notes as golden_notes
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import Chapter, load_chapters, unmarked
from roboscriptorium.ir import Document, SourceRef
from roboscriptorium.pdf import PageText


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


def reference(
    book: Book, chapters: tuple[int, int] | None, sliced: list[PageText] | None = None
) -> tuple[list[Chapter], Around]:
    """The reference's chapters scored, and the words around them. Given the pages of a
    slice that names no chapters (`sliced`), the paragraphs those pages hold."""
    chapters_text = load_chapters(Golden.load(book.golden).text_dir)
    if chapters is None and sliced:
        cut, around, _ = cut_to_pages(chapters_text, sliced)
        return cut, around
    return disagreements.slice_reference(chapters_text, chapters)


def cut_to_pages(
    reference: list[Chapter], pages: list[PageText]
) -> tuple[list[Chapter], Around, tuple[int, int]]:
    """The whole paragraphs of `reference` from the one holding the first words `pages`
    place to the one holding the last (`align`), with scene breaks and italics kept, the
    words around them, and how many reference words those edge paragraphs hold beyond
    the pages (before, after): a slice that starts and ends on a paragraph has none."""
    labels = align(pages, reference)
    # Each placed line's truth and how many words it shows. `align` spreads the words
    # before and after the slice over its first and last lines, so only lines whose
    # truth is about as long as what they show anchor the cut.
    placed = [
        (normalise(lab.truth).split(), len(normalise(page.lines[k].text).split()))
        for page in pages
        for k in range(len(page.lines))
        if (lab := labels.get(SourceRef(page.number, k))) and lab.role != "other" and lab.truth
    ]
    placed = [(w, n) for w, n in placed if w and n]
    # Each reference word's (chapter, paragraph); a heading's words have paragraph -1.
    words: list[str] = []
    at: list[tuple[int, int]] = []
    for c, ch in enumerate(reference):
        for p, text in [(-1, ch.heading)] + list(enumerate(map(unmarked, ch.paragraphs))):
            found = normalise(text).split()
            words += found
            at += [(c, p)] * len(found)
    first = _anchor(words, placed, 0)
    last = _anchor(words, placed[::-1], first[0] if first else 0, backwards=True)
    if first is None or last is None:
        return reference, ([], []), (0, 0)
    # The lines outside the anchoring runs, counted by the words they show.
    start, end = max(0, first[0] - first[1]), min(len(words) - 1, last[0] + last[1])
    if end < start:
        return reference, ([], []), (0, 0)
    (c0, p0), (c1, p1) = at[start], at[end]
    out = []
    for c in range(c0, c1 + 1):
        ch = reference[c]
        first = max(p0, 0) if c == c0 else 0
        last = p1 if c == c1 else len(ch.paragraphs) - 1
        out.append(
            Chapter(
                ch.heading if c > c0 or p0 < 0 else "",
                ch.paragraphs[first : last + 1],
                ch.italic[first : last + 1] if ch.italic else [],
                frozenset(i - first for i in ch.breaks if first <= i <= last),
            )
        )
    lo, hi = at.index((c0, p0)), len(at) - 1 - at[::-1].index((c1, p1))
    around = (
        words[:lo][-disagreements.CONTEXT_WORDS :],
        words[hi + 1 :][: disagreements.CONTEXT_WORDS],
    )
    return out, around, (start - lo, hi - end)


# Consecutive lines, each holding about the words it shows, that anchor each end of a slice.
RUN_LINES = 3


def _anchor(
    words: list[str], lines: list[tuple[list[str], int]], after: int, backwards: bool = False
) -> tuple[int, int] | None:
    """The first `RUN_LINES` consecutive `lines` (truth words, words shown) that each hold
    about what they show and occur together in `words` at or after `after`: where the run
    starts (where it ends, `backwards`, `lines` given last to first) and how many words
    the lines before it show; None if no run is found."""
    sound = [abs(len(w) - n) <= max(2, n // 3) for w, n in lines]
    shown = 0
    for k in range(len(lines) - RUN_LINES + 1):
        if all(sound[k : k + RUN_LINES]):
            group = [w for w, _ in lines[k : k + RUN_LINES]]
            run = [x for line in (group[::-1] if backwards else group) for x in line]
            for i in range(after, len(words) - len(run) + 1):
                if words[i : i + len(run)] == run:
                    return (i + len(run) - 1 if backwards else i), shown
        shown += lines[k][1]
    return None


def questions(book: Book, stages: pipeline.Stages) -> list[Flag]:
    """What the review asks of this build, the golden places aside."""
    regions = None
    if layout.available():
        numbers = [p.number for p in stages.pages]
        regions = layout.detect(book.source, numbers, book.stages / "layout.json")
    found = flags.find(
        stages.pages,
        stages.model_roles,
        regions,
        ocrdoubts.line_doubts(stages.suspects),
        stages.quote_lines,
        stages.quote_readings,
        stages.faint_pages,
        stages.epigraph_lines,
        {
            SourceRef(c.page, i)
            for c in Corrections(book.corrections_path).by_key.values()
            if c.action == "heading"
            for i in range(c.first, c.last + 1)
        },
    )
    found = _read_unread(book, stages, found)
    if not any(s.choice == "other" for s in stages.suspects):
        return found
    checked = {p.number: p for p in ocrcheck.apply(stages.pages, stages.suspects)}
    out = []
    for f in found:
        page = checked.get(f.page)
        if page is None or f.last < f.first or f.last >= len(page.lines):
            out.append(f)
            continue
        built = "\n".join(page.lines[k].text for k in range(f.first, f.last + 1))
        out.append(replace(f, built=built) if built != f.text else f)
    return out


# A question asks for text when it is about running text or a heading, or about printed
# text the layer lacks; a page number or scrap to drop is not read.
_READ = ("text", "heading")
# A region the layer has no line in is read as one line only up to this many line heights.
_ONE_LINE = 1.8


def _read_unread(book: Book, stages: pipeline.Stages, found: list[Flag]) -> list[Flag]:
    """The questions with no readings to choose from (a heading, a line the layer lacks),
    each with the read model's reading of its lines or its region as one, beside the
    layer's: an option to pick instead of typing, and what a typed answer is checked
    against (`review.doubtful`). Lines are read into the OCR check's cache of that
    model's readings, a region in `stages/question-readings.json`."""
    if not stages.read_prompt:
        return found
    settings = Settings.from_env()
    pages = {p.number: p for p in stages.pages}
    lines = [
        f
        for f in found
        if not f.readings and f.first <= f.last and f.treatment in _READ and f.page in pages
    ]
    regions = [
        f
        for f in found
        if not f.readings and f.last < f.first and f.box and "missing-text" in f.reasons
    ]
    refs = {SourceRef(f.page, k) for f in lines for k in range(f.first, f.last + 1)}
    read = readers.line_readings(
        book.source,
        [pages[n] for n in sorted({f.page for f in lines})],
        refs,
        settings.read_model,
        settings.ollama_url,
        book.stages / "third-reading.json",
        stages.read_prompt,
    ) if refs else {}  # fmt: skip
    boxes = readers.region_readings(
        book.source,
        [(f.page, f.box) for f in regions if _one_line(pages.get(f.page), f.box)],
        settings.read_model,
        settings.ollama_url,
        book.stages / "question-readings.json",
        stages.read_prompt,
    )
    out = []
    for f in found:
        if f in lines:
            text = "\n".join(read.get(SourceRef(f.page, k), "") for k in range(f.first, f.last + 1))
            f = _with_reading(f, f.text, text)
        elif f in regions and (text := boxes.get((f.page, f.box), "")):
            f = _with_reading(f, None, text)
        out.append(f)
    return out


def _one_line(page, box) -> bool:
    heights = sorted(ln.y1 - ln.y0 for ln in page.lines) if page and page.lines else []
    return bool(heights) and box[3] - box[1] <= _ONE_LINE * heights[len(heights) // 2]


def _with_reading(f: Flag, layer: str | None, text: str) -> Flag:
    """`f` with the read model's `text` as a reading, after the layer's where there is one."""
    if not text.strip():
        return f
    if layer is None:
        return replace(f, readings=[{"text": text, "votes": ["Qwen"]}])
    if text == layer:
        return replace(f, readings=[{"text": layer, "votes": ["Qwen"]}])
    return replace(f, readings=[{"text": layer, "votes": []}, {"text": text, "votes": ["Qwen"]}])


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
    chapters_text, around = reference(book, chapters, stages.pages if pages else None)
    patched, applied = disagreements.patch(chapters_text, verdicts(book), around)
    errors = disagreements.find(scored(book, stages), patched, stages.pages, book.language, around)
    return Scored(book_dir.name, book, stages, patched, errors, found, applied)


def italics_unlike(book: Book) -> str:
    """Why the book's reference sets italics unlike its print, or "" when it doesn't."""
    return getattr(Golden.load(book.golden).reference, "italics_unlike_print", "")


def breaks_unlike(book: Book) -> str:
    """Why the book's reference breaks paragraphs unlike its print, or "" when it doesn't."""
    return getattr(Golden.load(book.golden).reference, "breaks_unlike_print", "")


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
