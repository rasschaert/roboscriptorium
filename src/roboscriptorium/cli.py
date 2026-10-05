import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import httpx
import typer

from roboscriptorium import evaluate, pipeline
from roboscriptorium.book import Book
from roboscriptorium.clients import ollaya
from roboscriptorium.clients.ollama import OllamaClient
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.config import Settings
from roboscriptorium.golden import se
from roboscriptorium.golden.manifest import Golden, fetch
from roboscriptorium.golden.reference import load_chapters

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
def golden_derive(name: str) -> None:
    """Regenerate golden/<name>/text from the pinned Standard Ebooks commit."""
    golden = Golden.load(name)
    repo = se.checkout(golden.repo, golden.commit, Path("work/.cache/se") / name)
    report = se.write_reference(repo, golden.repo, golden.commit, golden.root)
    typer.echo(
        f"{len(report.commits)} editorial commits: {report.applied} changes undone, "
        f"{len(report.unmatched)} unmatched (see {golden.root / 'PROVENANCE.md'})"
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


@app.command("eval")
def evaluate_book(book_dir: Path) -> None:
    """Build a golden book's scan and score it against the reference text."""
    book = Book.load(book_dir)
    if book.golden is None:
        raise typer.BadParameter(f"{book_dir}/book.toml names no golden book")
    doc = pipeline.build(book)
    result = evaluate.score(doc, load_chapters(Golden.load(book.golden).text_dir))

    typer.echo(
        f"CER {result.cer:.2%}   WER {result.wer:.2%}   paragraph F1 {result.paragraph_f1:.3f}"
    )
    typer.echo(
        f"  paragraphs: precision {result.paragraph_precision:.3f}, "
        f"recall {result.paragraph_recall:.3f}; "
        f"words: {result.output_words} out / {result.reference_words} reference"
    )
    typer.echo("  most frequent differences (output → reference):")
    for got, want, n in result.confusions:
        typer.echo(f"    {n:4}× {got[:40]!r} → {want[:40]!r}")

    record = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
        ).stdout.strip(),
        **{k: v for k, v in asdict(result).items() if k != "confusions"},
    }
    with (book.root / "eval-history.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")
