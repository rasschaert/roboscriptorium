# How it works

A walk through what happens to a book, from the PDF to the EPUB, and how the
machine is measured and taught. [design.md](design.md) says *why* each part is
there and what it was measured to earn; [AGENTS.md](../AGENTS.md) lists the
modules; the [diagram](pipeline.svg) draws the stages with the model behind each.
This page is the story that connects them.

## The idea in one paragraph

A scanned book already carries an OCR text layer, and it is good: a few errors in a
thousand characters. Those few are the whole problem, because a careful edition
has none. No single reader fixes them; every OCR model has its own habits. So the
book is read several more times by readers that fail *differently*, the places
where the readings disagree become suspects, judges look at each one, and a model
trained on books whose true text is known decides which version to trust. What it
isn't sure of becomes a question for a person, with the scan crop beside it. The
person's answers go into the next build and become labels the machine learns from.
Around that core, other stages work out what each line *is* (body text, heading,
page number), join lines into paragraphs, and set the book's typography the way it
was printed.

## Two kinds of model

Every model call is one of two kinds, and the rule for choosing is strict:

- **Decision models** ("System One": winnow on Ollaya, clef and clef-flash on
  Ollama's `/v1/systemone`) answer a question whose options are fixed in advance
  and return a probability for each. "Is this line body text, a heading, a page
  number…?" "Which of these three versions does the crop show?" They generate no
  text, so there is no prose to parse.
- **Generative models** ("System Two": glm-ocr, qwen3.8 on Ollama) produce new
  text: reading a line crop, a printed line the layer lacks.

If the answer comes from a list known beforehand, a decision model gives it. A
model's confidence is not taken as the probability it is right; where that matters,
it is calibrated or learned from labelled data (see *Learned trust* below).

Everything runs on this machine. A hosted model is used only when the user allows
it for a particular run, pinned to one provider, and its outputs are cached under
the local model's name with a note of where they came from.

## A book on disk

A book is a directory, `work/<book>/`, holding `source.pdf` and a `book.toml`
(title, author, language, cover page, body page range, optionally the dash style).
Every stage caches what it produced under `work/<book>/stages/`: the text layer,
layout regions, each reading of each line, every decision a model made. A rebuild
reuses all of it, so only what changed costs model time. Caches are written whole
and versioned, and append-only ones skip a cut-off last line, so a run killed
halfway resumes where it stopped.

Nothing here is in git: books, scans and anything derived from them stay in
`work/`. Only code, prompts, configs and synthetic test fixtures are committed.

## The stages

`pipeline.run` builds a book in this order.

### 1. Read the page

**Text layer** (`pdf.py`). PyMuPDF reads the PDF's own text as visual lines, each
with its box on the page and a stable identity (`SourceRef`: page and line
number). That identity follows the line through every later stage: a fix, an
answer or a score always refers back to the line as the layer had it.

**Layout regions** (`layout.py`). DocLayout-YOLO, a vision model (not an LLM),
marks figures, captions, titles and page furniture on each page image. Pages that
hold only a picture are also run turned a quarter, to find captions printed
sideways.

**Missing lines** (`missing.py`, scans only). OCR layers drop short lines: a bare
chapter number, a one-word line of dialogue. Where the layout model sees a
one-line region with no text-layer line in it, glm-ocr reads that region and the
reading is added to a *copy* of the page as a line of its own, in reading order.

**Type** (`typestyle.py`). Each line's type size, stroke weight, letter width and
capitals, measured on the page image relative to the body text, with no model.
Lines set alike in one place on their pages (all chapter titles, say) form a group.

**Dash style** (`typography.py`) is measured here too, before any model reads a
line: en or em dash, and how wide the gaps around it are, from the stroke lengths
and spacing on the scan (or from `book.toml`). Together with the quote style the
layer shows (single or double quotes, the ellipsis glyph), it becomes a sentence
the readers and judges are told, because typography is a property of the book, not
of a line.

### 2. Understand the page: line roles

(`roles.py`) Each line gets a role: body, heading, page number, running head, or a
print artefact to drop. Lines in the middle of the text block, flush with the
margin, are body text without asking. The doubtful ones, near the top or bottom of
the page and short centred lines anywhere, go to clef-flash with their position,
their neighbours, and features the model can't see for itself (does this text
repeat on other pages, as a running head does?). Then rules in code override the
model where layout settles the question: what is true by definition is enforced,
not hoped for. A style group shares the role most of its lines got. Answers are
cached in `stages/decisions.jsonl`.

