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
- **Quality over speed.** Pick the more accurate method even when it is several
  times slower: a careful edition (scanning, OCR, proofreading, typesetting, as
  Standard Ebooks does it) takes people weeks, so hours of machine time per book
  are cheap. Cache slow stages per book so reruns stay cheap, and run long
  builds in the background.

## Engineering practices

This project's bugs so far came from a handful of habits. Each rule below names
the mistake it prevents; check a change against them before committing.

- **A stage returns new data; it never edits its input.** Answers once rewrote
  the text layer in place, and the review, which keyed on that text, then lost
  them. If a function must change pages, it returns changed copies.
- **Say which version of the data a consumer gets.** Raw text layer or
  corrected copy, model roles or answered roles: name it in the type, field or
  docstring. A key, cache entry or line reference must come from the version it
  identifies.
- **Positions aren't identities.** A line index means nothing once lines are
  inserted or removed. Carry the original identity (`Line.source`) through any
  stage that changes the list.
- **Before finishing, find every reader of what you changed.** Grep the
  consumers of a function, field or file, and check each one still gets what it
  expects. The bugs live in the seams.
- **Test the seams.** A new stage or a change in what flows between stages gets
  a test through `pipeline.run` (see `tests/test_pipeline.py`), not only unit
  tests of its parts.
- **A rule that changes the author's text needs its counterexamples tested.**
  `close_quotes` turned "the animals' language" into a closing quote. Write the
  cases where the rule must *not* fire before the ones where it must; when the
  two can't be told apart, flag for review instead of rewriting.
- **Measure on every golden book, not the one you're fixing.** A line-grouping
  change that helped Dolittle doubled Sense's CER.
- **Shared resources are shared deliberately.** PyMuPDF isn't thread-safe: hold
  `pdf.PDF_LOCK` wherever threads may meet, render on one thread and pool only
  the model calls.
- **Caches survive interruption.** Write them whole (`files.write_atomic`), skip
  a cut-off last line in append-only logs, and version their format.
- **Keep what you'll need again under `work/`, never in a session scratchpad.**
  A scratchpad disappears with the session: probe outputs, a run's log and
  the sources a golden reference was derived from were lost that way. Source
  EPUBs live in `work/.cache/gutenberg/<ebook>.epub` and
  `work/.cache/publisher/<golden>.epub` (checked against PROVENANCE.md), probe
  outputs in `work/probes/`.

## Purpose and scope

An end-to-end tool that turns books that aren't EPUBs into clean EPUB 3 files,
automated as far as possible. The goal: an edition as careful as Standard
Ebooks' (weeks of scanning, OCR, proofreading and typesetting by people), in
hours, with a human only answering the questions the machine can't.

