# Roboscriptorium

Turns a book's PDF into a clean EPUB 3, automated as far as possible and running
entirely on local AI (generative and decision models on Ollama).

It takes scanned books: a PDF with an OCR text layer, as the Internet Archive makes
them, or an image-only scan, which gets its first reading from tesseract. A
born-digital PDF (made from the typeset text, often by calibre from an EPUB) is out of
scope: its text converts back trivially.

![From PDF to EPUB: the stages and the model behind each](docs/pipeline.svg)

The diagram's source is [docs/pipeline.d2](docs/pipeline.d2); render it with
`d2 docs/pipeline.d2 docs/pipeline.svg`.

New to it, or back after a while? Start with [docs/primer.md](docs/primer.md).
How it all fits together: [docs/how-it-works.md](docs/how-it-works.md); why each part
is there: [docs/design.md](docs/design.md).

Work in progress. See [AGENTS.md](AGENTS.md) for scope, architecture and conventions.

```sh
uv run roboscriptorium doctor
```
