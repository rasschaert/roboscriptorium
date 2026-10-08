# AGENTS.md — Roboscriptorium

Instructions for any coding agent (and human) working in this repo. Read it before
starting; keep it true.

## Standing rules

- **Keep this file up to date yourself.** When something is learned or decided —
  a design choice, a tool or model installed, a model that scored better, a pitfall
  found — update AGENTS.md in the same change. Add a dated line to
  [docs/decisions.md](docs/decisions.md). Don't wait to be asked.
- **Write down why, not only what.** Every component's job and the evidence
  that it earns it live in [docs/design.md](docs/design.md): what it catches that
  the others don't, its own failure, the measurement. A component whose reason
  isn't there gets one before the change that touches it is committed; when new
  numbers change the reason, the file changes in the same commit. A reviewer
  should never have to rediscover from data why something is there.
- **Keep the docs and diagrams up to date too.** A change to the stages, their
  order, or the model, code or person behind one also updates `README.md`,
  `docs/how-it-works.md` and `docs/pipeline.d2` in the same commit; render the SVG again with
  `d2 docs/pipeline.d2 docs/pipeline.svg` and commit both. A diagram that shows
  the pipeline as it was is worse than none.
- **Local first.** AI runs on this machine via Ollama and Ollaya. A hosted model
  (OpenRouter, `clients/openrouter.py`) costs money and sends copyrighted page crops
  to its provider, so it is used **only when the user explicitly allows or asks for
  it**, for that use: never on an agent's own initiative, never by carrying an earlier
  permission over to another run, and never as a default in `config.py`. When it is
  used it is pinned to one provider and precision, never falls back, refuses
  providers that keep prompts, and is measured against the local model first.
- **No copyrighted material in git.** Books, page images, OCR output and golden
  pages live in `work/` (gitignored). Commit only code, prompts, question sets,
  configs and synthetic test fixtures.
- **Git:** signed commits straight to `main`, pushed whenever convenient; no PRs
  for now. Run lint and tests before every commit.
- **This file is the single source of agent instructions.** Claude Code reads
  AGENTS.md natively; don't add a `CLAUDE.md`.
- **Read `HANDOVER.md` at the start of a session** for where work stopped, and
  rewrite it at the end of one.
- **Keep [docs/checklist.md](docs/checklist.md) true.** It is the plan: every step,
  done and left, with who does it and how long it should take. In the same change
  that causes it: tick a step off, add a step the moment one is planned, mark one
  dropped (and why) when the plan changes, and update an estimate after a timed run.
  The user reads it to see where things stand, so a stale row misleads them.
