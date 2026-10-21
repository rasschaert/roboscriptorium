# Roboscriptorium

Turns a scanned book into a clean EPUB 3: the book's own words, paragraphs, headings,
italics and quote marks, with the page numbers, running heads and line-end hyphens of
paper gone. The aim is the care of a hand-made edition like
[Standard Ebooks'](https://standardebooks.org), which takes volunteers weeks, in a few
hours of machine time, with a person answering only the questions the machine can't
settle. Everything runs on your own computer, on local AI models.

Dutch and English prose for now. Work in progress.

## Why it's hard, and the idea

A scanned PDF is a photo of each page, with one OCR program's reading hidden underneath
it: the *text layer*. That reading gets two or three words wrong on a typical page (a
missing accent, two words glued together, a speck read as a letter), and it knows
nothing about structure: which line is a heading, a page number, the start of a
paragraph.

No single OCR program fixes this, because each makes mistakes of its own. But they make
*different* mistakes:

![Four readings of one line: where they disagree, a suspect](docs/primer/readers-disagree.svg)

So the machine reads every line again with several models, and wherever they disagree it
has a *suspect*. Judges look at each suspect, and a small model trained on books whose
correct text is known weighs them all: it fixes what it is sure of and asks you about
the rest, next to the scan. Other models decide what each line is, and plain code joins
lines into paragraphs and sets the book's typography.

Today, on clean modern novels, about one wrong word is left every three to five pages
once you've answered its questions, at about half a question a page.

## Read more

- **[docs/primer.md](docs/primer.md)**: start here. The whole project from first
  principles, with pictures: how it works, how a change is judged, where the remaining
  errors are and what is expected to fix them.
- [docs/how-it-works.md](docs/how-it-works.md): the detailed tour, following one book
  through every stage, with the [diagram](docs/pipeline.svg) of the stages and the
  model behind each.
- [docs/design.md](docs/design.md): why each part is there, with the measurements that
  earn it its place.
- [docs/outlook.md](docs/outlook.md): how close it is, and what was tried that didn't help.
- [docs/golden-books.md](docs/golden-books.md): the books it is measured on.

## Running it

It needs a Mac with Apple silicon and plenty of memory (it is developed on an M4 Max
with 64 GB; two of the models are MLX builds), [uv](https://docs.astral.sh/uv/), and
[Ollama](https://ollama.com) with these models:

```sh
ollama pull glm-ocr:bf16
ollama pull qwen3.8:27b-nvfp4
ollama pull clef:27b
ollama pull clef-flash:9b
ollama pull hf.co/Piotr1215/Winnow-12B-GGUF:Q4_K_M
```

Also tesseract and epubcheck (`brew install tesseract epubcheck`).
[docs/models.md](docs/models.md) (Setup) has how each model is served.

```sh
uv sync
uv run roboscriptorium doctor   # is Ollama up, and do the models answer?
```

A book lives in a folder under `work/` with its `source.pdf` and a `book.toml`:

```toml
title = "Wij doden Stella"
author = "Marlen Haushofer"
language = "nl"
cover_page = 1
body_pages = [5, 71]   # the pages of the text proper
```

```sh
uv run roboscriptorium init scan.pdf         # drafts work/<name>/book.toml: language, where the text starts and ends
uv run roboscriptorium build work/stella    # → work/stella/stella.epub
uv run roboscriptorium review work/stella   # the questions, on http://127.0.0.1:8765/
```

A build takes about a minute a page the first time; every model's answer is saved, so a
rebuild after answering questions takes minutes. The model that weighs the readings and
the one that sorts lines are trained from the golden books into `work/models/`; without
them, `ROBO_OCR_TRUST=0` and `ROBO_SORTER=0` use fixed rules instead.

## The code

Python 3.13, in `src/roboscriptorium/`, one module per stage
([docs/modules.md](docs/modules.md) lists them). Tests never need a model server.

```sh
uv run ruff format . && uv run ruff check . && uv run pytest
```

Most of the work happens with coding agents, which follow [AGENTS.md](AGENTS.md): the
rules, the scope, and which document holds what. A person changing the code should read
it too. The rule that matters most: a change is kept only when the bench, built on the
golden books before and after, says it made the books better (the primer explains how).

Books, scans and everything derived from them stay out of git, in `work/`.

## License

[GNU Affero General Public License v3](LICENSE.md).
