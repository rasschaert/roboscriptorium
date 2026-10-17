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
    initials,
    ocr,
    pipeline,
    quality,
    review,
)
from roboscriptorium.book import Book
from roboscriptorium.clients import decide, llama
from roboscriptorium.clients.ollama import OllamaClient
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections
from roboscriptorium.epub import keep_dated
from roboscriptorium.golden import epub as publisher_epub
from roboscriptorium.golden import gutenberg, scoring, se, signals
from roboscriptorium.golden.manifest import Golden, PublisherEpub, fetch, sha256
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import Document

app = typer.Typer(no_args_is_help=True, help="Turn books that aren't EPUBs into EPUBs.")


@app.command()
def doctor() -> None:
    """Check that Ollama is reachable and its decision models answer."""
    settings = Settings.from_env()
    ok = True

    try:
        names = OllamaClient(settings.ollama_url).models()
        typer.echo(f"ollama  {settings.ollama_url}  {len(names)} models")
    except httpx.HTTPError as exc:
        ok = False
        typer.echo(f"ollama  {settings.ollama_url}  UNREACHABLE: {exc}")

    # The decision models the pipeline asks, each on the runtime that serves it.
    for model in dict.fromkeys([settings.role_model, settings.judge_model, settings.check_model]):
        try:
            client = decide.for_model(model, settings.ollama_url)
            answer = client.decide(
                {"line": "12", "position": "last line, centred, below body text"},
                {
                    "role": decide.choice(
                        "What is this line?",
                        {"page_number": "A page number", "body": "Body text"},
                    )
                },
            )["role"]
            typer.echo(f"decide  {model}  smoke test: {answer.value} ({answer.confidence:.2f})")
        except httpx.HTTPError as exc:
            ok = False
            typer.echo(f"decide  {model}  FAILED: {exc}")
    if settings.alarm_model:
        try:
            client = llama.ReadoutClient(settings.alarm_model, settings.llama_url)
            question = decide.choice(
                "Which colour is a clear daytime sky?", {"blue": "", "red": ""}
            )
            answer = client.decide({}, {"q": question})["q"]
            typer.echo(
                f"llama   {settings.alarm_model}  {settings.llama_url}  smoke test: "
                f"{answer.value} ({answer.confidence:.2f})"
            )
        except (httpx.HTTPError, OSError) as exc:
            ok = False
            typer.echo(f"llama   {settings.alarm_model}  {settings.llama_url}  FAILED: {exc}")

    raise typer.Exit(0 if ok else 1)