### 3. Check the OCR (scans only)

This is the core, and where most of the model time goes.

**More readings.** Every body line is read again, short lines too, by three readers
chosen because they fail in different ways:

| Reader | Sees | Good at | Bad at |
| --- | --- | --- | --- |
| glm-ocr | the line's crop | letters and words | drops quote marks and diaereses |
| tesseract | the whole page, its own segmentation | marks the layer's boxes cut off, dashes | punctuation, opening quotes |
| qwen3.8, told the book's style | the line's crop | quote marks | swaps in a plausible real word |

A crop reaches one em past the line's ends and a few points above and below, but
stops at a neighbouring line's box, so a reader never sees half of the next line.

**Suspects.** Where any reading differs from the text layer, the differing stretch
(widened to whole words) becomes a *suspect* with its *versions*: the layer's
first, then each different reading. Take an invented line the layer reads as

    Hij keek naar buiten.

while glm-ocr also reads `buiten.` and qwen3.8 reads `buiten.’`. One suspect, two
versions: `buiten.` (layer, glm-ocr) and `buiten.’` (qwen3.8). Two places that
differ in one line are two suspects, so each can be settled on its own.

**Judges.** For every suspect:

- **clef:27b** sees the crop of the place on the scan and picks the version it
  shows. It is usually right, and is told the book's typesetting.
- **winnow:e4b** reads only the sentence and picks the version that reads right.
  Alone it is a poor judge; its value is as an alarm: where it disagrees with clef,
  clef is wrong several times as often.
- **The word list** (unpacked from tesseract's own language model) says which
  versions consist of known words. It is a vote, shown to the reviewer and used as
  a feature, never a decision on its own.

Each suspect also records which readings support which version.

**Learned trust** (`trust.py`). A small model (shallow gradient-boosted trees)
scores each version of each suspect: how likely is this what the page prints? Its
features are the judges' picks and confidences, which readings back the version,
the word list's verdict, the kind of difference (a quote mark, a letter, a word
break, a length change), and a *prior* for the exact substitution: across books,
`|` read for `I` is nearly always the layer's error, glm-ocr dropping a `’` nearly
always glm-ocr's. Then:

1. the suspects are ranked by how sure the model is of its best version;
2. the least sure are **asked**, up to a budget of questions per page, counted over
   the whole book so a bad page can take several and a clean page none;
3. every other suspect takes its best version: kept as the layer reads it, or
   **fixed**.

Fixes go into a copy of the pages; the original layer stays as it was, because
review answers are keyed on it. The trust model is trained only on tuning books
(see *Measuring*); if it is missing or was saved for another feature set, the
build stops rather than fall back silently. `ROBO_OCR_TRUST=0` selects the old
fixed rule (both judges agree and clef is at least somewhat sure) explicitly.

### 4. Review

Run with `roboscriptorium review work/<book>`. The build flags what a person
should look at (`flags.py`): the OCR doubts trust asked about, one question per
place; headings; lines dropped or kept without the model being sure; garbled text;
pictures, captions, titles that aren't headings; text the layout model sees and the
layer lacks; and paragraphs whose curly quotes don't pair up (`quotes.py`).

A local web page (`review.py`) shows each question beside its scan crop. An OCR
doubt lists each version on its own row with the part that differs marked and the
models that picked it; one key answers. A quote question offers qwen3.8's reading
of the line, but only its quote marks and the punctuation beside them, on the
checked letters, since its quote marks are reliable where its letters aren't. A
drawn initial gets a guess at its letter from clef-flash: which letters make the
word beside it a word, then which of those the drawing shows.

People slip too (about one answer in eight on Stella), so an answer is checked
before it is saved: a typed line must match one of the readings, and a straight
quote in a book set with curly ones is queried. The page says why once, and saves
on the second press.

Answers go to `work/<book>/review/regions.jsonl`. The flags are computed from the
model's decisions *before* answers are applied, so the list stays put while you
work through it.

### 5. Answers, then assembly

