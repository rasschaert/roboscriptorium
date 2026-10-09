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

The text layer is one reading of the book. No single OCR program fixes its
mistakes, because every one makes mistakes of its own. So more OCR models, the
*readers*, read the book again, chosen because they make different mistakes. Where a reader disagrees with
the text layer, the place becomes a *suspect*, and each way of reading it is a
*version*.

Other models, the *judges*, look at each suspect and each pick a version. Then the
*arbiter*, a model trained on books whose printed text is known, decides how far to
believe each reader and judge. Where the arbiter is unsure, it asks the *reviewer*: you, with
the scan beside the question.

Your answers go into the next build. They also become labels the arbiter learns from.

Before any of that, the *spotter* marks what is on each page, and the *sorter*
decides what each line is: body text, a heading, a page number. After it, plain
code joins the lines into paragraphs and sets the typography the way the book was
printed.

## The models and their roles

| Role | Model | What it does | Kind |
| --- | --- | --- | --- |
| spotter | DocLayout-YOLO | marks figures, captions, titles and page furniture on each page image | vision model |
| readers | glm-ocr, tesseract, qwen3.8 | read the text again from the scan | generative models and a classic OCR program |
| sorter | clef-flash:9b | decides what each doubtful line is | decision model |
| judges | clef:27b, winnow-ollama:e4b, the word list | each pick a version of a suspect | decision models and plain code |
| arbiter | the trust model (`trust.py`) | fixes, keeps, or asks about each suspect | trees trained on golden books |
| reviewer | you | answer what the arbiter is unsure of | a person |

### The readers

A reader looks at the scan and writes down the text it sees.

glm-ocr and qwen3.8 are generative models on Ollama. They read one line's crop at a
time. tesseract is a classic OCR program, and reads the whole page.

### The sorter and the judges

The sorter and the AI judges are decision models. Each answers a question whose
options are fixed in advance, such as "which of these versions does the crop
show?", with a probability for each option. They write no text, so there is no
prose to parse. clef, clef-flash and winnow run on Ollama's `/v1/systemone` endpoint.

The third judge, the word list, is plain code.

The split follows one rule: a job whose answer comes from a list known beforehand
goes to a decision model. Only a job that needs new text goes to a reader.

### The arbiter

A judge's confidence is a number it reports, and it can differ a lot from the
chance that the judge is right. So the arbiter takes no judge at its word. It has
learned, from labelled books, how far to believe each reader and judge for each
kind of difference.

### Local first

Every model runs on this machine. A reader or judge runs hosted only when the
user allows it for a particular run. It is then pinned to one provider, and what
it says is cached under the local model's name, with a note saying where it came
from.

## A book on disk

A book is a directory, `work/<book>/`, with two files in it to start:

- `source.pdf`, the scan or the born-digital PDF;
- `book.toml`, with the title, author, language, cover page, body page range and,
  optionally, the dash style (`dash`, `dash_spacing`) and the ellipsis style
  (`ellipsis`, `ellipsis_space`).

Everything the models say is cached under `work/<book>/stages/`: the text layer, the
spotter's regions, each reading of each line, every answer the sorter and the
judges gave. A rebuild reuses all of it, so only what changed costs model time.

Caches are written whole and include a format version, and append-only ones skip a
last line that was cut off. A run killed halfway resumes where it stopped.

Books, scans and everything derived from them stay in `work/`, outside git.

## Stage 1: the page

### The text layer

`pdf.py` takes the PDF's own text as visual lines. Each line has its box on the
page and an identity, `SourceRef`: its page and line number.

That identity follows the line through every later stage. A fix, an answer or a
score always refers back to the line as the text layer had it.

An image-only PDF has no text layer. tesseract, one of the readers, then reads each
page first, and its words, grouped into visual lines, stand in for the text layer.

### The spotter

The spotter (`layout.py`) looks at each page image and marks figures, captions,
titles, and page furniture such as running heads.

Pages with only a picture on them it looks at a second time, turned a quarter, to
find captions printed sideways.

### Lines the text layer missed

OCR layers drop short lines: a bare chapter number, a one-word line of dialogue.
The spotter still sees something printed there.

Where the spotter marks a region one line tall with no text-layer line in it, a
reader, glm-ocr, reads that region (`missing.py`). Its reading is added to a copy
of the page as a line of its own, in reading order, so the other models treat
it like any other line. This happens on scans only.

### Type, dashes and quotes

Plain code measures each line's type on the page image, relative to the body text:
its size, stroke weight, letter width, and whether it is set in capitals
(`typestyle.py`). Lines set alike in one place on their pages form a group, such as
all the chapter titles of a book.

Plain code also measures the book's dash on the scan: an en or an em dash, and how
wide the gaps around it are (`typography.py`). `book.toml` can set it instead. The
quote style (single or double quotes) comes from the text layer's own marks, and so
does the ellipsis style (`…`, `...` or `. . .`) unless `book.toml` sets it.

