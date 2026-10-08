import json
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import httpx
import typer

from roboscriptorium import (
    bench,
    disagreements,
    evaluate,
    flags,
    initials,
    layout,
    ocr,
    ocrcheck,
    pipeline,
    quality,
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
from roboscriptorium.golden import notes as golden_notes
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
            ref.note_classes,
            hyphen_dash=ref.hyphen_dash,
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


def _score_test() -> bool:
    return typer.Option(
        False, "--score-test", help="Score a book of the test set, which is done once, at the end"
    )


def _not_the_test_set(book_dir: Path, score_test: bool) -> None:
    """The test set is scored once, at the end, on purpose; refuse it otherwise."""
    if book_dir.name in bench.TEST_BOOKS and not score_test:
        raise typer.BadParameter(
            f"{book_dir.name} is in the test set, scored only at the end (pass --score-test)"
        )


def _build_golden(
    book_dir: Path, pages: str | None, chapters: str | None, no_models: bool, check_ocr: bool = True
) -> tuple[Book, pipeline.Stages, Document, list[Chapter]]:
    book = Book.load(book_dir)
    if book.golden is None:
        raise typer.BadParameter(f"{book_dir}/book.toml names no golden book")
    stages = pipeline.run(book, pages=_range(pages), use_models=not no_models, check_ocr=check_ocr)
    doc = _scored(book, stages)
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if (span := _range(chapters)) is not None:
        reference = reference[span[0] - 1 : span[1]]
    return book, stages, doc, reference


def _scored(book: Book, stages: pipeline.Stages) -> Document:
    """The document as scored: without the scan's footnotes where the reference sets them apart."""
    found = golden_notes.load(Golden.load(book.golden).notes_path)
    lines = golden_notes.note_lines(stages.pages, found) if found else set()
    return golden_notes.without(stages.doc, lines, {p.number: p for p in stages.pages})


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
        found = flags.find(
            stages.pages,
            stages.model_roles,
            regions,
            doubts,
            stages.quote_lines,
            stages.quote_readings,
        )
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
    score_test: bool = _score_test(),
) -> None:
    """Review where the output disagrees with the reference, next to the scan."""
    _not_the_test_set(book_dir, score_test)
    book, _, doc, reference = _build_golden(book_dir, pages, chapters, no_models)
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


def _questions_and_errors(spec: str, settings: Settings | None = None):
    """For a golden spec (book dir[:pages[:chapters]]): its name, the book, the build, the
    reference with verdicts applied, the remaining differences from it, the review's
    questions, and the number of verdicts applied."""
    book_dir, pages, chapters = (spec.split(":") + [None, None])[:3]
    book = Book.load(Path(book_dir))
    stages = pipeline.run(book, pages=_range(pages or None), settings=settings)
    regions = None
    if layout.available():
        numbers = [p.number for p in stages.pages]
        regions = layout.detect(book.source, numbers, book.stages / "layout.json")
    found = flags.find(
        stages.pages,
        stages.model_roles,
        regions,
        ocrcheck.doubts(stages.suspects),
        stages.quote_lines,
        stages.quote_readings,
    )
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if (span := _range(chapters or None)) is not None:
        reference = reference[span[0] - 1 : span[1]]
    reference, applied = disagreements.patch(reference, _verdicts(book))
    errors = disagreements.find(_scored(book, stages), reference, stages.corrected)
    return Path(book_dir).name, book, stages, reference, errors, found, applied