- **Installs:** Homebrew tools, Python deps and Ollama/Ollaya models may be
  installed freely. Record each one under [Environment](#environment).
- **Handholding first.** Prefer flagging uncertain output for human review over
  guessing silently. Automation increases only as measured quality earns it.
- **Quality over speed.** Pick the more accurate method even when it is several
  times slower: a careful edition (scanning, OCR, proofreading, typesetting, as
  Standard Ebooks does it) takes people weeks, so hours of machine time per book
  are cheap. Cache slow stages per book so reruns stay cheap, and run long
  builds in the background.
- **Time long runs and give an estimate first.** Run anything over a few minutes
  through `experiments/timed.sh`, which appends its minutes to
  [docs/run-times.md](docs/run-times.md). Before starting one, say how long it
  should take from that table. Start it detached, through `experiments/detached.sh
  <name> <command…>` (a `screen` session, output in `work/runs/<name>.out`), so it
  outlives the terminal and the agent session: the user must be able to close either.
  `screen -ls` lists the runs; an agent watches one with a background loop that ends
  when its screen does (the script's header), which is harmless to lose.

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
- **Measure with `roboscriptorium bench`, before and after.** A single run's CER
  moved by more than most changes did; only the bench's paired comparison says
  whether a change is real. Choose on `bench tuning`; `bench validation` checks
  that it carries over, and a choice made on validation scores makes them tuning.
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
    `ROBO_DECISION_MODEL`, `ROBO_ROLE_MODEL` and the others it lists (`ROBO_READ_MODEL`
    reads quote questions' lines, "" for none).
  - `clients/ollaya.py` also serves Ollama's `/v1/systemone`: `for_model` routes
    `clef-*` models there and everything else to Ollaya.
  - `clients/ollama.py`, `clients/ollaya.py`: thin httpx clients. All model calls go
    through these.
  - `clients/openrouter.py`: a hosted model, named `openrouter:<model>@<provider tag>`
    read by `ocrcheck.transcribe`; the key is `OPENROUTER_API_KEY`. As `ROBO_READ_MODEL`
    its readings cache under its own name; as `ROBO_READ_VIA`
    (`openrouter:qwen/qwen3.8-27b@deepinfra/bf16`) it reads in place of the local
    `read_model`, its readings cached under the local name and each listed under `via`
    in the cache, so a later local run reuses them and a reader can tell them apart. A
    decision model's hosted build answers through `ollaya.HostedClient` (`ROBO_JUDGE_VIA`
    for the judge), its answers cached under the local name with `via`. `experiments/probe_line_reader.py`
    compares it with the local readings of a book.
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
    punctuation spacing). A line-end hyphen stays or goes by evidence in order: the
    book's own spelling, the word list, a capital after the break, the parts beside an
    inner hyphen (docs/design.md). Without roles it falls back to a footer heuristic.
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
  - `docs/pipeline.d2`: the README's diagram of the stages and the model behind
    each; kept current under the standing rules.
  - `experiments/`: throwaway probes for comparing models (line roles, page types).
  - `golden/`: golden books. `manifest.py` (scans, fetch with sha256 check),
    `gutenberg.py` (derives the reference text from a Project Gutenberg EPUB),
    `epub.py` (from a publisher's EPUB: headings by tag or class prefix),
    `se.py` (derives Standard Ebooks' text, kept for later style work),
    `reference.py` (reads the reference chapters, with their italic words),
    `signals.py` (whether a pair still measures the pipeline: layer CER and unplaced
    lines against the reference, printed by `bench`), `notes.py` (a reference's footnotes, `notes.txt` from the manifest's
    `note_classes`: the scan's footnote lines are left out of every score).
  - `evaluate.py`: CER, WER and paragraph F1 against a golden reference. Typography
    the EPUB may set differently (quote and dash glyphs, an ellipsis glyph or spaced
    dots, joiners) is folded on both sides and counted per side (`folded_*`, printed
    by `eval`), so a pair's convention gap is visible, not silent.
  - `disagreements.py`: where output and reference differ, located on the scan;
    clearly garbled output and whitespace-only differences are auto-resolved.
    Verdicts (what the scan prints, plus a mistake category) are stored per scan
    and patched into the reference by `eval`.
  - `bench.py` (`roboscriptorium bench [tuning|validation|test]`): **the** measure for a
    change. Pinned golden slices per set, scored with `evaluate` and `quality`,
    saved whole to `work/bench/` (commit, settings, decider, model versions,
    per-page counts) and compared with the previous run page by page. One test
    decides: "after review", each book of the set weighing the same, must improve
    at the low, mean and high slip rate, and no book may get worse by ≥ 0.05 wrong
    words per page at 99% (a veto); the per-book intervals are diagnostics. A tuning book is
    scored with the trust model trained without it
    (`ocr-trust-without-<book>.pkl`, written by `train_ocr_trust.py --save`). "After review"
    adds the reviewer's own slips per question asked (`quality.slip_rates`, a Beta
    posterior from 8 wrong of 68 checked answers on Stella). Run it before and after a change; cite its
    starred lines, not single CER figures.
  - `quality.py` (`roboscriptorium quality book[:pages[:chapters]] …`): what a
    reviewer is left with. Wrong words per page before review and left unasked,
    with every question and at budgets of 0.25, 0.5 and 1 question per page
    (questions ranked by how often their kind caught an error in the *other*
    books given), each with a 95% bootstrap interval over pages; the unasked
    errors by kind (punctuation, quotes, letters, word breaks, missing words…).
  - `flags.py`: regions a human should check, i.e. what isn't plain running
    text: headings, lines dropped mid-page or without the model being sure,
    garbled text, centred or set-apart lines. Page furniture (repeated running
    heads, printed page numbers) isn't flagged. With layout regions it also
    flags pictures, captions, titles that aren't headings, and text the text
    layer lacks (one region per page, as an area rather than lines).
  - `quotes.py`: places where a paragraph's curly quotes don't pair up (a lost
    opening ‘, a lost closing ’), apostrophes, Dutch `’s`, plural possessives,
    nested quotes and quotations running over paragraphs aside. Found on the
    text before a human's answers (`Stages.quote_lines`) and flagged as `quotes`.
    Each such line (short ones too) is read by `read_model` (qwen3.8) with the book's
    typesetting in the prompt (`style_prompt`: quote marks, ellipsis, dashes); its
    marks on the OCR-checked line's letters (`proposed`) become the question's second
    reading (`Stages.quote_readings`, cached in `stages/quote-readings.json`).
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
    against glm-ocr's reading of each body line's crop (short lines too) (`ROBO_OCR_MODEL`),
    cached in `stages/second-reading.json`, tesseract's of the page, and
    `read_model`'s (qwen3.8) of the crop, told the book's typesetting
    (`stages/third-reading.json`). Where a line's readings differ, clef picks from
    the crop and winnow (`ROBO_CHECK_MODEL`) from the sentence; both agreeing
    with clef ≥ 0.3 applies the fix to a copy of the pages before reflow,
    anything else becomes an `ocr-doubt` review region.
    The judge is `judge_model` (clef:27b, `ROBO_JUDGE_MODEL`), not the role
    model; it is told the book's typesetting (`quotes.style_note`) and sees the
    versions set off by ⟨ ⟩. Suspects are saved to
    `stages/ocr-check.json`; `eval --no-check-ocr` skips the stage.
  - `lexicon.py`: a language's word list, unpacked from tesseract's own model
    (`<lang>.traineddata`'s LSTM word DAWG: Dutch 478k words, English 338k) into
    `work/lexicon/`, and which one of several readings it knows all the words
    of. Word breaks, line-end fragments, stress accents and words without a
    vowel get no verdict. The OCR check records its pick as a vote ("word list",
    shown in the review) but doesn't act on it.
  - `trust.py`: learned trust for the OCR check. A model (shallow gradient-boosted
    trees) scores each version of a suspect from the judges' picks and confidence,
    which second readings read it, the word list, the kind of difference and a prior
    for its exact substitution (`pair`: how often `|`→`I` was the print in the training
    books, pairs seen in two books or more, saved with the model);
    the least sure suspects are asked up to `ROBO_OCR_QUESTIONS` per page, the
    rest take their best version. The budget is book-wide (questions per page ×
    pages), so a bad page can take more than one. On by default (`ROBO_OCR_TRUST=0`
    for the fixed rule); a missing model, or one saved for another version or
    feature width (`MODEL_VERSION`, `FEATURES`), stops the build. The model lives
    in `work/models/ocr-trust.pkl`, trained by `experiments/train_ocr_trust.py
    --save` on the tuning books' suspects, never the validation ones (it refuses while a
    tuning book's data is missing or built before the current readings)
    (`experiments/ocr_trust_data.py`).
  - `typography.py`: the book's dash style (en or em; no, thin or word spacing),
    from `book.toml` (`dash`, `dash_spacing`) or, on a scan, measured on the page
    image (the stroke's length against the line's letter width, its gaps against
    the gaps between words; cached in `stages/typography.json`, and printed so a
    human can settle it). Every dash between words in the output is then set that
    way (a no-break space before it, narrow when thin); number ranges and hyphens
    stay. The OCR check no longer raises dash kind or spacing as a doubt.
  - `ocr.py`: tesseract on a page region, for drafts a human corrects (text the
    text layer lacks, or reads as scraps because it is printed sideways).
  - `initials.py`: guesses the letter of a decorated initial: the letters that
    make the word beside it a word (book vocabulary plus the system word list),
    then the role model picks among them from the drawing.
  - `corrections.py` also takes answers about one place in a line (`Flag.span`):
    an answer changes only that span, so several answers about one line, and the
    OCR check's own fixes elsewhere in it, combine (`apply(..., fixes)`). A break
    hyphen's place is asked across the break (`Flag.joined`: "dankbaar" or "dank
    baar") and answered back as the hyphen or none.
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

`pipeline.run` builds a book in this order; `docs/pipeline.d2` draws it with the
model behind each stage. Each stage caches its artefacts under `work/<book>/stages/`,
so a rerun skips finished work and model calls.

1. **Text layer** (`pdf.py`): the PDF's own text as visual lines with boxes. The
   body pages come from `book.toml` (no page classification yet).
2. **Layout regions** (`layout.py`, DocLayout-YOLO) and **missing lines**
   (`missing.py`, glm-ocr): printed lines the layer lacks, added in reading order.
3. **Type** (`typestyle.py`) and **line roles** (`roles.py`, clef-flash plus rules
   and a style vote): body, heading, page number, running head, drop.
4. **OCR check** (`ocrcheck.py`, `trust.py`): more readings of each body line,
   judges where they differ, learned trust to fix, keep or ask.
5. **Answers** (`corrections.py`): a human's review answers, applied to copies.
6. **Reflow** (`reflow.py`): lines into headings and paragraphs; de-hyphenation.
7. **Quote questions** (`quotes.py`): unpaired quotes, with a proposed reading.
8. **Italics** (`italics.py`), **dashes** (`typography.py`), **figures**
   (`figures.py`) on the IR (`ir.py`).
9. **EPUB** (`epub.py`), checked with epubcheck.

Review (`flags.py`, `review.py`) runs on a build's output; scoring is `eval`,
`quality` and `bench`. Not built yet: page classification, image preprocessing
(deskew, spreads), formats other than PDF.

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

**Model roles.** Every model has a role, and the docs, the diagram and talk with
the user refer to it by that role ([docs/how-it-works.md](docs/how-it-works.md)):

| Role | Model | Job |
| --- | --- | --- |
| spotter | DocLayout-YOLO | marks figures, captions, titles and furniture on the page image |
| reader | glm-ocr, tesseract, qwen3.8 | reads text from the scan (also a line the layer missed) |
| sorter | clef-flash:9b | decides each doubtful line's role; guesses a drawn initial |
| judge | clef:27b, winnow:e4b, the word list | picks a version of a suspect |
| arbiter | the trust model (`trust.py`) | fixes, keeps or asks, weighing readers and judges |
| reviewer | the user | answers what the arbiter is unsure of |

A new model is tried *for a role*: say which one it is tried for, measure it there
against the one playing it, and record it in the Models table with its role. A new
reader or judge reaches the arbiter only after the trust data is rebuilt and the
arbiter retrained.

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

OCR scores on "Teirlinck 12 pages" come from the retired pre-reform bench and
are history only. On modern Dutch (Goede dochter pp. 9–64, 1,622 body lines,
typesetting folded) the text layer reads 0.21% CER, glm-ocr 0.25%, tesseract
0.29%, qwen3.8 0.17%; re-bench candidates there and on the Boekenweek books and Reis om mijn
schedel before choosing an OCR model.

| Runtime | Model | Use | Status |
| --- | --- | --- | --- |
| Ollaya | `laya:multilingual` | Decisions on Dutch text | **unfit for line roles** (see docs/decisions.md) |
| Ollaya | `laya:en` | Decisions on English text | **unfit for line roles** (see docs/decisions.md) |
| Ollaya | `winnow:e4b` | Line roles (previous default) | P(body) ≥ 0.9: keeps 147/150 body lines, catches ~99% of junk; ~270 ms/line. Reads a leading page number ("2 SENSE AND…") as a chapter heading; ignores numeric features |
| Ollaya | `winnow:e4b` (as `check_model`) | Second opinion on OCR suspects, from the line's text only | Dolittle pp. 30–49: 74/90 right alone; its disagreeing with clef marks clef's errors (clef right on only 9/13 of those) |
| Ollaya | `winnow:12b` | Line roles candidate | Slightly better than e4b on 60 lines (0/30 body lost at 0.9), 2.6× slower (~700 ms/line) |
| Ollaya | `decider:2b-vision` | Page type from a page image | 19/23 sample pages right; low confidence on the hard ones, but confidently wrong on Stella p5 (an opening without heading). ONNX on **CPU**, ~3.8 s/page |
| Ollama | `clef-flash:9b` | **Line roles (in use)**; page types candidate | Line roles: 60/60 at P(body) ≥ 0.5 (its probabilities are softer than winnow's, so don't use 0.9). Pages: 19/23, low confidence where it errs. ~0.8 s/line and ~3.9 s/page, measured under load. Endpoint `/v1/systemone`; raw base64 PNG/JPEG/WebP in `images`; up to 64 questions per call; 64K context. Confidence = how concentrated the probabilities are, not P(correct) |
| Ollama | `gemma4:latest` (8B dense, nvfp4) | Vision OCR candidate; **unfit as the line reader** | Teirlinck 12 pages: CER 0.70% (0.63% with the old-spelling prompt) but **modernises** old Dutch: 41 (27) reform spellings per 12 pages (`tusschen→tussen`, `oogenblik→ogenblik`), plus word swaps (`eenvoud→eenvoudig`). ~22 s/page. Never use alone; pair with tesseract As a line reader told the book's style (Goede dochter pp. 9–20, 324 body lines, 2026-10-08): 0.31 s a line, 4.5× Qwen's speed, but CER 0.21% against Qwen's 0.10% and the layer's 0.13%, quote marks wrong on 4 lines against Qwen's 0 |
| — | tesseract 5.5.3 + `nld` (tessdata_best) | Plain OCR candidate | Teirlinck 12 pages: CER 0.90%, no modernisation; errors are visual (`,`/`.`, mangled ellipses) and dropped short lines. <1 s/page |
| Ollama | `glm-ocr:bf16` | OCR candidate (0.9B, document OCR) | Teirlinck 12 pages: **CER 0.38%**, best yet, and faithful (1 accent misread, no modernising); reads `....` as `...`. ~15 s/page under load. Its Ollama template has no stop token: it reads the page, then starts over, so the reading is cut where its opening repeats (`probe_ocr.py`, `NEVER_STOPS`). Prompt `Text Recognition:` |
| Ollama | `deepseek-ocr:3b` | OCR candidate | Teirlinck 12 pages: CER 0.37% but **modernises** 10× (`vóor→vóór`, `éen→één`, `streelend→strelend`) and keeps line-end hyphens. ~9 s/page. Prompt `Free OCR.`; the grounding/markdown prompt loops |
| Ollama | `numind/nuextract3:q6_k` | **Metadata candidate**: front pages in, a filled JSON template out | Stella, Lady into Fox, Crime: all fields right, 4–10 s per book, given **all** front pages as images and an instruction to ignore stamps and handwriting and to describe this edition (without it: Stella's original publisher, an owner's inscription as author, a library barcode as ISBN). Read Crime's title page, which the text layer lacks, verbatim ("FORD MADOX FORD"). `experiments/probe_metadata.py` |
| Ollama | `numind/nuextract3` (BF16 safetensors, `latest`) | — | **Broken under Ollama 0.40**: gibberish from images and text alike. Use the GGUF `q6_k` tag |
| Ollama | `clef:27b` | **OCR-check judge (in use, `judge_model`)** | OCR suspects (Dolittle pp. 30–49, glm-ocr readings): 54/55 right; hosted builds (OpenRouter `cloudflare/clef`, Goede dochter's 419 suspects) judge differently: Cloudflare 96.2% the same pick, 348 of 377 right against local's 352; PrimeIntellect hardly reads the image (275), so neither replaces it; confident (≥ 0.8) on 46, all right, where clef-flash was confident on 16. ~3.4 s per suspect under load. **Worse at line roles**: Crime CER 0.63% → 0.98%, paragraph precision 0.966 → 0.695 (keeps page numbers, splits paragraphs), so clef-flash keeps that job |
| Ollama | `translategemma:4b` | Tried as Dutch→Dutch OCR | **Unfit**: with its translation prompt it paraphrases (`hief`→`heeft`, `trillend opwiegelen`→`trilde omhoog`) and modernises, CER 4.9% on one page; any other prompt gives empty output |
| Ollama | `translategemma:12b` | Tried as Dutch→Dutch OCR | **Unfit**: its translation prompt hallucinates a scene description; with the old-spelling prompt it transcribes at ~1.4% CER (worse than gemma4 and tesseract), modernises 12×, and loops on one page of 12 (Ollama aborts: "token repeat limit reached"). ~14 s/page |
| Ollama | `translategemma:27b` | Tried as Dutch→Dutch OCR | **Unfit**: old-spelling prompt, Teirlinck 12 pages: CER 0.99% (gemma4 0.63%), word swaps (`eenvoud→eenvoudig`, `onschuld→onschuldig`), 11 accent/spelling changes. Merged with tesseract it stays at 0.99% with 11 wrong words unflagged. ~30 s/page |
| Ollama | `llava:34b` | Tried as Dutch OCR | **Unfit**: on one Teirlinck page it invents text and loops ("Hij had geen twijfel aan de verdiensten van…" over and over), CER 406%. ~170 s/page |
| Ollama | `nemotron3:33b` | Tried as Dutch OCR | **Unfit**: thinks by default (107 s and empty output); with `think: false`, 7 s/page but CER 14% on one Teirlinck page: invented words (`dampwalmen→dampwaarneming`) and modernised (`zijne→zijn`) |
| — | DocLayout-YOLO (DocStructBench, `layout` group) | Page layout regions from the page image | 20 tricky pages, 0.1–0.5 s/page on MPS. Finds figures, captions, drawn initials, titles (Crime's bare "III"), and furniture as `abandon`. Sees printed text the OCR layer lacks (Dolittle p97 subtitle). Misses Boze tongen's spaced part title (`abandon`). Run on a page turned a quarter, it finds a landscape plate's caption (8/8 Dolittle plates, no false positives on 4 books) but not which way is up. See `experiments/probe_layout.py`, `probe_orientation.py` |
| Ollama | `hf.co/unsloth/Qwen3.6-27B-MTP-GGUF:Q6_K` | Correction / structure candidate | available, unevaluated |
| Ollama | `qwen3.8:27b-nvfp4` (MLX, 18 GB) | **Reads quote questions' lines (in use, `read_model`)**; proofreader; reading and language-judge candidate | Quote questions, told the book's style, its marks on the layer's letters: right where the line is wrong / wrong where right: Reis 51/0 of 120, Vals alarm 29/0 of 60, Thief-Taker 76/3 of 287, validation De tuin 42/1 of 73. The style sentence matters: Reis raw readings 55/4 without it, 57/2 with. | Stella proofreading test (68 answered regions, 9 really wrong): transcribing the tight crop and comparing in code catches 9/9 with 3 false alarms in 58 (gemma4: 6/7, 5 alarms); yes/no on crop and text AUC 0.92, no false alarms, but catches only 3. As text judge between its reading and the answer: 9/12 right with thinking off (unsure on punctuation, ~0.53), 10/12 with thinking on and winnow reading its reply (punctuation 0.72–0.88), ~20 s/call. ~1 s per crop reading. Thinking is on by default: pass `think: false` for one-token answers. **Best line reading yet** on Goede dochter pp. 9–64: CER 0.17% folded, 1,504/1,622 lines exact (layer 0.20%, 1,460); right where the layer is wrong on 119 lines, wrong where it is right on 76. Its errors are real words (`doodgaan→doorgaan`, `woonden→wonden`, `verhieven→verheven`, once German `wartete`) and dropped or doubled letters, so it never decides alone **The cost of a cold run**: ~1.4 s a line, 70–75% of a trust-data rebuild's time (Dolittle 75 of 98 min, De tuin 36 of 51, Metro 104 of ~156). Hosted (OpenRouter, Goede dochter pp. 9–20): DeepInfra bf16 reads like it (0.11% CER, no quote marks wrong, the same line on 94.5%) at ~10 lines a second; Darkbloom fp4 is worse than the layer (0.15%, 5 quote marks wrong) |

## Environment

- Apple M4 Max, 64 GB RAM, macOS.
- Ollama 0.40.0 at `http://127.0.0.1:11434` (updated 2026-10-06 from 0.35.1; earlier scores were on 0.35.1).
- Ollaya at `http://127.0.0.1:11435`.
- Present: `uv`, `python3`, `pandoc`, calibre `ebook-convert`, poppler
  (`pdfinfo`, `pdftotext`, `pdfimages`).
- epubcheck (Homebrew).
- d2 (Homebrew), renders `docs/pipeline.d2` to the README's diagram.
- scikit-learn (Python dep) for the line-role classifier probe.
- Dependency group `layout` (a default group, so plain `uv run` has it): `doclayout-yolo` with
  PyTorch, and the DocLayout-YOLO DocStructBench weights
  (`juliozhao/DocLayout-YOLO-DocStructBench`, `doclayout_yolo_docstructbench_imgsz1024.pt`,
  in the Hugging Face cache). Used by `review` to flag regions from page images.
- Word lists: `work/lexicon/{nld,eng}-words.txt`, built by `lexicon.py` from the
  tessdata models with `combine_tessdata` and `dawg2wordlist` (both come with
  Homebrew's tesseract). Nothing installed.
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
dash = "–"             # optional: how the book prints dashes ("–" or "—") …
dash_spacing = "thin"  # … and their gaps ("none", "thin", "word"); else measured
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
and moves to the next unanswered region; a typed line that matches none of the readings,
or a straight quote in a curly-quoted book, is queried once and saved on the second
Save (`review.doubtful`; warned answers in `review/warnings.jsonl`). Arrows move through all regions. A
region with a box can be turned (`r`, ↺/↻) and read again by tesseract (`o`);
`-` and `+` zoom the crop out and back in. "Rebuild book" applies the answers and rebuilds
the EPUB. Flags come from the model's decisions before answers, so the list
stays put while you work.

### Golden books

Public-domain scans paired with a human-checked reference text, which is what
every change gets measured against. [docs/golden-books.md](docs/golden-books.md)
lists every book with its set, the pages scored, the estimated cold cost and how
far its text layer is from its reference. Each lives in `golden/<name>/` **in git**:
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
- **Three sets.** Tuning books are chosen on; validation books were consulted
  before, so they check that a change carries over; the **test set**
  (`bench.SETS["test"]`: Het geluid van bananen) is scored **once, at the end of
  the plan, and touched by nothing else**: no eval, quality, review or bench run,
  no trust data, no probe. `eval`, `quality`, `golden review` and `bench test`
  refuse it without `--score-test`.
- **Checking a candidate pair** (scan PDF plus the publisher's EPUB) before
  writing its manifest: `uv run python experiments/probe_candidate.py <scan.pdf>
  <ref.epub> [heading prefix …]`, no models, about 10 s per 100 pages. It prints
  the scan's kind, the EPUB's edition and markup, the body page range, the text
  layer's CER against the EPUB per band of pages and the most frequent word
  differences. A pair fits when the EPUB's colophon names the scan's printing and
  the differences are OCR slips (a letter, a quote mark) at the layer's own rate
  (0.2–0.5% CER), not real-word swaps or a band that jumps. Prefer IA Scribe scans
  (Stella's format); skip calibre-made PDFs, other printings, DRM and pre-1934
  spelling. An EPUB that sets its dashes as spaced hyphens gets
  `hyphen_dash = "–"` in `[reference]`, which derive sets as the print's dash.
- **Known deviations.** No publisher's EPUB matches its print in every
  convention. Each known deviation of a pair is handled in one of three places,
  and nowhere else: a gap derive can undo is declared in the manifest's `[reference]`
  (`hyphen_dash`) and listed in PROVENANCE.md; a glyph choice the output may
  make differently is folded by `evaluate.normalise` and counted per side, so
  `eval` prints how much it forgave; what neither covers (a corrected word, a
  later impression) is settled by a verdict. A deviation that lives only in a
  comment or in this table is untracked: move it to one of the three.
- **Retiring a book.** A reference can stop being one: when a book's remaining
  disagreements are mostly edition differences, or its verdict backlog never
  shrinks, its score measures the edition, not the pipeline. Two signals need no
  verdicts: the text layer's CER against the reference and the share of its body
  lines the aligner can't place (`golden/signals.py`). `bench` records both per book,
  over the lines the build calls body, and names each book past a threshold as a
  suspect pair; [docs/golden-books.md](docs/golden-books.md) has them over all lines
  (regenerate it with
  `uv run python experiments/golden_overview.py > docs/golden-books.md`, half a
  minute, no models, after adding, slicing or retiring a book; there furniture counts as
  unplaced too), and `eval`'s fold counts where the two sides differ. Past three times
  the set's median layer CER, or one body line in twenty unplaced, the book is suspect. **Whoever notices says
  so in the session's report and proposes retiring it, without being asked.**
  Retired books go to `work/retired/`, with a dated line in docs/decisions.md.

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

`eval` builds the book, prints the scores and the most frequent differences, and
appends a line to `work/<book>/eval-history.jsonl` with the commit, the settings,
which decider settled the OCR check (`fixed rule` or `trust <model hash>`) and each
model's Ollama digest or Ollaya release. Given several books it scores
them one after another and ends with a line per book.

**Disagreements and verdicts.** Gutenberg is a transcription, not the scan, so
where the output disagrees with it a human decides what the scan prints:

```sh
uv run roboscriptorium golden review work/the-nature-of-a-crime--doubleday-1924  # → http://127.0.0.1:8765/
```

Keys: `1` the reference is right (pick the pipeline mistake), `2` the scan prints
the output (edition difference or transcriber change), `3` type what the scan
prints, `0` unsure, arrows to move. Verdicts go to
`golden/<name>/verdicts/<scan>.jsonl` (in git), keyed on the reference words and
six words of context either side, so they survive pipeline changes. `eval`
patches them into the reference for that scan and reports the remaining
disagreements by mistake category.

Retired (in `work/retired/`, manifests in git history): Boze tongen, De dode
kamer, Sense and Sensibility (all three scans), Goede dochter's eighth printing.

| Golden book | Scan | Notes |
| --- | --- | --- |
| the-nature-of-a-crime | `doubleday-1924` | **The scan Gutenberg #75172 was made from**; 94 body pages, short; Times OCR layer; running heads |
| de-aanslag | `calibre-pdf` | Dutch, Mulisch, 51st printing. **Not a scan**: calibre's PDF of the retail EPUB, so its text layer is exact. For born-digital PDFs, page joins and (later) italics. **Copyrighted**, all text in `work/golden/` |
| lady-into-fox | `chatto-1922` | **Reserve** (in no bench set; still never trained on): retired from validation on 2026-10-08. Its reference differs from its print in typography, so its labels measure the reference more than the pipeline (docs/design.md). Its scores informed earlier choices, so it is no clean test. 1922 first edition, same as Gutenberg #10337; one continuous text, no chapters; wood engravings. **EU copyright until 2051**: only the manifest is in git, the reference and verdicts live in `work/golden/lady-into-fox/` (`eu_copyright_until` in the manifest) |
| grand-hotel-europa | `ia-scan` | **Reserve** (in no bench set; never trained on): retired from validation on 2026-10-08. Its EPUB was made from another printing than the scan, and 9 of the old slice's 16 reference headings have no line on the scan, so its score (build 1.9% CER against the layer's 0.4%) measures the pair more than the pipeline. Dutch, 2018, Pfeijffer; IA Scribe scan of the 11th printing (2019), 537 body pages. Reference: the retail EPUB, made from the 1st printing. Chapter label, title and numbered sections. Borrow-only scan; **copyrighted**, all text in `work/golden/`. Score it in slices (`--pages`/`--chapters`) |
| de-tuin-van-de-avondnevel | `ia-scan` | **Validation.** Dutch translation (Tan Twan Eng, Xander); IA scan of the 2014 paperback, reference the 2013 retail EPUB of the same translation and typesetter. Many italic foreign words. Pages 11–374, chapters 1–26. Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| goede-dochter | `ia-scan` | Dutch translation (Slaughter, HarperCollins Holland 2017); IA scan of the first printing, reference the retail EPUB of the same translation (typeset by Mat-Zet). The cleanest Dutch reference: **tune on it**. Pages 9–508, 25 chapters (a part title, then titled chapters). Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| vals-alarm | `ia-scan` | Dutch, 2011, Boersma (Verbum Crime). IA scan of the 2nd printing of the first edition, reference the retail EPUB. **Tune on it**: 48 chapter headings ("Vandaag", "1 Later", "2", "Epiloog") at the top of a new page. Pages 11–302. Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| villa-toscane | `calibre-pdf` | **Validation**, born-digital. Dutch, 2014, Van Rijn; calibre's PDF of the retail EPUB, like De aanslag. Novel = chapters 1–12 (13 is the colophon). **Copyrighted**, all text in `work/golden/` |
| the-story-of-doctor-dolittle | `stokes-1920` | Tenth printing, same as Gutenberg #501; full-page plates with captions, drawn initials the text layer drops. Bench slice pages 23–88, chapters 1–7 (20 pages with a plate or a drawn initial) |
| de-eerlijke-vinder | `ia-scan` | Dutch, Spit, CPNB Boekenweekgeschenk 2023; IA Scribe scan in **Stella's format** (360 ppi MRC, GlyphLessFont layer, 104 pages); reference CPNB's own EPUB of the edition (via calibre). Pages 12–95, 4 parts ("I"–"IV", the first a drawn numeral the layer lacks). Design Frank August. **Validation** since 2026-10-08, scored whole; never trained on since (it was in the line-role probes' leave-one-book-out set before, so it validates rather than tests). Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| monterosso-mon-amour | `ia-scan` | Dutch, Pfeijffer, CPNB Boekenweekgeschenk 2022; IA Scribe scan like Stella's; reference CPNB's EPUB, made after the first printing. Pages 9–96, 22 numbered chapters (the layer lacks the small "1"…). Typography Nico Richter: the same CPNB grid as De eerlijke vinder (13.2 pt pitch, ~57 characters a line) but another, lighter typeface. Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| reis-om-mijn-schedel | `ia-scan` | Dutch translation (Karinthy, Frans van Nes), **Van Gennep, Stella's publisher**, first printing 2014; IA Scribe scan in Stella's format, 260 pages; reference Van Gennep's EPUB "naar de eerste druk". Pages 11–255, 27 chapter titles ("kop"); its footnotes are in `notes.txt` and left out of the score. **The best stand-in for Stella**: same leading (15.0 pt), no running heads, folio centred at the foot, what looks like the same serif face; Stella's type is ~6% larger on a narrower measure (258 against 278 pt). Borrow-only scan; **copyrighted**, all text in `work/golden/`. Bench slice pages 11–110, the Voorwoord and chapters 1–10 (sections 1–11) |
| the-thief-takers-apprentice | `ia-scan` | **The first modern English scan**: Deas, Gollancz first edition 2010; reference Gollancz's eBook of the edition (via calibre). An older IA PDF: 300 ppi, LuraDocument, **InvisibleOCR** text layer (`pdf.py` reads it). Pages 11–292; three parts ("PART ONE" / "THE THIEF-TAKER") and 42 chapters (number line, name line), each label and title a heading (90); a large first letter on each chapter. Its layer drops some apostrophes and splits the word (`didn t`, `I m`). Borrow-only scan; **copyrighted**, all text in `work/golden/`. Bench slice pages 11–84, Part One and chapters 1–10 (sections 1–22) |
| afscheid-van-verspilde-tijd | `ia-scan` | **Tuning.** Dutch translation (Wijkmark, Elke Schütt), Uitgeverij de Rode Kamer, first printing 2011; IA Scribe scan in Stella's format, 132 pages; reference the publisher's own ebook (via calibre), whose dashes are spaced hyphens (`hyphen_dash`). Pages 9–124, 23 bare-numeral chapter headings, some of which the layer lacks; a Times-like face, spaced en dashes, specks read as characters. Borrow-only scan; **copyrighted**, all text in `work/golden/`. Bench slice pages 9–70, chapters 1–11 |
| het-geluid-van-bananen | `ia-scan` | **The test set: score nothing on it until the end (`--score-test`).** Dutch translation (Temelkuran, Margreet Dorleijn), **Van Gennep, Stella's publisher**, first printing 2013; IA Scribe scan in Stella's format, 328 pages, a library copy with stamps and a catalogue slip; reference Van Gennep's EPUB "naar de eerste druk", set like Reis's. Pages 9–323: three part pages, 28 numbered chapters, 26 footnotes in `notes.txt`, "* * *" scene breaks. Seen in the text layer alone: ç read as g (Tunç), dotless ı, superscript ordinals as °, single quotes as doubles, small chapter numerals missing or "Io". Borrow-only scan; **copyrighted**, all text in `work/golden/`. Scored on pages 9–101, Boek 3 and chapters 1–9 of Boek 1 (sections 1–14) |
| metro-2033 | `ia-scan` | **Tuning**, the second modern English scan: Glukhovsky, transl. Natasha Randall, **Gollancz 2010 like Thief-Taker**; IA Scribe scan (2022) of the trade paperback's fifth impression, 468 pages, 374×629 pt; reference Gollancz's eBook of the same year (one impression earlier). Pages 7–464, 20 chapters, each a label line ("CHAPTER 1", spaced sans capitals) and a title (40 headings); `<i>` italics. Typeset by The Spartan Press: spaced en dashes (the EPUB's spaced hyphens, `hyphen_dash`), spaced ellipses ". . ." in print and EPUB alike (the layer reads them both ways), single quotes read as doubles, "I" read as "|", "1" or "P" (`Pll`). Bench slice pages 7–111, chapters 1–5 (sections 1–10). Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| de-cipier | `ia-scan` | **Tuning.** Dutch translation (Delaney, Paul Heijman), Van Holkema & Warendorf first printing 2013; IA Scribe scan (2023), 488 pages, 346×566 pt, Garamond set by ZetSpiegel, a library copy; reference the publisher's e-book "naar de eerste druk" by the same typesetter. **No known deviations**: spaced en dashes, single quotes and the ellipsis glyph in both. Pages 9–482: a Woord vooraf, chapters 1–14, "Drie dagen later", Epiloog (17 h1 headings). The layer agrees at 0.21% CER but lacks the numerals 1–9, reads ë as é (`knieén`), hè as hé, drops stress accents (`háár`), and reads the small-capital police ranks as lower case (`pc` for DC). Bench slice pages 9–92, chapters 1–4 (sections 1–4). Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| artemis | `ia-scan` | **Tuning**, the third modern English scan: Weir, Del Rey (Ebury) UK paperback 2018, second printing; IA Scribe scan, 322×540 pt, a library copy; reference Penguin Books' 2026 e-book of the same UK text, one reissue later. **Known deviation**: the e-book writes "Vetrov" for the print's "Vetrova" (4, verdicts). Unlike every other scan: a serif body with emails set in a bold sans, running heads with the folio, double quotes, unspaced em dashes, spaced ellipses (the EPUB's glyph; folded), and each chapter opening with its number drawn in a circle, an image in the EPUB too (`image_heading`) and absent from the layer. The layer reads sans "I" as "\|" (213 times) and drops apostrophes (`youre`) and accents (`Palacio`). Pages 13–317, 17 chapters. Bench slice pages 13–80, chapters 1–3. Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| youre-never-weird-on-the-internet | `ia-scan` | **Validation**, the only English one and a layout torture test: Day's memoir, Touchstone first hardcover edition (2015), **fifth printing**; an older IA PDF like Thief-Taker's (300 ppi, LuraDocument, Times layer), 280 pages, a library copy; reference Touchstone's ebook of the edition, the same copyright page. The printing gap is accepted on the layer: 0.46% CER in every 20-page band, every frequent difference its own. Pictures with their captions and any text in them baked in (a book cover reading "LEARNING" the layer reads as a line; the reference has no words for them, so leaked picture text scores as errors); chapter numbers "- 1 -", titles, bracketed sections ("[ Jesus Loved Me! ]", brackets read as `j`, `!`, `|`) and a subtitle per chapter; lettered hanging lists; running heads with the folio; spaced ellipses. Pages 13–272, the Foreword to chapter 12. Bench slice pages 13–94, the Foreword, the Introduction and chapters 1–3 (sections 1–16). Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| 11-22-63 | `ia-scan` | **Tuning**, the fourth modern English scan and the first American one: King, **Scribner first edition, first printing** (November 2011, printer's key 1 3 5 7 9 10 8 6 4 2, designed by Erich Hobbing); IA Scribe 4.3 scan (Stella's vintage), 872 pages, 374×644 pt, a library copy; reference Scribner's eBook of the same edition, a calibre conversion of the Kindle file (obfuscated fonts, no content DRM). No known deviations. Six parts, 31 chapters and 345 numbered sections, each a heading (386 with the prologue, the Final Notes and the Afterword); serif body, chapter labels in a condensed bold sans, running heads with the folio, double quotes, unspaced em dashes, spaced ellipses, 1,500 italic paragraphs. The layer reads the capital I as T, \|, 1, \\ or J and merges "in a" to "ina". Pages 15–865. Bench slice pages 15–94, the prologue and chapters 1–3 (sections 1–24). Borrow-only scan; **copyrighted**, all text in `work/golden/` |
| het-ivoren-aapje (**retired as a bench**) | Gutenberg #28068 page images | Dutch, 1909, pre-1934 spelling; PNG page images and no text layer, so the OCR test bench. **EU copyright until 2038**: reference and images stay in `work/het-ivoren-aapje/`, see `experiments/probe_ocr.py`. **No longer used to choose OCR models**: pre-1934 spelling, unlike every book we target; re-bench on modern Dutch line crops instead |
