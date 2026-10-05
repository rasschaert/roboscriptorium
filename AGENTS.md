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
- **Read `HANDOVER.md` at the start of a session** for where work stopped, and
  rewrite it at the end of one.
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
  - `roles.py`: line roles via a decision model. A gate picks the doubtful lines
    (page edges, short centred lines), features include cross-page repetition,
    and answers are cached in `stages/decisions.jsonl`.
  - `reflow.py`: lines → blocks (headings, paragraphs; indents, de-hyphenation,
    punctuation spacing). Without roles it falls back to a footer heuristic.
  - `ir.py`: the IR (`Document`, `Paragraph` with `SourceRef`s back to page lines).
  - `epub.py`: IR → EPUB 3, hand-written with zipfile (no ebooklib).
  - `pipeline.py`: runs the stages for one book and caches artefacts under `stages/`.
  - `experiments/`: throwaway probes for comparing models (line roles, page types).
  - `golden/`: golden books. `manifest.py` (scans, fetch with sha256 check),
    `se.py` (derives the faithful reference text from a Standard Ebooks repo),
    `reference.py` (reads the reference chapters).
  - `evaluate.py`: CER, WER and paragraph F1 against a golden reference.
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

**How a new decision gets added** (the usual workflow for decision models):
prototype the question, collect a labelled set (from a golden book, or by
labelling with a large generative model on Ollama when there is none), refine
the rubric (option wording plus features the model can't see, such as
repetition across pages), then measure the decision model against that set.
**Start with ~10–60 items and scale up only once the results justify it.**
Enforce in code what is true by definition (a chapter heading appears once)
rather than hoping the model weighs it.

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

- Desktop app (`Ollaya.app`) plus the CLI at `/usr/local/bin/ollaya` (it may not be
  on the agent shell's PATH). Serves at `http://127.0.0.1:11435`.
- Models: `ollaya list`, `ollaya pull <model>`, `ollaya show <model>`. Use the
  documented CLI and API only. If they don't cover what's needed, ask the user
  rather than guessing endpoints.
- Vision (`decider:*-vision`): one base64 PNG per request in `images` (JPEG is
  rejected), at most ~1 MP (resized to multiples of 32), at most 10 options.
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
| Ollaya | `laya:multilingual` | Decisions on Dutch text | **unfit for line roles** (see log) |
| Ollaya | `laya:en` | Decisions on English text | **unfit for line roles** (see log) |
| Ollaya | `winnow:e4b` | **Line roles (in use)** | P(body) ≥ 0.9: keeps 147/150 body lines, catches ~99% of junk; ~270 ms/line. Reads a leading page number ("2 SENSE AND…") as a chapter heading; ignores numeric features |
| Ollaya | `winnow:12b` | Line roles candidate | Slightly better than e4b on 60 lines (0/30 body lost at 0.9), 2.6× slower (~700 ms/line) |
| Ollaya | `decider:2b-vision` | Page type from a page image | 19/23 sample pages right; low confidence on the hard ones, but confidently wrong on Stella p5 (an opening without heading). ONNX on **CPU**, ~3.8 s/page |
| Ollama | `clef-flash:9b` | Line roles and page types (candidate default) | Line roles: 60/60 at P(body) ≥ 0.5 (its probabilities are softer than winnow's, so don't use 0.9). Pages: 19/23, low confidence where it errs. ~0.8 s/line and ~3.9 s/page, measured under load. Endpoint `/v1/systemone`; raw base64 PNG/JPEG/WebP in `images`; up to 64 questions per call; 64K context. Confidence = how concentrated the probabilities are, not P(correct) |
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

### Golden books

Public-domain scans paired with a human-checked reference text, which is what
every change gets measured against. Each lives in `golden/<name>/` **in git**:
`manifest.toml` (the scans with URL and sha256, page ranges, and the reference
repo pinned to a commit), the derived chapters in `text/`, and `PROVENANCE.md`.

- The reference text is a **Standard Ebooks** production repo (CC0) with its
  `[Editorial]` commits undone (`golden derive`), so it is faithful to the
  scan SE proofread against. Their other fixes, including punctuation matched
  to that scan, are kept.
- Scans are never committed. `golden fetch` downloads them into
  `work/<name>--<scan>/` and writes its `book.toml`. Borrow-only scans have no
  `url`, so they have to be placed by hand and are then checked by sha256.
- Only the scan SE used is the same edition as the reference. Other editions
  differ in spelling, quote style, spaced dashes, "Mrs" vs "Mrs.", and so on,
  so their scores include edition differences, not just pipeline errors.

```sh
uv run roboscriptorium golden derive sense-and-sensibility
uv run roboscriptorium golden fetch sense-and-sensibility
uv run roboscriptorium eval work/sense-and-sensibility--tauchnitz-1864
# quick loop: chapters 1–9 only (~1 min with a cold decision cache)
uv run roboscriptorium eval work/sense-and-sensibility--tauchnitz-1864 --pages 7-45 --chapters 1-9
# heuristics only, no models
uv run roboscriptorium eval work/sense-and-sensibility--tauchnitz-1864 --no-models
```

`eval` builds the book, prints the scores and the most frequent differences, and
appends a line to `work/<book>/eval-history.jsonl`.

| Golden book | Scan | Notes |
| --- | --- | --- |
| sense-and-sensibility | `tauchnitz-1864` | SE's own scan; matches the reference; old Courier OCR layer; running heads, signature lines, "Digitized by Google" |
| sense-and-sensibility | `everyman-dent` | Dent, after 1946; yellowed; borrow-only |
| sense-and-sensibility | `everyman-1992` | Knopf 1992/1997; modern copyrighted introduction; borrow-only |

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
- 2026-10-05: Golden books instead of hand-corrected pages of the target book.
  The reference comes from Standard Ebooks with `[Editorial]` commits undone (458
  of 469 changes; 11 listed in PROVENANCE.md). A "modernisation pass" (the SE
  editorial changes as an optional pipeline stage) is a stretch goal.
- 2026-10-05: M2 baseline, existing text layers only, **no AI in the pipeline yet**:
  tauchnitz-1864 CER 8.05% / WER 5.18% / paragraph F1 0.589; everyman-dent
  5.79% / 4.68% / 0.553; everyman-1992 4.16% / 2.63% / 0.379.
- 2026-10-05: laya can't classify line roles. On 300 Tauchnitz lines (auto-labelled
  against the golden reference) with position and neighbour context:
  `laya:en` got 196/300 body-vs-other right and called most body lines
  "artifact"; `laya:multilingual` got 150/300 and called nearly everything
  "page_number". Next to try: `winnow:e4b`.
- 2026-10-05: Line roles with `winnow:e4b` (laya couldn't do them). Tauchnitz
  chapters 1–9: CER 7.30% → 4.23%, WER 5.18% → 3.48%, paragraph F1 0.592 →
  0.697, headings 0/9 → 9/9. That combines the roles, a cross-page repetition
  feature, the "a chapter heading appears once" rule, and closing spaces before
  punctuation.
- 2026-10-05: `clef-flash:9b` (Ollama) beats winnow on the line-role probe
  (60/60 vs 58/60) and matches decider on page types with better-calibrated
  confidence. It's the next default candidate; see HANDOVER.md.