@app.command("quality")
def quality_report(specs: list[str], score_test: bool = _score_test()) -> None:
    """Wrong words a reviewer is left with per page, at several question budgets.

    SPECS are golden book dirs, each optionally with :pages:chapters
    (work/goede-dochter--ia-scan:9-64:1-4).

    Each book's questions are ranked by how often each kind of question caught an
    error in the other books given.
    """
    books = []
    for spec in specs:
        _not_the_test_set(Path(spec.split(":")[0]), score_test)
        name, _, stages, _, errors, found, applied = _questions_and_errors(spec)
        numbers = [p.number for p in stages.pages if p.lines]
        typer.echo(
            f"{name}: {len(numbers)} pages, {len(errors)} differing stretches, "
            f"{len(found)} questions, {applied} verdicts applied"
        )
        books.append((name, numbers, errors, found))
    for name, numbers, errors, found in books:
        rates: dict[str, tuple[int, int]] = {}
        for other, _, other_errors, other_flags in books:
            if other != name:
                for r, (h, n) in quality.hit_rates(other_flags, other_errors).items():
                    h0, n0 = rates.get(r, (0, 0))
                    rates[r] = (h0 + h, n0 + n)
        typer.echo(f"\n== {name} (per page, 95% interval)")
        for label, estimate in quality.report(numbers, errors, found, rates).items():
            typer.echo(f"  {label:28} {estimate}")
        unasked = quality.unasked_by_category(errors, found)
        typer.echo(
            "  unasked wrong words by kind: " + ", ".join(f"{k} {v}" for k, v in unasked.items())
        )
        own = quality.hit_rates(found, errors)
        typer.echo(
            "  questions that caught an error, by reason: "
            + ", ".join(f"{r} {h}/{n}" for r, (h, n) in sorted(own.items(), key=lambda x: -x[1][1]))
        )


@app.command("bench")
def run_bench(
    set_name: str = typer.Argument("tuning", help=f"One of {', '.join(bench.SETS)}"),
    against: str | None = typer.Option(None, help="A saved run to compare with (default: last)"),
    score_test: bool = _score_test(),
) -> None:
    """Score a fixed set of golden slices, save the run, and compare it page by page."""
    if set_name not in bench.SETS:
        raise typer.BadParameter(f"no bench set {set_name!r}")
    if set_name == "test" and not score_test:
        raise typer.BadParameter("the test set is scored once, at the end: pass --score-test")
    settings = Settings.from_env()
    built = []
    for spec in bench.SETS[set_name]:
        typer.echo(f"== {spec}")
        own = bench.unseen(settings, spec.split(":")[0])
        name, book, stages, reference, errors, found, applied = _questions_and_errors(
            f"work/{spec}", own
        )
        score = evaluate.score(_scored(book, stages), reference)
        built.append((spec, name, stages, errors, found, applied, score, own))
    books = {}
    for spec, name, stages, errors, found, applied, score, own in built:
        rates: dict[str, tuple[int, int]] = {}
        for other in built:
            if other[1] != name:
                for r, (h, n) in quality.hit_rates(other[4], other[3]).items():
                    h0, n0 = rates.get(r, (0, 0))
                    rates[r] = (h0 + h, n0 + n)
        numbers = [p.number for p in stages.pages if p.lines]
        books[name] = {
            "spec": spec,
            "ocr_decider": stages.ocr_decider,
            "ocr_trust_model": own.ocr_trust_model,
            "ocr_suspects": dict(Counter(s.choice for s in stages.suspects)),
            "verdicts_applied": applied,
            "score": {k: v for k, v in asdict(score).items() if k != "confusions"},
            "quality": {
                k: asdict(v) for k, v in quality.report(numbers, errors, found, rates).items()
            },
            "unasked_by_kind": quality.unasked_by_category(errors, found),
            "pages": bench.page_counts(numbers, errors, found),
        }
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True
    ).stdout.strip()
    record = {
        "set": set_name,
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit + ("-dirty" if dirty else ""),
        "settings": {k: v for k, v in asdict(settings).items() if not k.endswith("_url")},
        "model_versions": _model_versions(settings),
        "books": books,
    }
    path = bench.save(record)
    typer.echo(f"\nsaved {path}")
    for name, b in books.items():
        q = b["quality"]
        typer.echo(
            f"{name[:40]:40} CER {b['score']['cer']:6.2%}"
            f"  wrong/page {q['wrong words']['mean']:.2f}"
            f"  questions {q['questions']['mean']:.2f}"
            f"  unasked {q['unasked, all questions']['mean']:.2f}"
            f"  after review {sum(v[3] for v in b['pages'].values()) / max(len(b['pages']), 1):.2f}"
        )
    old_path = Path(against) if against else bench.previous(set_name, path)
    if old_path is None:
        return
    old = json.loads(old_path.read_text())
    new = json.loads(path.read_text())
    found = bench.verdict(old, new)
    typer.echo(f"\nagainst {old_path.name}: {found.outcome.upper()}")
    for c in found.pooled:
        typer.echo(
            f"  all pages, {c.measure:26} {c.before:6.2f} → {c.after:6.2f}"
            f"  [{c.low:+.2f}, {c.high:+.2f}]"
        )
    if found.vetoes:
        typer.echo("  worse on its own: " + ", ".join(found.vetoes))
    typer.echo("per book (diagnostics, not tests; * where the 95% interval excludes 0):")
    for c in bench.compare(old, new):
        mark = "*" if c.real else " "
        typer.echo(
            f" {mark} {c.book[:40]:40} {c.measure:26} {c.before:6.2f} → {c.after:6.2f}"
            f"  [{c.low:+.2f}, {c.high:+.2f}]"
        )


