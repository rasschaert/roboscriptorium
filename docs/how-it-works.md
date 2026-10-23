# How it works

This page follows a book from its PDF to its EPUB, then explains how the machine
is measured and how it learns.

Three other documents go with it. [design.md](design.md) gives the reason for each
part and the measurements behind it. [modules.md](modules.md) lists the modules.
The [diagram](pipeline.svg) draws the stages with the model behind each one.

## The idea

A book comes as a scanned PDF, and what matters is how much of the printed page the
file already holds as text. (A born-digital PDF, made from the typeset text, holds it
exactly: it converts back trivially and is not what this project is for.)

- **A scan with a text layer**: the picture is the page. Over it, invisible, lies
  one OCR program's reading of it, which is what lets you search and copy in a
  scanned PDF. That reading is good, a few wrong characters in every thousand, and
  a careful edition has none. Those few are what this project exists to fix.
- **An image-only scan**: the picture is the page and nothing has read it yet.

The text layer is one reading of the book. No single OCR program fixes its
mistakes, because every one makes mistakes of its own. So more OCR models, the
*readers*, read the book again, chosen because they make different mistakes. Where
a reader disagrees with the text layer, the place becomes a *suspect*, and each way
of reading it is a *version*.

Other models, the *judges*, look at each suspect and each pick a version. Then the
*arbiter* decides how far to believe each reader and judge. The arbiter is a
*trained* model, which means it was not written as rules: it was shown thousands
of suspects from books whose printed text is known, each with the right version
marked, and fitted so that it reproduces those answers. It gets better as that
labelled set grows, and it can be wrong in ways nobody wrote down. Where it is
unsure, it asks the *reviewer*: you, with the scan beside the question.

Your answers go into the next build. They also become labels the arbiter learns from.

Before any of that, the *spotter* marks what is on each page, and the *sorter*
decides what each line is: body text, a heading, a page number. After it, plain
code joins the lines into paragraphs and sets the typography the way the book was
printed.

Each of those italic words is a *role*, and the roles are the point. The machine
is a set of jobs, not a set of models: whoever holds a job today, a model, a
program or you, holds it because it scored best on the golden books (under
*Measuring*), and a newer model that scores better takes the job over. The
diagram writes a role in capitals before whoever holds it. A *candidate*, drawn
dashed, is a model tried for a role and not yet in use: it stays off until the
measurement says it earns the job.

What comes out is an EPUB of the book's prose: paragraphs, headings, italics,
scene breaks, pictures with their captions. Footnotes, verse and tables are not
handled yet, nor any input but PDF.

## The models and their roles

| Role | Model | What it does | Kind |
| --- | --- | --- | --- |
| spotter | DocLayout-YOLO | marks figures, captions, titles and page furniture on each page image | vision model |
| readers | glm-ocr, tesseract, qwen3.8 | read the text again from the scan | generative models and a classic OCR program |
| sorter | clef-flash:9b | decides what each doubtful line is | decision model |
| judges | clef:27b, Winnow-12B, the word list | each pick a version of a suspect | decision models and plain code |
| arbiter | the trust model (`trust.py`) | fixes, keeps, or asks about each suspect | trees trained on golden books |
| reviewer | you | answer what the arbiter is unsure of | a person |

One model can hold several jobs. qwen3.8 is a reader in the OCR check, reads the
line again where quotes don't pair up, and is tried as a proofreader of the
reviewer's answers; clef-flash sorts lines and guesses a drawn initial's letter.

Two candidates, off by default: trees trained on the golden books' lines for the
sorter's job (under *What each line is*), and qwen3.8 proofreading the reviewer's
answers (under *Checking the reviewer*).

### The readers

A reader looks at the scan and writes down the text it sees.

glm-ocr and qwen3.8 are generative models on Ollama. They read one line's crop at a
time. tesseract is a classic OCR program, and reads the whole page.

### The sorter and the judges

The sorter and the AI judges are decision models. Each answers a question whose
options are fixed in advance, such as "which of these versions does the crop
show?", with a probability for each option. They write no text, so there is no
prose to parse. clef and clef-flash run on Ollama's `/v1/systemone` endpoint; winnow
is asked the same questions through the probabilities Ollama gives the first letter of
its answer, one label per option.

The third judge, the word list, is plain code.

The split follows one rule: a job whose answer comes from a list known beforehand
goes to a decision model. Only a job that needs new text goes to a reader.

### The arbiter

A judge's confidence is a number it reports, and it can differ a lot from the
chance that the judge is right. So the arbiter takes no judge at its word. It has
learned, from labelled books, how far to believe each reader and judge for each
kind of difference.

