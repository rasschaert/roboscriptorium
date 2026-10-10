# Checklist

The plan: what is left, in the order it runs, with who does it and how long it takes.
Every step is the machine's unless it says **user**. A time is an estimate until the run
is timed through `experiments/timed.sh` ([run-times.md](run-times.md)); then the measured
time replaces it. A step done moves to [Done](#done), one line with its date and the
number that settled it; the numbers behind it are in [decisions.md](decisions.md). A
dropped step stays there, struck through, with why. Updated in the same change that
plans, ticks or drops a step. Cite a step by its words: the section numbers are
positions and get renumbered.

Where the build stands and where results can still move: [outlook.md](outlook.md).
What runs right now and what waits on the user: `HANDOVER.md`.

**The plan now:** more training data from new golden books, settle the line-role trees,
then **Stella end to end with the user's review**, the target book, then Ex-minnaar. After them, the open
areas below in order, and the test set scored once at the end.

## 1. Running now

- [ ] Trust data for Thief-Taker and the five new golden books (`robo-newbooks`, waits for
      `robo-next`): ~567 pages, Qwen local, ~9–10 h; Kerk and Vuurspel for the record only,
      never trained on. Then the arbiter and trees retrained and both benches, rules and
      trees: **a new baseline**, not comparable with earlier runs (the sets changed).
      Check Doodskleed's unplaced lines (6.3%, likely its running heads)
- [ ] The `bughunt` branch benched against that baseline (`robo-bughunt`, waits for
      `robo-newbooks`): its trust data rebuilt warm and its arbiter retrained apart from
      main's (`work/probes/ocr-trust-bughunt`, `work/models/bughunt/`: the arbiter's
      `known` feature changed meaning), both benches with the rules' line roles. ~1 h.
      Merge if no book is vetoed

## 2. Right after the chains (~1 h)

- [ ] Line roles by trees on by default if their bench holds. On the longer slices: tuning
      **better** (breaks 0.33 → 0.32, words 0.54 → 0.52), validation no change (0.75 →
      0.68, Villa Toscane 0.12 → 0.06); 11/22/63, De cipier and Reis better, but
      **Thief-Taker 0.47 → 0.97**: find why first, then Crime p. 97 and De cipier p. 49
      (last lines dropped) and You're Never Weird's +3 spurious headings
- [ ] De tuin, if it still loses after the retrain: the four questions no longer asked on
      pp. 15, 23, 43 and 46 (local re-read, 0.77 → 0.85), what the arbiter gave them
- [ ] `ROBO_OCR_ASK_BELOW` at 0.7, 0.8 and 0.9 on the retrained arbiter (warm, ~2 min
      each); **user** weighs questions against wrong words

## 3. Stella, the target book

- [ ] **user** Agree what "done" means (outlook's proposal: under 0.3 wrong words a page
      after review, under 1 question a page, headings and paragraphs right, epubcheck
      clean). 5 min
- [ ] Build Stella with today's build (cold for the new crops and readings, ~1 h for 67
      pages); sample the questions before sending the reviewer (never obvious ones)
- [ ] **user** Review Stella: its 68 old answers stand, so only new questions; ~30–60
      at today's rate, ~30 min
- [ ] Rebuild, epubcheck, and **user** reads the EPUB through: what the bench can't see
      (layout, italics, front matter)

## 4. Ex-minnaar, the second book

Herman Brusselmans, Ooievaar 1998 (sixth printing), the user's own pick, no reference
EPUB. `work/ex-minnaar/`: the IA Scribe scan with its own hidden layer (Stella's format,
284 pages, body 9–279) and, beside it, an OmniPage OCR of the same scan (`omnipage.pdf`,
worse: the motto's "It's" reads "h's").

- [ ] Build it like Stella once Stella is done; sample the questions first. ~4 h cold
      for 271 pages
- [ ] Whether OmniPage earns a place as another reading (it fails differently from the
      layer); only if the questions show the layer and readers stuck together
- [ ] **user** Review, rebuild, epubcheck, **user** reads the EPUB

## 5. The reviewer's time

- [ ] The book teaches itself: after the answers, a per-book posterior per substitution
      pair rescores the unasked suspects; on the review page, one question per pattern
      (every `|` read as I) applied to all. Simulated: silent errors at .25/.5/1 a page
      over nine books 50/31/11 → 47/30/11. ~half a day, then `bench`
- [ ] The 15 line-end hyphens reflow still gets wrong, as a question on English books
      only (a break the word list is silent on whose parts are both words: 13 right, 3
      wrong; 0 against 44 on Dutch). ~2 h
- [ ] A typed answer checked against Qwen's cached reading of the line where the question
      had no readings (headings, missing text). ~1 h

## 6. Errors no question asks about

- [ ] De eerlijke vinder's 1.02 unasked a page, the most of any ordinary book (words 26,
      letters 21, extra words 18): find where they come from. ~1 h, no models
