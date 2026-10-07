# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State on 2026-10-07 (after two critical reviews)

Everything is committed on `main`. New today:

- **OCR check crops fixed** (word-union crops, one em past line ends). Crime
  review 453 → 54; Dolittle WER 1.92% → 1.81%.
- **Italics stage** (`italics.py`): stroke slant on the page image, no model,
  for scans and born-digital PDFs. A word is measured only if it has an upright
  stem; ink is darker than each page's Otsu threshold (pale scans print grey).
  Italic precision / recall: Crime 1.000 / 0.886, Dolittle 0.850 / 0.791,
  De aanslag 0.987 / 0.855, Goede dochter (pp. 9–64) 0.958 / 0.828.
- **Golden books reshaped** with the user's EPUB/PDF pairs (AGENTS.md's table
  and decision log):
  - Tuning, Dutch scans: **Goede dochter** (clean publisher EPUB, same
    translation) and **Vals alarm** (48 chapter headings).
  - Held out: Lady into Fox (EN scan), **Grand Hotel Europa**, **De tuin van
    de avondnevel** (NL scans), **Villa Toscane** (NL born-digital). Score
    them, never inspect their errors.
  - Retired to `work/retired/`: Boze tongen, De dode kamer, Sense's Everyman
    scans, Goede dochter's 8th printing (reasons in the decision log).
  - Parked (`work/parked/README.md`): Goede dochter as a Dwarsligger, sideways
    pages with an unusable OCR layer, for when the pipeline can OCR whole
    pages itself.
- Publisher manifests can list `italic_classes`, `roman_classes` and
  `blank_classes`.
- `experiments/probe_big_diffs.py` lists the largest differing stretches.
- **Missing lines** (`missing.py`, measured: see the decision log): layout regions about one line tall with no text-layer line
  in them are read by glm-ocr and added before the line roles. Vals alarm's
  layer drops its single-digit chapter numbers (7 of 48 headings); the probe
  (`experiments/probe_missing_lines.py`) read all 15 Vals alarm candidates
  right and invented nothing on Dolittle's 73.

Scores (chapters or pages in brackets):

| Book | Text layer only (`--no-models`) | Full pipeline |
| --- | --- | --- |
| Villa Toscane (held out, born-digital, ch. 1–12) | — | CER 0.04%, F1 0.993, headings 0/12 |
| De tuin van de avondnevel (held out, ch. 1–3, pp. 11–52) | CER 0.72%, F1 0.931, headings 0/3 | CER 0.41%, WER 0.25%, F1 0.946, headings 3/3; 389 suspects: 179 fixed, 148 review |
| Goede dochter (ch. 1–4, pp. 9–64) | CER 0.40%, F1 0.957, headings 0/4 | CER 0.23%, WER 0.23%, F1 0.973, headings 3/4, italics 0.977 / 0.841 |
| Vals alarm (whole book; full pipeline pp. 11–60, ch. 1–10) | CER 0.74%, F1 0.918, headings 0/48 (with the quote rule) | CER 0.47%, WER 0.18%, F1 0.950, headings 10/10 |

`--no-models` scores headings without the role model, so 0/n there says little:
compare headings on full runs.

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

1. **Error budget.** Settle Goede dochter's verdicts (pp. 9–64; 34 to answer
   in `golden review`), then sort the remaining errors by category (quotes,
   punctuation, letters, paragraph breaks, headings) and work on the biggest.
   Stella has no headings: don't assume headings are where the errors are.
2. **Measure what the human experiences.** The product is errors left after
   review against questions asked. Report unflagged errors per page at fixed
   question budgets (0.25, 0.5, 1 per page), with bootstrap error bars over
   pages; claim no gain inside them. Turning silent errors into flagged ones is
   a win even when CER stays flat.
3. **glm-ocr's logprobs.** Ollama 0.40 returns `logprobs`/`top_logprobs` for
   glm-ocr in `/api/generate`: a confidence per token of every reading and the
   runner-up where it was unsure. Flag low-margin tokens even where all
   readings agree (shared errors). No new runtime needed.
4. **Re-bench OCR models on modern Dutch** (Goede dochter line crops): glm-ocr
   was chosen, and vision models judged to modernise, on the 1909 Teirlinck
   bench in pre-reform spelling.
5. **Golden books as training data.** Align each scan with its reference word
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
9. **Run Stella through the current pipeline now and then**: its `stages/`
   holds only `textlayer.json` and `document.json`.
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