**Answers** (`corrections.py`) are applied to copies of the pages and roles on the
next build: a retyped line, a role changed, a picture marked, a missing line
inserted where its region sits. An answer about one place in a line changes only
that place, so several answers and the OCR check's own fixes in one line combine.

**Reflow** (`reflow.py`) joins lines into paragraphs and headings, using
indentation, short last lines and the roles. A line-end hyphen stays or goes by
evidence, strongest first: how the book spells the word elsewhere inside a line;
which of the two forms the word list knows; a capital after the break; the parts
beside a hyphen already in the word.

**Italics** (`italics.py`) come from each word's stroke slant on the page image,
no model. **Typography** sets every dash between words in the book's one style.
**Figures** (`figures.py`) are the layout model's pictures on body pages, trimmed
where a caption overlaps, turned upright where printed sideways, placed after the
paragraph they follow, with their captions.

**The EPUB** (`epub.py`) is written by hand with zipfile and must pass epubcheck
with no errors or warnings.

## Measuring: golden books

A change is good only if it is measured to be. The measure is a set of **golden
books**: real scans paired with a human-checked reference text (a Project
Gutenberg transcription of the same edition, or the publisher's own EPUB of the
same printing). [golden-books.md](golden-books.md) lists them.

- **Alignment.** The build's output is aligned with the reference
  (`golden/align.py`), and every difference is located on the scan.
- **Verdicts.** The reference isn't the scan either: an EPUB may correct a word or
  set a dash differently. Where output and reference differ, a person can say what
  the scan prints (`golden review`); verdicts are stored in git and patched into
  the reference. Typography the EPUB may set differently (quote glyphs, ellipses)
  is folded on both sides and counted, so the gap stays visible.
- **`eval`** prints CER, WER and paragraph F1 for one book.
- **`quality`** counts what a reviewer is left with: wrong words per page left
  unasked, at budgets of a quarter, a half and one question per page.
- **`bench`** is *the* measure for a change. It scores pinned slices of every
  book in a set before and after, page by page, and asks one question: does
  "after review" (unasked errors plus the reviewer's own slips per question)
  improve over the set's books, each weighing the same? Any single book getting
  clearly worse vetoes the change.

The books come in three sets. **Tuning** books are the ones choices are made on
and the trust model is trained on. **Validation** books check that a choice carries
over to books it wasn't made on. The **test** book is scored once, at the end, and
touched by nothing else; the CLI refuses to score it without `--score-test`.

A pair can stop measuring the pipeline: when its EPUB was made from another
printing, most "errors" are edition differences. The bench records two signals per
book that need no verdicts (the layer's own CER against the reference, and the
share of body lines that can't be placed), and a book past the threshold is
proposed for retirement.

## How the machine learns

The trust model is where the machine learns, and the loop goes like this:

1. **Trust data** (`experiments/ocr_trust_data.py`). A book is built and its
   suspects collected. Each version of each suspect is labelled by comparing the
   line with the aligned reference: does this version make the line read as
   printed? A suspect where no version comes close enough is left unsettled and out
   of training. A book without a reference (Stella) is labelled by the user's own
   review answers instead.
2. **Training** (`experiments/train_ocr_trust.py --save`). The trees are trained on
   every tuning book's settled suspects, and once more without each tuning book in
   turn, so the bench can score a tuning book with a model that never saw it.
   Validation and test books are never trained on.
3. **Benching.** The new model is measured on tuning, then validation.

A new model release fits the same loop: add it as a reading or a judge, rebuild
the trust data, retrain, and let the bench say whether it earns its place. The
target book comes out right because the machine does, not because rules were tuned
to it.

## Running it

```sh
uv run roboscriptorium doctor              # are Ollama and Ollaya answering?
uv run roboscriptorium build work/stella   # → work/stella/stella.epub
uv run roboscriptorium review work/stella  # questions on http://127.0.0.1:8765/
uv run roboscriptorium eval work/<golden scan> --pages 9-64 --chapters 1-4
uv run roboscriptorium bench tuning
```

A cold build costs about a minute per page, most of it the line readers and
judges; a warm rebuild, seconds. Long runs go through `experiments/detached.sh`
(in `screen`, so they outlive the terminal) and `experiments/timed.sh` (which
records their minutes in [run-times.md](run-times.md)).