It is a set of small decision trees, each a short chain of yes-or-no questions
about a suspect, combined so that each corrects the last (gradient boosting).
Trees suit this job: there are a few thousand labelled suspects, not millions, and
the facts about each are few and already worked out, so a large network would have
nothing to learn from.

### Local first

Every model runs on this machine. A hosted model costs money and sends page crops
to its provider, so one is used only when the user allows it for a particular run.

## A book on disk

A book is a directory, `work/<book>/`, with two files in it to start:

- `source.pdf`, the scan;
- `book.toml`, with the title, author, language, cover page, body page range and,
  optionally, the dash style (`dash`, `dash_spacing`) and the ellipsis style
  (`ellipsis`, `ellipsis_space`).

Everything the models say is cached under `work/<book>/stages/`: the text layer, the
spotter's regions, each reading of each line, every answer the sorter and the
judges gave. A rebuild reuses all of it, so only what changed costs model time.

Caches are written whole and include a format version, and append-only ones skip a
last line that was cut off. A run killed halfway resumes where it stopped.

Books, scans and everything derived from them stay in `work/`, outside git.

## 1 · Read the page

### The first reading

The first stage makes a first reading of every page: its text as visual lines, each
with its box on the page. Who makes it depends on the kind of PDF. For a
scan with a text layer, `pdf.py` reads the PDF's own
text out with PyMuPDF; in a scan that text is invisible, drawn in a font without
letter shapes, at the places where the OCR program read each word. An image-only
scan has no such text, so tesseract, one of the readers, reads each page image
first, and its words, grouped into visual lines, stand in. The rest of this page
calls the first reading the *text layer*, whoever made it.

Each line gets an identity, `SourceRef`: its page and line number. That identity
follows the line through every later stage. A fix, an answer or a score always
refers back to the line as the text layer had it.

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
does the ellipsis's form (`…` or `...`); whether its dots are spaced (`. . .`) and a space
comes before it is measured on the scan, unless `book.toml` sets it.

Both are measured before any reader sees a line, and the readers and judges are
told them in a sentence. Typography belongs to the book: asked line by line, the
readers and judges set it inconsistently.

## 2 · What each line is

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
there. Last comes the *style vote*: a group of lines set alike, in the same size,
weight and capitals, takes the role the sorter gave most of them, so one misjudged
chapter title follows its siblings.

Those rules were written one book at a time and don't carry over well: on a
book they weren't written for they found none of its twelve headings. The candidate for the
job is a set of trees trained on the golden books' lines, labelled body, heading
or other by aligning the scan with its reference text. The trees see what the
rules see (place on the page, width, indent, gaps, repetition across pages), the
line's type, the spotter's regions and the sorter's answer, and give every line a
role. `ROBO_SORTER=1` turns them on; the bench decides whether they become the
default.

## 3 · Check the OCR

This stage runs on scans only, and it costs most of a build's model time.

### The readers read

Every body line is read again by the three readers, short lines included:

| Reader | Sees | Good at | Weak at |
| --- | --- | --- | --- |
| glm-ocr | the line's crop | letters and words | drops quote marks and diaereses |
| tesseract | the whole page, finding the lines itself | words at the edge of a crop, dashes | punctuation, opening quotes |
| qwen3.8, told the book's style | the line's crop | quote marks | sometimes writes a plausible but wrong word |

A crop reaches one em past each end of the line and a few points above and below
it. It stops at the next line's box, so a reader never sees part of another line.

Two more readers are built but not yet on: glm-ocr and qwen3.8 reading the whole page,
each reading split back into the page's lines. Seeing the page, they catch what a
line's crop hides; they go on once the arbiter has learned how far to believe them.

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

winnow (Winnow-12B) reads only the sentence and picks the version that reads well.
Right on four suspects in five, it is weaker than clef alone and there mostly as an
alarm: where it disagrees with clef, clef is wrong about one time in three; where they
agree, one time in fifty.

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
get several questions and a clean page none. A suspect whose best version it gives 80%
or more is never asked, budget or not: those it nearly always gets right, and a
question isn't free: the reviewer slips too, and their time counts (the bench prices
20 questions at one wrong word).

The OCR check leaves washed-out pages alone. On their faint crops the readers invent
fluent text and the judges pick it; the reviewer types such a page instead.

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

## 4 · Review

`roboscriptorium review work/<book>` builds the book and serves the questions on a
local web page.

### What the reviewer is asked

`flags.py` collects what the reviewer should look at:

- the lines where the arbiter left a suspect for a human, one question per line;
- headings;
- lines the sorter dropped, or kept without being sure;
- garbled text;
- a page scanned too faint to read (`faint.py`: little contrast between paper and
  ink, yet a text layer full of scraps), one question for the whole page;
