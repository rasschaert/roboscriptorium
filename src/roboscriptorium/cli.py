from pathlib import Path

import httpx
import typer

from roboscriptorium import pipeline
from roboscriptorium.book import Book
from roboscriptorium.clients import ollaya
from roboscriptorium.clients.ollama import OllamaClient
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.config import Settings

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
