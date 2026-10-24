# Why it is built this way

Each component, what job it does, and the evidence that it earns that job. When
the evidence changes, this file changes with it (AGENTS.md's standing rules). The
dated history behind each line is in [decisions.md](decisions.md).

Numbers marked *trust data* come from the OCR check's labelled suspects
(`experiments/ocr_trust_data.py`, each version labelled from the aligned golden
text, settled ones only): 5,412 over 14 books on 2026-10-09, the three validation books
among them (counted here, never trained on). The relabelling of that evening (ellipsis
style folded, a space beside a quote no longer forgiven) settled more of them, 4,275
training suspects on the tuning books; the judges' figures below are from before it.

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

**A number printed apart from its line is a line of its own** (`pdf._apart`). Some
layers join a page number in the outer margin to the body line at its height ("16
Daarna stapte hij op"), so no stage sees a page number: De eerlijke vinder kept 28 of
them in its text, 28 of its 38 errors no question asked about, six inside a word broken
across the page ("moes- 15 ten"). A bare number more than 1.5 line heights from the
rest of its line is split off in front of it, and the line roles judge it as any other
line; a word space or a heading's own number ("Chapter 3") is far closer. Only beside a
line of at least 0.8 of the page's full width: split off a running head ("Puddleby
… 5"), the title left alone read as a chapter heading on 33 Dolittle pages and its
paragraph breaks went from 0.39 to 0.68 wrong a page. On the bench slices it splits De
eerlijke vinder's 31 page numbers beside full lines (wrong words 0.88 → 0.42 a page,
unasked 0.59 → 0.16) and a few specks read as digits; three numbers beside a short
last line stay joined.

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

Every reading in the trust data and the bench is the local build's (2026-10-10), as
Stella's are. Re-read locally where DeepInfra's bf16 had read: tuning 0.56 → 0.56,
validation 0.77 → 0.79, no change; De tuin alone worse (0.77 → 0.85).

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

**How an ellipsis is set is no difference.** The typography stage sets every ellipsis the
book's way, so a glyph against three dots isn't asked or judged. It was: Reis spent 16 of
its 83 questions on it, and in the trust data 208 suspects whose versions differed only so
were left out as ties, 44 of them hiding a real lost ellipsis (`kra.` for `kra…`) the
arbiter then never saw a label for. Folded (2026-10-09): Reis's questions 1.09 → 0.34 a
page and after review 0.32 → 0.22; the set unchanged by the test.

**A full stop for a line's last comma before a lower-case line is no version.** No
sentence ends where the next line opens in lower case, so a reading that only turns the
line's closing comma into a stop there is dropped before judging (`stop_for_comma`),
unless the book prints the word as an abbreviation elsewhere ("bijv. de"). In the trust
data every such place (about 40, all books) prints the comma; on the bench the arbiter
took the stop, unasked, on 6 places of De vergelding, whose commas the readers see as
stops. The two arbiter features tried for it first ("the next line opens in lower case",
"the span ends the line") made other errors. Taken 2026-10-24: tuning after review 0.290 → 0.286
[−0.007, −0.000], 6 unasked words fixed and none made.

Two more kinds of reading are never the print, by the same test (wrong in every book's
trust data, and true by definition): an accent on one letter of a doubled a, o or u
("doóde", "voór"; stress is marked on both, `half_accent`; e is left out, as French
endings and "Eén" set it so), 27 versions, never right; and a mark prose doesn't
print (`~`, `^`, `|`, `garbled`), on 50 suspects, never right: where the layer was
wrong (11) a kept version always had it right, so dropping them loses no catch. A
capital inside a lower-case word ("aaN") is never the print either, but a reader's
"wA-dienstplicht" for a word set in small capitals was what raised that place's question
(De vergelding), so it stays a version.

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
- *winnow (Winnow-12B) reads the sentence, not the image.* Asked through its answer's
  token probabilities (`tokens:`, `clients/decide.py`), it is right alone on 7,363 of
  9,131 trust-data suspects (81%, clef about 90%) and is kept as **an alarm on clef**:
  where winnow agrees with clef, clef is wrong on 144 of 6,730 (2%); where it
  disagrees, on 851 of 2,401 (35%). The arbiter retrained on its votes: tuning after
  review 0.30 → 0.28 [−0.03, −0.00], validation 0.37 → 0.39 [−0.01, +0.05], no veto
  (2026-10-18). The smaller winnow-ollama:e4b it replaced was right alone on 67% with a
  4% / 22% alarm, and works only through Ollama's systemone, which versions after
  0.40.3 refuse it; asked through tokens it was at chance. On two books winnow beats
  clef (De kerk van de dode meisjes, The Nature of a Crime): their references are more
  standard than their prints. Told the book's style, an
  earlier winnow got worse on Goede dochter (91 → 84 of 200), so it isn't.
  Taken away (an arbiter trained without its votes, the check run without it,
  2026-10-24): tuning after review 0.282 → 0.316 [+0.02, +0.05], 164 wrong words made
  against 79 fixed, questions down on most books: without it the arbiter is surer and
  wrong more often.
- *imajev-4b, a second vision judge, is not used* (`ROBO_ALARM_MODEL`, off). Asked clef's
  question on the crop, it is right alone on 85% and a sharper alarm than winnow-ollama:e4b
  where it speaks (clef wrong on 37% of their disagreements against 5% of their
  agreements) but it speaks less (904 disagreements against that winnow's 2,049), and as the arbiter's third
  judge the bench saw no change: tuning 1.02 → 1.01 after review [−0.04, −0.00],
  validation 0.81 → 0.80 [−0.05, +0.02] (2026-10-09). Not worth a second model server and
  a quarter second a suspect. Its votes stay in the trust data; training uses only the
  judges the settings name.
- *The word list is a vote, not a judge.* Where it knows only one version's words
  it is nearly always right, but acting on it added unasked errors on two
  validation books (lost compounds, stress accents). It is shown to the reviewer
  and is a trust feature.

**A version the vision judge saw none of is never applied.** Where clef answers "neither",
the readings missed the print: Thief-Taker p. 46 has a crop of the wrong line, read as
whole other sentences, and the arbiter applied winnow's pick of them. Such a suspect is
asked first and otherwise keeps the layer's reading, which was right on 17 of the 23 in
the trust data: too few for the trees to learn it (Thief-Taker 0.82 → 0.55 after review).

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
only that book's own answers can teach it: they join its arbiter's table, each counted
three golden suspects' worth (`trust.with_answers`). Ex-minnaar's answers settle "we" →
"wc" and its stress accents that way: of its answered suspects, held out a line at a
time, the arbiter asks 75 → 42 with no more wrong (decisions.md, 2026-10-16). The bench decides whether
the gain carries into a build. It does: the arbiter retrained with an empty pair table (2026-10-11) is worse on both
benches, tuning 0.31 → 0.34 and validation 0.70 → 0.73 wrong words a page after review,
each interval clear of zero. The fixed rule (both judges
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
user chose it (2026-10-09).

**The arbiter's sureness is calibrated**, so that line holds through retrains: an isotonic
map, fitted on each training book scored by trees trained on the others, from how sure
the trees are of a suspect's likeliest version to how often it was the print
(`trust.sureness`). It changed little on today's arbiter (raw 0.8 was right 83% of the
time, 0.9 95%), and the bench saw no change (tuning 0.56 → 0.57, validation 0.80 → 0.80,
2026-10-09); its worth is that 0.8 means four in five after the next retrain too.

**Doubts are asked per line** (the user, 2026-10-16: "you ask me what the line says …
don't ask me twice"). One question per line, however many places in it are in doubt;
its options are the whole line as the text layer reads it, as each reader and each
judge has it, with each place as most models read it ("likeliest"), and as built
(`ocrdoubts.line_doubts`); the answer is the line. Asked per place before, a line with
two places got two questions, and a line where each place was right in a different
reading had no right option, so the reviewer typed it and added an error: the
"likeliest" line combines them, and "Something else" starts from any option (✎) rather
than from the text layer. A line question catches any error on its line, the whole line
being in front of the reviewer. Benched: tuning 0.29 → 0.29 [−0.01, −0.00], validation
0.51 → 0.49 [−0.03, −0.01], questions 1,106 → 1,082, no book worse.

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

## Context judge

**A thinking model that settles questions from the text around them** (`contextjudge.py`,
`ROBO_CONTEXT_MODEL`, off until measured). The judges in use see a line's crop (clef) or
its sentence (winnow); many questions the reviewer answered were settled by the
paragraph or the book: Ex-minnaar asked "we"/"wc" 13 times and small capitals read as
"BMw" about 16, where one version is ungrammatical or the book never writes it
(the user, 2026-10-17: "if it cuts down on questions being asked in human review, i'm
for it"). It only settles questions the arbiter would ask, so it can cut questions and
cannot add silent errors to suspects the arbiter decides; its failure is settling a
question wrongly, which costs a wrong word where the question cost about a seventh of
one (the reviewer's slips and time).

The probe (`experiments/probe_context_judge.py`, 2026-10-17, qwen3.8 hosted on DeepInfra
bf16, thinking capped at 1,500 tokens) on 336 suspects the held-out arbiter would ask:
alone it is right on 86% of the golden books' (the arbiter's likeliest 68%) and 76% of
Ex-minnaar's answers (79%), but it overturns one in five of the suspects the arbiter
settles rightly, so it never overrules. Where it picks the arbiter's likeliest version,
220 of the 336 (65%), that version is wrong 17 times (8%), under a question's price:
those are settled, the rest asked. Each version's count in the book, first in the
prompt, made it worse (74% and 64%): "we" 241 times against "wc" 9 outweighed the
sentence. It can't see the scan, so quote marks and accents gain least, and it reads
for sense, so a misprint (the printer's "zeI") is where it errs by design.

**Its agreement is information; the arbiter's sureness says when to take it** (2026-10-19,
the same 336 hosted answers and the local 100, no new model calls). Where the arbiter is
unsure (likeliest under 0.6) it is right on 54% (23 of 38 locally; 45 of 84 hosted); when
the judge agrees, on 86% (18 of 21; 33 of 39); when it disagrees, on 29% (5 of 17; 12 of
45). The wrong settles sit where the arbiter is least sure: hosted, judge agreeing, 6 of 39
below 0.6, 6 of 54 from 0.6 to 0.7, 5 of 127 from 0.7 up (4%, against 8% for every
agreement). So `ROBO_CONTEXT_MIN` (`Settings.context_min`, default 0: every agreement
settles) leaves a suspect asked, unread by the judge, where the arbiter's likeliest is
under that sureness. A threshold is a setting the bench can choose, not a hand-written
rule on text; the sets' benches say whether the questions it keeps cut still pay for the
errors it avoids.

## Page readers

**Two more readers that see the whole page** (`pagereader.py`, `ROBO_PAGE_READERS`,
off until the arbiter is trained with them). glm-ocr and qwen3.8 each read a body page
whole, at 1.6 million pixels. Where both read a place right that the build got wrong,
they point at 60 errors over the tuning books that no question asks, about a quarter of
what is left after review; where they agree against a right build, 68 places
(decisions.md, 2026-10-14). Alone each is wrong far more often than right (glm-ocr four
false places a catch), so neither raises a question by itself: each reading is split
back into the layer's lines and joins the line readers, and the arbiter learns per kind
of error how far to believe it.

The split aligns the reading's words to the layer's page-wide on their letters, then
gives each line the words that align to it. A word the layer breaks over a line end is
cut where the layer cuts it, its hyphen kept, and a word is cut after a dash that runs
into the next one, so a dash one side lost costs one word, not two lines' worth. A run
of more than two words the layer lacks (a running head, a caption, invented text) is
dropped; a page whose reading matches fewer than half the layer's words reads no line
(glm-ocr invents text on near-empty pages).

**What it can't carry.** A line reading only says what a line's words are. A compound
hyphen at a line end ("night-" + "vision") splits back to what the layer has, and a
kept page number has no words to vote with. Of the 40 errors the probe lists, about 9
sit within a line; the rest (line-end hyphens, page numbers, words glued across a join)
need the page reading as evidence in the hyphen and line-role decisions instead.

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

A layer can drop every gap, though: The Stranger's Child prints `Ka . . .’`, its layer
reads `Ka...` throughout, and the vote set it tight with no space (4.57 wrong words a page
after review, 370 of its 389 unasked errors). So the gaps are measured on the scan too
(`scanstyle.measure_ellipses`): three dots are short runs of ink near the baseline, and
the blank before the first and between them is weighed against the line's word gaps. On
every golden scan the two kinds part widely: before the first dot at most 0.62 of the
word gap where no space is printed, at least 0.86 where one is; dots 0.28–0.63 letters
apart when tight, 0.91–1.21 when spaced. The scan sets the gaps; the layer still chooses
between the glyph and three tight dots, which look alike on paper. Of the 26 golden
books only The Stranger's Child changed.

Straight quotes and apostrophes are the layer's, never the print's: a printed book sets
curly ones. `quotes.curl` curls what is left of them after the answers, by place: opening
after a space, bracket, dash or opening mark, closing elsewhere, `’` inside a word and
where it elides letters (`’s`, `’t`, `’n`, `’em`, `’tis`, `’60s`), a double quote opening
as the book's own (“ or „, by majority). An opening mark is followed by its word, so a
mark after a dash with nothing after it closes the speech the dash broke off (Goede
dochter's `minderjarige –’`). A mark right after a digit (a foot, an inch) or spaced on
both sides says neither way and stays. Every golden book had some: Metro 124 in
its slice, Dolittle's layer straight throughout (541 words); the bench saw none of it
until it counted typography apart (2026-10-13), since `normalise` folds quote marks.

## Quote questions

A paragraph whose quotes don't pair up is flagged where the mark is missing, and
the question offers Qwen's reading of the line, keeping only its quote marks and
the punctuation beside them on the OCR-checked letters: its letters slip too often
to take (`krimpachtig`, a Cyrillic word), its quote marks rarely do (Reis right on
51 lines where the line is wrong, wrong on none where it is right).

**A quote question offers up to three readings beside the layer's** (`quotes.readings`):
the line as the OCR check left it, its letters fixed and the print's marks kept, which may
be wrong in print too (Goede dochter p. 36 sets `Charlie.’ Waarom`, and so does the
publisher's EPUB); the line with the read model's quote marks and the punctuation beside
them, never its dashes or letters (Qwen read `directeursk-’` for `—’`); and, for a
quotation inside dialogue (`‘“…”’`), the two readings' marks combined, a doubled `““`
read as `‘“` in a single-quoted book. In the slip review the quote questions offered a
right reading on 0 of 4; with these, 3 of 4 (2026-10-09).

**Speech closed on a letter at a paragraph's end is asked too.** De tuin kerns a
paragraph's last full stop under the closing quote (`Frederik.’`), and the layer and the
vision judge both miss it there. Of about 33,000 quote-ending paragraphs in the golden
references 6 end on a letter, half of them a quoted term (`het ‘invoelend’`); in the
tuning books' output 17 did, about 15 of them a lost stop. A quoted term or title, three
words or fewer opening inside a sentence (`quotes.TERM_WORDS`), isn't asked. Bench
(2026-10-11): tuning **better** 0.37 → 0.37 (De tuin 0.46 → 0.41 for 0.08 more
questions a page), validation unchanged.

**A quote left open at a paragraph's end is asked whatever follows.** A quotation that
runs on into a paragraph opening with a quote looks exactly like a closing quote the
layer lost before speech that follows; the golden references run a quote over in 56 of
~58,000 paragraphs, and De tuin alone loses about 40 closing quotes there. Bench
(2026-10-11): tuning 0.37 → 0.36 [−0.02, −0.00] (De tuin's unasked 0.24 → 0.16 for 0.35
more questions a page), validation 0.75 → 0.75, no book worse.

**An open mark right after a word is asked where it stands.** "Open at end" points the
question at the paragraph's last lines, which is where speech loses its closing mark; a
speck read as an opening mark mid-sentence ("zich ‘schrap zette") can sit many lines
above, out of view. A mark left open right after a word is asked at the mark instead.
Bench (2026-10-11): tuning **better** 0.33 → 0.32 [−0.03, −0.00] for no more questions
(Afscheid 0.58 → 0.45), validation no change.

## Missing lines

A layout region with no text-layer line in it is read by glm-ocr only when it is about
one line tall (1.8× the book's line height): taller ones are pictures or blocks the
figures stage owns. Above a sunk page's text, where a chapter opens, regions up to five
lines tall are read too: Artemis draws each chapter number in a circle about four lines
high, which DocLayout-YOLO marks and glm-ocr reads right ("1", "2", "3"). Headings 0/3 →
3/3, no other book changed (bench, 2026-10-09).

## Lost lines

An OCR layer sometimes loses a whole printed line, and when the spotter sees nothing there
either, `missing.py` can't read it. The layer's own boxes still show it: a line's height
of white space below a line that stops mid-word or mid-sentence (Vals alarm p. 33, after
"be-"). Such a gap becomes a question of its own, the reviewer typing the line from a
tesseract draft (`flags.lost-line`); not where a picture fills the gap, nor above a
footnote or a speck at the foot, which made most of a first version's false questions.
13 questions over 15 books caught 2 errors at first; with those left out, `bench` no
change (tuning 0.57 → 0.56, validation 0.80 → 0.77; De eerlijke vinder 1.28 → 1.14).

## Lost drawn initials

A drawn initial is a picture to the text layer, which leaves its word without a first
letter below the chapter heading ("asteel Araluen", "et wolvenschip"; Het ijzige land
opens every chapter so). When a section's first text line opens in lower case below a
heading, the line is flagged (`flags._initial_lost`) and the reviewer types it with its
letter. Lower case mid-section, or below no heading, isn't flagged. Bench (2026-10-11):
Het ijzige land 0.25 → 0.20 after review for 0.05 more questions a page, pooled no
change, no book worse. A first word set in capitals, two letters or more, is flagged the
same way: Dolittle sets a chapter's first word so after its initial and loses the letter
("HAT" for "THAT"); among the built books only Crime's "YOU" opens so with nothing lost.
Bench: Dolittle 0.44 → 0.40 for 0.08 more questions a page, pooled no change.

## Line roles

clef-flash:9b answers the doubtful lines, and rules in `roles.py` override it
where layout settles the question. The rules don't carry over to unseen books
(Villa Toscane headings 0/12). Trees over layout, type, repetition and clef's answer
(`sorter.py`, `ROBO_SORTER=1`) make 152 role errors to the rules' 406 on the tuning
books and 29 to 77 on validation, leaving one book out (five English books now, where
three made them unstable). Three things are enforced in code, being true by definition or
by every label: text repeated at the pages' edges is furniture (346 labelled lines, none
body); a line is kept as text, flagged, while the trees give it P(body) ≥ 0.25 (a lost
line costs ten words, a stray folio one or two); and a line the role model wasn't asked
about, away from the edges and inside a text block the layout model is sure of, stays
body: the trees dropped such full-width prose (Crime pp. 36, 42 and 98, a whole line
each), and the guard takes the tuning books' lost body lines from 72 to 57. On the new
baseline (2026-10-11), before the guard: no change by the test, tuning 0.50 → 0.48,
validation 0.74 → 0.67; Metro, De cipier, Artemis, 11/22/63 and Villa Toscane clearly
better, Thief-Taker and Crime leaning worse.

**On by default since 2026-10-13.** Two things made them hold. Their labels called a line
of bare marks (a speck, a lone quote) body, so they kept specks as text; fixed in the
aligner. And they had seen one book with pictures: two photo slices joined their training
only (De tunnels' chapter 12, Steve Jobs' photo insert), and a body line now weighs ten
times its class's share, because a body line dropped loses text unasked where a speck kept
is asked about (weight 1 dropped 38 of Steve Jobs' caption lines, 10 drops 3). Warm
benches against the rules: tuning no change 0.32 → 0.32 (Goede dochter, Metro, Monterosso
better), validation no change 0.59 → 0.50 [−0.23, +0.00] (Normal People 0.20 → 0.13), no
book worse. Left: Dolittle's text set around its drawings (short lines beside a picture,
their type measured small), which the trees still drop when trained without it; a book
with text wrapped around pictures would teach it.

The trees also take two cases rules once did: a line the role model drops that goes on
with running text (a page's first line called a running head, a short last line an
artifact), and a chapter numeral the layer misreads at a page's top ("l" for 1, "UH" for
11 on Afscheid). Switched off one at a time for the trees' features, each rule cost
more errors than it saved (`experiments/probe_retire_rules.py`: both off, line-role
errors 200 → 180 on tuning and 57 → 55 on validation); the rules left in `roles.py` each
cost errors when switched off.

**A word line called a page number above a heading is its label.** De kus in de nacht
opens on "Deel een" over "Proloog", set right; the sorter called "Deel een" a page number
(at 0.06) and it was dropped. A page number holds a number; a line of words without one,
right above a chapter heading, is the heading's label and joins it (`heading-label`), as
"CHAPTER" over "I." does. Bench (2026-10-11): no change on either set.

**The read model's page roles, tried and not taken (off, `ROBO_PAGE_ROLES`).** Shown a whole
page and its numbered lines, qwen names the heading and furniture lines (`pageroles.py`, a
short answer at ~6 s a page). On 208 tuning pages with certain labels, half holding a
heading, it had 4 roles wrong of 5,967 lines where the pipeline had 22, and found all 126
headings where the pipeline found 110, 3 false (`experiments/probe_page_roles.py --short`,
2026-10-23). Its answer is three more features for the trees (asked, heading, furniture),
not a rule over them, so they learn where to trust it; trees trained with it live at their
own path (`ROBO_SORTER_MODEL`), and a build refuses trees trained on the other features.
On 2026-10-24 they cut role errors by a fifth left one book out, yet `bench tuning` made 60
wrong words for 30 fixed, most on Dolittle's picture pages, where Qwen calls text beside a
drawing furniture (docs/decisions.md).

## Reflow: where paragraphs start

**The margin was the indent in a run of dialogue.** A line starts a paragraph when it
stands right of the margin, and the margin is the lower quartile of line starts within
five lines either side, which follows skew down the page. In a run of one-line dialogue
paragraphs every line in that window is indented, so none started a paragraph (Artemis
p. 26, Reis p. 77). The page's own margin now takes over where it lies further left:
fitted from the lines that reach the right margin (most are inner lines of paragraphs),
following the skew their right ends show. After a full line the window's margin holds,
so an indented block (You're Never Weird's hanging lists) isn't split line by line.

**White space starts a paragraph too.** Reis sets a blank line before an unindented
paragraph, and Artemis spaces its letters' paragraphs apart. A line further below the
one before it than 1.5 pitches, at its top and its bottom alike (Crime's box tops jitter
by several points), after a line ending in punctuation, starts one. Below a line ending
mid-word (Vals alarm p. 33, "be-") the gap is a line the layer lost.

Measured as paragraph breaks set wrong per page (2026-10-09): tuning 0.46 → 0.33, validation
0.32 → 0.21, words unchanged. Goede dochter 0.31 → 0.02, Vals alarm 0.36 → 0.04, Artemis
1.29 → 0.75. Left: Afscheid's are its EPUB's (it breaks paragraphs where the print runs
on), Artemis's letters set without spacing, and a section break that falls on a page
turn, where nothing on the page shows it.

**In unindented text a short sentence end starts a paragraph, if the text is justified.**
A.W. Bruna sets Vuurspel and De stilte van de hel without indents, so a break shows
only as a line ending a sentence short of the right margin. That only means something
in justified text, which was judged on all eleven lines around the line: dialogue's short
lines made a justified page look ragged, and about half the breaks were lost (De
stilte's recall 0.54). Only lines that stop mid-sentence judge it now: in justified text
they reach the margin whatever the dialogue does, in ragged text they don't (the
counterexample in `tests/test_reflow.py`). A line is short from 2% of the line width (a
justified line ends within 3 pt; lines 7–16 pt short were real ends), and a page that
ends on a short sentence starts a paragraph on the next page's first line, unless that
opens in lower case. Bench (2026-10-11): validation breaks 1.97 → 0.21 a page (Vuurspel
7.91 → 0.44, De stilte 4.90 → 0.36), tuning 0.26 → 0.22 (Artemis 0.75 → 0.46), no book
worse, words unchanged. Left on De stilte, 3.5% of its breaks: sentences that end within
3 pt of the margin, which the print doesn't show either.

**A scene break is white space of two lines, or an ornament line.** Over 1.8 pitches
after a sentence (one blank line is two pitches), or a line of three ornament marks or
more ("* * *"; one or two are a speck), puts a break before the next paragraph, set
unindented after an `<hr class="break"/>`. Scored since 2026-10-11 where a reference
records its breaks (ten books, 295 breaks): the white space and ornaments alone found 255.

**A page that opens flush left after a finished paragraph opens a scene**, where the book
indents its paragraphs: a break at the foot of a page leaves no white space to see, and
half the breaks missed fell there (20 of 40). The line must sit on the margin, not left
of it: the layer's box for a page's first line can slip left of an indented line (De
tuin's at −1.8 to −6.6 points; Reis's flush ones from −1.0), so 1.5 points is the slack.
Bench (2026-10-11): breaks found 255 → 272 of 295 (Reis 156 → 168), 2 more set where the
reference has none; words and paragraph breaks unchanged on both sets.

**A dropped sliver doesn't end a run of text.** Indents are measured per run of body
lines, and a run of short dialogue lines alone can't find the page's margin. The layer
sometimes splits a mark off a line onto its row (Artemis p. 47: a word, a closing quote);
the roles drop it, and it used to cut the run, so a page of one-line paragraphs became
one. A dropped line of one or two marks, narrower than 8 points, on a neighbour's row is
passed over; a picture's garbled reading, wide, still ends the run (letting those through
too made Dolittle and 11/22/63 worse). Bench (2026-10-11): Artemis paragraph F1 0.975 →
0.980, tuning breaks 0.22 → 0.21, words unchanged.

**No paragraph starts inside a broken word.** Beside a picture or a drawn initial the
margin moves, and a line continuing "seen her hus-" read as indented: the word was split
over two paragraphs ("hus- band"). A line starting in lower case after one ending in a
letter and a hyphen continues the paragraph, however it is set. Bench (2026-10-11):
tuning **better** 0.32 → 0.31, validation **better** 0.74 → 0.70 (You're never weird
0.94 → 0.77, Monterosso 0.64 → 0.50), paragraph F1 up on every book that moved.

**Where the geometry can't tell, the vision judge does** (`parabreaks.py`). After all the
rules above, the breaks set wrong were of two kinds: starts no geometry shows (Vuurspel's
dialogue at the margin, Artemis's letters set flush and unspaced) and lines set apart
that carry a paragraph on (Dolittle's verse and the lines beside its drawn initials,
Normal People's emails, You're Never Weird's lists). A text table learned from the tuning
books (a quote after a closing quote at the margin starts a paragraph 87 times in 88) did
nothing: the one book that needs it validates. The judge (clef:27b) sees the line between
its neighbours, cropped across the text block, with their text, and says whether it
starts a paragraph; where it is at least 0.7 sure, its answer stands. On 1,488 lines of
tuning pages (every page with a break error and as many without), the reflow had 56
starts wrong; with the judge's sure answers 19, and none it had right made wrong
(`experiments/probe_break_judge.py`, 2026-10-17). A body line that begins in lower case
after a line that doesn't end a sentence carries on, unasked: of 3,800 such lines two
started a paragraph, both after a scrap. That leaves about a third of the lines to ask.

**That check stays; the judge is off** (`ROBO_BREAK_JUDGE=1` turns it on). Built with and
without it, every bench slice from its caches (`experiments/probe_break_conditions.py`,
2026-10-17): the check fixed 75 starts and broke none; the judge's sure answers fixed 43
and broke 63. Most of its wrong answers are flush dialogue after narration taken for a
new paragraph in a book that indents (all 9 of Goede dochter's), though it is told how
the book sets them; on the two books that set no indent, where it was meant to help, it
fixed 22 and broke 29. With the check alone, against the judge: tuning breaks 0.16 →
0.15 a page (no change), validation 0.16 → 0.13 (**better**), words unchanged on both;
Goede dochter back to 0.00, De stilte 0.47 → 0.30, Dolittle 0.10 → 0.18 (0.39 before
either).

## Footnotes

**A footnote leaves the running text.** Printed at a page's foot, a note read as body
became a paragraph in the middle of the story, or ran into the next page's (Reis p. 167).
`footnotes.py` takes the block of lines below the page's last line in body type when
they are small (under 0.78 of body type: Reis sets notes at 0.7, folios at 0.8, text at
1.0) and the first opens on a mark. Two guards came from false notes on the benches:
a picture or smudge read as small type has heavy strokes (Afscheid's 1.6–2.6 against
Reis's notes' 0.7–0.8; limit 1.2), and most of a note's words must be in the word list
(which alone was too lenient: the Dutch list knows "hd" and "vip"). The block's first
line may also open on a quote glyph before a capital: in small type the layer reads a
"*" as "“" (Een Russische roman p. 270, whose note stayed in the running text, spliced
mid-sentence), and the OCR check puts the star back afterwards, so `collect` finds the
mark; the guards above bound the risk (small type, below body text, mostly words). A note keeps its OCR
check, then is set apart and linked to its mark; where the mark wasn't read the note
follows its page's last paragraph. Bench (2026-10-11): Reis 7 of 8 found, all linked
(the eighth's mark read "ie"), paragraph breaks 0.07 → 0.06 (tuning BETTER), no notes
in any other book; Reis's EPUB passes epubcheck.

## Epigraphs

**A motto on a page of its own is set apart.** Ex-minnaar opens on "‘It’s closing time’
(Leonard Cohen, The Future)" alone on p. 7: read as body it became the book's first
paragraph and the sorter dropped the attribution. A page of at most six short lines, all
set at least 0.15 of a full line in from the book's margin (measured on full pages
nearby, as crops move it), with no heading, is a motto; a chapter's last lines start at
the margin. On the benches the first version also took pictures' garbled readings, a
title "11/22/63" and an unrecognised "DEEL EEN" (six books); it now needs three words of
two letters or more, no garbled line and some lower case, and finds none in any bench
slice (both NO CHANGE). The word list isn't asked: mottos are often in another
language, as this one is.

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
| the book's own spelling inside lines (`spellings`), counted over the book's whole body (a slice's pages as built, the rest as the layer reads them: `pipeline._book_spellings`) | 12 of 12 right where it spoke; counted over a bench slice only, it was silent on words the book hyphenates elsewhere (3 of 27 compounds closed wrongly, tuning compound hyphens 0.023 → 0.020 once the whole body counts) | silent on a word printed once (24 of those 27 compounds) |
| the word list knows exactly one of the two forms | fixes 7 wrong calls, breaks none where the book is silent | knows a closed form the print hyphenates (`faceplate`, `northernmost`: 3); knows both (`make-up`, `makeup`) |
| a capital after the break (`Noord-Holland`) | right on every true capital | a word set in capitals (`WE-` + `RELDGESCHIEDENIS`), 0 of 3: so it no longer counts as one |
| a hyphen already in the word | `Mens-erger-je-niet`, `good-for-nothing` | kept as a rule it was wrong 8 of 10 (`Zuid-Lon-den`, `Majuba-theeplan-tage`): now only where the parts beside the break are both words and don't make one |
| in an English book, the judge (clef:27b) asked how the word is spelled in its sentence (`hyphens.Compounds`) | where the rest is silent English compounds keep the hyphen 34 times in 77: the judge is right on 63, joining on 43 | a hyphenated form the reference closes (`timeout`, `bleedthrough`); 13 compounds it still joins |

After the change 15 of the 1,574 are wrong (Vals alarm 0, De cipier 1, Goede dochter 2,
De tuin 2, Artemis 2, Metro 8). What is left is English compounds the list lacks or
knows closed (`night-vision`, `semi-erased`, `slate-black`), `make-up` with both forms
known, and one Dutch compound (`heen-en-weerbewegingen`, closed in print though both
parts are words). Both parts being words is no rule for them: it fired 13 right against
3 wrong on the English slices and 0 against 44 on the Dutch.

**The OCR check never takes a line's break hyphen off.** Where its versions of a line's last
word differ only by the hyphen ("Oran-" / "Oran"), the judges are shown the word joined
with the next line (`ocrcheck.hyphen_only`) and may well choose the bare stem; but
writing the stem into the line leaves `join` no hyphen to see, and it sets the next line
after a space ("Oran je", "ver plaatsen"). `ocrcheck.fixed_text` keeps the hyphen on such a fix where the
word list knows the joined word ("Oran-" + "je" is "Oranje") and leaves the join to
reflow. Where it doesn't ("is-" + "uitgesproken": a speck the layer read as a hyphen,
print "ze is uitgesproken") the check's fix stands: keeping every hyphen glued it on
validation. Found 2026-10-20 in De vergelding, where its 12 such fixes came out split
(13 over all the books' caches; the other books' readers keep the hyphen); 10 keep the
hyphen now; an unlisted compound ("vlas-" + "fabriek") stays split, and so does "Enge-".

**The judge settles the English ones, not a question.** The scan can't show
whether a broken word keeps its hyphen; that is the language's spelling, which a
reviewer reading the crop knows no better than a model. Over the tuning books 438
breaks are left undecided by the rest with a one-way reference
(`experiments/probe_hyphen_judge.py`): in Dutch 355 of 361 close and the judge is no
better than joining (353 right at 0.5); in English 43 of 77 close, and clef:27b picks
right on 63 (clef-flash 59, winnow 46). So only English books ask it.

Four cases aren't a word's hyphen at all and skip the evidence: a Dutch word broken at its
diaeresis ("democratie-" / "en"), which the break drops, is joined with it
("democratieën") where the word list knows that form and not the plain one (true by
definition, so code; it ran ahead of the next case, which took "democratie- en" for a
word left open); a word left open before
a conjunction ("in-" / "en uitvoer", "pre-" / "and post-war") keeps its hyphen and the
space after it, unless the book or the word list knows the closed form ("Toron-" / "to");
a line ending in a digit
and a hyphen before a line starting with a digit is a number range broken at the end
("1914-" / "1918"), kept closed for the typography stage's range rule; and whether the
next line starts lowercase is asked of the letter itself (`str.islower`), not of a Latin-1
range that took "ĳ" and "ç" for capitals and kept the hyphen.

## The reviewer's answers are checked

**A question isn't free: the reviewer slips.** 8 of 68 checked answers on Stella were
wrong, and 2 of 32 on Goede dochter's questions of today (one choice: the right quote
mark where the print sets the wrong one); the bench pools them, 10 of 100
(`quality.slip_rates`, the user's choice, 2026-10-09), a middle figure over two kinds of
question. On Stella's rate, at one question a page that is about 0.12 wrong
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

## Misprints: errata, not answers

**A misprint is the book's error, not a reader's.** Ex-minnaar p. 94 prints "zeI ik"
(a capital I for l); every reader that read "zeI" is right, so an answer of "zei" would
train the arbiter to distrust them (the user, 2026-10-16: "i don't want to punish them
for being right"). The answer therefore says what the page prints, and the correction
lives apart, in `work/<book>/errata.toml` (`errata.py`), applied after reflow. An
erratum is found by its page and its printed words, never by a paragraph, line or word
number: those are positions, and every change to reflow or to the line list would move
them (positions aren't identities). Its failure is loud, not silent: words its page
holds twice or not at all stop the build, so a pipeline change that moves a word can't
put the correction somewhere else. Only the reviewer adds one (AGENTS.md, Fidelity);
the edition doesn't list its corrections (the user).

## Measuring

- **`bench`, not single runs.** Warm caches replay themselves, so reruns agree;
  the noise is which pages a book happens to have. Rebuilding every cache cold moves
  `bench tuning` by 0.01 a page at most (A/A, 2026-10-15: 0.32 → 0.33 after review
  [+0.00, +0.01], no book apart), so a change upstream of the caches needs no wider
  margin than a warm one. Runs are compared page by
  page, with one primary test ("after review" averaged over the set's books, each
  weighing the same, at the low, mean and high slip rate; pooling pages would let
  the three longest books, 78% of the pages, decide) and a veto when a book alone
  gets worse by ≥ 0.05 wrong words, or paragraph breaks set wrong, per page on the
  mean with its 99% interval above zero (at 95% the eleven tuning books would veto
  about one change in four that leaves them all as they were; at 99%, one in
  nineteen): 24 separate intervals would star about one by chance each run. A change
  clearly worse at any slip rate is worse, whatever the breaks did: a change that adds
  questions can look better at a low slip rate and worse at a high one.
- **"After review" counts the reviewer's slips and time.** 10 of 100 checked answers
  over two reviews were wrong (Beta posterior 0.06–0.18), so a question isn't free;
  and the reviewer's time is worth something too: one wrong word left is worth 20
  questions (the user, 2026-10-13), so each question adds 1/20 of a wrong word
  (`quality.QUESTION_COST`). With slips alone, a question catching an error one time
  in nine paid for itself however many were added. A comparison recomputes the measure
  from each page's unasked errors and questions, so runs saved before a price changed
  compare at today's; this morning's tuning run stays better at the new price
  (0.57 → 0.55 [−0.03, −0.01]).
- **Paragraph breaks count.** A break in the wrong place is as visible in an edition as
  a wrong word, and no question asks about it, so the bench counts them per page
  (`disagreements.break_errors`: a reference paragraph starting mid-paragraph in the
  output, or the reverse, where both sides' words align) and a change that clearly moves
  them decides like the words. On the tuning books they ran 0.01–0.42 a page beside
  0.19–0.99 wrong words after review, Artemis 1.29 and Afscheid 1.73 (most of those its
  EPUB's: it breaks paragraphs where the print runs on).
- **Typography counts, apart.** `normalise` folds quote marks, dashes and ellipses so
  that an edition's glyph choices don't count as wrong words, which left the bench
  blind to them. `disagreements.glyph_errors` counts, per page, the words whose quote
  marks, dashes or ellipsis differ from the reference's where the folded words align;
  a kind counts only where the reference sets it in its own glyphs (curly quotes ten to
  one over straight, an en or em dash, spaced dots somewhere: Crime's transcription and
  Artemis's e-book set every ellipsis tight where the print spaces them), and "…" and
  "..." are alike, as on paper. Its first run (2026-10-13, warm tuning) found what no measure could: the output
  keeps the text layer's straight quotes and apostrophes in curly books (Metro 124 `'`
  for `’`, Dolittle 541 words, every book some). A measure of its own, not yet in the
  verdict.
- **A question catches the error at its place.** A question about one place in a line
  catches an error only when they share a word; a question about a whole line (the OCR
  doubts since 2026-10-16) catches any error on it.
- **A typed washed-out page is a question per line.** Counted as one question, its
  three hundred typed words cost one answer's slips: Afscheid 0.25 after review where it
  is 0.64.
- **An error over a page break counts on the page holding most of it.** Counted on
  its first word's page, washed-out Afscheid p. 38 (one region the reviewer types)
  scored as 297 unasked words on p. 37, and the scraps of Dolittle's p. 57 plate as
  13 on p. 56: Afscheid read 5.03 wrong words a page after review where it is 0.24.
  A whole page typed by the reviewer still counts as one question's slips, which
  flatters a washed-out book.
- **Validation books are not a test.** Earlier choices were made on their scores
  (`bench.SETS`; You're Never Weird on the Internet the hardest layout, pictures holding
  text). Scans only: a born-digital PDF is out of scope (the user, 2026-10-17). A pair
  that fails (an EPUB of another printing, reference headings the scan lacks) is retired,
  not kept: Grand Hotel Europa was.
- **Every new pair gets a first look.** Validation wears out: every change is benched
  on it, and a choice made on it makes it tuning. So each new pair is scored once, before anything is
  chosen or trained on it, and then joins tuning or validation: the first looks,
  together, say how the build does on books it has never seen (the user, 2026-10-17).
  The CLI refuses to score such a pair without `--first-look`.
- **A reference can stop being one.** When a book's remaining disagreements are
  mostly edition differences, or its verdicts never settle, its score measures
  the edition. The text layer's CER against the reference and the share of body
  lines the aligner can't place say so without verdicts
  (`golden/signals.py`): the bench records both per book over the build's body lines
  and names a book past 3× the set's median layer CER, or with one body line in twenty
  unplaced, as a suspect pair. Over body lines, because page furniture is unplaced by
  design: counted over all lines, seven books pass 5%.
- **Picks not yet measured** (audit of 2026-10-12): each of these was set without a
  measurement behind its value, so treat it as a default to test, not a finding.
  *Slice size* (~90 pages): the rescoring of a bench pair on 20, 45 and 90 pages a book
  is in the checklist. *The veto's size* (0.05 wrong words a page): its 99% level is
  argued above, its size isn't. *The suspect-pair thresholds* (3× the median layer CER,
  one body line in twenty): never checked against the pairs they flagged. *The question
  budget* (1 a page): set with the first trust run; `ocr_ask_below` was swept, the
  budget wasn't. *Headings outside the primary test*: the bench reports headings found
  and spurious but no verdict rests on them. *Footnotes outside the score*
  (`golden/notes.py`): left out because the pipeline didn't place notes; it has since
  2026-10-11, so the reason has expired. *Quote and dash glyphs folded in the score*
  (`evaluate.normalise`): right for EPUBs that set them unlike the print, but it leaves
  the bench blind to a wrong quote glyph or dash, which the fidelity goal counts.
- **Tuning books are scored by models trained without them**
  (`*-without-<book>.pkl`).
- **The reference isn't the truth either.** Two groups of suspects lack a clean
  label. 563 of 3,232 (17%) are unsettled (no single version is close enough to
  the aligned reference) and are left out of the trust data; in a build they are
  questions with no right option, where the reviewer types and slips more. 394 of
  the 2,669 settled ones (15%) have no version equal to the truth, and are trained
  on with the closest version marked right: 286 of them one character off, 108
  more. How much of that is alignment noise and how much a wrong label is
  unmeasured. Verdicts (the review's questions on a golden book) settle the reference's side. A
  version is labelled by comparing the line as the score compares it, with what reflow
  sets anyway folded too (spaced dots, a space before punctuation): before that, Crime's
  and Dolittle's faithful `you. . . .` and `listen :` were labelled wrong and the
  sentence judge right, the error that made Lady into Fox's labels favour winnow.