Both are measured before any reader sees a line, and the readers and judges are
told them in a sentence. Typography belongs to the book: asked line by line, the
readers and judges set it inconsistently.

## Stage 2: the sorter

The sorter (`roles.py`) gives each line a role: body, heading, page number, running
head, or a print artefact to drop.

Lines in the middle of the text block, flush with the margin, are body text, and
the sorter isn't asked about them.

The doubtful lines go to the sorter: lines near the top or bottom of the page, and
short centred lines anywhere. It is given each line's position and neighbours, and
facts it can't see for itself, such as whether the same text appears on other
pages, as a running head does.

Rules in code then overrule the sorter where the layout decides the question. What
is true by definition, such as a chapter heading appearing once, is enforced
there. A group of lines set alike takes the role the sorter gave most of them.

## Stage 3: the OCR check

This stage runs on scans only, and it costs most of a build's model time.

### The readers read

Every body line is read again by the three readers, short lines included:

| Reader | Sees | Good at | Weak at |
| --- | --- | --- | --- |
| glm-ocr | the line's crop | letters and words | drops quote marks and diaereses |
| tesseract | the whole page, with its own line finding | marks the layer's boxes cut off, dashes | punctuation, opening quotes |
| qwen3.8, told the book's style | the line's crop | quote marks | sometimes writes a plausible but wrong word |

A crop reaches one em past each end of the line and a few points above and below
it. It stops at the next line's box, so a reader never sees part of another line.

### Suspects

Where a reader disagrees with the text layer, the differing stretch, widened to
whole words, becomes a suspect. Its versions are the text layer's reading first,
then each reader's different one.

An invented example: the text layer reads a line as

    Hij keek naar buiten.

glm-ocr agrees, and qwen3.8 reads `buiten.’`, with a closing quote. That gives one
suspect with two versions: `buiten.` from the text layer and glm-ocr, and
`buiten.’` from qwen3.8.

Two differences in one line make two suspects, and each is decided on its own.

### The judges pick

Every suspect goes to the three judges.

clef:27b looks at the crop of that place on the scan and picks the version it
shows. It is told the book's typesetting, and it is usually right.

winnow (winnow-ollama:e4b) reads only the sentence and picks the version that reads well. On its
own it is a poor judge. It is there as an alarm: where it disagrees with clef,
clef is wrong several times as often as where they agree.

The word list, unpacked from tesseract's own language model, picks the versions
made of words it knows. It decides nothing by itself; the arbiter weighs it, and
the reviewer sees it.

### The arbiter decides

The arbiter is a set of shallow gradient-boosted trees. For each version of each
suspect, it estimates how likely that version is what the page prints.

It weighs:

- what each judge picked, and how sure it was;
- which readers read the version;
- what kind of difference it is: a quote mark, a letter, a word break, a change in
  length;
- how often this exact substitution was the printed text in the books it learned
  from.

That last one is there because a scan's errors repeat. Across books, `|` for `I` is
almost always the text layer's mistake, and a `’` that glm-ocr drops is almost
always glm-ocr's.

With every version scored, the arbiter sorts the book's suspects by how sure it is
of its best version. It asks the reviewer about the least sure ones, up to a budget
of questions per page. The budget is counted over the whole book, so a bad page can
get several questions and a clean page none.

Every other suspect gets its best version. If that is the text layer's, the line
stays as it was; if not, it is fixed.

Fixes go into a copy of the pages. The original text layer stays as it was,
because the reviewer's answers are keyed on it.

### Without an arbiter

The arbiter learns from the tuning books only, described under *Measuring*.

If its file is missing, or was saved for a different set of features, the build
stops rather than continue without it. `ROBO_OCR_TRUST=0` replaces it on purpose
with a fixed rule. It applies a version when clef and winnow both pick it and clef is
at least somewhat sure (0.3), or when clef alone picks it at 0.5 or more where the
versions differ only in punctuation, dashes or spacing, which winnow can't tell
apart from the sentence. Everything else goes to the reviewer.

## Stage 4: the reviewer

`roboscriptorium review work/<book>` builds the book and serves the questions on a
local web page.

### What the reviewer is asked

`flags.py` collects what the reviewer should look at:

- the suspects the arbiter chose to ask about, one question per place;
- headings;
- lines the sorter dropped, or kept without being sure;
- garbled text;
- a page scanned too faint to read (`faint.py`: little contrast between paper and
  ink, yet a text layer full of scraps), one question for the whole page;
- pictures, captions, and titles that aren't headings;
- text the spotter sees and the text layer lacks;
- paragraphs whose curly quotes don't pair up (`quotes.py`).

The list is built before any answers are applied, so it doesn't change while you
work through it.

### Answering

`review.py` shows each question beside its crop of the scan.

A suspect lists each version on its own row, with the differing part marked and
the judges that picked it beside it. One key answers.

A quote question offers qwen3.8's reading of the line, but takes only its quote
marks and the punctuation next to them, laid on the checked letters. As a reader,
qwen3.8 is reliable on quote marks and less so on letters.