**Build the machine, not the book.** A general harness of compounded models,
not rules tuned to one book: several readings and judges that fail
differently, combined by voting and by each model's measured reliability per
kind of error, with the human's answers as labels that improve the weights.
Every job keeps a labelled set, so a newly released model is benchmarked and,
where it wins, plugged in. The target book comes out right because the machine
does.

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
  - `config.py`: `Settings`, overridable via `ROBO_OLLAMA_URL`, `ROBO_OLLAYA_URL`,
    `ROBO_DECISION_MODEL` and `ROBO_ROLE_MODEL`.
  - `clients/ollaya.py` also serves Ollama's `/v1/systemone`: `for_model` routes
    `clef-*` models there and everything else to Ollaya.
  - `clients/ollama.py`, `clients/ollaya.py`: thin httpx clients. All model calls go
    through these.
  - `book.py`: a book directory (`work/<book>/`) and its `book.toml`.
  - `pdf.py`: reads the PDF text layer as visual lines with boxes; renders pages.
  - `page.py`: what a page's layout says without a model, shared by roles,
    flags and reflow: geometry, edge lines, text repeated across pages, sunk
    pages, printed page numbers, heading labels and numerals, garbled lines.
    "Centred" has two meanings, named apart: `centred_on_page` (loose, chooses
    what to ask the model) and `centred_in_text` (strict, for flagging).
  - `roles.py`: line roles via a decision model. A gate picks the doubtful lines
    (page edges, short centred lines), features include cross-page repetition,
    and answers are cached in `stages/decisions.jsonl`. Rules in code then
    override the model where layout settles it; `LineRole.rule` names the rule
    that set a role ("" for the model's own answer).
  - `reflow.py`: lines → blocks (headings, paragraphs; indents, de-hyphenation,
    punctuation spacing). Without roles it falls back to a footer heuristic.
  - `ir.py`: the IR (`Document`; `Paragraph` and `Heading` with `SourceRef`s back
    to page lines; `Figure` with its image file, page box and caption).
  - `figures.py`: the pictures in the book. The layout model's figures on body
    pages (≥ 0.5) unless a human answered them as something else; trimmed
    where a caption overlaps; sideways plates turned upright (the human's turn,
    else the quarter turn in which the caption reads); captions from the
    human, else a sideways caption's reading. Each goes after the last block
    that starts above it; JPEG at 300 dpi, at most 1600 px.
  - `epub.py`: IR → EPUB 3, hand-written with zipfile (no ebooklib).
  - `pipeline.py`: runs the stages for one book and caches artefacts under `stages/`.
  - `experiments/`: throwaway probes for comparing models (line roles, page types).
  - `golden/`: golden books. `manifest.py` (scans, fetch with sha256 check),
    `gutenberg.py` (derives the reference text from a Project Gutenberg EPUB),
    `epub.py` (from a publisher's EPUB: headings by tag or class prefix),
    `se.py` (derives Standard Ebooks' text, kept for later style work),
    `reference.py` (reads the reference chapters, with their italic words).
  - `evaluate.py`: CER, WER and paragraph F1 against a golden reference.
  - `disagreements.py`: where output and reference differ, located on the scan;
    clearly garbled output and whitespace-only differences are auto-resolved.
    Verdicts (what the scan prints, plus a mistake category) are stored per scan
    and patched into the reference by `eval`.
  - `flags.py`: regions a human should check, i.e. what isn't plain running
    text: headings, lines dropped mid-page or without the model being sure,
    garbled text, centred or set-apart lines. Page furniture (repeated running
    heads, printed page numbers) isn't flagged. With layout regions it also
    flags pictures, captions, titles that aren't headings, and text the text
    layer lacks (one region per page, as an area rather than lines).
  - `layout.py`: DocLayout-YOLO regions per page from the page image, cached in
    `stages/layout.json`; run by `review`. Picture-only pages are also run turned a
    quarter, to find captions printed sideways.
  - `typestyle.py`: each line's type relative to the body text, measured on the
    page image (no model): size (tallest letters to baseline), stroke width, ink
    width per letter, capitals; cached in `stages/type.json`. `groups` gathers
    display lines (larger or capitals) set alike in one place on their pages;
    `roles.py` lets such a group share the role most of it got.
  - `italics.py`: italic words, from each text-layer word's stroke slant on
    the page image (no model; scans and born-digital PDFs alike), marked on paragraphs by aligning their
    words with their source lines'; cached in `stages/italics.json`. The EPUB
    sets them in `<i>`; `eval` scores italic words.
  - `missing.py`: printed lines the OCR layer lacks (bare chapter numbers,
    page numbers, short lines of dialogue). A layout region about one line tall
    with no text-layer line in it is read by glm-ocr and added to a copy of the
    page in reading order, before the line roles; figures, captions and regions
    a human answered are left alone. Scans only; cached in
    `stages/missing-lines.json`. Review answers find their lines again by text
    when lines are added above them.
  - `ocrcheck.py`: checks a scan's OCR layer (born-digital PDFs are skipped)
    against glm-ocr's reading of each body line's crop (`ROBO_OCR_MODEL`),
    cached in `stages/second-reading.json`. Where a line's readings differ, clef picks from
    the crop and winnow (`ROBO_CHECK_MODEL`) from the sentence; both agreeing
    with clef ≥ 0.3 applies the fix to a copy of the pages before reflow,
    anything else becomes an `ocr-doubt` review region.
    The judge is `judge_model` (clef:27b, `ROBO_JUDGE_MODEL`), not the role
    model. Suspects are saved to
    `stages/ocr-check.json`; `eval --no-check-ocr` skips the stage.
  - `ocr.py`: tesseract on a page region, for drafts a human corrects (text the
    text layer lacks, or reads as scraps because it is printed sideways).
  - `initials.py`: guesses the letter of a decorated initial: the letters that
    make the word beside it a word (book vocabulary plus the system word list),
    then the role model picks among them from the drawing.
  - `corrections.py`: a human's answers about regions (text, heading, drop,
    image, initial, caption, optionally the text as printed and the turn that
    makes the region upright; typed text for a missing region is
    inserted where the region sits, blank lines separating paragraphs), stored in
    `work/<book>/review/regions.jsonl` and applied to the line roles on the
    next build.
  - `review.py` + `regions.html` / `review.html`: the local review pages (stdlib
    HTTP server on 127.0.0.1), with scan crops: regions for any book, and
    disagreements for golden books.
- HTTP: `httpx`. Tests inject `httpx.MockTransport`, so unit tests never need a
  running model server.
- Lint/format: `ruff` (line length 100; `experiments/` excluded). Tests: `pytest`.
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
| Ollaya | `winnow:e4b` | Line roles (previous default) | P(body) ≥ 0.9: keeps 147/150 body lines, catches ~99% of junk; ~270 ms/line. Reads a leading page number ("2 SENSE AND…") as a chapter heading; ignores numeric features |
| Ollaya | `winnow:e4b` (as `check_model`) | Second opinion on OCR suspects, from the line's text only | Dolittle pp. 30–49: 74/90 right alone; its disagreeing with clef marks clef's errors (clef right on only 9/13 of those) |
| Ollaya | `winnow:12b` | Line roles candidate | Slightly better than e4b on 60 lines (0/30 body lost at 0.9), 2.6× slower (~700 ms/line) |
| Ollaya | `decider:2b-vision` | Page type from a page image | 19/23 sample pages right; low confidence on the hard ones, but confidently wrong on Stella p5 (an opening without heading). ONNX on **CPU**, ~3.8 s/page |
| Ollama | `clef-flash:9b` | **Line roles (in use)**; page types candidate | Line roles: 60/60 at P(body) ≥ 0.5 (its probabilities are softer than winnow's, so don't use 0.9). Pages: 19/23, low confidence where it errs. ~0.8 s/line and ~3.9 s/page, measured under load. Endpoint `/v1/systemone`; raw base64 PNG/JPEG/WebP in `images`; up to 64 questions per call; 64K context. Confidence = how concentrated the probabilities are, not P(correct) |
| Ollama | `gemma4:latest` | Vision OCR candidate | Teirlinck 12 pages: CER 0.70% (0.63% with the old-spelling prompt) but **modernises** old Dutch: 41 (27) reform spellings per 12 pages (`tusschen→tussen`, `oogenblik→ogenblik`), plus word swaps (`eenvoud→eenvoudig`). ~22 s/page. Never use alone; pair with tesseract |
| — | tesseract 5.5.3 + `nld` (tessdata_best) | Plain OCR candidate | Teirlinck 12 pages: CER 0.90%, no modernisation; errors are visual (`,`/`.`, mangled ellipses) and dropped short lines. <1 s/page |
| Ollama | `glm-ocr:bf16` | OCR candidate (0.9B, document OCR) | Teirlinck 12 pages: **CER 0.38%**, best yet, and faithful (1 accent misread, no modernising); reads `....` as `...`. ~15 s/page under load. Its Ollama template has no stop token: it reads the page, then starts over, so the reading is cut where its opening repeats (`probe_ocr.py`, `NEVER_STOPS`). Prompt `Text Recognition:` |
| Ollama | `deepseek-ocr:3b` | OCR candidate | Teirlinck 12 pages: CER 0.37% but **modernises** 10× (`vóor→vóór`, `éen→één`, `streelend→strelend`) and keeps line-end hyphens. ~9 s/page. Prompt `Free OCR.`; the grounding/markdown prompt loops |
| Ollama | `numind/nuextract3:q6_k` | **Metadata candidate**: front pages in, a filled JSON template out | Stella, Lady into Fox, Crime: all fields right, 4–10 s per book, given **all** front pages as images and an instruction to ignore stamps and handwriting and to describe this edition (without it: Stella's original publisher, an owner's inscription as author, a library barcode as ISBN). Read Crime's title page, which the text layer lacks, verbatim ("FORD MADOX FORD"). `experiments/probe_metadata.py` |
| Ollama | `numind/nuextract3` (BF16 safetensors, `latest`) | — | **Broken under Ollama 0.40**: gibberish from images and text alike. Use the GGUF `q6_k` tag |
| Ollama | `clef:27b` | **OCR-check judge (in use, `judge_model`)** | OCR suspects (Dolittle pp. 30–49, glm-ocr readings): 54/55 right; confident (≥ 0.8) on 46, all right, where clef-flash was confident on 16. ~3.4 s per suspect under load. **Worse at line roles**: Crime CER 0.63% → 0.98%, paragraph precision 0.966 → 0.695 (keeps page numbers, splits paragraphs), so clef-flash keeps that job |
| Ollama | `translategemma:4b` | Tried as Dutch→Dutch OCR | **Unfit**: with its translation prompt it paraphrases (`hief`→`heeft`, `trillend opwiegelen`→`trilde omhoog`) and modernises, CER 4.9% on one page; any other prompt gives empty output |
| Ollama | `translategemma:12b` | Tried as Dutch→Dutch OCR | **Unfit**: its translation prompt hallucinates a scene description; with the old-spelling prompt it transcribes at ~1.4% CER (worse than gemma4 and tesseract), modernises 12×, and loops on one page of 12 (Ollama aborts: "token repeat limit reached"). ~14 s/page |
| Ollama | `translategemma:27b` | Tried as Dutch→Dutch OCR | **Unfit**: old-spelling prompt, Teirlinck 12 pages: CER 0.99% (gemma4 0.63%), word swaps (`eenvoud→eenvoudig`, `onschuld→onschuldig`), 11 accent/spelling changes. Merged with tesseract it stays at 0.99% with 11 wrong words unflagged. ~30 s/page |
| Ollama | `llava:34b` | Tried as Dutch OCR | **Unfit**: on one Teirlinck page it invents text and loops ("Hij had geen twijfel aan de verdiensten van…" over and over), CER 406%. ~170 s/page |
| Ollama | `nemotron3:33b` | Tried as Dutch OCR | **Unfit**: thinks by default (107 s and empty output); with `think: false`, 7 s/page but CER 14% on one Teirlinck page: invented words (`dampwalmen→dampwaarneming`) and modernised (`zijne→zijn`) |
| — | DocLayout-YOLO (DocStructBench, `layout` group) | Page layout regions from the page image | 20 tricky pages, 0.1–0.5 s/page on MPS. Finds figures, captions, drawn initials, titles (Crime's bare "III"), and furniture as `abandon`. Sees printed text the OCR layer lacks (Dolittle p97 subtitle). Misses Boze tongen's spaced part title (`abandon`). Run on a page turned a quarter, it finds a landscape plate's caption (8/8 Dolittle plates, no false positives on 4 books) but not which way is up. See `experiments/probe_layout.py`, `probe_orientation.py` |
| Ollama | `hf.co/unsloth/Qwen3.6-27B-MTP-GGUF:Q6_K` | Correction / structure candidate | available, unevaluated |

## Environment

- Apple M4 Max, 64 GB RAM, macOS.
- Ollama 0.40.0 at `http://127.0.0.1:11434` (updated 2026-10-06 from 0.35.1; earlier scores were on 0.35.1).
- Ollaya at `http://127.0.0.1:11435`.
- Present: `uv`, `python3`, `pandoc`, calibre `ebook-convert`, poppler
  (`pdfinfo`, `pdftotext`, `pdfimages`).
- epubcheck (Homebrew).
- Dependency group `layout` (a default group, so plain `uv run` has it): `doclayout-yolo` with
  PyTorch, and the DocLayout-YOLO DocStructBench weights
  (`juliozhao/DocLayout-YOLO-DocStructBench`, `doclayout_yolo_docstructbench_imgsz1024.pt`,
  in the Hugging Face cache). Used by `review` to flag regions from page images.
- tesseract 5.5.3 (Homebrew, `eng`/`osd` only). The Dutch model is
  `nld.traineddata` from tessdata_best in `work/tessdata/` (pass
  `--tessdata-dir work/tessdata`); `tesseract-lang` (~650 MB) is not installed.

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

**Reviewing a book.** `uv run roboscriptorium review work/<book>` builds the
book, flags the regions that aren't plain running text and serves them on
http://127.0.0.1:8765/ next to scan crops. Each region asks what it is (radio buttons: `1` running text,
`2` heading, `3` drop, `4` image, `5` caption, `6` decorated initial on drawings,
with its letter guessed from the word it begins), with the pipeline's call
preselected, and takes the text as printed in a text box. Where OCR readings
differ it asks which one matches the scan instead: each reading on its own row,
the differing part marked, with the models that picked it (`a`, `b`, …; `e` for
something else). One Save button (`↵`; `⌘↵` in the text box) records the answer
and moves to the next unanswered region; arrows move through all regions. A
region with a box can be turned (`r`, ↺/↻) and read again by tesseract (`o`);
`-` and `+` zoom the crop out and back in. "Rebuild book" applies the answers and rebuilds
the EPUB. Flags come from the model's decisions before answers, so the list
stays put while you work.

### Golden books

Public-domain scans paired with a human-checked reference text, which is what
every change gets measured against. Each lives in `golden/<name>/` **in git**:
`manifest.toml` (the scans with URL and sha256, page ranges, the Gutenberg
source and chapter range), the derived chapters in `text/` with `PROVENANCE.md`,
and `standard-ebooks/` (SE's text, see below).

- The reference text is a **Project Gutenberg** transcription (`golden derive`),
  taken as it stands: Gutenberg keeps the printed edition's wording and
  spelling. Gutenberg rebuilds its EPUBs, so the committed `text/` is the pinned
  artefact; `PROVENANCE.md` records the EPUB's hash and the transcriber's notes
  (their own corrections to the print).
- **Standard Ebooks is not a fidelity reference.** Its texts are modernised and
  restyled, and undoing its `[Editorial]` commits restores whatever its
  starting text had, possibly from another edition. `golden derive-se` keeps it
  in `standard-ebooks/` for later style work; the SE manual of style is at
  https://standardebooks.org/manual/1.9.1/single-page.
- Scans are never committed. `golden fetch` downloads them into
  `work/<name>--<scan>/` and writes its `book.toml`. Borrow-only scans have no
  `url`, so they have to be placed by hand and are then checked by sha256.
- A scan of another edition than the transcription differs in spelling, quote
  style, spaced dashes, "Mrs" vs "Mrs.", and so on, so its scores include
  edition differences, not just pipeline errors.

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
appends a line to `work/<book>/eval-history.jsonl`. Given several books it scores
them one after another and ends with a line per book.

**Disagreements and verdicts.** Gutenberg is a transcription, not the scan, so
where the output disagrees with it a human decides what the scan prints:

```sh
uv run roboscriptorium golden review work/the-nature-of-a-crime--doubleday-1924  # → http://127.0.0.1:8765/
```

Keys: `1` Gutenberg is right (pick the pipeline mistake), `2` the scan prints
the output (edition difference or transcriber change), `3` type what the scan
prints, `0` unsure, arrows to move. Verdicts go to
`golden/<name>/verdicts/<scan>.jsonl` (in git), keyed on the reference words and
six words of context either side, so they survive pipeline changes. `eval`
patches them into the reference for that scan and reports the remaining
disagreements by mistake category.

| Golden book | Scan | Notes |
| --- | --- | --- |
| the-nature-of-a-crime | `doubleday-1924` | **The scan Gutenberg #75172 was made from**; 94 body pages, short; Times OCR layer; running heads |
| de-aanslag | `calibre-pdf` | Dutch, Mulisch, 51st printing. **Not a scan**: calibre's PDF of the retail EPUB, so its text layer is exact. For born-digital PDFs, page joins and (later) italics. **Copyrighted**, all text in `work/golden/` |
| lady-into-fox | `chatto-1922` | **Held out: score it to check that changes carry over, never tune on it.** 1922 first edition, same as Gutenberg #10337; one continuous text, no chapters; wood engravings. **EU copyright until 2051**: only the manifest is in git, the reference and verdicts live in `work/golden/lady-into-fox/` (`eu_copyright_until` in the manifest) |
| grand-hotel-europa | `ia-scan` | **Held out, like Lady into Fox.** Dutch, 2018, Pfeijffer; IA Scribe scan of the 11th printing (2019), 537 body pages. Reference: the retail EPUB, made from the 1st printing. Chapter label, title and numbered sections. Borrow-only scan; **copyrighted**, all text in `work/golden/`. Score it in slices (`--pages`/`--chapters`) |
| de-tuin-van-de-avondnevel | `ia-scan` | **Held out.** Dutch translation (Tan Twan Eng, Xander); IA scan of the 2014 paperback, reference the 2013 retail EPUB of the same translation and typesetter. Many italic foreign words. Pages 11–374, chapters 1–26. Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| goede-dochter | `ia-scan` | Dutch translation (Slaughter, HarperCollins Holland 2017); IA scan of the first printing, reference the retail EPUB of the same translation (typeset by Mat-Zet). The cleanest Dutch reference: **tune on it**. Pages 9–508, 25 chapters (a part title, then titled chapters). Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| vals-alarm | `ia-scan` | Dutch, 2011, Boersma (Verbum Crime). IA scan of the 2nd printing of the first edition, reference the retail EPUB. **Tune on it**: 48 chapter headings ("Vandaag", "1 Later", "2", "Epiloog") at the top of a new page. Pages 11–302. Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| villa-toscane | `calibre-pdf` | **Held out**, born-digital. Dutch, 2014, Van Rijn; calibre's PDF of the retail EPUB, like De aanslag. Novel = chapters 1–12 (13 is the colophon). **Copyrighted**, all text in `work/golden/` |
| the-story-of-doctor-dolittle | `stokes-1920` | Tenth printing, same as Gutenberg #501; full-page plates with captions, drawn initials the text layer drops |
| sense-and-sensibility | `tauchnitz-1864` | Not the edition of Gutenberg #161 (1811 first edition); old Courier OCR layer; running heads, signature lines, "Digitized by Google" |
| het-ivoren-aapje (probe only) | Gutenberg #28068 page images | Dutch, 1909, pre-1934 spelling; PNG page images and no text layer, so the OCR test bench. **EU copyright until 2038**: reference and images stay in `work/het-ivoren-aapje/`, see `experiments/probe_ocr.py` |

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
- 2026-10-05: Full-book Tauchnitz with winnow roles: CER 8.05% → 4.68%, WER
  5.18% → 3.34%, paragraph F1 0.589 → 0.667, headings 28/50.
- 2026-10-06: References switched from Standard Ebooks to Project Gutenberg.
  Undoing SE's `[Editorial]` commits put back spellings from SE's starting
  text, Gutenberg #161 of the 1811 edition: the reference said "shewing" where
  Tauchnitz prints "showing". SE is kept for later style work only. New golden
  books: *The Nature of a Crime* (Gutenberg made from the same scan) and
  *Doctor Dolittle* (same printing). Sense now has no same-edition reference.
- 2026-10-06: `clef-flash:9b` replaces winnow for line roles. Tauchnitz chapters
  1–9 against the (old) SE reference: CER 4.23% → 3.73%, WER 3.48% → 3.04%,
  paragraph F1 0.697 → 0.728, headings 9/9.
- 2026-10-06: Disagreements get human verdicts instead of trusting any
  transcription blindly: `roboscriptorium review` serves a local page with scan
  crops. Garbled output (stray symbols, words in neither the reference nor
  `/usr/share/dict/words`) and whitespace-only differences are auto-resolved.
  Sense chapters 1–9 still leave ~300 for review (another edition), Crime far
  fewer (same scan). Full-book Tauchnitz against Gutenberg: heuristics CER 7.23%,
  winnow 4.98%, clef 4.75% (WER 3.15%, paragraph F1 0.682, headings 28/50).
- 2026-10-06: OCR candidates on 12 pages of *Het ivoren aapje* (Teirlinck, 1909;
  Gutenberg #28068 publishes its page images; the transcribers' corrections are
  reverted to the print via their "Bron:" notes). Vision LLMs modernise old Dutch
  spelling, even when told not to; tesseract doesn't but misreads punctuation
  and drops short lines. Merging them (spelling-reform differences take
  tesseract's form, every other disagreement keeps gemma4's and is flagged)
  gives CER 0.54% against 0.63% (gemma4) and 0.90% (tesseract), 89 flags (56
  real errors) and almost no unflagged wrong words. This is the M3 OCR design:
  several candidates, rules for known biases, flags for the rest.
- 2026-10-06: Full-book headings 28/50 → 50/50. The repetition feature matched
  "CHAPTER II." and "CHAPTER III." as the same text (letters ≥ 85% similar),
  so over 50 chapters every heading looked like a running head and was
  demoted. A trailing Roman numeral must now match exactly. Crime with clef
  roles: CER 0.72%, WER 0.53%, paragraph F1 0.965, headings 5/8.
- 2026-10-06: Tried a page-level feature for line roles ("text begins 26% down
  this page; most pages begin at 8%"), since chapter pages open sunk. clef
  ignored it: Crime headings 5/8 → 3/8, CER 0.72% → 0.82%; reverted. Bare
  Roman numerals ("V", "VI") stay ambiguous to clef (called page numbers at
  ~0.1 confidence). Layout facts like this belong in code, not in the state.
- 2026-10-06: Visual lines now group word boxes by vertical overlap (≥ half a
  fragment's height) instead of tops within 3 pt: OCR layers box each word, and
  one line's tops differ by up to ~5 pt. Sense had 560 fragmented lines,
  Dolittle 1,450. With clef roles, against Gutenberg: Sense full book CER 4.75%
  → 3.02%, WER 3.15% → 1.39%, paragraph F1 0.682 → 0.805, headings 49/50;
  Dolittle CER 21% → 5.48%, paragraph F1 0.43 → 0.839 (but 27 headings for
  21 chapters: its two-line headings split). Crime unchanged (0.72%).
  The text-layer cache now carries a version and rebuilds when it changes.
- 2026-10-06: `eval` now matches headings against the reference chapter
  headings (an order-preserving alignment maximising similarity) and reports
  spurious ones; it used to count headings only. Correction: the "50/50" above
  was 49 real headings plus one false one. Repeats across pages now use an edit
  budget (one edit per 10 letters) instead of a similarity ratio, because
  "THE FIFTH CHAPTER" and "THE SIXTH CHAPTER" were ≥ 85% similar; a heading
  repeated on 3+ other pages is a running head (was 5). Headings now: Sense
  49/50 (+0 spurious), Dolittle 14 → 20/21 (spurious 13 → 5), Crime 4/8 (+1).
- 2026-10-06: Garbled lines (under half the tokens look like words: OCR read
  from a drawing or a smudge) are now line-role candidates wherever they sit,
  and clef calls them artefacts. Dolittle CER 5.48% → 4.82%, paragraph F1
  0.839 → 0.861; Sense 3.02% → 3.00%. Plate captions still end up in the text
  (a caption role belongs with the figures work).
- 2026-10-06: `translategemma:27b` as OCR: CER 0.99% on the 12 Teirlinck pages,
  worse than gemma4 (0.63%), and the merge with tesseract gains nothing (0.99%,
  11 unflagged wrong words). No size of translategemma is worth keeping.
- 2026-10-06: `llava:34b` as OCR: one Teirlinck page took 170 s and came back
  as invented, looping Dutch (CER 406%); not run on the full sample.
- 2026-10-06: Bare Roman numeral headings get a rule in code, since clef calls
  them page numbers: on a sunk page (text starts ≥ 8% of page height lower than
  on most pages), a bare numeral in the first 3 lines is a chapter heading
  ("Ill" read for "III" is normalised). A numeral joins the heading line above
  only after CHAPTER/PART/BOOK (or the Dutch words), so a book title over "I"
  stays separate. Crime headings 4/8 → 8/8 (+1: the book title), CER 0.72% →
  0.71%, paragraph F1 0.965 → 0.972; Sense and Dolittle unchanged.
- 2026-10-06: More chapter-opening rules for Dolittle. The first 3 lines of a
  sunk page always go to the model (a drop cap shortens the median line, so a
  wide centred heading failed the centring gate). Lines between a chapter heading
  and the text are its title (clef called "PUDDLEBY" an artifact, dropping it). A
  heading line containing CHAPTER/PART/BOOK starts a new heading, so the book
  title above it stays separate. A "heading" that carries the page's printed
  number (file page minus the book's usual offset) or repeats an earlier
  heading line is a running head. Dolittle headings 20/21 (+5) → 21/21 (+1: the
  book title), CER 4.82% → 4.80%; Sense 49/50 and Crime 8/8 unchanged.
- 2026-10-06: First held-out golden book, *Lady into Fox* (Chatto & Windus 1922
  = Gutenberg #10337), never to be tuned on. A golden book under EU copyright
  sets `eu_copyright_until` and keeps its text and verdicts in `work/golden/`.
  First score: CER 0.93%, WER 0.33%, paragraph F1 0.841. Most errors: this
  printing spaces opening quotes (`" What`). *De kleine Johannes* was rejected:
  the scan is a 1986 Querido edition in modern spelling, Gutenberg #10819 is in
  the old spelling.
- 2026-10-06: `nemotron3:33b` as OCR: CER 14% on one Teirlinck page with
  thinking off (empty output with it on). Of all the vision models tried,
  only gemma4 is worth pairing with tesseract.
- 2026-10-06: First born-digital PDF, *De aanslag* (calibre's PDF of the retail
  EPUB): CER 0.64% → 0.15%, headings 6/22 → 26/26. Ligatures (ﬁ, ﬀ, ﬃ) are
  spelled out. A bare number opening a page, above body text and not near the
  printed page number, is a section number; a page offset needs ≥ 3 pages and a
  quarter of the edge numbers to agree (one "1945" had set it to −1936). Lines
  under a heading that survives the running-head checks are its subtitle on
  any page. A lowercase line under a body line that stops mid-sentence is body
  (clef dropped short last lines like "kijken."). A line-end hyphen stays in a
  compound that has hyphens elsewhere ("Mens-erger-je-niet"); a spaced dash
  keeps its spaces. Reference fixes: spans join without spaces ("nsb-leider"),
  and every EPUB heading is its own chapter. Crime 0.71% → 0.63%, Dolittle
  4.80% → 4.77%, Sense 3.00% → 2.99%; held-out Lady into Fox unchanged (0.93%).
  Still lost on De aanslag: inscriptions and signs set apart in the text,
  which clef calls artifacts; these need flags for review, not more rules.
  The font's private-use glyphs (U+E000 "Th", U+E005 "fj") come out as junk.
- 2026-10-06: Region review for any book: `roboscriptorium review` flags what
  isn't plain running text and takes a human's answer per region, applied on
  the next build (the golden disagreement page moved to `golden review`).
  Flags per book: De aanslag 48, Crime 12, Lady into Fox 4, Dolittle 85,
  Sense 118 (half of them headings). clef's P(body) doesn't separate page
  furniture from real text (running heads score up to 0.4), so furniture is
  recognised by repetition and page numbers instead. A line counts as centred
  for flagging only with equal margins on both sides and under 80% of a line.
- 2026-10-06: DocLayout-YOLO probe on 20 tricky pages: worth adding as a flag
  source for pictures, captions, titles without a heading, and text the OCR
  layer lacks (Dolittle chapter 9's subtitle is printed, not drawn: the layer
  just skipped it). Not trusted alone: it called Boze tongen's part title
  furniture.
- 2026-10-06: Layout regions feed the review flags. Dolittle: 131 regions, among
  them 51 pictures and 24 captions, and one whole page (p97) whose text the OCR
  layer lacks except its heading; the review page drafts it with tesseract
  (near perfect, bar the drawn initial) for the human to correct.
- 2026-10-06: A heading keeps its label and title as separate lines ("THE FIRST
  CHAPTER" / "PUDDLEBY", written with `<br/>` in the EPUB); a title wrapped over
  two lines stays one. First score for Boze tongen (Dutch scan, omnibus
  reference): CER 1.36%, WER 1.15%, paragraph F1 0.749 (recall 0.655), headings
  13/18 (+2). Most differences: the OCR layer reads ‘ as " and drops closing
  quotes, and reads a capital I as l (`lets`, `leder`, `ledereen`).
- 2026-10-06: Decorated initials: a reviewer answers a picture region with the
  letter it shows; the letter goes back in front of the text beside the
  drawing ("O" + "NCE"), the lines beside it continue the paragraph, and the
  EPUB sets it as a CSS drop cap (`span.initial`). The artwork itself waits for
  the figures work.
- 2026-10-06: Initial-letter guesses: tesseract (single character) and gemma4
  both misread decorated letters (`E`/`J` for an O). Restricting to the letters
  that complete the word beside the drawing, then asking clef with the crop,
  got 8/8 Dolittle initials (0.5–2 s each); with no word beside it (a page the
  text layer lacks) it guesses nothing.
- 2026-10-06: Sideways text (a landscape plate's caption) shows in the text
  layer as a column of 1–3 character scraps. Such a page gets one region; the
  review page reads it turned 90° and 270° and keeps the turn that gives words
  (tesseract's own orientation detection said 180° on a picture page), shows
  it upright and drafts its text.
- 2026-10-06: Whole-page orientation probed on Dolittle's six suspect pages
  (scraps or garbled text layers): scoring four turns by tesseract word
  confidence ties 90° with 180°; by dictionary words it is right on 3/6
  (drawings read as junk words); on the scrap lines' strip alone it fails
  where scraps spread over the drawing. Not adopted; see HANDOVER.md.
- 2026-10-06: Sideways plates found with the layout model. A page with a picture
  (≥ 0.5) and no text is run again turned 90° and 270°: on a landscape plate the
  model then finds the caption, and on blank, stamp or title pages nothing
  (the figure gate removes Crime's bindery stamp and Lady into Fox's half-title).
  It labels the strip under a figure a caption whichever side is up, so the
  review page still picks 90° or 270° by reading the caption box with
  tesseract (tesseract's default mode reads a vertical block on its own, so it
  only separates 90° from 270°, never upright from sideways). Dolittle: 8/8
  plates (pp. 6, 25, 57, 83, 87, 90, 107, 200), all turning 90°; the earlier
  "truth" of 270° for pp. 83 and 87 was wrong.
- 2026-10-06: Specks (a quote mark's second stroke read as "1", "7", "5")
  became one-character lines that the model dropped and the review flagged.
  Letting a fragment join a line when the overlap covers half of the shorter
  of the two glued lines together in Sense (CER 2.99% → 5.99%); rejected. Dropped
  specks are now just not flagged.
- 2026-10-06: Boze tongen doesn't indent paragraphs. In justified text a line
  after one that ends a sentence well short of the margin now starts a
  paragraph (not when it opens lowercase or with punctuation): Boze tongen
  paragraph recall 0.655 → 0.768, precision 0.875 → 0.888; the others
  unchanged. Of its remaining missed breaks, ~160 are mid-line in the scan
  (edition differences) and ~60 follow a full line (undetectable).
- 2026-10-06: A short line holding CHAPTER/PART/BOOK (or HOOFDSTUK/DEEL/BOEK)
  always goes to the role model: Sense's "» CHAPTER XXV." was off centre
  because of a speck. Sense headings 49/50 → 50/50.
- 2026-10-06: Private-use glyphs (a font's own Th and fj ligatures) are
  spelled out by tesseract (eng) reading the rendered word: what it reads
  between the known letters must be a ligature, majority per glyph. Dutch
  tesseract reads Th as "Ih". De aanslag: 7/7 resolved, CER 0.15% → 0.136%.
- 2026-10-06: Old OCR layers (Dolittle, Sense) flatten quotes to straight ones
  and often read a closing ” as `'` ("asleep in his chair'"). In
  straight-quoted text, a word-final `'` while a `"` is open and no `'` is
  now closes the `"`. Dolittle CER 4.76% → 4.60%, WER 2.18% → 2.02%; Sense
  unchanged. Newer layers keep the printed curly quotes.
- 2026-10-06: OCR check probe (`experiments/probe_ocr_check.py`), Dolittle pp.
  30–49: tesseract reads each page; where its reading of a visual line
  differs from the text layer's (widened to whole words), clef picks between
  the two from the crop. 99 suspects (~5/page), 90 with a truth from the
  reference: tesseract right 56, text layer 34, clef 79 (88%). Clef at
  confidence ≥ 0.5: 49/50 right; below 0.5: 30/40. The layer loses em-dashes
  (`up if` for `up—if`) and closing ”; tesseract misreads opening “ as ‘, and
  clef can't tell those apart. ~0.8 s per suspect. Second opinions on the
  same 90: decider:2b-vision (crop) 74 right, winnow:e4b (the line as text, no
  image) 74; each disagrees with clef 13 times, where clef is right only 9.
  Applying only when clef and winnow agree and clef ≥ 0.3: 62 applied, 1
  wrong, 28 left for review. Agreement isn't proof: the wrong unanimous cases
  are the opening-quote blind spot every model shares.
- 2026-10-06: Book metadata from the front pages with `nuextract3:q6_k`
  (vision, JSON template): right on Stella, Lady into Fox and Crime once it
  sees every page before the body and is told to ignore library stamps and
  handwriting and to describe this edition, not the original. The candidate
  for filling `book.toml` and the EPUB's metadata, with a human confirming.
- 2026-10-06: Models per job, chosen from measurements (the user leaves the
  choice to the agent): clef-flash for line roles, clef:27b to judge OCR
  suspects, winnow:e4b as the text-only second opinion, glm-ocr and tesseract
  as the second readings (glm-ocr for letters, tesseract for dashes). A bigger
  model isn't better at everything: clef:27b judges crops far better and line
  roles worse.
- 2026-10-06: OCR check stage in the pipeline (`ocrcheck.py`, tesseract as the
  second reading). Dolittle: CER 4.60% → 2.16%, WER 2.02% → 1.84%, paragraph
  P/R 0.808/0.942 → 0.815/0.951; 624 suspects: 376 fixed, 105 kept, 143 for
  review (~0.7 per page).
- 2026-10-06: Two document-OCR models on the Teirlinck bench: `glm-ocr`
  CER 0.38% with no modernising (best so far, against gemma4 0.63% and
  tesseract 0.90%); `deepseek-ocr:3b` 0.37% but modernises old accents and
  spelling. glm-ocr is the candidate to replace tesseract as the OCR check's
  second reading.
- 2026-10-06: **Quality over speed** (standing rule above). The OCR check's
  second reading is glm-ocr on each line's crop, not tesseract on the page,
  though it is ~10× slower (~30 s against ~3 s per page). On Dolittle pp.
  30–49: 67 suspects instead of 99; the second reading right 93% of the time
  against 62%; clef right 96% against 88%; with clef and winnow agreeing and
  clef ≥ 0.3, 47 fixes applied with none wrong and 8 left for review, against
  62 applied with 1 wrong and 28 for review.
- 2026-10-07: Figures stage. Dolittle: 48 pictures in 2.5 s, all 7 sideways
  plates turned upright, their captions read (6 of 7 verbatim, `Tord` for
  `Lord`) and trimmed out of the picture, the decorated initials answered as
  such left out. Shared page analysis moved from roles.py to page.py, with
  identical roles, reflow and flags on all six golden books; `LineRole.rule`
  names the rule that overrode the model.
- 2026-10-07: OCR check crops fixed. Crime's text layer gives lines boxes about
  twice the print's height (font metrics), so glm-ocr read the neighbouring line
  into its reading; a line's crop is now its words' boxes together. Crops (the
  line's, and a suspect's at a line end) also reach one em past the line, where
  the text layer misses dashes: Dolittle's line-end em dashes were cut to
  hyphens, which the judge then applied ("live on-" + "even" → "oneven").
  Joining two words is no longer a punctuation-only difference the vision judge
  decides alone, and a `¬` line-end hyphen equals `-`. Crime: suspects 928 →
  236, for review 453 → 54, CER 0.53% → 0.52%. Dolittle: CER 1.89% → 1.84%,
  WER 1.92% → 1.81%, applied fixes the reference contradicts 24 → 3, for review
  100 → 107. Held-out Lady into Fox: CER 0.93% → 0.92%, WER 0.309% → 0.305%.
- 2026-10-07: Second held-out book, *Grand Hotel Europa* (Dutch, a scan with an
  OCR layer, like Stella), since every other Dutch golden book has been tuned on.
  `golden derive` now reads a `<div>` holding no other blocks as a paragraph:
  its EPUB has no `<p>`. Boze tongen's and De aanslag's references re-derive
  byte-identical. Cold-start score, chapters 1–3 (pp. 15–44): text layer alone
  CER 2.51%, WER 2.38%, paragraph F1 0.772, headings 0/16; full pipeline CER
  1.92%, WER 1.80%, F1 0.814, headings 3/16 (the 16 count each chapter label,
  title and section number); 146 OCR suspects, 74 for review.
- 2026-10-07: Italics. Page-level "are there italic words?" with clef-flash:
  11/15 italic pages at P ≥ 0.7, no false alarms; clef:27b says yes to every
  page. Better and model-free: each text-layer word's **stroke slant** on the
  scan (shear the ink above the baseline; the angle with the most peaked column
  profile). Dolittle: italic median 16°, roman −1°; at ≥ 8°, 59/61 italic words
  caught, 25 of 20,605 roman words flagged, nearly all of them italic in print
  but unmarked by Gutenberg (running heads, phrases the truth didn't place).
  Below the baseline is left out: a y's descender leans like italic. Crime,
  same thresholds: 23/25, the 9 flags italic foreign words. ~0.2 s/page
  (`experiments/probe_italic_words.py`). References now keep `<i>`/`<em>` as
  italic words (`Chapter.italic`), also through verdict patches; plain text
  unchanged on every golden book. Publisher EPUBs that italicise by CSS class
  (the Dutch ones) don't carry italics yet.
- 2026-10-07: Italics stage (`italics.py`), slant ≥ 8° on words of 2+ letters
  (single letters between italic words fill in). Italic words, precision /
  recall: Crime 0.952 / 0.909, Dolittle 0.833 / 0.814 (7 of 9 misses are
  dash-glued words with one half italic, `instead—they'll`, which need marks
  below the word), held-out Lady into Fox 0.315 / 0.895 (54 marked against 19;
  on the tuned books such extras were mostly italics Gutenberg left unmarked,
  unverified here). CER and the rest unchanged; epubcheck clean.
- 2026-10-07: Italics on born-digital PDFs too, and a word is measured only
  if it has an upright stem: two stems (h, n, u count two, m three), or one in
  a word without diagonal letters. Two-letter words like "zo" and "ze" read as
  italic in any type (De aanslag precision 0.377 at two letters). A line is
  measured only when its words spell it (`pdf.spells`, private-use ligatures
  allowed). Italic precision / recall: Crime 0.951 / 0.886, Dolittle 0.872 /
  0.791, De aanslag (now with italics from its CSS classes) 0.987 / 0.855.
- 2026-10-07: Two more Dutch golden books from the user. *De dode kamer*: a
  scan with a reference of the same first edition, the first such Dutch book,
  so it is tuned on. Text layer alone, chapters 1–4 (pp. 19–57): CER 5.31%,
  WER 5.71%, paragraph F1 0.889, headings 0/4, italics 0.837 / 0.903.
  With the OCR check: CER 5.20%, but 92% of that is ~2 pages of print the
  EPUB lacks (pp. 50–51); without them, text layer ~0.50% → ~0.39%. The
  EPUB itself has OCR errors ("lorras", "sucretaresse"), so it needs
  verdicts. Pipeline misses: `*****` scene breaks, chapter titles.
  `experiments/probe_big_diffs.py` lists the largest differing stretches.
  *Villa Toscane*: born-digital, held out. Boze tongen's italic score (0.13 /
  0.05) is an edition difference: the omnibus sets the diary in italics, the
  2002 print in an upright sans-serif. Boze tongen pp. 11–132 with the new
  crops: CER 1.68% → 1.53% with the OCR check, paragraph F1 0.845 → 0.866.
- 2026-10-07: *De tuin van de avondnevel*, a third held-out book: a Dutch
  scan whose reference is the same translation's retail EPUB. Its EPUB fills
  blank lines with ".." paragraphs, so a manifest's `blank_classes` now leaves
  such paragraphs out.
- 2026-10-07: *Goede dochter* (Dutch translation, first printing, with the
  publisher's own EPUB) becomes the main Dutch tuning book: De dode kamer's
  EPUB was made by OCR and misses text, Boze tongen's is another edition.
- 2026-10-07: Italics: ink is what is darker than each page's Otsu threshold,
  not a fixed grey of 128. Goede dochter's pale scan prints in grey (120–140),
  so most strokes went unseen: italic words 0.617 / 0.245 → 0.958 / 0.828
  (pp. 9–64). Crime 0.951 → 1.000 precision; De aanslag unchanged; Dolittle
  0.872 → 0.850 precision; De dode kamer 0.837 / 0.903 → 0.831 / 0.898.
- 2026-10-07: Golden books culled to those whose reference matches the scan
  closely enough to tell pipeline errors from edition differences. Retired
  (files moved to `work/retired/`, manifests in git history): Boze tongen
  (omnibus reference with revisions, the diary italic in one and not the
  other), De dode kamer (its EPUB was made by OCR and lacks printed text),
  Sense's two Everyman scans (other editions, never scored), and Goede
  dochter's eighth printing (same text as the first).
- 2026-10-07: *Vals alarm*, a second Dutch tuning book (another publisher and
  typesetter). Text layer alone, whole book: CER 0.79%, WER 0.42%, paragraph
  F1 0.891, headings 0/48, italics 0.697 / 0.736. Its errors: opening ‘ read
  as " or lost, a period lost before a closing quote, `zon` for `zo'n`.
- 2026-10-07: First held-out score of *De tuin van de avondnevel*, chapters
  1–3: text layer alone CER 0.72%, WER 0.60%, F1 0.931, headings 0/3; full
  pipeline CER 0.41%, WER 0.25%, F1 0.946, headings 3/3 (389 OCR suspects: 179
  fixed, 148 for review). The OCR check carries over to an unseen Dutch scan.
- 2026-10-07: Dutch print sets dialogue in ‘…’, and Internet Archive's OCR reads
  many openings as “ (Vals alarm 226 “ in the layer against 6 in print, Goede
  dochter 777 against 101). In a book whose text opens with ‘ more than twice
  as often as with “, a “ that the next quote mark (apostrophes aside) doesn't
  close as ” or ’’ becomes ‘. Text layer alone: Goede dochter pp. 9–64 CER
  0.45% → 0.40%, F1 0.943 → 0.957; Vals alarm CER 0.79% → 0.74%, F1 0.891 →
  0.918. De aanslag unchanged (its real “ close with ” or ’’); English books
  are double- or straight-quoted, so the rule doesn't run. Still open: ‘ the
  layer drops altogether, and a period lost before a closing ’.
- 2026-10-07: Missing-lines stage measured. Vals alarm pp. 11–60 (full
  pipeline): 13 lines read back, all printed (7 chapter numbers, 5 page
  numbers, one `'Ja.'`); headings 2/10 → 8/10 (+0 spurious), paragraph F1
  0.929 → 0.937, CER 0.48% either way. Dolittle: 71 lines added, all printed
  (mostly furniture, which the roles drop; four text lines of p97, whose layer
  lacks them), CER 1.84% → 1.80%, headings and paragraphs unchanged. Crime
  unchanged (one page number). Goede dochter pp. 9–64, full pipeline before
  the stage and the quote rule: CER 0.29%, WER 0.24%, F1 0.958, headings 2/4.
- 2026-10-07: Closing quotes in the OCR check. On Vals alarm the layer reads
  `.’` as `’`, glm-ocr as `.`, tesseract as `.'`, so no reading the judges saw
  was right. Readings now take a curly-quoted layer's quote style, and where
  readings of one word each lost a different trailing mark (one a period, one
  the quote) the word with both is offered too; the judges still decide. Vals
  alarm pp. 11–60: CER 0.48% → 0.47%, paragraph F1 0.937 → 0.948; Crime CER
  0.52% → 0.50%, F1 0.976 → 0.983; Dolittle unchanged. Many combined readings
  still go to review: clef often misses the small period and keeps the
  layer's `zijn’`, and winnow can't tell `zijn.` from `zijn.’` without the
  open quote earlier in the paragraph.
- 2026-10-07: The OCR check's text judge (winnow) now reads the lines before
  and after the suspect line, where a quote opens or a sentence goes on. Vals
  alarm pp. 11–60: WER 0.20% → 0.18%, applied 109 → 114, review 110 → 108;
  Dolittle CER 1.80% → 1.78%; Crime unchanged in CER, but one italic word
  lost (winnow now keeps `fiancee.` on p61). Against clef's sure picks (≥ 0.8)
  winnow agrees, with context / without: Crime 56 / 65 of 79, Dolittle 397 /
  379 of 419, Vals alarm 31 / 31 of 44 (`experiments/probe_reader_context.py`).
  15–20% of its answers flip with the added lines: winnow is a noisy judge,
  which argues for trust measured per model and kind of error over fixed
  thresholds. `eval` now prints and records the OCR check's counts (fixed,
  kept, for review). Crime: 236 suspects, 46 fixed, 123 kept, 67 for review.
- 2026-10-07: A number with a short title opening a sunk page ("1 Later") is a
  chapter heading, whatever the page number: a page number with words beside it
  is a running head, and chapter openings carry none. clef called both of Vals
  alarm's titled numbers page numbers (at 0.07). Vals alarm pp. 11–60 headings
  8/10 → 10/10, paragraph F1 0.948 → 0.950; Crime, Dolittle, De aanslag
  unchanged. On Vals alarm the sunk pages are exactly the chapter openings.
- 2026-10-07: Sunk pages are also those whose running text (the first line of
  near full width) starts low, since a chapter label can sit at the usual
  height above a sunk opening (Goede dochter's "EEN"). On a sunk page, a short
  first line set apart from the text (or alone on the page) is the chapter
  heading unless the model calls it body, it repeats on other pages, or it is
  garbled. Goede dochter pp. 9–64 headings 2/4 → 3/4; Vals alarm, Crime,
  Dolittle, De aanslag unchanged. Still missed: the part title "DONDERDAG 16
  MAART, 1989", alone on p9.
- 2026-10-07: Critical review of the approach (see HANDOVER.md). The
  `roles.py` overrides don't carry over to held-out books (Villa Toscane
  headings 0/12, Grand Hotel Europa 3/16), the role model sees no typography,
  errors every reading shares go unflagged, and verdicts are unsettled so
  small CER gains are noise. New direction: no new layout rules; type-size
  features and book-wide heading clusters, learned trust over thresholds, a
  Dutch lexicon, grouped review questions, changes reported as error counts.
- 2026-10-07: Type measured per line from the scan (`typestyle.py`). Headings
  stand apart on every tuning book: Goede dochter 1.5× the body text, Vals
  alarm 1.3–1.7×, De aanslag 1.7–1.9×, Dolittle in letterspaced capitals;
  page numbers are smaller (~0.7×). Crime's bare numerals differ only by being
  capitals (`experiments/probe_type_features.py`). Telling clef the type in the
  state ("larger than the body text (1.5×), in capitals") changed none of its
  answers on Goede dochter pp. 9–64, so it is used book-wide instead: display
  lines in one style and place vote with the model's roles, weighted by its
  confidence, and a group that votes heading makes all its lines headings.
  Goede dochter headings 3/4 → 4/4 (the part title "DONDERDAG 16 MAART, 1989";
  "EEN" now by style, not the `sunk-opening` rule). Vals alarm, Crime,
  Dolittle, De aanslag unchanged. Held-out Villa Toscane still 0/12: a vote
  spreads the model's heading calls but can't make one.
- 2026-10-07: The missing-lines stage added regions that lie inside a
  text-layer line (Dolittle's page number at the end of its running head, read
  again as "II"). Such regions are skipped now: Dolittle CER 1.78% → 1.72%.
- 2026-10-07: Tried asking clef about a whole style group at once ("these lines
  share one type and place: what are they?", `experiments/probe_style_groups.py`).
  Right on every tuning-book group (Crime's numerals 0.9, Vals alarm's "1 Later"
  0.69), but held out it changed nothing (Villa Toscane 0/12, Grand Hotel Europa
  3/16) and added 2 spurious headings to De tuin; not adopted. The plain vote
  stays: De tuin 3/3 (+0).