- [ ] Bad pages by the readers' disagreement: a page whose suspects per line far exceed
      the book's (Afscheid p. 20: 50 against ~8) flagged, and as an arbiter feature.
      ~2 h, then `bench`
- [ ] A reader of the finished text, for errors every reading shares or reflow makes:
      a stronger proposer (Qwen3.8 thinking, or gemma4:26b) with clef as the filter, on
      Goede dochter's and Metro's built text. Guards: it only asks, in closed kinds; told
      the text is a transcription; measured silent on a counterexample set first (You're
      Never Weird's play on spelling, fragments, foreign words). The first probe found
      ~4 real errors among 56 flags; clef's filter kept both clear catches and dropped 31
      of 37 urges. ~2 h probe; a stage only if `bench` says so

## 7. Structure

- [ ] Score scene breaks: derive keeps a reference's blank-line paragraphs and ornaments
      as a break mark, counted like paragraph breaks. ~2 h
- [ ] Footnotes into the EPUB as notes, out of the running text: Reis has them and the
      test set has 26, now only left out of the score (`notes.txt`). Before the test set;
      ~half a day
- [ ] De eerlijke vinder's part numerals I–IV (0/4): read from the drawing
- [ ] You're Never Weird's headings (5/16: bracketed sections, "- 1 -" numbers) and p. 47's
      picture text read into the body
- [ ] Dolittle's captions scored: derive them into the reference, or leave caption lines
      out of the score as footnotes are

## 8. Better pixels: Internet Archive's own files

Public on public-domain items only (Crime, Dolittle); private on lending-library items.

- [ ] Readers on the page images (`experiments/probe_ia_images.py`, ~15 min): reader set
      v1's Crime and Dolittle lines cut from the JP2s, read by Qwen and glm-ocr. A win
      makes the JP2s the image source where a book has them
- [ ] ABBYY's letter confidence as an arbiter feature: first check the PDF's layer is
      ABBYY's reading, then does a low one separate the real errors? ~1 h, no models
- [ ] `_scandata.xml` page types as labels for page classification (public on every IA
      item). ~30 min
- [ ] **user** Whether a borrowed item's `_jp2.zip` can be downloaded while on loan

## 9. Beyond the golden books' kind

- [ ] Page classification, so `body_pages` needn't be set in book.toml: the page-type
      models so far miss the same pages (prefaces, blanks at the edges); start from the
      scandata labels above
- [ ] An image-only scan through the whole pipeline (Goede dochter with its layer removed:
      tesseract 0.35% CER against the layer's 0.20%): does the OCR check close the gap?
      ~1 h cold. Then italics from tesseract's word boxes

## 10. Golden books and housekeeping

- [ ] **user** More golden pairs: modern English Scribe scans with the publisher's EPUB of
      the same printing, and a third Dutch validation scan
- [ ] **user** Settle verdicts on the tuning books (`golden review`), the disagreements
      the arbiter's labels sit on first: hours, spread out, whenever convenient
- [ ] The pair prior's own ablation (an empty table, retrained, both benches): it shipped
      inside the arbiter unbenched on its own. ~20 min
- [ ] Training code for shipped models (trust, trees) into the package, with a
      feature-count test
- [ ] Remove the `baseline` and `qwen2` worktrees when convenient

## 11. At the end

- [ ] Score the test set once: `bench test --score-test`

## Later

- [ ] Qwen on fewer lines (quote marks, disagreements), for speed: only if cold runs
      become the bottleneck (a new book's ~100 pages take ~2 h)
- [ ] MiniCPM-V 4.6 as a faster reader: the readers already cover nearly every line, so
      it pays only by speed
- [ ] Surya's layout model as a second spotter: screen it on the drawn numerals
      DocLayout-YOLO misses and the figure pages
- [ ] Block quotes, epigraphs and verse: find golden pages that have them first
- [ ] Per-book image tuning for pale or tinted scans: null on normal pages so far
- [ ] Het Kindeken Jezus as a golden book, only if the image probe looks
      language-dependent
- [ ] `golden check <pdf> <epub>` writing a draft manifest, once a batch of candidates comes
- [ ] French, the user's idea (2026-10-09), undecided: it brings its own typography
      (« », a thin space before `; : ! ?`, dialogue dashes) that `quotes.py`,
      `typography.py` and the arbiter's training data would all need, and Gallica is
      mostly older print. If it comes: one French Wikisource book proofread page by page
      against its scan, held out like the test set. Proposed first instead: count the
      accent errors Dutch already leaves unasked (`knieén`, `hé` for `hè`, lost stress
      accents, Stella's `scenes`), by book

# Done

By area, newest first within each; one line a step. Dates and numbers are as recorded in
[decisions.md](decisions.md) on the day.

## Measurement

- [x] 2026-10-10 Longer tuning slices, each ending on a chapter (Goede dochter 9–162, Reis
      whole, De cipier 9–174, Metro 7–162, De tuin 11–122): 446 new pages in 7.5 h, arbiter
      and trees retrained; tuning 0.53 → 0.53, validation 0.77 → 0.76, no change. The
      pooled slip rate lowered "after review" a little everywhere (a measure, not a build
      change); the quote questions' new readings changed nothing the bench counts
- [x] 2026-10-10 The bench books read again by the local Qwen (30,572 lines, ~9 h), trust
      data and arbiter rebuilt: tuning 0.56 → 0.56, validation 0.77 → 0.79, no change; the
      bench now measures the build Stella gets
- [x] 2026-10-09 The slip rate measured again on today's questions: 30 of 32 right (picks
      17/18, typed 6/7, roles 7/7); the bench uses the two reviews pooled, 10 of 100 (the
      user's choice), applied after the chains as the new baseline
- [x] 2026-10-09 The bench counts paragraph breaks set wrong, catches an error only at the
      question's place, counts a typed page as a question per line: tuning 0.48 → 0.56 on
      the same build, honest; prints headings and reports heading and paragraph-F1 changes
      beside its test (`bench.structure`); records the hosted share of each book's readings
- [x] 2026-10-09 The arbiter's sureness calibrated (isotonic), so 0.8 means 80% right
      whatever the retrain: no change by the bench, kept for the threshold's meaning
- [x] 2026-10-09 An error over a page break counts on the page holding most of it
      (Afscheid 5.03 → 0.24 after review)
- [x] 2026-10-09 clef's cached answers stand for fresh ones: judge set v1 re-asked, 2 flips
      of 518, both at confidence ≤ 0.1
- [x] 2026-10-09 Retirement signals per book in the bench (`golden/signals.py`: layer CER,
      unplaced body lines, a suspect named)
- [x] 2026-10-08 Judge set v1 frozen (518 settled suspects, 25 wrong and 25 right a book);
      reader set v1 (550 lines, 30 the layer reads wrong and 20 right a book);
      `experiments/tryout.py` screens a candidate for a role against the incumbent
- [x] 2026-10-07 `roboscriptorium bench`: pinned slices, one JSON per run, paired page by
      page; one primary test with books weighing the same and a per-book veto; the
      reviewer's slips counted; leave-one-out trust models for tuning books; a missing
      or stale trust model stops the build; `eval` records decider, settings and model
      digests; long runs timed into run-times.md; design.md and decisions.md started

## Golden books

- [x] 2026-10-10 Sets changed (the user's go): De kerk van de dode meisjes and Vuurspel
      validate; De tuin, Het heft in eigen hand, Doodskleed and Het ijzige land tune.
      Derive learns `capital_classes` and a spaced `--` as the print's dash. Rejected:
      Cavendon Hall, Alsof het niets is, Het spel van de engel (EPUBs made through Word or
      OCR); De stilte van de hel kept unused as Vuurspel's sibling
- [x] 2026-10-10 ~~The five tuning books whole~~ dropped (the user): more pages of books
      already trained on add the same errors again
- [x] 2026-10-09 Internet Archive's own files fetched by manifest (`[scans.ia]`): Crime and
      Dolittle. Five public-domain Dutch Scribe items pair with Gutenberg (Het Kindeken
      Jezus, David Malan, …) but all in pre-1934 spelling: none taken
- [x] 2026-10-08 Grand Hotel Europa and Lady into Fox retired to reserve (another printing;
      a reference unlike its print in typography); De eerlijke vinder and You're Never
      Weird into validation; Metro, De cipier, Artemis, 11/22/63, Afscheid and Reis into
      tuning; Het geluid van bananen frozen as the test set
- [x] 2026-10-08 `experiments/probe_candidate.py`: a no-model check of a scan and EPUB
      pair; known deviations tracked in the manifest, the fold or a verdict, nowhere else
- [x] 2026-10-08 Hosted clef as the judge, measured against criteria fixed first: fails all
      three (PrimeIntellect hardly reads the image; Cloudflare 96.2% the same pick, fewer
      right), so clef stays local

## Trust data and the arbiter

One book per run, `experiments/ocr_trust_data.py --rebuild <book>`; about 1.1 min a page
cold, Qwen's reading 70–75% of it. Per book: suspects, settled (a clear label), and how
many the layer had wrong.

| Book | Pages | Suspects | Settled | Layer wrong | Note |
| --- | --- | --- | --- | --- | --- |
| Goede dochter | 9–64 | 419 | 377 | — | Qwen readings cached by the line bench |
| Vals alarm | 11–60 | — | — | — | its lost full stop is in no other book |
| Crime | 94 pages | 262 | 231 | — | relabelled with the score's fold |
| Dolittle | 23–88 | 684 | 570 | 396 | |
| De tuin | 42 pages | 473 | 455 | 350 | |
| Grand Hotel Europa | 30 pages | 173 | — | 99 | retired since |
| Stella | 5–71 | 66 | — | 34 | labelled by the user's answers only |
| Metro 2033 | 7–111 | 835 | 745 | 222 | the crop fix's clear gain |
| Artemis | 13–80 | 317 | 273 | 207 | its `\|` for I |
| 11/22/63 | 15–94 | 357 | 319 | 188 | three runs: Ollama stalls |
| De cipier | 9–92 | 429 | 327 | 97 | |
| Afscheid | 9–70 | 266 | 240 | 88 | |
| Reis om mijn schedel | 11–110 | 480 | 363 | 94 | |
| De eerlijke vinder | 12–95 | 895 | 829 | 85 | validation |
| You're Never Weird | 13–94 | 317 | 283 | 87 | validation; clef right on 268 |

- [x] 2026-10-09 imajev-4b as a third judge: trust data with its votes, retrained, no
      change (tuning 1.02 → 1.01, validation 0.81 → 0.80); off. Page types 19/23 like
      clef-flash, body ends 227 against 231: `body_pages` stays in book.toml. Which way a
      plate is up: 10/10, the candidate for plates without a caption
- [x] 2026-10-09 Qwen's third reading stays: without it tuning 1.00 → 1.33, validation
      0.81 → 1.01. Short lines stay. Qwen's second look at 450 dpi as a trust feature: no
      change, branch `qwen-second-look`. Washed-out pages left out of the check (`faint.py`),
      the arbiter's ≥ 0.8 suspects not asked (`ROBO_OCR_ASK_BELOW`): questions halved
- [x] 2026-10-08 winnow-ollama:e4b as the second judge (right alone 285/208/265 on three
      books against Ollaya's 174 each); Ollaya stripped; trust data re-asked for 14 books,
      retrained, bench no change (1.00 → 1.02)
- [x] 2026-10-08 The substitution-pair prior (`trust.pair`, model version 3): silent errors
      at 0/.25/.5/1 questions a page [153, 87, 44, 23] → [110, 48, 25, 10], leave one book
      out; the trainer uses only data that exists and has every reading, never trains on
      validation books
- [x] 2026-10-08 The retrained arbiter against the fixed rule: after review 1.37 → 1.00,
      eight books better, none worse. Metro's veto before it was its spaced ellipses,
      fixed book-wide by `typography.py` (4.63 → 0.43)
- [x] 2026-10-08 The crop bug: a line's crop reached into its neighbour's box on up to 97%
      of lines (Metro); `crop_span` stops at the neighbour. glm-ocr on Metro's changed
      crops CER 1.87% → 0.29%; every book re-read and rebuilt, Metro the clear gain, the
      rest neutral. ~~An ink-fitted crop~~ tried, not adopted: the readers read no better
      from it. ~~A reading far off its line's length counting as none~~ dropped: readers
      stray on 1 line in 958 since
- [x] 2026-10-08 Faster readers screened: gemma4 8B (quote marks wrong), qwen3.6 MoE (wraps
      narration in quotes), gemma4:26b MoE (reads whole other lines on Metro): all out; the
      failed MoE models deleted. On Goede dochter and Metro only 1 line in ~1,000 has no
      current reading right: the errors left come from choosing, not from missing readings.
      Local and hosted Qwen interchangeable (same reading on 97.6%). ~~winnow:12b~~ dropped
      with Ollaya

## The reviewer

- [x] 2026-10-09 Quote questions offer the OCR-checked line, Qwen's marks on it (quote
      marks only, no dashes) and the nested-quote combination: 3 of 4 now offer the right
      line, where none did
- [x] 2026-10-09 A lost line as a question (`lost-line`), scene breaks in the EPUB
      (`break_before`, unscored), budget diagnostics in shuffled order
- [x] 2026-10-08 Answers checked before they are saved (`review.doubtful`): a typed line
      matching no reading, or a straight quote in a curly-quoted book, is queried once;
      warnings logged. The review page tints the line and underlines the place, nothing
      drawn over the letters
- [x] 2026-10-08 A reader of the finished text, probed: gemma4 flags 56 on 200 paragraphs,
      ~4 real; clef as the filter keeps both clear catches and drops 31 of 37 urges. The
      proposer is the weak part (open step above)

## Structure and line roles

- [x] 2026-10-09 Line roles by trees (`sorter.py`, `ROBO_SORTER=1`, off): role errors
      406 → 152 tuning, 77 → 29 validation leaving one book out; bench no change, three
      books clearly better, Crime one lost line
- [x] 2026-10-09 Paragraph starts from a page margin fitted on full lines: breaks set wrong
      −28% tuning, −34% validation, the second review's one clear win
- [x] 2026-10-09 Headings: 11/22/63's numbered sections 5 → 23 of 24; Villa Toscane 0 → 12;
      De cipier 3 → 4; Afscheid's misread numerals 8 → 11 (`numeral-slot`); Artemis's
      circled numbers 0 → 3 (`missing.py` reads five lines above a sunk page)
- [x] 2026-10-08 Line-end hyphens by evidence in order (the book's spelling, the word
      list, a capital, the parts beside an inner hyphen): wrong 29 → 15 of 1,574
- [x] 2026-10-08 Italics measured against Metro's print: the print sets every station
      name in italics, the eBook two; marked unscored (`italics_unlike_print`)
- [x] 2026-10-08 PP-DocLayoutV3 as the spotter: worse downstream (Dolittle CER 1.22% →
      1.71%), not adopted. ~~A crop reader on tesseract's boxes~~ dropped: an image-only
      scan's layer is tesseract's already
- [x] 2026-10-08 tesseract's first reading of an image-only PDF (`pdf.first_reading`):
      Goede dochter without its layer 0.35% CER against 0.20%

## Reviews of the build

- [x] 2026-10-09 Fable's second review: what the bench couldn't see and leaks in the OCR
      check, each change benched alone; the ledger of probe against verdict is in
      outlook.md
- [x] 2026-10-09 Strict review of the codebase: six reviewers, every finding checked,
      fixes with tests in seven commits; trust data rebuilt, tuning 1.00 → 0.96,
      validation no change. Qwen's read prompt (five variants) and crop (dpi, upscale,
      contrast, sharpen, margin) can't be improved: each fixes as many lines as it breaks