A drawn initial comes with a guess at its letter. Code finds the letters that make
the word beside it a word, and the sorter picks the one the drawing shows.

### Checking the reviewer

The reviewer makes mistakes too: about one answer in eight on Stella was wrong. So
an answer is checked before it is saved.

A line typed for a question must match one of the readings, apart from quote
glyphs and spacing. A straight quote in a book set with curly quotes is queried.
The page says why once, and saves when you press Save again.

Answers are stored in `work/<book>/review/regions.jsonl`.

## Stage 5: the book

### The reviewer's answers

On the next build, `corrections.py` applies the reviewer's answers to copies of the
pages and roles. An answer can retype a line, change a role the sorter gave, mark a
picture, or insert a line where the spotter saw one.

An answer about one place in a line changes only that place. Several answers in
one line, and the arbiter's own fixes there, all apply together.

### Paragraphs

Plain code (`reflow.py`) joins lines into paragraphs and headings, using
indentation, short last lines and the sorter's roles.

A hyphen at the end of a line stays or goes by evidence, strongest first:

1. how the book spells the word elsewhere, inside a line;
2. which of the two forms the word list knows;
3. a capital after the break, as in `Noord-Holland`;
4. whether the parts beside a hyphen already in the word are words themselves.

### Italics, dashes, ellipses and figures

Plain code finds italic words from the slant of each word's strokes on the page
image (`italics.py`), and sets every dash between words and every ellipsis in the
book's one style (`typography.py`): the dash measured on the scan, the ellipsis read
in the text layer (`word . . .` or `word...`), either one settled in `book.toml`
when it sets it.

`figures.py` takes the pictures the spotter marked on body pages. It trims a
picture where a caption overlaps it, turns it upright if it was printed sideways,
and places it after the paragraph it follows, with its caption.

### The EPUB

`epub.py` writes the EPUB 3 file directly with zipfile. It has to pass epubcheck
with no errors and no warnings.

## Measuring

A change counts as an improvement only once it is measured as one. The models are
measured on golden books.

### Golden books

A golden book is a scan paired with a reference text a person checked: a Project
Gutenberg transcription of the same edition, or the publisher's own EPUB of the
same printing. [golden-books.md](golden-books.md) lists them.

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

`quality` counts what the reviewer is left with: the wrong words per page that no
question covers, at a quarter, a half and one question per page.

`bench` decides whether a change goes in. It scores fixed slices of every book in
a set, before and after the change, and compares them page by page. The change has
to improve the "after review" figure, which adds the reviewer's own expected
mistakes to the errors the arbiter left unasked, with each book weighing the same.
If any one book gets clearly worse, the change is rejected.

### Three sets of books

Tuning books are the ones choices are made on, and the arbiter learns from them.

Validation books check that a choice also works on books it wasn't made on.

The test book is scored once, at the end of the plan, and used for nothing else.
The command line refuses to score it without `--score-test`.

### Retiring a book

A pair of scan and reference can stop measuring the pipeline. When the EPUB was made
from another printing, most of the "errors" are differences between editions.

The bench records two signals for each book that need no verdicts: the text
layer's own error rate against the reference, and the share of body lines that
can't be aligned. A book past either threshold is proposed for retirement.

## How the arbiter learns

The arbiter is the model that learns, in three steps.

### 1. Trust data

`experiments/ocr_trust_data.py` builds a golden book and collects its suspects,
with what each reader read and each judge picked. Each version is labelled by
comparing the line with the aligned reference: does this version make the line read
as printed?

A suspect where no version comes close enough to the reference is left out.

Stella has no reference, so its suspects are labelled from the reviewer's answers.

### 2. Training

`experiments/train_ocr_trust.py --save` trains the arbiter on every tuning book's
labelled suspects. It then trains it again once for each tuning book, leaving that
book out, so the bench can score each tuning book with an arbiter that never saw
it.

The arbiter never learns from validation or test books.

### 3. Benching

The retrained arbiter is measured on the tuning books, then on the validation
books.

A new model is tried through the same loop. It is added as a reader or a
judge, the trust data is rebuilt, the arbiter retrained, and the bench decides whether
it stays.

## Running it

```sh
uv run roboscriptorium doctor              # is Ollama up, do its decision models answer?
uv run roboscriptorium build work/stella   # → work/stella/stella.epub
uv run roboscriptorium review work/stella  # questions on http://127.0.0.1:8765/
uv run roboscriptorium eval work/<golden scan> --pages 9-64 --chapters 1-4
uv run roboscriptorium bench tuning
```

A build with nothing cached costs about a minute per page, most of it spent on the
readers and judges. A rebuild with warm caches takes seconds.

Long runs go through two scripts. `experiments/detached.sh` starts them in
`screen`, so they keep running after the terminal closes. `experiments/timed.sh`
records how many minutes they took in [run-times.md](run-times.md).
