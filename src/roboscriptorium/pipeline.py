"""Run the stages for one book, from source PDF to EPUB."""

import json
from dataclasses import asdict

from roboscriptorium.book import Book
from roboscriptorium.epub import write_epub
from roboscriptorium.ir import Document
from roboscriptorium.pdf import cached_text_layer, render_jpeg
from roboscriptorium.reflow import reflow


def build(book: Book) -> Document:
    pages = cached_text_layer(book.source, book.stages / "textlayer.json")
    first, last = book.body_pages
    body = [p for p in pages if first <= p.number <= last]

    doc = Document(book.title, book.author, book.language, reflow(body))
    (book.stages / "document.json").write_text(
        json.dumps(asdict(doc), ensure_ascii=False, indent=1)
    )

    cover = render_jpeg(book.source, book.cover_page) if book.cover_page else None
    write_epub(doc, book.epub_path, cover)
    return doc
