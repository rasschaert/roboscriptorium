# Why it is built this way

Each component, what job it does, and the evidence that it earns that job. When
the evidence changes, this file changes with it (AGENTS.md's standing rules). The
dated history behind each line is in [decisions.md](decisions.md).

Numbers marked *trust data* come from the OCR check's labelled suspects
(`experiments/ocr_trust_data.py`, each version labelled from the aligned golden
text, settled ones only): 5,412 over 14 books on 2026-10-09, the three validation books
among them (counted here, never trained on).

## The text layer is one reading, not the truth

A scan's OCR layer is good (Goede dochter: 0.20% CER on body lines) but drops
quote marks, misreads accents and splits contractions. Every other reading exists
to catch what it gets wrong; none replaces it, because each has errors of its own
(bench: `experiments/bench_line_readings.py`, Goede dochter pp. 9–64).

**An image-only scan's first reading is tesseract's.** It gives words with boxes, which
the rest of the pipeline needs as lines, and it is the reader that segments a page on
its own. Against the scan's own OCR layer, on Goede dochter pp. 9–64 with the layer
removed and the images untouched (`experiments/probe_first_reader.py`): CER 0.35%
against 0.20%, bare-word 0.57% against 0.44%, unplaced lines 2.4% against 2.7%. Its
extra errors are mostly quote marks (a `’` dropped 83 times), which qwen3.8 reads best;
whether the OCR check closes the gap is not measured yet.

## OCR check

**Several readings that fail differently.** A reading only helps where it is
right and the layer is wrong, so readings are chosen for different errors, not
for the best score alone:

| Reading | Why it is there | Its own failure |
| --- | --- | --- |
| glm-ocr, line crop | letters and words (right where the layer is wrong on 114 of Goede dochter's lines) | drops quotes, diaereses; a word now and then |
| tesseract, whole page | its own line segmentation, so it sees marks the layer's boxes cut off; dashes | punctuation, opening quotes |
| qwen3.8, line crop, told the book's style | quote marks (keeps them where glm-ocr loses 31, tesseract 80) | plausible real words (`doodgaan→doorgaan`); its cost: 70–75% of a cold run |

qwen3.8 earns its cost in a build: without it (trust data rebuilt and the arbiter
retrained without its reading), `bench tuning` goes from 1.00 to 1.33 wrong words a
page after review [+0.07, +0.75] and `bench validation` from 0.81 to 1.01 [+0.12,
+0.27]; 11/22/63, Artemis, Vals alarm and De tuin lose most (2026-10-09). Without it 867
of 6,145 suspects are never raised, and the ones that are leave more unasked errors.

No faster reader matches qwen3.8 yet: gemma4 8B reads a line in a quarter of the
time but gets quote marks wrong where Qwen doesn't (Goede dochter pp. 9–20: 4 lines
against 0, CER 0.21% against 0.10%), and the newest open models that might
(DeepSeek V4.1, GLM-5.3, MiMo 2.6, Step 3.7) are 200–760B, too big for this machine.

Its prompt is the book's style and an instruction to transcribe exactly, nothing more.
Five richer prompts on the reader set (hosted, 330 hard lines) each fixed about as many
lines as they broke: "never correct or modernise" 2 against 5, the lines above and
below 5 against 5, both 4 against 3, the layer's own reading 10 against 13 (it copies
the layer's errors). Its misreads are visual, so prompt work there buys nothing
(`experiments/probe_read_prompt.py`, 2026-10-09).

Each crop reaches one em past the line's ends and 3 pt above and below it, but never
into a neighbouring line's box (`crop_span`): where boxes are as tall as the line pitch
(Metro, Dolittle, Crime, most of De tuin) the margin used to take in half the next line,
and glm-ocr read it (Metro pp. 7–30: CER 1.87% on those lines, 0.29% cut short).

glm-ocr and qwen3.8 read crops cut from the layer's boxes, so they share its
segmentation errors; only tesseract doesn't.

**Every body line is read, short ones too.** A dialogue line ending "keek.’" is
where a closing quote is lost. On Goede dochter pp. 9–64, reading the lines under 12
characters added 18 suspects. About three of them are real layer errors (`weg?` for
`weg?’`, `zin.` for `zijn.’`, `moet—` for `moet –’`). Eight came from glm-ocr
alone, and the layer was right on all eight: on a tiny crop it returns `?`, `‘` or a
markdown fence. clef was right on all 14 settled ones, and trust sees which readings
back a version, so these are left to trust and the bench, with no rule of their own.

**Two judges where the readings differ.**

- *clef:27b looks at the crop.* It is the judge that is usually right: 4,846 of
  5,412 alone (90%, trust data of 14 books, 2026-10-09). Told the book's typesetting
  and given options in ⟨ ⟩ rather than “ ”, it picks right more often on typography
  (Goede dochter 92 → 98 of 102).
- *winnow (`winnow-ollama:e4b`) reads the sentence, not the image.* It is a poor judge
  alone (3,610 of 5,412, 67%) and is kept as **an alarm on clef**: where winnow agrees
  with clef, clef is wrong on 141 of 3,363 (4%); where it disagrees, on 425 of 2,049
  (21%). The alarm works on 12 of 14 books, Goede dochter included (2/265 against
  23/112); it is weak on 11/22/63 (12% against 17%) and reversed on Stella's 65
  suspects (8/40 against 2/25). Its Ollaya build, the one before it, got 63% alone
  with a 4% / 22% alarm and none on Goede dochter. Lady into Fox, whose labels
  differ from its print in typography, favoured winnow over clef there, which measured
  the reference more than the judges; it is in no set now. Told the book's style, the
  Ollaya build got worse on Goede dochter (91 → 84 of 200), so it isn't.
- *imajev-4b, a second vision judge, is not used* (`ROBO_ALARM_MODEL`, off). Asked clef's
  question on the crop, it is right alone on 85% and a sharper alarm than winnow where it
  speaks (clef wrong on 37% of their disagreements against 5% of their agreements) but
  it speaks less (904 disagreements against winnow's 2,049), and as the arbiter's third
  judge the bench saw no change: tuning 1.02 → 1.01 after review [−0.04, −0.00],
  validation 0.81 → 0.80 [−0.05, +0.02] (2026-10-09). Not worth a second model server and
  a quarter second a suspect. Its votes stay in the trust data; training uses only the
  judges the settings name.
- *The word list is a vote, not a judge.* Where it knows only one version's words
  it is nearly always right, but acting on it added unasked errors on two
  validation books (lost compounds, stress accents). It is shown to the reviewer
  and is a trust feature.

**Learned trust decides, not a fixed rule.** The judges' confidences aren't
probabilities of being right, and how much each signal is worth differs by kind of
error and book (the winnow numbers above). Shallow trees over the judges' picks
and confidence, the readings' support, the word list and the kind of difference
learn that from labels: leaving one book out, silent errors at the rule's own
number of questions fell 57 → 15 over seven books.

**The exact substitution is a prior.** A scan's errors are a few signatures: the
top five (layer → print) cover 135 of Vals alarm's 202 layer-wrong suspects, 294 of
Dolittle's 372, 110 of Artemis's 207, and across books they go one way: a lost `’` is
the print 223 of 234 times it is raised, `|`→`I` 59 of 59, `é`→`ë` 28 of 28, while
glm-ocr dropping a `’` is wrong 232 of 235 times. The kind features ("same letters",
"length differs") can't tell `é`→`ë` from `ë`→`e`, so each version carries how often
its exact substitution was the print in the training books (`trust.pair`, Laplace
smoothed, with how often it was seen). Leaving one book out over nine books
(`experiments/probe_trust_pair_prior.py`), silent errors at 0 / 0.25 / 0.5 / 1
questions a page fell from 153 / 87 / 44 / 23 to 110 / 48 / 25 / 10, stable to one
more training book left out. Two guards, each measured: a pair counts only when seen
in two training books (one book's reference conventions must not teach the rest;
Lady into Fox showed they can), and a training book's suspects get their priors from
the other training books only, as a scored book's do. With its own book counted in
the prior repeats the label and the trees lean on it: 76 / 48 / 28 at 0.25 / 0.5 / 1,
worse than none; with only the suspect's own label left out a signature common in
its book still looks surer than it will on a new one, 117 / 50 / 31 / 11. What the prior can't know is a signature in no other book: Vals
alarm loses the full stop before a closing quote 47 times (`word’` for `word.’`), and
only that book's own answers can teach it (checklist 6b). The bench decides whether
the gain carries into a build. The fixed rule (both judges
agree, clef ≥ 0.3) asks about 35% of suspects because it needs winnow's
agreement; it is only an explicit fallback (`ROBO_OCR_TRUST=0`). A missing or
mismatched model stops the build, because a silent fallback once ran unnoticed.

**The question budget is book-wide.** Questions go where the model is least sure,
which may be several on one bad page; a per-page cap would spend questions on
clean pages.

**A suspect the arbiter is sure of isn't asked, budget or not** (`ocr_ask_below`,
0.8). Most books filled their budget with suspects the arbiter gave 0.9 or more
(Crime 68 of its 94 questions, De cipier 44 of 84), and nearly all of those it had
right. At 0.8, `bench tuning` 0.50 → 0.48 wrong words a page after review, validation
0.75 → 0.79 (no change by the test), with questions about halved: Goede dochter 1.24 →
0.75 a page (and 0.25 → 0.19 after review), Metro 1.31 → 0.62, De cipier 1.18 → 0.44,
Crime 1.21 → 0.30, De eerlijke vinder 1.88 → 1.15. The loss is You're Never Weird
0.84 → 1.03: text inside a picture (p. 47) the readers read and the arbiter now
applies; picture text is that book's known gap. 0.9 asks more for no gain (tuning 0.49,
validation 0.80). The bench's test counts wrong words, not the reviewer's time, so the
user chose it (2026-10-09). **Revisit** it with a new arbiter, judge or reader: its
probabilities move, and so does the right line.

