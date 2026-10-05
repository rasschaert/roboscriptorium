# AGENTS.md — Roboscriptorium

Instructions for any coding agent (and human) working in this repo. Read it before
starting; keep it true.

## Standing rules

- **Keep this file up to date yourself.** When something is learned or decided —
  a design choice, a tool or model installed, a model that scored better, a pitfall
  found — update AGENTS.md in the same change. Add a dated line to the
  [Decision log](#decision-log). Don't wait to be asked.
- **Local only.** No cloud APIs or hosted models. All AI runs on this machine via
  Ollama and Ollaya.
- **No copyrighted material in git.** Books, page images, OCR output and golden
  pages live in `work/` (gitignored). Commit only code, prompts, question sets,
  configs and synthetic test fixtures.
- **Git:** signed commits straight to `main`, pushed whenever convenient; no PRs
  for now. Run lint and tests before every commit.
- **This file is the single source of agent instructions.** Claude Code reads
  AGENTS.md natively; don't add a `CLAUDE.md`.
- **Installs:** Homebrew tools, Python deps and Ollama/Ollaya models may be
  installed freely. Record each one under [Environment](#environment).
- **Handholding first.** Prefer flagging uncertain output for human review over
  guessing silently. Automation increases only as measured quality earns it.

## Purpose and scope

An end-to-end tool that turns books that aren't EPUBs into clean EPUB 3 files,
automated as far as possible.

- **Order of attack:** scanned PDF → born-digital PDF → other formats
  (MOBI/AZW3, DOCX, HTML, …).
- **Content order:** prose/fiction first; footnotes, figures, tables, verse later.
- **Book languages:** Dutch and English.
- **Fidelity:** exact wording and spelling, original paragraphs, italics and scene
  breaks. Drop print artefacts (page numbers, running heads, line-end hyphens).
  Fix only clear OCR errors — never "improve" the author's text.
- **Non-goals (for now):** loose photo folders, dewarping phone photos, cloud
  models, non-Latin scripts.

### Current target book

*Wij doden Stella* by Marlen Haushofer (Dutch). We iterate until this one comes out
right, then expand.

- Internet Archive scan (Scribe), 76 pages, 325×554 pt, 360 ppi MRC layers
  (JPX background/foreground + JBIG2 mask).
- Pages: 1 cover · 2–3 scan noise and IA stamp · 4 colophon · 5–71 body (one
  continuous text, no headings or scene breaks; page 5 is a sunk opening) ·
  72–75 blank or library barcode · 76 back cover. Page sizes differ per page (crops).
- Has a **hidden OCR text layer** (GlyphLessFont) of decent quality. Observed
  errors: page number "10" → "Io", missing spaces ("vijfjaar"), missing accents
  ("scenes" for "scènes"), line-end hyphenation, indented paragraph starts,
  specks read as characters ("haar-hadden" for "haar hadden", a stray "»"),
  a smudge under the text read as "><", misread page numbers ("Io", "Paes").
  Pages 5–9 have no page number in the text layer.
- That text layer is one OCR candidate among several, not the truth.

## Stack and conventions

- Python 3.13, managed with **uv**. Package and CLI are both named `roboscriptorium`.
- Layout: `src/roboscriptorium/` (src layout), tests in `tests/`.
  - `cli.py`: typer app, the entry point.
  - `config.py`: `Settings`, overridable via `ROBO_OLLAMA_URL`, `ROBO_OLLAYA_URL`
    and `ROBO_DECISION_MODEL`.
  - `clients/ollama.py`, `clients/ollaya.py`: thin httpx clients. All model calls go
    through these.
  - `book.py`: a book directory (`work/<book>/`) and its `book.toml`.
  - `pdf.py`: reads the PDF text layer as visual lines with boxes; renders pages.
  - `reflow.py`: lines → paragraphs (footer removal, indents, de-hyphenation).
  - `ir.py`: the IR (`Document`, `Paragraph` with `SourceRef`s back to page lines).
  - `epub.py`: IR → EPUB 3, hand-written with zipfile (no ebooklib).
  - `pipeline.py`: runs the stages for one book and caches artefacts under `stages/`.
- HTTP: `httpx`. Tests inject `httpx.MockTransport`, so unit tests never need a
  running model server.
- Lint/format: `ruff` (line length 100). Tests: `pytest`.
- Comments describe the code as it is now, briefly; history belongs in commit messages.

## Architecture

The pipeline runs as stages. Each stage writes resumable, per-page artefacts under
`work/<book>/`, so a rerun skips finished work and LLM calls get cached.

1. **Ingest / triage**: detect the format; PDF → born-digital or scanned; extract
   page images and any existing text layer.
2. **Page classification** (Ollaya): cover, blank, front matter, TOC, body, plate,
   back matter.
3. **Image preprocessing**: deskew, crop, contrast, split spreads.
4. **OCR**: several candidates (existing text layer, tesseract-nld, vision LLM);
   Ollaya picks or merges per block, with confidence.
5. **Line/block roles** (Ollaya): body, running head, page number, heading
   level, scene break, footnote.
6. **Reflow** (Ollaya + Ollama): de-hyphenation, paragraph continuation across
   pages, italics, correcting OCR errors in context.
7. **IR**: one semantic document model. Every input format feeds into it, and the
   EPUB builder reads only from it.
8. **Review UI**: a local web page showing flagged items next to the scan crop.
   Corrections are written back into the IR.
9. **EPUB 3 build**: metadata, cover, nav/TOC, CSS; validated with epubcheck.
10. **QA report**: a confidence summary and CER against the golden pages.

### Milestones

- M0: AGENTS.md, repo skeleton, uv project, Ollama/Ollaya client smoke tests
- M1: Stella end to end (crude), from the existing text layer to a valid EPUB
- M2: golden pages + evaluation harness
- M3: better OCR (multiple candidates + Ollaya arbitration) and reflow
- M4: review web UI
- M5: Stella "nailed"; loosen the thresholds; then a second book or format

## AI usage

Two kinds of model, used for different jobs:

- **Ollaya: decision models ("System One").** Answers bounded questions whose
  options are declared in advance, with a typed answer and a probability. It
  generates no text.
- **Ollama: generative models ("System Two").** Produces text: vision-LLM OCR,
  OCR-error correction, structure and metadata.

**Rule: if the answer comes from a list that's known in advance, use Ollaya. If it
needs new text, use Ollama.** Never prompt an LLM and parse its prose for a
decision that Ollaya can make.

### Ollaya

- Desktop app (`Ollaya.app`); serves at `http://127.0.0.1:11435`. No `ollaya` CLI
  on PATH.
- Jev/TypeSafe-compatible: `/v1/systemone`, `/v1/decisions`, `/v1/models`, plus
  the native `POST /api/decide`.
- Question types: `choice` (probability per declared option), `score` (ordinal
  scale), `noul` (probability that a statement is true).

```sh
curl http://127.0.0.1:11435/api/decide -d '{
  "model": "laya:multilingual",
  "state": "<text, or JSON describing the situation>",
  "questions": {"role": {"type": "choice", "instructions": "...",
                "criteria": {"page_number": "...", "body": "..."}}}
}'
```

The response holds `answers.<name>.choice`, `confidence` and `probabilities`.

- **Give decisions context.** A bare string is ambiguous. Pass a JSON state with
  the candidate plus its position on the page, its neighbouring lines and the page
  type. Confidence is **not** correctness: calibrate thresholds on golden pages
  before trusting them.
- Load time is ~1.5 s on the first call, then ~50 ms per decision.
- `noul` answers carry only `noul` (P(true)). `choice` and `score` carry
  `confidence` and `probabilities`. `OllayaClient.decide` normalises all three
  into `Answer(type, value, confidence, probabilities)`.

### Models

The model for each stage is chosen by its score on golden pages, then pinned
(never `latest`) and recorded here. More models can be pulled whenever needed,
for example OCR-specialised vision models, or `winnow` for decisions.

| Runtime | Model | Use | Status |
| --- | --- | --- | --- |
| Ollaya | `laya:multilingual` | Decisions on Dutch text | available, unevaluated |
| Ollaya | `laya:en` | Decisions on English text | available, unevaluated |
| Ollama | `gemma4:latest` | Vision OCR / correction candidate | available, unevaluated |
| Ollama | `hf.co/unsloth/Qwen3.6-27B-MTP-GGUF:Q6_K` | Correction / structure candidate | available, unevaluated |

## Environment

- Apple M4 Max, 64 GB RAM, macOS.
- Ollama 0.35.1 at `http://127.0.0.1:11434`.
- Ollaya at `http://127.0.0.1:11435`.
- Present: `uv`, `python3`, `pandoc`, calibre `ebook-convert`, poppler
  (`pdfinfo`, `pdftotext`, `pdfimages`).
- epubcheck (Homebrew).
- Not yet installed: tesseract (+ `nld` data).

## Running, reviewing, evaluating

A book lives in `work/<book>/` with `source.pdf` and a `book.toml`:

```toml
title = "Wij doden Stella"
author = "Marlen Haushofer"
language = "nl"
cover_page = 1
body_pages = [5, 71]   # inclusive; Ollaya page classification replaces this later
```

```sh
uv run roboscriptorium doctor            # are Ollama and Ollaya reachable and answering?
uv run roboscriptorium build work/stella # → work/stella/stella.epub
epubcheck work/stella/stella.epub        # must report 0 errors / 0 warnings
uv run ruff format . && uv run ruff check . && uv run pytest
```

(Pipeline, review UI and evaluation commands get added here as they land.)

- Golden pages: ~5–10 hand-corrected pages of the target book in `work/<book>/golden/`
  (gitignored). Quality is measured as CER plus structure metrics against them.

## Decision log

- 2026-10-05: Project started. Python + uv; local only (Ollama + Ollaya);
  scanned PDF first, with *Wij doden Stella* as the first target; Dutch and English;
  faithful text, clean ebook; human review via a local web UI, automation earned by
  measured quality; golden pages for evaluation; copyrighted material kept out of git;
  commits go straight to `main`.
- 2026-10-05: Ollaya smoke test. `laya:multilingual` labelled the bare
  string "Io" (a misread page number) as a heading at 0.93 confidence. Decision
  calls need context, and their thresholds need calibration.
- 2026-10-05: M0 skeleton landed (uv, typer, httpx, ruff, pytest; `doctor`
  command). With a context-rich state ("Io", last line, centred, previous page
  9), `laya:multilingual` answered `page_number` at 0.90. Given "12" with only
  position context and two options, it answered `body` at 0.65. laya is shaky on
  layout questions; evaluate `winnow` and richer state once golden pages exist.
- 2026-10-05: M1 landed. Stella builds from its existing text layer into an
  EPUB that passes epubcheck (244 paragraphs). Footer = short lines after a
  wide gap in the bottom fifth. Left margin = lower quartile of nearby line
  starts (follows skew, works on short pages). A line-end hyphen before a
  capital is kept.
