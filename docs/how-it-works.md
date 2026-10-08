# How it works

This page follows a book from its PDF to its EPUB, then explains how the machine
is measured and how it learns.

Three other documents go with it. [design.md](design.md) gives the reason for each
part and the measurements behind it. [AGENTS.md](../AGENTS.md) lists the modules.
The [diagram](pipeline.svg) draws the stages with the model behind each one.

## The idea

A scanned book usually comes with an OCR text layer, and that layer is good: a few
wrong characters in every thousand. A careful edition has none, so those few are
what this project exists to fix.

No single OCR model fixes them, because every one makes mistakes of its own. So
the book is read several more times, by *readers* chosen because they make
different mistakes. Each reader gives a *reading* of every line. Where a reading
differs from the text layer, the place becomes a *suspect*, and each way of reading
it is a *version*.

*Judges* look at each suspect and pick a version. Then the *trust model*, trained
on books whose printed text is known, decides which version to believe. Where the
trust model is unsure, a person gets a question, with the scan beside it.

The person's answers go into the next build. They also become labels the trust
model learns from.

Around this OCR check, other stages work out what each line is (body text, a
heading, a page number), join lines into paragraphs, and set the typography the
way the book was printed.

## Who does what

| Job | Who | Kind |
| --- | --- | --- |
| Find figures, captions and titles on the page image | DocLayout-YOLO | vision model |
| Read a printed line the text layer lacks | glm-ocr | reader |
| Decide what each doubtful line is (body, heading, page number…) | clef-flash:9b | decision model |
| Read every body line again | glm-ocr, tesseract, qwen3.8 | readers |
| Pick a version of each suspect | clef:27b, winnow:e4b, the word list | judges |
| Fix, keep or ask about each suspect | the trust model | trees trained on golden books |
| Answer what the machine is unsure of | you | reviewer |

### Readers write text

A reader looks at the scan and writes down the text it sees. glm-ocr and qwen3.8
are generative models on Ollama, reading one line's crop at a time. tesseract is a
classic OCR program, reading the whole page.

### Judges choose from a list

The AI judges are decision models. They answer a question whose options are
fixed in advance, such as "which of these versions does the crop show?", and give
a probability for each option. They write no text, so there is no prose to parse.
clef runs on Ollama's `/v1/systemone` endpoint, winnow on Ollaya.

The third judge, the word list, is plain code.

clef-flash, which decides line roles, is the same kind of decision model as the
judges, asked a different question.

The rule behind this split: if the answer comes from a list known beforehand, a
decision model gives it. Only a job that needs new text gets a reader.

### The trust model weighs them

A judge's confidence is a number it reports, and it can differ a lot from the
chance that the judge is right. So the trust model doesn't take any judge's word.
It learns from labelled books how far to believe each reader and judge, for each
kind of difference.

### Local first

Every model runs on this machine. A hosted model is used only when the user allows
it for a particular run. It is then pinned to one provider, and its outputs are
cached under the local model's name, with a note saying where they came from.

## A book on disk

A book is a directory, `work/<book>/`, with two files in it to start:

- `source.pdf`, the scan or the born-digital PDF;
- `book.toml`, with the title, author, language, cover page, body page range and,
  optionally, the dash style.

Every stage caches its output under `work/<book>/stages/`: the text layer, the
layout regions, each reading of each line, every decision a model made. A rebuild
reuses all of it, so only what changed costs model time.

Caches are written whole and include a format version, and append-only ones skip a
last line that was cut off. A run killed halfway resumes where it stopped.

Books, scans and everything derived from them stay in `work/`, outside git.

## Stage 1: reading the page

### The text layer

`pdf.py` reads the PDF's own text with PyMuPDF, as visual lines. Each line has its
box on the page and an identity, `SourceRef`: its page and line number.

That identity follows the line through every later stage. A fix, an answer or a
score always refers back to the line as the text layer had it.

### Layout regions

`layout.py` runs DocLayout-YOLO, a vision model, on each page image. It marks
figures, captions, titles, and page furniture such as running heads.

Pages with only a picture on them are run a second time, turned a quarter, to find
captions printed sideways.

### Missing lines

OCR layers drop short lines: a bare chapter number, a one-word line of dialogue.
The layout model still sees a region there.

Where it sees a region one line tall with no text-layer line in it, `missing.py`
has glm-ocr, one of the readers, read that region. The reading is added to a copy of the page as a line
of its own, in reading order, so the later stages treat it like any other line.
This runs on scans only.

### Type

`typestyle.py` measures each line's type on the page image, relative to the body
text: its size, stroke weight, letter width, and whether it is set in capitals. No
model is involved.

Lines set alike in one place on their pages form a group, such as all the chapter
titles of a book.

### Dashes and quotes

`typography.py` measures the book's dash on the scan: an en or an em dash, and how
wide the gaps around it are. `book.toml` can set it instead.