@app.command("eval")
def evaluate_books(
    book_dirs: list[Path],
    pages: str | None = typer.Option(None, help="Body pages to build, e.g. 7-45"),
    chapters: str | None = typer.Option(None, help="Reference chapters to compare, e.g. 1-9"),
    no_models: bool = typer.Option(False, help="Skip decision models (heuristics only)"),
    check_ocr: bool = typer.Option(True, help="Check the OCR layer against a second reading"),
    score_test: bool = _score_test(),
) -> None:
    """Build golden books' scans and score each against its reference text, one by one."""
    for book_dir in book_dirs:
        _not_the_test_set(book_dir, score_test)
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


def _model_versions(settings: Settings) -> dict[str, str]:
    """What each model name served now is: Ollama's digest, Ollaya's release date."""
    out = {}
    try:
        for m in httpx.get(f"{settings.ollama_url}/api/tags", timeout=5).json()["models"]:
            digest = m["digest"][:12]
            out[m["name"]] = ",".join(sorted({*out.get(m["name"], "").split(","), digest} - {""}))
        for m in httpx.get(f"{settings.ollaya_url}/v1/models", timeout=5).json()["models"]:
            out[m["name"]] = m.get("release_date", "")
    except httpx.HTTPError:
        pass
    used = {
        settings.role_model, settings.check_model, settings.judge_model,
        settings.ocr_model, settings.read_model,
    }  # fmt: skip
    return {name: out.get(name, "?") for name in sorted(used - {""})}


def _evaluate_book(
    book_dir: Path, pages: str | None, chapters: str | None, no_models: bool, check_ocr: bool
) -> evaluate.Score:
    book, stages, doc, reference = _build_golden(book_dir, pages, chapters, no_models, check_ocr)
    suspects = Counter(s.choice for s in stages.suspects)
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
    if suspects:
        typer.echo(
            f"  OCR check: {sum(suspects.values())} suspects, {suspects['other']} fixed, "
            f"{suspects['ours']} kept, {suspects['review']} for review"
        )
    typer.echo("  most frequent differences (output → reference):")
    for got, want, n in result.confusions:
        typer.echo(f"    {n:4}× {got[:40]!r} → {want[:40]!r}")

    settings = Settings.from_env()
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
        "ocr_suspects": dict(suspects),
        "ocr_decider": stages.ocr_decider,
        "settings": {k: v for k, v in asdict(settings).items() if not k.endswith("_url")},
        "model_versions": _model_versions(settings) if not no_models else {},
        **{k: v for k, v in asdict(result).items() if k != "confusions"},
    }
    with (book.root / "eval-history.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")
    return result
