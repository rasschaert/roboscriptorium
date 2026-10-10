# AGENTS.md — Roboscriptorium

Instructions for any coding agent (and human) working in this repo. Read it before
starting; keep it true. It holds the rules, the scope and the map; the detail lives in
the documents it names, each with one job.

## The documents

Each fact lives in one file; the others point to it. A change updates the file that
owns the fact in the same commit.

| File | Job | When it changes |
| --- | --- | --- |
| `AGENTS.md` | rules, scope, conventions, the map | a rule, tool or convention changes |
| `HANDOVER.md` | the state of play: what runs, what's next, what waits on the user | rewritten at the end of every session |
| [docs/checklist.md](docs/checklist.md) | the plan: every open step in order, who does it, how long; below it what's done, one line each | the same change that plans, ticks or drops a step |
| [docs/outlook.md](docs/outlook.md) | how close the build is, where results can still move, what was tried without effect | the bench moves, or a probe comes back null |
| [docs/decisions.md](docs/decisions.md) | the dated log: what was learned or decided, with the numbers | every change that teaches something |
| [docs/design.md](docs/design.md) | why each component is there: what it catches, its failure, the measurement | a component or the evidence for it changes |
| [docs/run-times.md](docs/run-times.md) | wall-clock minutes of long runs, appended by `experiments/timed.sh` | each timed run |
| [docs/modules.md](docs/modules.md) | the code, module by module | a module changes |
| [docs/models.md](docs/models.md) | every model tried, by role, with its verdict | a model is screened |
| [docs/golden-notes.md](docs/golden-notes.md) | each golden pair: edition, what makes it hard, known deviations | a pair is added, sliced or retired |
| [docs/golden-books.md](docs/golden-books.md) | the pairs' numbers, **generated** by `experiments/golden_overview.py` | regenerated after a pair changes |
| `README.md`, [docs/how-it-works.md](docs/how-it-works.md), `docs/pipeline.d2` | for people: what it is and how a build runs | the stages, their order or their models change |

Cite a step or a section by its words, never by its number: numbers are positions and
get renumbered. Don't add a file to this table without a job no other file has.

## Standing rules

- **Keep this file true yourself.** When something is learned or decided (a design
  choice, a tool or model installed, a model that scored better, a pitfall found), update
  the file that owns it in the same change and add a dated line to docs/decisions.md.
  Don't wait to be asked.
- **Write down why, not only what.** Every component's job and the evidence that it earns
  it live in docs/design.md. A component whose reason isn't there gets one before the
  change that touches it is committed. A reviewer should never have to rediscover from
  data why something is there.
- **Keep the diagram true.** A change to the stages, their order or the model behind one
  also updates `README.md`, `docs/how-it-works.md` and `docs/pipeline.d2`; render again
  with `d2 docs/pipeline.d2 docs/pipeline.svg` and commit both.
- **Local first.** AI runs on this machine via Ollama. A hosted model (OpenRouter,
  `clients/openrouter.py`) costs money and sends copyrighted page crops to its provider,
  so it is used **only when the user explicitly allows or asks for it**, for that use:
  never on an agent's own initiative, never by carrying an earlier permission over to
  another run, never as a default in `config.py`. When it is used it is pinned to one
  provider and precision, never falls back, refuses providers that keep prompts, and is
  measured against the local model first.
- **No copyrighted material in git.** Books, page images, OCR output and golden pages
  live in `work/` (gitignored). Commit only code, prompts, question sets, configs and
  synthetic test fixtures.
- **Git:** signed commits straight to `main`, pushed whenever convenient; no PRs for now.
  Run lint and tests before every commit.
- **This file is the single source of agent instructions.** Claude Code reads AGENTS.md
  natively; don't add a `CLAUDE.md`.
- **Read `HANDOVER.md` at the start of a session** and rewrite it at the end of one.
  Choose what to work on from docs/checklist.md (the order) and docs/outlook.md (the
  room left).
