import json
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import httpx
import typer

from roboscriptorium import (
    disagreements,
    evaluate,
    flags,
    initials,
    layout,
    ocr,
    ocrcheck,
    pipeline,
    review,
)
from roboscriptorium.book import Book
from roboscriptorium.clients import ollaya
from roboscriptorium.clients.ollama import OllamaClient
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections
from roboscriptorium.disagreements import Verdicts
from roboscriptorium.golden import epub as publisher_epub
from roboscriptorium.golden import gutenberg, se
from roboscriptorium.golden.manifest import Golden, PublisherEpub, fetch, sha256
from roboscriptorium.golden.reference import Chapter, load_chapters
from roboscriptorium.ir import Document
from roboscriptorium.pdf import cached_text_layer

app = typer.Typer(no_args_is_help=True, help="Turn books that aren't EPUBs into EPUBs.")


@app.command()
def doctor() -> None:
    """Check that Ollama and Ollaya are reachable and answering."""
    settings = Settings.from_env()
    ok = True

    try:
        names = OllamaClient(settings.ollama_url).models()
        typer.echo(f"ollama  {settings.ollama_url}  {len(names)} models")
    except httpx.HTTPError as exc:
        ok = False
        typer.echo(f"ollama  {settings.ollama_url}  UNREACHABLE: {exc}")

    try:
        client = OllayaClient(settings.ollaya_url, settings.decision_model)
        names = client.models()
        typer.echo(f"ollaya  {settings.ollaya_url}  {', '.join(names)}")
        answer = client.decide(
            {"line": "12", "position": "last line, centred, below body text"},
            {
                "role": ollaya.choice(
                    "What is this line?", {"page_number": "A page number", "body": "Body text"}
                )
            },
        )["role"]
        typer.echo(f"ollaya  decision smoke test: {answer.value} ({answer.confidence:.2f})")
    except httpx.HTTPError as exc:
        ok = False
        typer.echo(f"ollaya  {settings.ollaya_url}  UNREACHABLE: {exc}")

    raise typer.Exit(0 if ok else 1)


@app.command()
def build(book_dir: Path) -> None:
    """Build an EPUB from a book directory holding book.toml and the source file."""
    book = Book.load(book_dir)
    doc = pipeline.build(book)
    typer.echo(f"{len(doc.blocks)} paragraphs → {book.epub_path}")


golden_app = typer.Typer(no_args_is_help=True, help="Golden reference books.")
app.add_typer(golden_app, name="golden")


@golden_app.command("derive")
def golden_derive(name: str, epub: Path | None = None) -> None:
    """Regenerate a golden book's reference text from its Gutenberg or publisher's EPUB."""
    golden = Golden.load(name)
    ref = golden.reference
    out = golden.data_root
    if isinstance(ref, PublisherEpub):
        if epub is None:
            raise typer.BadParameter(f"{name}'s reference can't be downloaded; pass --epub")
        if (actual := sha256(epub)) != ref.sha256:
            raise typer.BadParameter(f"{epub}: sha256 {actual}, expected {ref.sha256}")
        chapters = publisher_epub.write_reference(
            epub,
            ref.source,
            list(ref.files),
            ref.heading_prefixes,
            out,
            ref.italic_classes,
            ref.roman_classes,
            ref.blank_classes,
        )
    else:
        epub = epub or gutenberg.download(
            ref.url, Path("work/.cache/gutenberg") / f"{ref.ebook}.epub"
        )
        chapters = gutenberg.write_reference(epub, ref.ebook, ref.url, ref.chapters, out)
    typer.echo(
        f"{len(chapters)} chapters, {sum(len(c.paragraphs) for c in chapters)} paragraphs "
        f"(see {out / 'PROVENANCE.md'})"
    )


