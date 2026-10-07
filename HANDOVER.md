# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State on 2026-10-07, evening

Everything is committed on `main`. Earlier today: OCR-check crops, the italics
stage, the golden books reshaped, missing lines (see the decision log). This
afternoon, after the second review:

- **Goede dochter pp. 9–64 verdicts settled** by the user (23; the reference
  was right in all but one). Its score now counts pipeline errors only: CER
  0.18%, paragraph F1 0.979, headings 4/4. Comparisons fold `…` to `...`.
- **`roboscriptorium quality book[:pages[:chapters]] …`** (`quality.py`): wrong
  words per page before review and left unasked, at 0.25/0.5/1 questions per
  page, with bootstrap intervals and the unasked errors by kind. Goede dochter:
  1.53 wrong words/page, 2.24 questions/page, 0.58 left unasked; only 28 of 116
  OCR-doubt questions sit on an error. Ranking questions by their kind is too
  coarse to fill a budget well.
- **Error budget, Goede dochter**: punctuation and quotes 23, OCR letters 18
  (accents `én`/`één`, `hygiéne`, `lemand`), lost text 2. Not headings.
- **`golden/align.py`**: every golden line's printed truth and role (body,
  heading, other), by word alignment with the reference.
  `disagreements.patch` keeps printed glyphs now.
- **OCR bench on modern Dutch** (`experiments/bench_line_readings.py`, Goede
  dochter, typesetting folded): text layer 0.21%, glm-ocr 0.25% (drops quotes
  and sometimes words), tesseract 0.29%. Item 4 answered for this book: no
  single reading wins; their errors differ.
- **glm-ocr token confidence**: flat, not a question source (decision log).
- **Line-role classifier** (`experiments/train_line_roles.py`, scikit-learn
  trees, leave one book out): 153 role errors against 182 for `roles.py` over
  nine books; with the two CPNB books, eleven books: 224 (`roles.py`) against
  279 (trees) and 272 (trees + clef). Big wins on unseen Dutch books
  (Monterosso headings 3/19 → 18/19, Grand Hotel Europa 6/17 → 17/17, Villa
  Toscane 0/12 → 12/12), big losses on Dolittle and Lady into Fox, and
  unstable between runs (`work/probes/line-roles/run3.log`). The style vote (`typestyle.py` +
  `roles._heading_styles`) is a stopgap the classifier is meant to replace.