The quote style (single or double quotes, the ellipsis glyph) comes from the text
layer's own marks.

Both are measured before any reader sees a line. The readers and judges are told
them in a sentence, because typography belongs to the book. Asked line by line,
the readers and judges set it inconsistently.

## Stage 2: what each line is

`roles.py` gives each line a role: body, heading, page number, running head, or a
print artefact to drop.

Lines in the middle of the text block, flush with the margin, are body text, and
no model is asked about them.

The doubtful lines go to clef-flash. These are lines near the top or bottom of
the page, and short centred lines anywhere. clef-flash is given each line's
position and neighbours, and facts it can't see for itself, such as whether the
same text appears on other pages, as a running head does.

Rules in code then override clef-flash where the layout decides the question. What
is true by definition, such as a chapter heading appearing once, is enforced
there. A style group takes the role most of its lines got.

The answers are cached in `stages/decisions.jsonl`.

## Stage 3: checking the OCR

This stage runs on scans only, and it costs most of a build's model time.

### More readings

Every body line is read again by three readers, short lines included:

| Reader | Sees | Good at | Weak at |
| --- | --- | --- | --- |
| glm-ocr | the line's crop | letters and words | drops quote marks and diaereses |
| tesseract | the whole page, with its own line finding | marks the layer's boxes cut off, dashes | punctuation, opening quotes |
| qwen3.8, told the book's style | the line's crop | quote marks | sometimes writes a plausible but wrong word |

A crop reaches one em past each end of the line and a few points above and below
it. It stops at the next line's box, so a reader never sees part of another line.

### Suspects

Where any reading differs from the text layer, the differing stretch, widened to
whole words, becomes a suspect. Its versions are the text layer's reading first,
then each different reading.

An invented example: the text layer reads a line as

    Hij keek naar buiten.

glm-ocr agrees, and qwen3.8 reads `buiten.’`, with a closing quote. That gives one
suspect with two versions: `buiten.` from the text layer and glm-ocr, and
`buiten.’` from qwen3.8.

Two differences in one line make two suspects, and each is decided on its own.

### Judges

Every suspect goes to three judges.

clef:27b looks at the crop of that place on the scan and picks the version it
shows. It is told the book's typesetting, and it is usually right.

winnow:e4b reads only the sentence and picks the version that reads well. On its
own it is a poor judge. It is there as an alarm: where it disagrees with clef,
clef is wrong several times as often as where they agree.

The word list, unpacked from tesseract's own language model, is the third judge.
It says which versions consist of known words. Its pick is shown to the reviewer
and used by the trust model, and it decides nothing by itself.

Each suspect also records which readings back which version.

### Learned trust

The trust model (`trust.py`) is a set of shallow gradient-boosted trees. For each
version of each suspect, it estimates how likely that version is what the page prints.

It looks at:

- what the judges picked, and how sure they were;
- which readings back the version;
- what the word list says;
- what kind of difference it is: a quote mark, a letter, a word break, a change in
  length;
- how often this exact substitution was the printed text in the training books.

That last feature exists because a scan's errors repeat. Across books, `|` read
for `I` is almost always the text layer's mistake, and glm-ocr dropping a `’` is
almost always glm-ocr's.

With every version scored, the book's suspects are sorted by how sure the trust model
is of its best version. The least sure ones are asked, up to a budget of questions
per page. The budget is counted over the whole book, so a bad page can get several
questions and a clean page none.

Every other suspect takes its best version. If that is the text layer's, the line
stays as it was; if not, it is fixed.

Fixes go into a copy of the pages. The original text layer stays as it was,
because review answers are keyed on it.

### When there is no trust model

The trust model is trained on the tuning books only, described under *Measuring*.

If the trust model's file is missing, or was saved for a different set of features, the
build stops. It doesn't fall back silently. `ROBO_OCR_TRUST=0` chooses the older
fixed rule on purpose: apply a fix when both judges agree and clef is at least
somewhat sure.

## Stage 4: the review

`roboscriptorium review work/<book>` builds the book and serves its questions on a
local web page.

### What gets asked

`flags.py` collects what a person should look at:

- the OCR doubts that trust chose to ask, one question per place;
- headings;
- lines clef-flash dropped, or kept without being sure;
- garbled text;
- pictures, captions, and titles that aren't headings;
- text the layout model sees and the text layer lacks;
- paragraphs whose curly quotes don't pair up (`quotes.py`).

The list is built before any answers are applied, so it doesn't change while you
work through it.

### Answering

`review.py` shows each question beside its crop of the scan.

An OCR doubt lists each version on its own row, with the differing part marked and
the judges that picked it beside it. One key answers.

A quote question offers qwen3.8's reading of the line, but takes only its quote
marks and the punctuation next to them, laid on the checked letters. Its quote
marks are reliable where its letters are not.

A drawn initial comes with a guess at its letter. Code finds the letters that make
the word beside it a word, and clef-flash picks the one the drawing shows.