@app.command()
def build(
    book_dir: Path,
    pages: str | None = typer.Option(None, help="Body pages to build, e.g. 7-45"),
) -> None:
    """Build an EPUB from a book directory holding book.toml and the source file. No
    scores: it warms a first look's caches without looking."""
    book = Book.load(book_dir)
    doc = pipeline.build(book, _range(pages))
    typer.echo(f"{len(doc.blocks)} paragraphs → {book.epub_path}")
    if kept := keep_dated(book.epub_path, book.epubs):
        typer.echo(f"kept as {kept}")


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
            image_heading=ref.image_heading,
            capitals=ref.capital_classes,
            note_mark=ref.note_mark,
            breaks=ref.break_classes,
            opening=ref.opening_classes,
            closing=ref.closing_classes,
            initial_images=ref.initial_images,
            leading_text=ref.leading_text,
            markup_spaces=ref.markup_spaces,
        )
    else:
        epub = epub or gutenberg.download(
            ref.url, Path("work/.cache/gutenberg") / f"{ref.ebook}.epub"
        )
        chapters = gutenberg.write_reference(
            epub, ref.ebook, ref.url, ref.chapters, out, ref.ellipsis_space
        )
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
    """A range "7-45" or a single page "7", as an option gives it."""
    try:
        return scoring.page_range(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None


def _first_look() -> bool:
    return typer.Option(
        False, "--first-look", help="Score a new pair's first look, done once, before any choice"
    )


def _not_a_first_look(book_dir: Path, first_look: bool) -> None:
    """A pair awaiting its first look is scored once, on purpose; refuse it otherwise."""
    if book_dir.name in bench.FIRST_LOOK and not first_look:
        raise typer.BadParameter(
            f"{book_dir.name} awaits its first look, scored once (pass --first-look)"
        )


def _build_golden(
    book_dir: Path, pages: str | None, chapters: str | None, no_models: bool, check_ocr: bool = True
) -> tuple[Book, pipeline.Stages, Document, list[Chapter], disagreements.Around]:
    book = Book.load(book_dir)
    if book.golden is None:
        raise typer.BadParameter(f"{book_dir}/book.toml names no golden book")
    stages = pipeline.run(book, pages=_range(pages), use_models=not no_models, check_ocr=check_ocr)
    reference, around = scoring.reference(book, _range(chapters))
    return book, stages, scoring.scored(book, stages), reference, around


@app.command("review")
def review_regions(
    book_dir: Path,
    pages: str | None = typer.Option(None, help="Body pages to build, e.g. 7-45"),
    chapters: str | None = typer.Option(
        None, help="A golden book's reference chapters to compare, e.g. 1-9"
    ),
    port: int = typer.Option(8765, help="Port on 127.0.0.1"),
    first_look: bool = _first_look(),
) -> None:
    """Review the regions that aren't plain running text, next to the scan; for a golden
    book also where its text and the reference differ, whose answers are verdicts."""
    _not_a_first_look(book_dir, first_look)
    book = Book.load(book_dir)
    if book.golden is not None:
        reference, around = scoring.reference(book, _range(chapters))

    def rebuild():
        stages = pipeline.run(book, pages=_range(pages))
        if pages is None:
            keep_dated(book.epub_path, book.epubs)
        found = scoring.questions(book, stages)
        places = []
        if book.golden is not None:
            # The paragraphs' line references point into the pages before answers (the
            # text layer with missing lines added), as `Line.source` does on the corrected copy.
            doc = scoring.scored(book, stages)
            differ = disagreements.find(doc, reference, stages.pages, book.language, around)
            places = [d for d in differ if not d.auto]
        return stages.pages, found, stages.corrections_applied, places

    body, regions, applied, places = rebuild()
    corrections = Corrections(book.corrections_path)
    done = sum(f.key in corrections.by_key for f in regions)
    typer.echo(f"{len(regions)} regions to look at ({done} already answered, {applied} applied)")
    golden = None
    if book.golden is not None:
        golden = review.GoldenQuestions(places, scoring.verdicts(book))
        done = sum(d.key in golden.verdicts.by_key for d in golden.items.values())
        typer.echo(
            f"{len(golden.items)} places where the text and the reference differ "
            f"({done} already answered)"
        )
    typer.echo(f"Reviewing on http://127.0.0.1:{port}/ (Ctrl-C to stop)")
    settings = Settings.from_env()
    decider = decide.for_model(settings.role_model, settings.ollama_url)
    vocab = initials.vocabulary(body, book.language)
    page = review.RegionReview(
        book.source,
        body,
        regions,
        corrections,
        rebuild,
        ocr.language(book.language),
        lambda png, line: initials.guess(decider, vocab, png, line),
        golden,
        book.root,
    )
    page.applied = applied
    review.serve(page, port)


@app.command("quality")
def quality_report(specs: list[str], first_look: bool = _first_look()) -> None:
    """Wrong words a reviewer is left with per page, at several question budgets.

    SPECS are golden book dirs, each optionally with :pages:chapters
    (work/goede-dochter--ia-scan:9-64:1-4).

    Each book's questions are ranked by how often each kind of question caught an
    error in the other books given.
    """
    for spec in specs:
        try:
            book_dir, _, _ = scoring.parse_spec(spec)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from None
        _not_a_first_look(book_dir, first_look)
    books = []
    for spec in specs:
        name, _, stages, _, errors, found, applied = scoring.build(spec)
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


def _commit() -> str:
    """The checkout's commit, "-dirty" with uncommitted changes. Read when a run starts:
    the code a run executes is what was there when Python imported it."""
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True
    ).stdout.strip()
    return commit + ("-dirty" if dirty else "")


@app.command("bench")
def run_bench(
    set_name: str = typer.Argument("tuning", help=f"One of {', '.join(bench.SETS)}"),
    against: str | None = typer.Option(None, help="A saved run to compare with (default: last)"),
    first_look: bool = _first_look(),
) -> None:
    """Score a fixed set of golden slices, save the run, and compare it page by page."""
    if set_name not in bench.SETS:
        raise typer.BadParameter(f"no bench set {set_name!r}")
    if set_name == "first-look" and not first_look:
        raise typer.BadParameter("a first look is scored once, on purpose: pass --first-look")
    settings = Settings.from_env()
    record = bench.run(
        set_name,
        settings,
        _commit(),
        _model_versions(settings),
        on_book=lambda spec: typer.echo(f"== {spec}"),
    )
    books = record["books"]
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
            f"  breaks {sum(v[6] for v in b['pages'].values()) / max(len(b['pages']), 1):.2f}"
            f"  typography {sum(v[7] for v in b['pages'].values()) / max(len(b['pages']), 1):.2f}"
            f" ({', '.join(b['typography_kinds']) or 'none'})"
            f"  headings {b['score']['headings_found']}/{b['score']['headings_expected']}"
            f" (+{b['score']['headings_spurious']})"
            f"  scenes {bench.scenes(b['score'])}"
        )
    pairs = {name: signals.Signals(**b["pair"]) for name, b in books.items()}
    for name, why in signals.suspects(pairs).items():
        typer.echo(f"  suspect pair, consider retiring {name}: {'; '.join(why)}")
    old_path = Path(against) if against else bench.previous(set_name, path)
    if old_path is None:
        return
    old = json.loads(old_path.read_text())
    new = json.loads(path.read_text())
    found = bench.verdict(old, new)
    typer.echo(f"\nagainst {old_path.name}: {found.outcome.upper()}")
    for change in bench.settings_changed(old, new):
        typer.echo(f"  made with other settings, {change}")
    for c in found.pooled:
        typer.echo(
            f"  all pages, {c.measure:26} {c.before:6.2f} → {c.after:6.2f}"
            f"  [{c.low:+.2f}, {c.high:+.2f}]"
        )
    if (c := found.breaks) is not None:
        typer.echo(
            f"  all pages, {c.measure:26} {c.before:6.2f} → {c.after:6.2f}"
            f"  [{c.low:+.2f}, {c.high:+.2f}]"
        )
    if found.vetoes:
        typer.echo("  worse on its own: " + ", ".join(found.vetoes))
    if changed := bench.structure(old, new):
        typer.echo("structure (not in the test above):")
        for line in changed:
            typer.echo(f"   {line}")
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
    first_look: bool = _first_look(),
) -> None:
    """Build golden books' scans and score each against its reference text, one by one."""
    for book_dir in book_dirs:
        _not_a_first_look(book_dir, first_look)
    commit = _commit()
    summary = []
    for book_dir in book_dirs:
        typer.echo(f"== {book_dir.name}")
        result = _evaluate_book(book_dir, pages, chapters, no_models, check_ocr, commit)
        summary.append(
            f"{book_dir.name[:40]:40} CER {result.cer:6.2%}  WER {result.wer:6.2%}  "
            f"paragraphs P {result.paragraph_precision:.3f} R {result.paragraph_recall:.3f}  "
            f"headings {result.headings_found}/{result.headings_expected}"
            f" (+{result.headings_spurious})  scenes {bench.scenes(asdict(result))}"
        )
    if len(book_dirs) > 1:
        typer.echo("\n" + "\n".join(summary))