- pictures, captions, and titles that aren't headings;
- text the spotter sees and the text layer lacks;
- white space inside a sentence, where the text layer lost a printed line;
- paragraphs whose curly quotes don't pair up (`quotes.py`).

The list is built before any answers are applied, so it doesn't change while you
work through it.

How much there is to answer depends on the book: about half a question a page on a
clean scan of modern prose, one to three on a busy layout with pictures, and a
washed-out scan asks for whole pages to be typed.

### Answering

`review.py` shows each question beside its crop of the scan.

A suspect lists each version on its own row, with the differing part marked and
the judges that picked it beside it. One key answers.

A quote question offers qwen3.8's reading of the line, but takes only its quote
marks and the punctuation next to them, laid on the checked letters. As a reader,
qwen3.8 is reliable on quote marks and less so on letters.

A drawn initial comes with a guess at its letter. Code finds the letters that make
the word beside it a word, and the sorter picks the one the drawing shows.

### The page and its keys

Each region asks what it is: `1` running text, `2` heading, `3` drop, `4` image,
`5` caption, `6` decorated initial (its letter guessed from the word it begins). The
pipeline's call is preselected. The text as printed goes in a text box.

Where the readings differ, the question asks which one matches the scan instead, once
per line. Each row is a whole line: the text layer's, each reader's and each judge's,
the likeliest at each place, and the line as built. The differing parts are marked,
with who has them. Keys `a`, `b`, … pick a row; `e` types something else, starting from
the chosen row, or from any row with its ✎. A question with no readings of its own (a
heading, a line the layer lacks) gets qwen3.8's reading beside the layer's.

Save (`↵`, or `⌘↵` in the text box) records the answer and moves to the next unanswered
region; the arrows move through all of them. A region with a box can be turned (`r`,
↺/↻) and read again by tesseract (`o`); `-` and `+` zoom the crop.

Where the book itself is wrong, `m` (a misprint) takes the line as the edition should
read it, in the one box left to type in: what the page prints stands above it as read,
and a correction already typed into the text before `m` moves into the misprint box.
The answer stays what the page prints, which the readers are scored on, and the words
that differ go to the book's errata (`errata.py`).

On a golden book's question (our text against the publisher's e-book), `m` works the same: the
box starts from our text, and the erratum is made from our text, not from the reading the
answer chose, because the build holds ours. It is refused where our text already reads what
was typed, and where the words can't be found exactly once in the page's text layer (an OCR
correction or a line break in the way): that entry goes into `errata.toml` by hand.

A line the machine didn't ask about, such as a misprint seen while reading, joins the
questions with `review work/<book> --find "<words>"`: each line holding those words,
answered like any other, its answer kept in later builds without asking again.

For a golden book, `review work/<book> --only <list.json>` asks only the places a list of
error rows names (a bench's `errors.jsonl` rows: page, output words, reference words), and
no flagged regions. It includes places the code settles by their kind (spacing- or
hyphen-only differences), which the review otherwise leaves out and so never gets a verdict
that would mend the reference where it departs from the print.

"Rebuild book" applies the answers and rebuilds the EPUB. The questions come from the
model's decisions before any answers, so the list stays put while you work.

### Checking the reviewer

The reviewer makes mistakes too: about one answer in ten, pooled over the books
reviewed so far. So an answer is checked before it is saved.

A line typed for a question must match one of the readings, apart from quote
glyphs and spacing. A straight quote in a book set with curly quotes is queried.
The page says why once, and saves when you press Save again.
Answers saved over such a warning are logged in `review/warnings.jsonl`.

Answers are stored in `work/<book>/review/regions.jsonl`.

A candidate goes further: qwen3.8 reads the crop and compares its reading with
the answer. On Stella's answers it caught all nine wrong ones with three false
alarms in fifty-eight. It is not wired in yet.

## 5 · Assemble the book

### The reviewer's answers

On the next build, `corrections.py` applies the reviewer's answers to copies of the
pages and roles. An answer can retype a line, change a role the sorter gave, mark a
picture, or insert a line where the spotter saw one.

An answer about one place in a line changes only that place. Several answers in
one line, and the arbiter's own fixes there, all apply together.

### Footnotes

Plain code (`footnotes.py`) takes a page's footnotes out of the running text. A note
is a block of lines at the foot of the page, below the text, in type smaller and
lighter than the body's, opening on its mark (`*`, `†`, a number). Its lines are read
and checked like any other line; then the note is set apart from the paragraphs and
linked to the paragraph that carries its mark, both ways in the EPUB. A note whose
mark wasn't read in the text follows the last paragraph of its page, unlinked.

A page holding only a few short lines set well in from the margin, of real words and
not all capitals, is a motto (`epigraphs.py`): "‘It’s closing time’ (Leonard Cohen,
The Future)". Its lines are set apart as one epigraph block before the text.