### Checking the answers

People make mistakes too: about one answer in eight on Stella was wrong. So an
answer is checked before it is saved.

A line typed for a question must match one of its readings, apart from quote
glyphs and spacing. A straight quote in a book set with curly quotes is queried.
The page says why once, and saves when you press Save again.

Answers are stored in `work/<book>/review/regions.jsonl`.

## Stage 5: assembling the book

### Answers

`corrections.py` applies the answers on the next build, to copies of the pages and
roles. An answer can retype a line, change a role, mark a picture, or insert a
missing line where its region sits.

An answer about one place in a line changes only that place. Several answers in
one line, and the OCR check's own fixes there, all apply together.

### Paragraphs

`reflow.py` joins lines into paragraphs and headings, using indentation, short last
lines and the roles.

A hyphen at the end of a line stays or goes by evidence, strongest first:

1. how the book spells the word elsewhere, inside a line;
2. which of the two forms the word list knows;
3. a capital after the break, as in `Noord-Holland`;
4. whether the parts beside a hyphen already in the word are words themselves.

### Italics, dashes and figures

`italics.py` finds italic words from the slant of each word's strokes on the page
image, with no model.

`typography.py` sets every dash between words in the book's one style.

`figures.py` takes the layout model's pictures on body pages. It trims a picture
where a caption overlaps it, turns it upright if it was printed sideways, and
places it after the paragraph it follows, with its caption.

### The EPUB

`epub.py` writes the EPUB 3 file directly with zipfile. It has to pass epubcheck
with no errors and no warnings.

## Measuring

A change counts as an improvement only once it is measured as one.

### Golden books

The measuring is done on golden books: scans paired with a reference text a person
checked. The reference is a Project Gutenberg transcription of the same edition,
or the publisher's own EPUB of the same printing. [golden-books.md](golden-books.md)
lists them.

The build's output is aligned with the reference, and every difference is located
on the scan.

### Verdicts

The reference isn't identical to the scan either: an EPUB may correct a word or
set a dash differently. Where output and reference differ, a person can say what
the scan prints, with `golden review`. These verdicts are kept in git and patched
into the reference.

Typography an EPUB may set differently, such as quote glyphs and ellipses, is
folded to one form on both sides and counted, so the gap stays visible.

### The scores

`eval` prints a book's character and word error rates and how well its paragraphs
match.

`quality` counts what a reviewer is left with: the wrong words per page that no
question covers, at a quarter, a half and one question per page.

`bench` decides whether a change goes in. It scores fixed slices of every book in
a set, before and after the change, and compares them page by page. The change has
to improve the "after review" figure, which adds the reviewer's own expected
mistakes to the errors left unasked, with each book weighing the same. If any one
book gets clearly worse, the change is rejected.

### Three sets of books

Tuning books are the ones choices are made on, and the trust model is trained on
them.

Validation books check that a choice also works on books it wasn't made on.

The test book is scored once, at the end of the plan, and used for nothing else.
The command line refuses to score it without `--score-test`.

### Retiring a book

A pair of scan and reference can stop measuring the pipeline. When the EPUB was
made from another printing, most of the "errors" are differences between editions.

The bench records two signals for each book that need no verdicts: the text
layer's own error rate against the reference, and the share of body lines the
aligner can't place. A book past either threshold is proposed for retirement.

## How the machine learns

The trust model is what learns, in three steps.

### 1. Trust data

`experiments/ocr_trust_data.py` builds a golden book and collects its suspects.
Each version of each suspect is labelled by comparing the line with the aligned
reference: does this version make the line read as printed?

A suspect where no version comes close enough to the reference is left out of the
training data.

Stella has no reference, so its suspects are labelled from the user's own review
answers.

### 2. Training

`experiments/train_ocr_trust.py --save` trains the trees on every tuning book's
labelled suspects. It then trains them again once for each tuning book, leaving
that book out, so the bench can score each tuning book with a model that never saw
it.

Validation and test books are never trained on.

### 3. Benching

The retrained trust model is measured on the tuning books, then on the validation books.

A newly released model goes through the same loop. It is added as a reader or a
judge, the trust data is rebuilt, the trust model retrained, and the bench decides
whether it stays.

## Running it

```sh
uv run roboscriptorium doctor              # are Ollama and Ollaya answering?
uv run roboscriptorium build work/stella   # → work/stella/stella.epub
uv run roboscriptorium review work/stella  # questions on http://127.0.0.1:8765/
uv run roboscriptorium eval work/<golden scan> --pages 9-64 --chapters 1-4
uv run roboscriptorium bench tuning
```

A build with nothing cached costs about a minute per page, most of it spent on the
line readers and judges. A rebuild with warm caches takes seconds.

Long runs go through two scripts. `experiments/detached.sh` starts them in
`screen`, so they keep running after the terminal closes. `experiments/timed.sh`
records how many minutes they took in [run-times.md](run-times.md).