- **New golden books**: De eerlijke vinder and Monterosso mon amour (CPNB, in
  Stella's scan format; different typesetters). Text layer alone: CER 0.37% /
  0.31%.
- **Reis om mijn schedel** (Van Gennep 2014, Stella's publisher) added: same
  leading, furniture and, by eye, typeface as Stella; the best stand-in for
  measuring Stella. Text layer alone CER 0.72%, F1 0.853. A full `eval` was
  started at the end of the session (`work/reis-om-mijn-schedel--ia-scan/logs/`).
- **Retired**: Sense and Sensibility (no same-edition reference). **The
  Teirlinck bench no longer chooses OCR models**; re-bench on modern Dutch
  (Goede dochter, the Boekenweek books, Reis) with
  `experiments/bench_line_readings.py` once each has a full build's readings.
- **Stella** built end to end for the first time: 44 OCR fixes (one wrong:
  `besefeen`), 1.06 review questions per page.

## Critical review (2026-10-07): change of course

A review of the approach, done with the user, who agreed with it. Read this
before picking up any task below: it changes what counts as progress.

**Where we stand.** The pipeline cuts the text layer's errors by ~40% (Goede
dochter CER 0.40% → 0.23%, Vals alarm 0.74% → 0.47%, De tuin 0.72% → 0.41%).
Against the goal it is far off: 0.25–0.45% CER is ~4–8 wrong characters a
page, and review asks 2–3.5 questions a page. A 300-page book would leave
~1,500 errors before review and ~800 questions for the human.

**What the review found:**

1. **The rule pile doesn't carry over.** Each tuning-book failure added a
   rule to `roles.py` (`sunk-numeral`, `sunk-opening`, `section-number`,
   `subtitle`, …). On the held-out books: Villa Toscane headings 0/12, Grand
   Hotel Europa 3/16, Lady into Fox italic precision 0.31. That is the "tuned
   to one book" failure AGENTS.md warns about.
2. **The role model is blind to typography.** `roles.state()` sends text,
   position, width, alignment and neighbours. No image, no type size, cap
   height, all-caps, letterspacing or weight. Those are how a typesetter
   marks a heading, and why clef reads "V" as a page number.
3. **Decisions are per line; the structure is per book.** Page numbers form a
   sequence, running heads alternate verso/recto, a book's chapter headings
   share one style. `page_offset` and `Repeats` use this piecemeal.
4. **Errors every reading shares are invisible.** Suspects come only from
   disagreement. No per-word confidence is used (tesseract's, the layer's, or
   glm-ocr's token probabilities). The only word list is the English
   `/usr/share/dict/words`, also on Dutch books (`initials.py`,
   `disagreements.py`).
5. **The judges get a hard question.** "Which string does the crop show?"
   fails where options differ by a period or a quote mark (clef misses small
   periods; every model shares the opening-quote blind spot). `SURE` and
   `SURE_ALONE` are guesses on top.
6. **Measurements are noisier than the log suggests.** `verdicts_applied` is
   0 on every recent run, so residual CER mixes real errors with edition
   differences, and many logged wins (0.48% → 0.47% on 14.5k words) are a
   couple of characters.

**Rules for the next agent:**

- **No new layout rules in `roles.py`** to fix a tuning-book miss. Fix the
  model's evidence or the book-wide inference instead. Judge heading work by
  the held-out scores (scored, never inspected).
- **Report changes as error counts** with their book and slice, and say when
  a difference is within noise. Settle verdicts on a tuning book before
  claiming sub-0.1% gains on it.
- **Group review questions** wherever one answer can settle many (a heading
  style, a confusion pattern, a running head).

## Second review (2026-10-07, agreed with the user): the machine learns nothing

Every gain so far is a hand-written rule, a threshold or an off-the-shelf
model; the golden books only score. Session 2026-10-07 (afternoon) confirmed
it: type features per line (`typestyle.py`) plus a style vote gave Goede
dochter one heading; clef ignores type in its state; a per-group question was
right on every tuning group yet gained nothing held out (+2 spurious on De
tuin), so it was dropped. The type measurements stay, as features for item 5.

Don't: add rules that fix one book, swap in bigger judge models hoping for
better calibration, or add another OCR library on its own.

## Next steps, in order

1. **Error budget.** Goede dochter's verdicts are settled; its biggest
   category is punctuation and quotes (a closing ’ lost after `,` `?` `!`, ‘
   read as “), then accents. Work there next, measured with `quality`. Settle
   verdicts on the CPNB books too (`golden review`), since they're the closest
   to Stella.
2. **Measure what the human experiences.** The product is errors left after
   review against questions asked. Report unflagged errors per page at fixed
   question budgets (0.25, 0.5, 1 per page), with bootstrap error bars over
   pages; claim no gain inside them. Turning silent errors into flagged ones is
   a win even when CER stays flat.
3. **glm-ocr's logprobs** (probed: flat on Goede dochter, see the log; keep
   only as a feature for learned trust). Ollama 0.40 returns `logprobs`/`top_logprobs` for
   glm-ocr in `/api/generate`: a confidence per token of every reading and the
   runner-up where it was unsure. Flag low-margin tokens even where all
   readings agree (shared errors). No new runtime needed.
4. **Re-bench OCR models on modern Dutch** (done for the cached readings on
   Goede dochter; next the Boekenweek books and Reis, after a full build of
   each; candidates not yet tried there: deepseek-ocr, gemma4) (Goede dochter line crops): glm-ocr
   was chosen, and vision models judged to modernise, on the 1909 Teirlinck
   bench in pre-reform spelling.
5. **Golden books as training data** (classifier probe running). Next:
   regularise the trees (min samples per leaf, depth, fewer features; check
   stability over seeds and training sets), find why Dolittle gets 87 false
   headings (captions and picture text? labels for caption lines?), report
   errors with bootstrap intervals over pages, then put the classifier in the
   pipeline behind a switch and compare with `quality`. Align each scan with its reference word
   by word for labelled line crops and line roles. Train a small line-role
   classifier (gradient-boosted trees) on geometry, type size (`typestyle.py`),
   cap height, capitals, letterspacing, repetition and page-sequence features;
   score it leaving one book out at a time. Aim: replace the `roles.py`
   overrides. Once it beats the current roles held out, **delete** the style
   vote (`roles._heading_styles`) and every override it covers (`sunk-numeral`,
   `sunk-opening`, `section-number`, `subtitle`, …); keep `typestyle.py` as
   features. Labels: `golden/align.py` (done). Later: fine-tune glm-ocr (MLX) or a tesseract/Kraken line model
   on aligned crops plus synthetic pages rendered from the EPUBs.
6. **Page image first, sooner.** Full-page document models (dots.ocr, olmOCR,
   MinerU, PaddleOCR-VL, Docling) see layout, heading size and italics; add
   them as votes in the alignment. Ask the user before adding a runtime.
7. **Book-level inference.** Page-number sequences, verso/recto running heads,
   one heading style, a word spelled one way 50 times and once otherwise. Model
   the book jointly (HMM/CRF over page states, or a small ILP) rather than
   adding per-line features; this also yields grouped review questions.
8. **More readings whose errors differ**: a second scan of the same edition
   beats another vision model of a similar family.
9. **Run Stella through the current pipeline now and then** (done today; its
   73 review items await a human).
10. Older items still open: Learned trust (Dawid–Skene) over `SURE`/
   `SURE_ALONE`; a Dutch lexicon (ask before installing); quotes in Dutch IA
   layers; `*****` scene breaks; paragraph breaks after a full line; italics
   marks below the word; the metadata stage (`nuextract3:q6_k`); Dolittle
   p23's initial "E"; em dashes after a space.

## Working with the user

- **Before every long run, say why, what it should show, how long it takes and
  what each outcome would mean.** Post updates while it runs. Answer every
  question, even mid-task.
- **One book per long command**, results reported before the next.
- Be honest about the value of the books the user brings; retire what doesn't
  help and say what would (Dutch 1960s–90s scans with a same-edition ebook;
  real publisher print PDFs with their EPUB; another typesetting of a text we
  already have). English same-scan Gutenberg pairs the agent finds itself.
- Held-out books are scored, never used to find errors.
- The user picks no models: choose from measurements and record why. Ask before
  adding a runtime or anything they must install or pull.
- Commit after every step and keep this file current: the laptop may lock.
  Commits are signed through 1Password; if signing fails, stop and ask for it
  to be unlocked.
- Their connection is slow: avoid large downloads. Golden sources are in
  `work/.cache/` (checked against PROVENANCE.md).
