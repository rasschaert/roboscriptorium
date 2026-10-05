"""Run the stages for one book, from source PDF to EPUB."""

import json
from dataclasses import asdict

from roboscriptorium.book import Book
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.config import Settings
from roboscriptorium.epub import write_epub
from roboscriptorium.ir import Document
from roboscriptorium.pdf import cached_text_layer, render_jpeg
from roboscriptorium.reflow import reflow
from roboscriptorium.roles import DecisionCache, classify


def build(book: Book, pages: tuple[int, int] | None = None, use_models: bool = True) -> Document:
    """Build the book's EPUB. `pages` narrows the body range for quick experiments."""
    first, last = pages or book.body_pages
    body = [
        p
        for p in cached_text_layer(book.source, book.stages / "textlayer.json")
        if first <= p.number <= last
    ]

    roles = None
    if use_models:
        settings = Settings.from_env()
        client = OllayaClient(settings.ollaya_url, settings.role_model)
        roles = classify(body, client, DecisionCache(book.stages / "decisions.jsonl"))

    doc = Document(book.title, book.author, book.language, reflow(body, roles))
    (book.stages / "document.json").write_text(
        json.dumps(asdict(doc), ensure_ascii=False, indent=1)
    )

    cover = render_jpeg(book.source, book.cover_page) if book.cover_page else None
    write_epub(doc, book.epub_path, cover)
    return doc