- **Installs:** Homebrew tools, Python deps and Ollama models may be installed freely;
  the user pulls large model downloads themselves. Record each under
  [Environment](#environment).
- **Handholding first.** Prefer flagging uncertain output for human review over guessing
  silently. Automation increases only as measured quality earns it.
- **Quality over speed.** Pick the more accurate method even when it is several times
  slower: a careful edition takes people weeks, so hours of machine time per book are
  cheap. Cache slow stages per book so reruns stay cheap, and run long builds in the
  background.
- **Time long runs and give an estimate first.** Run anything over a few minutes through
  `experiments/timed.sh` (label, pages, log file, command), which appends its minutes to
  docs/run-times.md; before starting one, say how long it should take from that table.
  Start it detached, through `experiments/detached.sh <name> <command…>` (a `screen`
  session, output in `work/runs/<name>.out`), so it outlives the terminal and the agent
  session. `screen -ls` lists the runs; watch one with a background loop that ends when
  its screen does.
- **Cheap experiments are welcome, unasked:** A/B a prompt, a crop or a setting on a
  frozen set, and record null results too. Anything over a few minutes, or that costs
  the user time or money, is explained first: why, what it should teach, how long.
- **Questions the bench can't weigh** (the reviewer's time against wrong words, say) are
  the user's call: ask in one short sentence.

## Engineering practices

This project's bugs so far came from a handful of habits. Each rule below names the
mistake it prevents; check a change against them before committing.

- **A stage returns new data; it never edits its input.** Answers once rewrote the text
  layer in place, and the review, which keyed on that text, then lost them. If a
  function must change pages, it returns changed copies.
- **Say which version of the data a consumer gets.** Raw text layer or corrected copy,
  model roles or answered roles: name it in the type, field or docstring. A key, cache
  entry or line reference must come from the version it identifies.
- **Positions aren't identities.** A line index means nothing once lines are inserted or
  removed. Carry the original identity (`Line.source`) through any stage that changes
  the list.
- **Before finishing, find every reader of what you changed.** Grep the consumers of a
  function, field or file, and check each one still gets what it expects. The bugs live
  in the seams.
- **Test the seams.** A new stage or a change in what flows between stages gets a test
  through `pipeline.run` (see `tests/test_pipeline.py`), not only unit tests of its parts.
- **A rule that changes the author's text needs its counterexamples tested.**
  `close_quotes` turned "the animals' language" into a closing quote. Write the cases
  where the rule must *not* fire before the ones where it must; when the two can't be
  told apart, flag for review instead of rewriting.
- **Measure with `roboscriptorium bench`, before and after.** A single run's CER moved by
  more than most changes did; only the bench's paired comparison says whether a change is
  real. Choose on `bench tuning`; `bench validation` checks that it carries over, and a
  choice made on validation scores makes them tuning.
- **Measure on every golden book, not the one you're fixing.** A line-grouping change
  that helped Dolittle doubled Sense's CER.
- **Shared resources are shared deliberately.** PyMuPDF isn't thread-safe: hold
  `pdf.PDF_LOCK` wherever threads may meet, render on one thread and pool only the model
  calls.
- **Caches survive interruption.** Write them whole (`files.write_atomic`), skip a
  cut-off last line in append-only logs, and version their format.
- **Keep what you'll need again under `work/`, never in a session scratchpad.** A
  scratchpad disappears with the session. Source EPUBs live in
  `work/.cache/gutenberg/<ebook>.epub` and `work/.cache/publisher/<golden>.epub` (checked
  against PROVENANCE.md), probe outputs in `work/probes/`.
- **Comments describe the code as it is now,** briefly; history belongs in commit
  messages.

## Purpose and scope

An end-to-end tool that turns books that aren't EPUBs into clean EPUB 3 files, automated
as far as possible. The goal: an edition as careful as Standard Ebooks' (weeks of
scanning, OCR, proofreading and typesetting by people), in hours, with a human only
answering the questions the machine can't.

**Build the machine, not the book.** A general harness of compounded models, not rules
tuned to one book: several readings and judges that fail differently, combined by voting
and by each model's measured reliability per kind of error, with the human's answers as
labels that improve the weights. Every job keeps a labelled set, so a newly released
model is benchmarked and, where it wins, plugged in. The target book comes out right
because the machine does.

- **Order of attack:** scanned PDF → born-digital PDF → other formats (MOBI/AZW3, DOCX,
  HTML, …).
- **Content order:** prose/fiction first; footnotes, figures, tables, verse later.
- **Book languages:** Dutch and English.
- **Fidelity:** exact wording and spelling, original paragraphs, italics and scene breaks.
  Drop print artefacts (page numbers, running heads, line-end hyphens). Fix only clear
  OCR errors; never "improve" the author's text.