**Doubts are asked per place, not per line.** Two wrong places in one line, each
fixed by a different reading, left no right option, and the reviewer then typed
the line and added an error.

**A washed-out page is one question, from the scan's contrast** (`faint.py`). Some
scans have pages too faint to read (Afscheid 9, 11/22/63 13, Grand Hotel Europa 9), yet
their text layer is full: short scraps that pass for words, 89% of them in the word list
on Afscheid p. 20, so neither the garbled-line rule nor a word-list share finds them
(11/22/63's normal pages go as low as 68%). The image does: between the paper and the
ink inside the layer's line boxes, every washed-out page measures under 10 grey levels
and every printed one of 18 books 48 or more (2026-10-09); the line is drawn at 30. Such
a page becomes one region of all its lines instead of one OCR doubt per scrap: `bench
tuning` better, after review 1.02 → 1.00 [−0.04, −0.01] (Afscheid 5.07 → 4.94, its
questions 1.58 → 0.55 a page), validation unchanged. No model reads these pages; a
human types them or rescans.

The OCR check leaves such a page out (no readings, suspects or fixes). On Afscheid
p. 20 Qwen read near-blank crops as fluent dialogue ("‘Ik heb het niet gedaan,’ zei
hij." five times), clef picked it, the word list knew every word, and the arbiter
applied it: about 170 invented lines over four pages. Its scraps were also the least
sure suspects, so they took 55 of Afscheid's 62 questions out of sight; the budget
now counts only pages the check reads. The text isn't in the PDF to recover: Internet
Archive's mask layer holds traced blobs, not letters, and its background only smears.

**Where the body starts and ends stays in book.toml.** Asked the page-type question
on the four pages outside each end of the body and three inside (252 pages of 18
books), imajev-4b put 227 on the right side and clef-flash 231 (2026-10-09), and both
missed the same kind of page: a preface or foreword inside the range, a blank or title
page at its first page, an afterword just past it. Those are as much the range's
convention as the models' errors, and one wrong end cuts or pads a book, so a model
would need a human to confirm both ends anyway.

## Book-wide style

Dash kind and spacing, the ellipsis, and the quote style, are a property of the book,
not of a line: asked line by line they came out mixed. Dashes are measured on the scan;
quote style comes from the layer's own marks. All of it is measured on the whole body,
even when a slice is built: a slice is short of evidence (Dolittle's 23–88 has too few
dashes to measure, Vals alarm's 11–60 none, Goede dochter's 9–64 twelve, which read
thin where sixty read word-spaced), and a style that differs from the whole book's
gives the read model another prompt, so the slice and the book were read twice.

The ellipsis is read in the layer: the glyph, three dots or spaced dots, and whether a
space comes before it. The five English trade books print `word . . .` with a space
before; the Dutch ones `word...` or `word…`. Layers merge spaced dots and drop that
space on a third to half of their reads, but hardly ever invent gaps (Dutch books: at
most 1% of runs read spaced), so a book is spaced when a quarter of its runs read so,
and the space before is voted on by the runs that kept their gaps. This reads every
golden book's space as its reference has it, Crime aside, whose transcription drops
the space its print sets (fixed in derive, `ellipsis_space`). Without it, reflow's
tidying squashed every spaced ellipsis, and the bench counted each as a wrong word:
Metro 4.63 → 0.43 wrong words a page after review, the set 1.53 → 1.00. Models that read or judge
typography are told the style; this halved Qwen's wrong quote proposals on Reis.

## Quote questions

A paragraph whose quotes don't pair up is flagged where the mark is missing, and
the question offers Qwen's reading of the line, keeping only its quote marks and
the punctuation beside them on the OCR-checked letters: its letters slip too often
to take (`krimpachtig`, a Cyrillic word), its quote marks rarely do (Reis right on
51 lines where the line is wrong, wrong on none where it is right).

## Line roles

clef-flash:9b answers the doubtful lines, and rules in `roles.py` override it
where layout settles the question. The rules don't carry over to unseen books
(Villa Toscane headings 0/12); a tree classifier over layout, type and clef's
answer makes 111 role errors to the rules' 256 over twelve books, but is unstable
on the English books with three to train on. It replaces the rules once more
English data makes it stable and the bench says so.

A chapter number the text layer misreads ("l" for 1, "e," for 2, "UH" for 11 on
Afscheid) matches no numeral rule, and clef-flash calls it a page number or an
artifact, so it was dropped before any reader saw it. Its box gives it away: at the
top, centred, as tall as the numerals the book's other chapters open with (21–22 pt on
every Afscheid chapter page). `numeral-slot` keeps such a line as a heading, and the
OCR check then reads its crop: glm-ocr, tesseract and Qwen read all three right, and
the arbiter fixed all three. Headings 8/11 → 11/11, no other book changed (bench,
2026-10-09). A washed-out line at the top (Afscheid p. 32) is as tall but wide and off
centre, so it isn't taken.

## Reflow: line-end hyphens

**Nothing else looks at a line-end hyphen.** The OCR check starts where readings
differ, and every reading agrees a line ends in "-"; whether the word keeps it is
decided in reflow alone, four to six times a page in Dutch. Measured against the
reference on six golden slices (`experiments/probe_hyphen_breaks.py`, 1,574 decidable
breaks, no models), the old rules were wrong 29 times, 0.02–0.17 words a page per
book: more than the OCR check's silent errors at one question a page.

**Evidence in order of its measured reliability**, strongest first, each used only
where the stronger ones are silent:

| Evidence | Why it is there | Its own failure |
| --- | --- | --- |
| the book's own spelling inside lines (`spellings`) | 12 of 12 right where it spoke | silent on a word printed once |
| the word list knows exactly one of the two forms | fixes 7 wrong calls, breaks none where the book is silent | knows a closed form the print hyphenates (`faceplate`, `northernmost`: 3); knows both (`make-up`, `makeup`) |
| a capital after the break (`Noord-Holland`) | right on every true capital | a word set in capitals (`WE-` + `RELDGESCHIEDENIS`), 0 of 3: so it no longer counts as one |
| a hyphen already in the word | `Mens-erger-je-niet`, `good-for-nothing` | kept as a rule it was wrong 8 of 10 (`Zuid-Lon-den`, `Majuba-theeplan-tage`): now only where the parts beside the break are both words and don't make one |

After the change 15 of the 1,574 are wrong (Vals alarm 0, De cipier 1, Goede dochter 2,
De tuin 2, Artemis 2, Metro 8). What is left is English compounds the list lacks or
knows closed (`night-vision`, `semi-erased`, `slate-black`), `make-up` with both forms
known, and one Dutch compound (`heen-en-weerbewegingen`, closed in print though both
parts are words). Those are the question's: a break where the list is silent and both
parts are words fired 13 right against 3 wrong on the English slices and 0 against 44
on the Dutch, so it can trigger a question on an English book and never decide.

## The reviewer's answers are checked

**A question isn't free: the reviewer slips.** 8 of 68 checked answers on Stella were
wrong (`quality.slip_rates`), and at one question a page that is about 0.12 wrong
words a page, more than trust leaves silent at that budget and more than the hyphen
breaks. Transcribing the crop and comparing in code caught 9 of 9 slips there with
3 false alarms in 58; the readings every question already carries are the same
comparison without a model call. So before an answer is saved (`review.doubtful`): a
line typed for a question with readings must match one of them, letter for letter
but for quote glyphs and spacing, and an answer with a straight quote where the
book's line or readings set curly ones is a slip no model is needed for. The page
says why once and saves on the second Save; the warned answer is logged beside the
answers (`review/warnings.jsonl`), so the slip-rate review measures slips before and
after the check. Its failure: a line the reviewer rightly retypes at two places
matches no reading and is queried once; and a region with no readings (a heading
typed in, text the layer lacks) gets only the quote check.

## Measuring

- **`bench`, not single runs.** Warm caches replay themselves, so reruns agree;
  the noise is which pages a book happens to have. Runs are compared page by
  page, with one primary test ("after review" averaged over the set's books, each
  weighing the same, at the low, mean and high slip rate; pooling pages would let
  the three longest books, 78% of the pages, decide) and a veto when a book alone
  gets worse by ≥ 0.05 wrong words per page on the mean with its 99% interval above
  zero (at 95% the eleven tuning books would veto about one change in four that
  leaves them all as they were; at 99%, one in nineteen): 24 separate intervals
  would star about one by chance each run.
- **"After review" counts the reviewer's slips.** 8 of 68 checked answers on
  Stella were wrong (Beta posterior 0.06–0.21), so a question isn't free.
- **An error over a page break counts on the page holding most of it.** Counted on
  its first word's page, washed-out Afscheid p. 38 (one region the reviewer types)
  scored as 297 unasked words on p. 37, and the scraps of Dolittle's p. 57 plate as
  13 on p. 56: Afscheid read 5.03 wrong words a page after review where it is 0.24.
  A whole page typed by the reviewer still counts as one question's slips, which
  flatters a washed-out book.
- **Validation books are not a test.** Earlier choices were made on their scores. They
  are De tuin, Villa Toscane, De eerlijke vinder and You're Never Weird on the Internet
  (the only English one, and the hardest layout: pictures holding text). Grand Hotel Europa was one until
  its pair failed: an EPUB of another printing, and reference headings the scan lacks.
- **The test set is a book nothing was chosen on.** Het geluid van bananen
  (Stella's publisher and scan format) is scored once, at the end of the plan;
  no model trains on it and the CLI refuses to score it without `--score-test`.
  A change that carries over to the validation books proves less than that.
- **A reference can stop being one.** When a book's remaining disagreements are
  mostly edition differences, or its verdicts never settle, its score measures
  the edition. The text layer's CER against the reference and the share of body
  lines the aligner can't place say so without verdicts
  (`golden/signals.py`): the bench records both per book over the build's body lines
  and names a book past 3× the set's median layer CER, or with one body line in twenty
  unplaced, as a suspect pair. Over body lines, because page furniture is unplaced by
  design: counted over all lines, seven books pass 5%.
- **Tuning books are scored by models trained without them**
  (`*-without-<book>.pkl`).
- **The reference isn't the truth either.** Two groups of suspects lack a clean
  label. 563 of 3,232 (17%) are unsettled (no single version is close enough to
  the aligned reference) and are left out of the trust data; in a build they are
  questions with no right option, where the reviewer types and slips more. 394 of
  the 2,669 settled ones (15%) have no version equal to the truth, and are trained
  on with the closest version marked right: 286 of them one character off, 108
  more. How much of that is alignment noise and how much a wrong label is
  unmeasured. Verdicts (`golden review`) settle the reference's side. A
  version is labelled by comparing the line as the score compares it, with what reflow
  sets anyway folded too (spaced dots, a space before punctuation): before that, Crime's
  and Dolittle's faithful `you. . . .` and `listen :` were labelled wrong and the
  sentence judge right, the error that made Lady into Fox's labels favour winnow.
