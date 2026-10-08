# Roboscriptorium

Turns books that aren't EPUBs into clean EPUBs, automated as far as possible and
running entirely on local AI (generative models on Ollama; decision models on Ollaya
and Ollama's systemone endpoint). Scanned PDFs
come first.

![From PDF to EPUB: the stages and the model behind each](docs/pipeline.svg)

The diagram's source is [docs/pipeline.d2](docs/pipeline.d2); render it with
`d2 docs/pipeline.d2 docs/pipeline.svg`.

How it all fits together: [docs/how-it-works.md](docs/how-it-works.md); why each part
is there: [docs/design.md](docs/design.md).

Work in progress. See [AGENTS.md](AGENTS.md) for scope, architecture and conventions.

```sh
uv run roboscriptorium doctor
```