- **Non-goals (for now):** loose photo folders, dewarping phone photos, cloud models,
  non-Latin scripts.

### Current target book

*Wij doden Stella* by Marlen Haushofer (Dutch). We iterate until this one comes out
right, then expand.

- Internet Archive scan (Scribe), 76 pages, 325×554 pt, 360 ppi MRC layers (JPX
  background/foreground + JBIG2 mask).
- Pages: 1 cover · 2–3 scan noise and IA stamp · 4 colophon · 5–71 body (one continuous
  text, no headings or scene breaks; page 5 is a sunk opening) · 72–75 blank or library
  barcode · 76 back cover. Page sizes differ per page (crops).
- Has a **hidden OCR text layer** (GlyphLessFont) of decent quality. Observed errors: page
  number "10" → "Io", missing spaces ("vijfjaar"), missing accents ("scenes" for
  "scènes"), line-end hyphenation, indented paragraph starts, specks read as characters
  ("haar-hadden", a stray "»"), a smudge read as "><". Pages 5–9 have no page number in
  the text layer.
- That text layer is one OCR candidate among several, not the truth.

## Stack and conventions

- Python 3.13, managed with **uv**. Package and CLI are both named `roboscriptorium`.
- Layout: `src/roboscriptorium/` (src layout), tests in `tests/`, throwaway probes and
  training scripts in `experiments/`, frozen tryout sets in `tryouts/`, golden books in
  `golden/`, books and every cache under `work/` (gitignored).
- HTTP: `httpx`. Tests inject `httpx.MockTransport`, so unit tests never need a running
  model server.
- Lint/format: `ruff` (line length 100; `experiments/` excluded). Tests: `pytest`.
- Settings: `config.py`'s `Settings`, each overridable by a `ROBO_*` variable it lists
  (`ROBO_OLLAMA_URL`, `ROBO_READ_MODEL`, `ROBO_JUDGE_MODEL`, `ROBO_SORTER`,
  `ROBO_OCR_TRUST`, `ROBO_OCR_QUESTIONS`, `ROBO_OCR_ASK_BELOW`, …).

The map, one line a module; [docs/modules.md](docs/modules.md) has each in full.