@golden_app.command("derive-se")
def golden_derive_se(name: str) -> None:
    """Regenerate golden/<name>/standard-ebooks from the pinned Standard Ebooks commit."""
    golden = Golden.load(name)
    if (se_ref := golden.standard_ebooks) is None:
        raise typer.BadParameter(f"{name} has no [standard_ebooks] in its manifest")
    repo = se.checkout(se_ref.repo, se_ref.commit, Path("work/.cache/se") / name)
    report = se.write_reference(repo, se_ref.repo, se_ref.commit, golden.se_dir)
    typer.echo(
        f"{len(report.commits)} editorial commits: {report.applied} changes undone, "
        f"{len(report.unmatched)} unmatched (see {golden.se_dir / 'PROVENANCE.md'})"
    )


@golden_app.command("fetch")
def golden_fetch(name: str, scan: str | None = None) -> None:
    """Fetch a golden book's scans into work/<name>--<scan>/, checking sha256."""
    golden = Golden.load(name)
    for s in golden.scans if scan is None else [golden.scan(scan)]:
        try:
            typer.echo(f"{s.id}: {fetch(golden, s)}")
        except FileNotFoundError as exc:
            typer.echo(f"{s.id}: {exc}")


def _range(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    first, _, last = value.partition("-")
    return int(first), int(last or first)


def _build_golden(
    book_dir: Path, pages: str | None, chapters: str | None, no_models: bool, check_ocr: bool = True
) -> tuple[Book, Document, list[Chapter]]:
    book = Book.load(book_dir)
    if book.golden is None:
        raise typer.BadParameter(f"{book_dir}/book.toml names no golden book")
    doc = pipeline.build(book, pages=_range(pages), use_models=not no_models, check_ocr=check_ocr)
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if (span := _range(chapters)) is not None:
        reference = reference[span[0] - 1 : span[1]]
    return book, doc, reference


def _verdicts(book: Book) -> Verdicts:
    scan_id = book.root.name.split("--", 1)[-1]
    return Verdicts(Golden.load(book.golden).verdicts_dir / f"{scan_id}.jsonl")


@app.command("review")
def review_regions(
    book_dir: Path,
    pages: str | None = typer.Option(None, help="Body pages to build, e.g. 7-45"),
    port: int = typer.Option(8765, help="Port on 127.0.0.1"),
) -> None:
    """Review the regions that aren't plain running text, next to the scan."""
    book = Book.load(book_dir)

    def rebuild():
        stages = pipeline.run(book, pages=_range(pages))
        regions = None
        if layout.available():
            numbers = [p.number for p in stages.pages]
            regions = layout.detect(book.source, numbers, book.stages / "layout.json")
        doubts = ocrcheck.doubts(stages.suspects)
        found = flags.find(stages.pages, stages.model_roles, regions, doubts)
        return stages.pages, found, stages.corrections_applied

    body, regions, applied = rebuild()
    corrections = Corrections(book.corrections_path)
    done = sum(f.key in corrections.by_key for f in regions)
    typer.echo(f"{len(regions)} regions to look at ({done} already answered, {applied} applied)")
    typer.echo(f"Reviewing on http://127.0.0.1:{port}/ (Ctrl-C to stop)")
    settings = Settings.from_env()
    decider = ollaya.for_model(settings.role_model, settings.ollaya_url, settings.ollama_url)
    vocab = initials.vocabulary(body, book.language)
    page = review.RegionReview(
        book.source,
        body,
        regions,
        corrections,
        rebuild,
        ocr.language(book.language),
        lambda png, line: initials.guess(decider, vocab, png, line),
    )
    page.applied = applied
    review.serve(page, port)


@golden_app.command("review")
def review_disagreements(
    book_dir: Path,
    pages: str | None = typer.Option(None, help="Body pages to build, e.g. 7-45"),
    chapters: str | None = typer.Option(None, help="Reference chapters to compare, e.g. 1-9"),
    no_models: bool = typer.Option(False, help="Skip decision models (heuristics only)"),
    port: int = typer.Option(8765, help="Port on 127.0.0.1"),
) -> None:
    """Review where the output disagrees with the reference, next to the scan."""
    book, doc, reference = _build_golden(book_dir, pages, chapters, no_models)
    text_layer = cached_text_layer(book.source, book.stages / "textlayer.json")
    found = disagreements.find(doc, reference, text_layer)
    verdicts = _verdicts(book)
    manual = [d for d in found if not d.auto]
    done = sum(d.key in verdicts.by_key for d in manual)
    typer.echo(
        f"{len(found)} disagreements: {len(found) - len(manual)} auto-resolved, "
        f"{len(manual)} to review ({done} already done)"
    )
    typer.echo(f"Reviewing on http://127.0.0.1:{port}/ (Ctrl-C to stop)")
    review.serve(review.Review(book.source, text_layer, found, verdicts), port)


@app.command("eval")
def evaluate_books(
    book_dirs: list[Path],
    pages: str | None = typer.Option(None, help="Body pages to build, e.g. 7-45"),
    chapters: str | None = typer.Option(None, help="Reference chapters to compare, e.g. 1-9"),
    no_models: bool = typer.Option(False, help="Skip decision models (heuristics only)"),
    check_ocr: bool = typer.Option(True, help="Check the OCR layer against a second reading"),
) -> None:
    """Build golden books' scans and score each against its reference text, one by one."""
    summary = []
    for book_dir in book_dirs:
        typer.echo(f"== {book_dir.name}")
        result = _evaluate_book(book_dir, pages, chapters, no_models, check_ocr)
        summary.append(
            f"{book_dir.name[:40]:40} CER {result.cer:6.2%}  WER {result.wer:6.2%}  "
            f"paragraphs P {result.paragraph_precision:.3f} R {result.paragraph_recall:.3f}  "
            f"headings {result.headings_found}/{result.headings_expected}"
            f" (+{result.headings_spurious})"
        )
    if len(book_dirs) > 1:
        typer.echo("\n" + "\n".join(summary))


def _evaluate_book(
    book_dir: Path, pages: str | None, chapters: str | None, no_models: bool, check_ocr: bool
) -> evaluate.Score:
    book, doc, reference = _build_golden(book_dir, pages, chapters, no_models, check_ocr)
    verdicts = _verdicts(book)
    reference, applied = disagreements.patch(reference, verdicts)
    result = evaluate.score(doc, reference)

    typer.echo(
        f"CER {result.cer:.2%}   WER {result.wer:.2%}   paragraph F1 {result.paragraph_f1:.3f}"
        f"   headings {result.headings_found}/{result.headings_expected}"
        f" (+{result.headings_spurious} spurious)"
    )
    typer.echo(
        f"  paragraphs: precision {result.paragraph_precision:.3f}, "
        f"recall {result.paragraph_recall:.3f}; "
        f"words: {result.output_words} out / {result.reference_words} reference"
    )
    if result.italic_expected or result.italic_output:
        typer.echo(
            f"  italic words: precision {result.italic_precision:.3f}, "
            f"recall {result.italic_recall:.3f} "
            f"({result.italic_output} out / {result.italic_expected} reference)"
        )
    if verdicts.by_key:
        text_layer = cached_text_layer(book.source, book.stages / "textlayer.json")
        mistakes = Counter(
            verdicts.by_key[d.key].category if d.key in verdicts.by_key else d.auto or "unreviewed"
            for d in disagreements.find(doc, reference, text_layer)
        )
        typer.echo(
            f"  {applied} scan readings patched into the reference; remaining disagreements: "
            + ", ".join(f"{k} {n}" for k, n in mistakes.most_common())
        )
    typer.echo("  most frequent differences (output → reference):")
    for got, want, n in result.confusions:
        typer.echo(f"    {n:4}× {got[:40]!r} → {want[:40]!r}")

    record = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
        ).stdout.strip(),
        "pages": pages,
        "chapters": chapters,
        "models": not no_models,
        "ocr_check": check_ocr and not no_models,
        "verdicts_applied": applied,
        **{k: v for k, v in asdict(result).items() if k != "confusions"},
    }
    with (book.root / "eval-history.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")
    return result
