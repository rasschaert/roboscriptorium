# Roboscriptorium

Turns books that aren't EPUBs into clean EPUBs, automated as far as possible and
running entirely on local AI (Ollama for text, Ollaya for decisions). Scanned PDFs
come first.

![From PDF to EPUB: the stages and the model behind each](docs/pipeline.svg)

The diagram's source is [docs/pipeline.d2](docs/pipeline.d2); render it with
`d2 docs/pipeline.d2 docs/pipeline.svg`.

Work in progress. See [AGENTS.md](AGENTS.md) for scope, architecture and conventions.

```sh
uv run roboscriptorium doctor
```