def _model_versions(settings: Settings) -> dict[str, str]:
    """What each model name served now is: its Ollama digest."""
    out = {}
    try:
        for m in httpx.get(f"{settings.ollama_url}/api/tags", timeout=5).json()["models"]:
            digest = m["digest"][:12]
            out[m["name"]] = ",".join(sorted({*out.get(m["name"], "").split(","), digest} - {""}))
    except httpx.HTTPError:
        pass
    used = {
        settings.role_model, settings.check_model, settings.judge_model,
        settings.ocr_model, settings.read_model,
    }  # fmt: skip
    versions = {name: out.get(name, "?") for name in sorted(used - {""})}
    if settings.alarm_model:
        size = settings.alarm_model.removeprefix("imajev-")
        readout = llama.READOUTS / f"{size}-decision_readout.safetensors"
        versions[settings.alarm_model] = sha256(readout)[:12] if readout.exists() else "?"
    return versions


def _evaluate_book(
    book_dir: Path,
    pages: str | None,
    chapters: str | None,
    no_models: bool,
    check_ocr: bool,
    commit: str,
) -> evaluate.Score:
    book, stages, doc, reference, around = _build_golden(
        book_dir, pages, chapters, no_models, check_ocr
    )
    suspects = Counter(s.choice for s in stages.suspects)
    verdicts = scoring.verdicts(book)
    patched, applied = disagreements.patch(reference, verdicts, around)
    result = evaluate.score(doc, patched)

    typer.echo(
        f"CER {result.cer:.2%}   WER {result.wer:.2%}   paragraph F1 {result.paragraph_f1:.3f}"
        f"   headings {result.headings_found}/{result.headings_expected}"
        f" (+{result.headings_spurious} spurious)   scene breaks {bench.scenes(asdict(result))}"
    )
    typer.echo(
        f"  paragraphs: precision {result.paragraph_precision:.3f}, "
        f"recall {result.paragraph_recall:.3f}; "
        f"words: {result.output_words} out / {result.reference_words} reference"
    )
    if unlike := scoring.italics_unlike(book):
        typer.echo(
            f"  italic words: not scored, the reference's italics aren't the print's ({unlike})"
        )
    elif result.italic_expected or result.italic_output:
        typer.echo(
            f"  italic words: precision {result.italic_precision:.3f}, "
            f"recall {result.italic_recall:.3f} "
            f"({result.italic_output} out / {result.italic_expected} reference)"
        )
    folded = {
        k: (result.folded_output.get(k, 0), v)
        for k, v in result.folded_reference.items()
        if v or result.folded_output.get(k)
    }
    if folded:
        typer.echo(
            "  typography folded before scoring (output / reference): "
            + ", ".join(f"{k} {o}/{r}" for k, (o, r) in folded.items())
        )
    if verdicts.by_key:
        # Found on the unpatched reference, as the review records its verdicts; a
        # verdict that the scan prints the output settles its disagreement.
        found = disagreements.find(doc, reference, stages.pages, book.language, around)
        mistakes = Counter(
            verdicts.by_key[d.key].category if d.key in verdicts.by_key else d.auto or "unreviewed"
            for d in found
            if d.key not in verdicts.by_key
            or evaluate.normalise(verdicts.by_key[d.key].truth or "") != d.got
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
        "commit": commit,
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