### Paragraphs

Plain code (`reflow.py`) joins lines into paragraphs and headings, using
indentation, short last lines, white space and the sorter's roles.

A line starts a paragraph when it stands right of the margin. The margin is read
from the lines around it, and from the page's full lines where every line around it
is indented, as in a run of one-line dialogue. A line's height of white space after a
sentence starts a paragraph too, and two lines' worth, or a line of ornaments such as
`* * *`, is a scene break.

A hyphen at the end of a line stays or goes by evidence, strongest first:

1. how the book spells the word elsewhere, inside a line;
2. which of the two forms the word list knows;
3. a capital after the break, as in `Noord-Holland`;
4. whether the parts beside a hyphen already in the word are words themselves;
5. in an English book, the judge (clef:27b), asked how the word is spelled in its
   sentence (`hyphens.py`): English compounds keep their hyphen about as often as not.

### Italics, quotes, dashes, ellipses and figures

Plain code finds italic words from the slant of each word's strokes on the page
image (`italics.py`), and sets every dash between words and every ellipsis in the
book's one style (`typography.py`): the dash measured on the scan, the ellipsis's gaps
measured there too (`word . . .` or `word...`) and its glyph read in the text layer,
either one settled in `book.toml` when it sets it. A straight quote or apostrophe left
from the text layer is curled by its place (`quotes.curl`): a printed book sets curly
ones.

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
the scan prints, in the book's review: those places are more questions in the
same list as its flagged regions. These verdicts are kept beside the reference (in
git for a public-domain book, under `work/` for one in copyright) and patched into
it.

Typography an EPUB may set differently, such as quote glyphs and ellipses, is
folded to one form on both sides and counted, so the gap stays visible. Where the
words agree once folded, the bench counts apart the words whose quote marks, dashes
or ellipsis differ from the reference's, for the kinds the reference sets in its
own glyphs.

### The scores

`eval` prints a book's character and word error rates and how well its paragraphs
match.

`quality` counts what the reviewer is left with: the wrong words per page that no
question covers, at a quarter, a half and one question per page.

`bench` decides whether a change goes in. It scores fixed slices of every book in
a set, before and after the change, and compares them page by page. The change has
to improve the "after review" figure, which adds the reviewer's own expected
mistakes to the errors the arbiter left unasked, with each book weighing the same,
or the number of paragraph breaks set wrong, without the other getting clearly worse.
If any one book gets clearly worse, the change is rejected.

A question counts as catching an error only at its own place in a line, and a page
the reviewer types whole counts as a question for each of its lines.

### Sets of books

Tuning books are the ones choices are made on, and the arbiter learns from them.

Validation books check that a choice also works on books it wasn't made on. They can
only stop a change, never pick one: a choice made on them would make them tuning books.

A new pair is scored once before anything is chosen or trained on it: its first look,
the fairest measure of how the build does on a book it has never seen. Then it joins
tuning or validation. The command line refuses to score a pair awaiting its first look
without `--first-look`.

A quick tier holds a chapter or two of each tuning book, about a quarter of their
pages: a change is tried there first, and the full tuning set confirms it.

### Retiring a book

A pair of scan and reference can stop measuring the pipeline. When the EPUB was made
from another printing, most of the "errors" are differences between editions.

The bench records two signals for each book that need no verdicts: the text
layer's own error rate against the reference, and the share of body lines that
can't be aligned. A book past either threshold is proposed for retirement.

## How the arbiter learns

Two models are trained here rather than taken as they come: the arbiter, and the
candidate sorter, which is trained the same way on labelled lines
(`experiments/train_sorter.py`). The arbiter learns in three steps.

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

The arbiter never learns from validation books, or from a pair awaiting its first look.

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
uv run roboscriptorium build scan.pdf      # no book.toml yet: `init` drafts one first
uv run roboscriptorium review work/stella  # questions on http://127.0.0.1:8765/
uv run roboscriptorium eval work/<golden scan> --pages 9-64 --chapters 1-4
uv run roboscriptorium bench tuning
```

A build with nothing cached costs about a minute per page, most of it spent on the
readers and judges. A rebuild with warm caches takes seconds.

Long runs go through two scripts. `experiments/detached.sh` starts them in
`screen`, so they keep running after the terminal closes. `experiments/timed.sh`
records how many minutes they took in [run-times.md](run-times.md).
