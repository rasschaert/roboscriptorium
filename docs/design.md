# Why it is built this way

Each component, what job it does, and the evidence that it earns that job. When
the evidence changes, this file changes with it (AGENTS.md's standing rules). The
dated history behind each line is in [decisions.md](decisions.md).

Numbers marked *trust data* come from the OCR check's labelled suspects
(`experiments/ocr_trust_data.py`, each version labelled from the aligned golden
text, settled ones only): 2,514 over eight books on 2026-10-07, Lady into Fox left
out (its labels differ from its print in typography; see winnow below; as a
validation book it is scored, never trained on).

## The text layer is one reading, not the truth

A scan's OCR layer is good (Goede dochter: 0.20% CER on body lines) but drops
quote marks, misreads accents and splits contractions. Every other reading exists
to catch what it gets wrong; none replaces it, because each has errors of its own
(bench: `experiments/bench_line_readings.py`, Goede dochter pp. 9–64).

## OCR check

**Several readings that fail differently.** A reading only helps where it is
right and the layer is wrong, so readings are chosen for different errors, not
for the best score alone:

| Reading | Why it is there | Its own failure |
| --- | --- | --- |
| glm-ocr, line crop | letters and words (right where the layer is wrong on 114 of Goede dochter's lines) | drops quotes, diaereses; a word now and then |
| tesseract, whole page | its own line segmentation, so it sees marks the layer's boxes cut off; dashes | punctuation, opening quotes |
| qwen3.8, line crop, told the book's style | quote marks (keeps them where glm-ocr loses 31, tesseract 80) | plausible real words (`doodgaan→doorgaan`) |

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

- *clef:27b looks at the crop.* It is the judge that is usually right: 2,236 of
  2,514 alone (89%, trust data). Told the book's typesetting and given options in
  ⟨ ⟩ rather than “ ”, it picks right more often on typography (Goede dochter 92 →
  98 of 102).
- *winnow:e4b reads the sentence, not the image.* It is a poor judge alone (1,596
  of 2,514, 63%) and is kept as **an alarm on clef**: where winnow agrees with
  clef, clef is wrong on 58 of 1,495 (4%); where it disagrees, on 220 of
  1,019 (22%). The alarm works on every book but the cleanest: on Goede dochter clef is
  wrong 13/170 against 12/191, no lift. On Lady into Fox winnow even beats clef
  (132 against 54 of 149), but that book's labels differ from its print in
  typography, so the number measures the reference more than the judges, and the book
  is left out of these totals. Told the
  book's style winnow got worse on Goede dochter (91 → 84 of 200), so it isn't.
- *The word list is a vote, not a judge.* Where it knows only one version's words
  it is nearly always right, but acting on it added unasked errors on two
  validation books (lost compounds, stress accents). It is shown to the reviewer
  and is a trust feature.

**Learned trust decides, not a fixed rule.** The judges' confidences aren't
probabilities of being right, and how much each signal is worth differs by kind of
error and book (the winnow numbers above). Shallow trees over the judges' picks
and confidence, the readings' support, the word list and the kind of difference
learn that from labels: leaving one book out, silent errors at the rule's own
number of questions fell 57 → 15 over seven books. The fixed rule (both judges
agree, clef ≥ 0.3) asks about 35% of suspects because it needs winnow's
agreement; it is only an explicit fallback (`ROBO_OCR_TRUST=0`). A missing or
mismatched model stops the build, because a silent fallback once ran unnoticed.

**The question budget is book-wide.** Questions go where the model is least sure,
which may be several on one bad page; a per-page cap would spend questions on
clean pages.

**Doubts are asked per place, not per line.** Two wrong places in one line, each
fixed by a different reading, left no right option, and the reviewer then typed
the line and added an error.

## Book-wide style

Dash kind and spacing, and the quote style, are a property of the book, not of a
line: asked line by line they came out mixed. Dashes are measured on the scan;
quote style comes from the layer's own marks. Models that read or judge
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

## Measuring

- **`bench`, not single runs.** Warm caches replay themselves, so reruns agree;
  the noise is which pages a book happens to have. Runs are compared page by
  page, with one primary test ("after review" averaged over the set's books, each
  weighing the same, at the low, mean and high slip rate; pooling pages would let
  the three longest books, 78% of the pages, decide) and a veto when a book alone
  gets worse by ≥ 0.05 wrong words per page at 99% (at 95% six books would veto
  about one good change in seven): 24 separate intervals would star about one by
  chance each run.
- **"After review" counts the reviewer's slips.** 8 of 68 checked answers on
  Stella were wrong (Beta posterior 0.06–0.21), so a question isn't free.
- **Validation books are not a test.** Earlier choices were made on their scores.
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