| Module | Job |
| --- | --- |
| `cli.py`, `config.py`, `book.py`, `files.py` | the CLI, settings, a book directory and its `book.toml`, atomic cache writes |
| `clients/` | Ollama (`ollama.py`), decision models on `/v1/systemone` (`decide.py`), imajev on llama-server (`llama.py`), a hosted model (`openrouter.py`), retries (`retry.py`) |
| `pdf.py`, `page.py` | the text layer as visual lines with boxes (tesseract's for an image-only scan); what a page's layout says without a model |
| `layout.py`, `typestyle.py`, `faint.py` | DocLayout-YOLO regions; each line's type against the body; washed-out pages |
| `missing.py` | printed lines the layer lacks, read by glm-ocr |
| `roles.py`, `sorter.py` | line roles: a decision model plus rules; the trees behind `ROBO_SORTER=1` |
| `ocrcheck.py`, `trust.py`, `lexicon.py` | more readings of each body line, judges where they differ, the learned trust that fixes, keeps or asks; the word list |
| `corrections.py`, `quotes.py` | the reviewer's answers applied; unpaired quotes as questions with a proposed reading |
| `reflow.py`, `typography.py`, `italics.py`, `figures.py`, `initials.py` | lines into paragraphs and headings; the book's dash and ellipsis style; italic words from stroke slant; pictures and captions; decorated initials |
| `ir.py`, `epub.py` | the document model with references back to page lines; EPUB 3 by hand |
| `pipeline.py` | the stages for one book, each cached under `work/<book>/stages/` |
| `flags.py`, `review.py` | what a human should check; the local review pages |
| `golden/`, `evaluate.py`, `disagreements.py`, `quality.py`, `bench.py` | golden books (manifests, derived references, alignment, retirement signals); CER, WER and paragraph scores; differences located on the scan; what a reviewer is left with; **the** paired measure of a change |

## Architecture

`pipeline.run` builds a book in this order; `docs/pipeline.d2` draws it with the model
behind each stage. Each stage caches its artefacts under `work/<book>/stages/`, so a
rerun skips finished work and model calls.

1. **Text layer** (`pdf.py`): the PDF's own text as visual lines with boxes. The body
   pages come from `book.toml` (no page classification yet).
2. **Layout regions** (`layout.py`, DocLayout-YOLO) and the book's **dash style**
   (`typography.py`: `book.toml`, else measured on a scan), which the readers are told.
   Then **missing lines** (`missing.py`, glm-ocr): printed lines the layer lacks, added
   in reading order.
3. **Type** (`typestyle.py`) and **line roles** (`roles.py`, clef-flash plus rules and a
   style vote): body, chapter heading, page number, running head, artifact. A line not
   sure enough to be body is dropped, or kept as a heading.
4. **Washed-out pages** (`faint.py`, scans only), then the **OCR check** (`ocrcheck.py`,
   `trust.py`) on the other pages: more readings of each body line, judges where they
   differ, learned trust to fix, keep or ask.
5. **Answers** (`corrections.py`): a human's review answers, applied to copies.
6. **Reflow** (`reflow.py`): lines into headings and paragraphs; de-hyphenation.
7. **Quote questions** (`quotes.py`): unpaired quotes, with a proposed reading.
8. **Italics** (`italics.py`), **dashes and ellipses** (`typography.py`), **figures**
   (`figures.py`) on the IR (`ir.py`).
9. **EPUB** (`epub.py`), checked with epubcheck.

Review (`flags.py`, `review.py`) runs on a build's output; scoring is `eval`, `quality`
and `bench`. Not built yet: page classification, image preprocessing (deskew, spreads),
formats other than PDF.

## AI usage

**How a new decision gets added:** prototype the question, collect a labelled set (from a
golden book, or by labelling with a large generative model on Ollama when there is none),
refine the rubric (option wording plus features the model can't see, such as repetition
across pages), then measure the decision model against that set. **Start with ~10–60
items and scale up only once the results justify it.** Enforce in code what is true by
definition (a chapter heading appears once) rather than hoping the model weighs it.

**Model roles.** Every model has a role, and the docs, the diagram and talk with the
user refer to it by that role (docs/how-it-works.md):

| Role | Model | Job |
| --- | --- | --- |
| spotter | DocLayout-YOLO | marks figures, captions, titles and furniture on the page image |
| reader | glm-ocr, tesseract, qwen3.8 | reads text from the scan (also a line the layer missed) |
| sorter | clef-flash:9b | decides each doubtful line's role; guesses a drawn initial |
| judge | clef:27b, winnow-ollama:e4b, the word list | picks a version of a suspect |
| arbiter | the trust model (`trust.py`) | fixes, keeps or asks, weighing readers and judges |
| reviewer | the user | answers what the arbiter is unsure of |

**Every new model gets two questions.** Can it replace a model in a role we have? And
could the application improve by *adding* it: as another reader or judge beside the ones
in use, which the arbiter weighs, or as the model for a decision still made by hand, by
`book.toml` or by a rule? List both kinds of use, rank them by what they could gain, and
screen the best on the frozen sets (`experiments/tryout.py run reader|judge`). A new
reader or judge reaches the arbiter only after the trust data is rebuilt and the arbiter
retrained. Record the verdict in [docs/models.md](docs/models.md): the model for each
role is chosen by its score on golden pages, then pinned (never `latest`).

Two kinds of model, used for different jobs:

- **Decision models ("System One")**, on Ollama's `/v1/systemone`. Answer bounded
  questions whose options are declared in advance, with a typed answer and a
  probability. They generate no text.
- **Generative models ("System Two")**, on Ollama. Produce text: vision-LLM OCR,
  OCR-error correction, structure and metadata.

**Rule: if the answer comes from a list that's known in advance, ask a decision model.
If it needs new text, a generative one.** Never prompt an LLM and parse its prose for a
decision a decision model can make.

### Decision models

clef, clef-flash and winnow (`winnow-ollama:e4b`) answer on Ollama's `/v1/systemone`;
every question the pipeline asks is a `choice`. A model pulled as a plain GGUF lacks the
`decision` capability; a Modelfile adds it (Environment, `winnow-ollama:e4b`).

- Images: raw base64 PNG, JPEG or WebP in `images`, one per request.
- Question types: `choice` (probability per declared option), `score` (ordinal scale),
  `noul` (probability that a statement is true).

```sh
curl http://127.0.0.1:11434/v1/systemone -d '{
  "model": "winnow-ollama:e4b",
  "state": "<text, or JSON describing the situation>",
  "questions": {"role": {"type": "choice", "instructions": "...",
                "criteria": {"page_number": "...", "body": "..."}}}
}'
```

The response holds `answers.<name>.choice`, `confidence` and `probabilities`.

- **Give decisions context.** A bare string is ambiguous. Pass a JSON state with the
  candidate plus its position on the page, its neighbouring lines and the page type.
  Confidence is **not** correctness: calibrate thresholds on golden pages before
  trusting them.
- `noul` answers carry only `noul` (P(true)). `choice` and `score` carry `confidence`
  and `probabilities`. `DecisionClient.decide` normalises all three into
  `Answer(type, value, confidence, probabilities)`.

## Environment

- Apple M4 Max, 64 GB RAM, macOS. Ollama drains the battery even on the charger, and Low
  Power Mode slows runs by an unmeasured amount: ask before chaining long runs.
- Ollama 0.40.2 at `http://127.0.0.1:11434` (scores before 2026-10-06 were on 0.35.1).
  Ollaya was uninstalled on 2026-10-08; every model runs on Ollama.
- Present: `uv`, `python3`, `pandoc`, calibre `ebook-convert`, poppler (`pdfinfo`,
  `pdftotext`, `pdfimages`), epubcheck, d2 (all Homebrew where applicable).
- llama.cpp (Homebrew, 0.6.0): `llama-server` runs imajev for the judge tryout on
  Ollama's own blobs, its readout applied in `clients/llama.py`
  (`experiments/llama-serve.sh <size> [port]`), because Ollama's systemone takes no
  images for GGUF models. Its image placeholder is random per start; read it from
  `/props` (`media_marker`). Readouts and calibrations in `work/models/imajev/` (from
  `mohit67890/imajev-{2b,4b,9b}`, 2–4 MB each).
- `imajev:4b` (Ollama): mindchain's imajev-4b (`hf.co/mindchain/imajev-4b-GGUF:Q8_0`)
  made a decision model with `modelfiles/imajev-4b.Modelfile`. The candidate for plates
  without a caption; off in the pipeline. The 2B and 9B were deleted after their screen
  (their Modelfiles and readouts remain).
- `winnow-ollama:e4b` (Ollama): winnow:e4b's Hugging Face GGUF
  (`hf.co/EldanRing/Winnow-E4B:Q8_0`) made a decision model with
  `modelfiles/winnow-ollama-e4b.Modelfile`. **A workaround:** a pulled GGUF has no
  `decision` capability, so the Modelfile adds `CAPABILITY decision` and `CAPABILITY
  vision` and an empty `TEMPLATE {{ .Prompt }}`, copied from clef-flash's. Ollama then
  renders the decision prompt its own way, not in the layout winnow was trained on
  (EldanRing/winnow-inference `native/protocol.h`). The pipeline's second judge.
- scikit-learn (Python dep) for the trust model and the line-role trees.
- Dependency group `layout` (a default group): `doclayout-yolo` with PyTorch, and the
  DocLayout-YOLO DocStructBench weights (`juliozhao/DocLayout-YOLO-DocStructBench`,
  `doclayout_yolo_docstructbench_imgsz1024.pt`, in the Hugging Face cache). `layout.py` runs it on every build.
- Word lists: `work/lexicon/{nld,eng}-words.txt`, built by `lexicon.py` from the tessdata
  models with `combine_tessdata` and `dawg2wordlist` (both come with Homebrew's
  tesseract).
- tesseract 5.5.3 (Homebrew, `eng`/`osd` only). The Dutch model is `nld.traineddata`
  from tessdata_best in `work/tessdata/` (pass `--tessdata-dir work/tessdata`);
  `tesseract-lang` (~650 MB) is not installed.
- 1Password signs commits; when it is locked, stop and ask for it to be unlocked.

## Running, reviewing, evaluating

A book lives in `work/<book>/` with `source.pdf` and a `book.toml`:

```toml
title = "Wij doden Stella"
author = "Marlen Haushofer"
language = "nl"
cover_page = 1
body_pages = [5, 71]   # inclusive; page classification replaces this later
dash = "–"             # optional: how the book prints dashes ("–" or "—") …
dash_spacing = "thin"  # … and their gaps ("none", "thin", "word"); else measured
ellipsis = "..."       # optional: "…", "..." or ". . ." …
ellipsis_space = false # … and a space before it; else read in the text layer
```

```sh
uv run roboscriptorium doctor            # is Ollama up, and do its decision models answer?
uv run roboscriptorium build work/stella # → work/stella/stella.epub
epubcheck work/stella/stella.epub        # must report 0 errors / 0 warnings
uv run ruff format . && uv run ruff check . && uv run pytest
```

**Reviewing a book.** `uv run roboscriptorium review work/<book>` builds the book,
flags the regions that aren't plain running text and serves them on
http://127.0.0.1:8765/ next to scan crops. Each region asks what it is (radio buttons:
`1` running text, `2` heading, `3` drop, `4` image, `5` caption, `6` decorated initial,
with its letter guessed from the word it begins), with the pipeline's call preselected,
and takes the text as printed in a text box. Where OCR readings differ it asks which one
matches the scan instead: each reading on its own row, the differing part marked, with
the models that picked it (`a`, `b`, …; `e` for something else). One Save button (`↵`;
`⌘↵` in the text box) records the answer and moves to the next unanswered region; a
typed line that matches none of the readings, or a straight quote in a curly-quoted
book, is queried once and saved on the second Save (`review.doubtful`; warned answers in
`review/warnings.jsonl`). Arrows move through all regions. A region with a box can be
turned (`r`, ↺/↻) and read again by tesseract (`o`); `-` and `+` zoom the crop. "Rebuild
book" applies the answers and rebuilds the EPUB. Flags come from the model's decisions
before answers, so the list stays put while you work. **Sample the questions before
sending the user to review**: never obvious ones.

### Golden books

Public-domain or lending-library scans paired with a human-checked reference text, which
is what every change gets measured against. [docs/golden-notes.md](docs/golden-notes.md)
describes every pair; [docs/golden-books.md](docs/golden-books.md) has their numbers.
Each lives in `golden/<name>/` **in git**: `manifest.toml` (the scans with URL and
sha256, page ranges, the source and chapter range), the derived chapters in `text/` with
`PROVENANCE.md`, and `standard-ebooks/` (SE's text, see below).

- The reference text is a **Project Gutenberg** transcription (`golden derive`) or the
  publisher's own EPUB of the same edition, taken as it stands. Gutenberg rebuilds its
  EPUBs, so the committed `text/` is the pinned artefact; `PROVENANCE.md` records the
  EPUB's hash and the transcriber's notes.
- **Standard Ebooks is not a fidelity reference.** Its texts are modernised and restyled.
  `golden derive-se` keeps it in `standard-ebooks/` for later style work; the SE manual
  of style is at https://standardebooks.org/manual/1.9.1/single-page.
- Scans are never committed. `golden fetch` downloads them into `work/<name>--<scan>/`
  and writes its `book.toml`. A scan's `[scans.ia]` lists Internet Archive's own files
  for it (`item`, and `files` with their sha256), fetched into its `ia/` folder: the
  page images the PDF was compressed from (`_jp2.zip`), ABBYY's OCR with per-letter
  confidence (`_abbyy.gz`), page types and crop boxes (`_scandata.xml`) and printed page
  numbers (`_page_numbers.json`); a leaf with `addToAccessFormats` true is a PDF page,
  in order. Public on public-domain items (Crime, Dolittle). A lending-library item
  (`access-restricted-item` in its metadata) keeps all but `_scandata.xml` private, and
  its scan has no `url`, so it is placed by hand and then checked by sha256.
- A scan of another edition than the transcription differs in spelling, quote style,
  spaced dashes, "Mrs" vs "Mrs.", and so on, so its scores include edition differences,
  not just pipeline errors.
- **Three sets** (`bench.SETS`). Tuning books are chosen on; validation books were
  consulted before, so they check that a change carries over; the **test set** (Het
  geluid van bananen) is scored **once, at the end of the plan, and touched by nothing
  else**: no eval, quality, review or bench run, no trust data, no probe. `eval`,
  `quality`, `golden review` and `bench test` refuse it without `--score-test`. A
  validation book's sibling (same publisher, translator and e-book house) never trains
  while it validates.
- **Checking a candidate pair** (scan PDF plus the publisher's EPUB) before writing its
  manifest: `uv run python experiments/probe_candidate.py <scan.pdf> <ref.epub> [heading
  prefix …]`, no models, about 10 s per 100 pages. It prints the scan's kind, the EPUB's
  edition and markup, the body page range, the text layer's CER against the EPUB per band
  of pages and the most frequent word differences. A pair fits when the EPUB's colophon
  names the scan's printing and the differences are OCR slips at the layer's own rate
  (0.2–0.5% CER), not real-word swaps or a band that jumps. Prefer IA Scribe scans
  (Stella's format); skip calibre-made PDFs, other printings, DRM and pre-1934 spelling.
  Skip an EPUB that isn't the publisher's own (made through Word or OCR: `MsoNormal`
  classes, an ABBYY generator, a colophon naming only the print): it carries its maker's
  edits. An EPUB that sets its dashes as spaced hyphens or a spaced `--` gets
  `hyphen_dash = "–"` in `[reference]`; one that writes small capitals in lower case with
  a class gets `capital_classes`; a Gutenberg transcription that drops the space its
  print sets before an ellipsis gets `ellipsis_space = true`.
  `experiments/chapter_pages.py` gives the scan page each derived chapter starts on, to
  end a bench slice on a chapter.
- **Known deviations.** No publisher's EPUB matches its print in every convention. Each
  known deviation of a pair is handled in one of three places, and nowhere else: a gap
  derive can undo is declared in the manifest's `[reference]` (`hyphen_dash`,
  `capital_classes`) and listed in PROVENANCE.md; a glyph choice the output may make
  differently is folded by `evaluate.normalise` and counted per side, so `eval` prints
  how much it forgave; what neither covers (a corrected word, a later impression) is
  settled by a verdict. A deviation that lives only in a comment or a note is untracked:
  move it to one of the three.
- **Retiring a book.** A reference can stop being one: when a book's remaining
  disagreements are mostly edition differences, or its verdict backlog never shrinks,
  its score measures the edition, not the pipeline. Two signals need no verdicts: the
  text layer's CER against the reference and the share of its body lines the aligner
  can't place (`golden/signals.py`). `bench` records both per book and names each book
  past a threshold as a suspect pair; docs/golden-books.md has them over all lines
  (regenerate it with `uv run python experiments/golden_overview.py >
  docs/golden-books.md`, half a minute, no models, after adding, slicing or retiring a
  book). Past three times the set's median layer CER, or one body line in twenty
  unplaced, the book is suspect. **Whoever notices says so in the session's report and
  proposes retiring it, without being asked.** A retired book's files are deleted from
  `work/` and its manifest from git, with a dated line in docs/decisions.md.

```sh
uv run roboscriptorium golden derive the-nature-of-a-crime
uv run roboscriptorium golden fetch the-nature-of-a-crime
uv run roboscriptorium eval work/the-nature-of-a-crime--doubleday-1924
# quick loop: a slice of pages and the chapters they hold
uv run roboscriptorium eval work/goede-dochter--ia-scan --pages 9-64 --chapters 1-4
# heuristics only, no models
uv run roboscriptorium eval work/goede-dochter--ia-scan --no-models
# a publisher's EPUB can't be downloaded: pass it to derive
uv run roboscriptorium golden derive goede-dochter --epub work/.cache/publisher/goede-dochter.epub
```

`eval` builds the book, prints the scores and the most frequent differences, and appends
a line to `work/<book>/eval-history.jsonl` with the commit, the settings, which decider
settled the OCR check (`fixed rule` or `trust <model hash>`) and each model's Ollama
digest. Given several books it scores them
one after another and ends with a line per book.

**Disagreements and verdicts.** Gutenberg is a transcription, not the scan, so where the
output disagrees with it a human decides what the scan prints:

```sh
uv run roboscriptorium golden review work/the-nature-of-a-crime--doubleday-1924  # → http://127.0.0.1:8765/
```

Keys: `1` the reference is right (pick the pipeline mistake), `2` the scan prints the
output (edition difference or transcriber change), `3` type what the scan prints, `0`
unsure, arrows to move. Verdicts go to `golden/<name>/verdicts/<scan>.jsonl` (in git),
keyed on the reference words and six words of context either side, so they survive
pipeline changes. `eval` patches them into the reference for that scan and reports the
remaining disagreements by mistake category.
