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

**The plan now:** the codebase review's steps first (the user, 2026-10-13: bug fixes
first, no urgency in building books), then accuracy from what the bench data shows,
new suspects where the readings agree first, then **Stella end to end with the user's
review**, the target book, then the user's four books. After them, the open
areas below in order. Each new pair is scored once, at its first look, before it joins
a set.

## First, after the slice growth (the user, 2026-10-17)

The weekend's order (the user left it to the agent): each step feeds the next.
1. Saturday ~20:00, the queue ends: the context-judge probe starts on its own (qwen3.8,
   ~3 h). Beside it, on cached data: `bench quick` as the tier's baseline, then the
   merges, the role trees and the arbiter retrained on the long slices, all benches
   (quick, tuning, validation): the quick tier's first check.
   Between the two stages: the error categories (below), from stage (a)'s saved errors.
2. Saturday ~23:00 to Sunday ~13:00 (`robo-first-look-reads`): the first-look slices
   read, no scores: Het geluid van bananen, Het schaduwhuis, Steve Jobs, De geruchten,
   Verminkt whole (tuning-bound books first).
3. Sunday 10:18: the first looks scored once (decisions.md, 2026-10-18). Next, once
   `robo-w12b` and `robo-cj-bench` are done (they compare against stage (b)'s sets):
   the books into their sets (Het geluid van bananen and Het schaduwhuis to tuning:
   Stella's publisher and scan, the stress accents and "wc" the arbiter must learn; De
   geruchten and Verminkt to validation), their trust data with Winnow-12B as the
   text judge (it passed its benches), the arbiter retrained on the larger tuning set, benches. If
   the context judge's bench passed, it as a stage after the arbiter, benched on
   tuning. Steve Jobs scores no words (the user, 2026-10-18): its photo insert stays line-role
   training.
4. De geruchten's section headings (a narrator's name in capitals mid-page, "DOLF"):
   0 of 21 found. A validation book, so not chosen on: the next tuning book that sets
   headings so teaches it, or a probe of what the trees see on those lines.
5. Au pair is tuning (2026-10-19, after its first look); its trust data and the line roles'
   training on De laatste roker (`sorterdata.EXTRA`, its manifest and reference first; the
   user's files were placed only for Au pair) wait for the next trust rebuild.
6. De vergelding's, Glazuur's and Vanille en andere smaken's first looks (slices 9–107,
   11–101 and 9–79, now the first-look set): their reading runs overnight 2026-10-19 (~2 h,
   2 h and 1.5 h, cold), then `bench first-look --first-look` scores the three once each,
   their scores go in decisions.md, then each joins a set. Done 2026-10-20: De vergelding and Glazuur tuning, Vanille validation (no trust data for the first two yet).
7. Trim the sets (the user, 2026-10-18: "trim the fat"; after tonight's benches, batched
   with one retrain and new baselines). Done 2026-10-23: Afscheid's paragraph breaks
   unscored (`breaks_unlike_print`); The Nature of a Crime out of tuning and quick, but
   kept in the arbiter's training (without it: unasked fixed 7, made 16); Dolittle's
   quick slice kept (every line places; its layer is poor, not another edition). Na die nacht
   held back, not retired (the user, 2026-10-23: its files kept, `bench.RESERVE`). Left: Het
   laatste bevel's glued words as verdicts (the user's time). Verminkt sliced to 7–100 (2026-10-23,
   `scoring.cut_to_pages`).
8. The next set review (AGENTS.md, "Reviewing the sets"): after the four waiting pairs'
   first looks, by 2026-10-25 at the latest; the gaps in docs/golden-notes.md go to the
   user as the books to look for.

- [ ] No fixed test set: a first look for every new pair (the user, 2026-10-17: soon,
      ahead of other accuracy work). Validation wears out as changes are benched and
      some decided on it; one test book is a sanity check, not an exam. Each new pair
      gets one untouched score on a slice (~90 pages, ending on a chapter) before
      anything is chosen or trained on it, then joins tuning or validation. Code
      (branch `first-look`, agent ~1 h): `bench.SETS["first-look"]` replaces "test", its
      guard (`--first-look`) refuses every eval, review, probe and trust data on such a
      book, `bench first-look` scores and saves it; design.md's reason. First looks
      (one night, ~14 h): Het geluid van bananen, Het schaduwhuis, Steve Jobs (its
      words; its roles trained the sorter, so its role scores aren't a first look), De
      geruchten, Verminkt whole. Na die nacht is held back (a sibling of two
      tuning books; `bench.RESERVE`). De tunnels stays role training (an EPUB that can't score
      words). New pairs the user finds go through the same flow
- [x] Error categories tracked per run (2026-10-17): 16 causes read from an error's two
      sides alone (`errorlog.cause`), chosen from stage (a)'s 618 saved errors across 23
      books; each run's record keeps them by book, `bench` and `bench-diff` print each
      before → after with its interval. "Reference fault" isn't one: a verdict settles it
- [ ] One more reader? Taking readers away costs the most of any block (without qwen3.8
      silent errors 12 → 75 at a question a page; `probe_subtract.py`), so adding one
      may pay where nothing else reaches: layer errors no reader doubts. Measure on the
      frozen reader set's hard lines the errors a candidate reads right where every
      current reader is wrong ("unique catches"); dropped if it adds none beyond noise,
      whatever its own score. Candidates: qwen3.8 with another prompt or crop, a vision
      model not yet screened. Locally in a gap (agent, ~1 h)
- [ ] Winnow subtracted? The context judge reads the whole paragraph where winnow reads
      the sentence, and on the asked suspects it beats the arbiter that weighs winnow
      (86% against 68% on the golden books). If the arbiter without winnow, with the
      context judge after it, benches no worse, winnow goes. Leave-one-out on the trust
      data with winnow-ollama:e4b (2026-10-17, no models): silent errors at
      0/0.25/0.5/1 questions a page 148/54/24/12 with it, 151/58/25/16 without: small,
      every budget the same way, within a book's noise; Winnow-12B, a sharper alarm,
      may weigh more. Next: an arbiter trained without winnow under its own name,
      `bench tuning` and `validation` warm with `ROBO_CHECK_MODEL=` against the
      Winnow-12B runs (cached, no model calls; agent, ~1 h). The word list's vote goes
      in the same bench: taken away it changes nothing (`experiments/probe_subtract.py`),
      the arbiter reading the same knowledge from the `known` feature
- [ ] A context judge (the user, 2026-10-17: "if it cuts down on questions being asked
      in human review, i'm for it"): probed hosted (the user allowed OpenRouter for its
      test): without each version's count in the prompt, it settles 220 of 336 asked
      suspects by agreeing with the arbiter, 17 of them wrong (8%, under a question's
      price); alone it never overrules (it overturns one in five right suspects). Built
      that way, off. The local qwen3.8 on 100 of them (2026-10-17): the same pick as
      hosted on 84, settling 66 with 8 wrong (12%). `bench quick` with it (2026-10-18,
      38 min): after review 0.30 → 0.26 [−0.07, −0.02], BETTER; questions 0.72 → 0.60 a
      page (book mean), fixed 24 wrong words, made none. Left: `bench tuning` and
      `validation` with it against the Winnow-12B runs (cold for the context judge,
      ~41 s a call: tuning ~3 h, validation ~1.5 h, overnight); on by default only if
      both hold

## Assumptions to test (quick probes, minutes to an hour each)

The pipeline reads lines and joins them by hand-built geometry because that was what
models could do. Each probe below asks whether that's still true, on a few golden pages
(tuning books), before any building. Record each result, null ones too.

- [x] Whole-page reading (`probe_page_reader.py`, 2026-10-13): Qwen 76 wrong words and
      32 breaks over 19 pages against the pipeline's 27 and 7 (letters doubled at page
      resolution, dialogue paragraphs merged); glm-ocr near-exact on plain text pages at a
      third of the size, but invents text on near-empty and picture pages
- [x] glm-ocr whole pages at full resolution (2026-10-13): 103 wrong words over 18 text
      pages against the pipeline's 27, but right on 5 of the pipeline's 9 error places,
      nearly all line joins; it invents text on near-empty pages
- [x] glm-ocr's page reading as a reader (2026-10-13): right on 226 of 473 pipeline error
      places, but wrong on 910 where the pipeline is right: alone, four false questions a
      catch
- [x] Two page readers agreeing against the pipeline (2026-10-14): outside paragraph
      breaks, right 152 times to 65 (70%), about 0.7 places a page; breaks not trustworthy
- [x] The two readers' agreement on the errors left after review (2026-10-14): 60 errors
      no question catches (+21 unmatched), 71 asked already, 68 false: about a quarter of
      what's left after review, for ~0.3 questions a page
- [x] Build it (the user chose this way, 2026-10-14): `pagereader.py`, two more readers
      for the OCR check behind `ROBO_PAGE_READERS`, the arbiter keeping which readings
      it was trained on
- [x] Read the pages and train with them (2026-10-15, a night): `bench tuning` no change
      0.32 → 0.32, validation 0.50 → 0.43 after review but worse before it on two
      books; the page readers stay off as line readers
- [x] ~~A line no page reader has words for as a feature of the line-role trees~~
      (2026-10-16, dropped): the trees get the unread lines right but for 5 of 657; the
      line-role mistakes left (49 of 25,555) are on lines both readers read
- [x] ~~Both page readers' spelling of a line-end compound as evidence for a learned
      hyphen decision~~ (2026-10-15, dropped): with the judge's answers, as the build runs,
      the build is wrong on 19 of 3,184 line-end hyphens; the readers agreeing fix 9 and
      break about 6, under the bench's noise
- [x] Whole-page reading by the bigger build (2026-10-14): `qwen3.8:27b-mxfp8` 65 wrong
      words over 19 pages against the nvfp4's 76, mostly one page; 60% slower; not taken
- [ ] Whole-page reading with the page before as context, for paragraphs that cross a page
- [ ] The whole-page reading as one more reader: where it and the line readers differ,
      a suspect for the arbiter; how many of the undoubted errors it would have raised
- [x] Paragraph breaks by a model (2026-10-23, NOT TAKEN; `probe_page_breaks.py`): on 47
      tuning pages with a break error it fixes 53 of 78 wrong starts, but it sets 7 wrong
      on 47 clean pages (0.15 a page, against the reflow's 0.06 over all pages). The page
      image plus the pipeline's lines, "which lines
      start a paragraph?", against `reflow.indented`. A learned text table (quote after quote at
      the margin: 87 of 88 starts) did nothing, the tuning books having no unindented
      book (2026-10-16, `work/probes/parastarts.patch`); Vuurspel's unindented layout is
      rare (the user, 2026-10-17), so no pair is sought for it; the vision judge on line crops (±1 and ±4 lines) gains
      nothing over the lower-case check (2026-10-17): a page-level reading is what's left
- [x] Grow the seven short tuning slices (2026-10-17): read 10:28–17:55; trust data, role
      trees and arbiter retrained on them; validation 0.41 → 0.37 after review, tuning 0.30 → 0.30
- [x] `heading-pairs` and `number-lookalikes` merged (2026-10-17), the trees retrained on the
      long slices: Metro's headings 3/8 → 8/8; extra text 1.08 → 0.63 a page on tuning
- [ ] Line roles by Qwen from the page image (text, heading, running head, page number,
      caption, picture), against the rules and the trees. **Probe 2026-10-23: a strong signal**
      (`probe_page_roles.py`, 208 tuning pages, half holding a heading, certain labels only):
      5,993 lines, the pipeline 22 wrong and Qwen 3 (three datelines called headings);
      headings found 126/126 against 110, 3 false. 25 s a page. Next: the short answer
      (heading and furniture numbers only, queued), then Qwen's call as an input to the
      role trees over every tuning page, benched
- [ ] The text layer as a second reader only: the page built from the whole-page reading,
      the layer and the line readers judging where they differ
- [ ] Page kinds for `init` (cover, front matter, body, back matter) by Qwen from the page
      image, on `tryouts/page-kinds-v1.json`
- [ ] **Per-book settings and extra witnesses** (the user, 2026-10-22: do some books respond
      better to some settings, and can a quick pre-pass tell which?). Evidence so far: qwen at
      300/450/600 dpi on 50 lines of each of 16 books differs by 1–4 lines per book, noise
      except perhaps Reis om mijn schedel (45 → 49) and Artemis (50 → 48); the cold `bench quick`
      at 450 dpi fixed more than it made in De tuin and De eerlijke vinder, the reverse in
      Dolittle and De cipier. One page can't show it (about 0.2 wrong words a page), and an
      unknown book has no reference to score against. In order, each a cheap test first:
      The first two steps share one list of variants: read each variant once over the reader
      set's 850 lines, then score it both ways (its agreement, and its vote gain as a witness).
      - [ ] Does *agreement* predict the right setting? On the golden books, per setting
            (dpi, contrast, crop padding, prompt wording) the share of lines agreeing with an
            independent reader; does the setting with the most agreement score best on the
            reader set? No models beyond the readings already made for dpi; contrast, crop and
            prompt variants need one reading each of the 850 lines.
      - [ ] Variants as extra *witnesses* for the vote simulation, not a choice: contrast
            stretch, tighter and wider crop, a second prompt wording, each through
            `vote_sim.py`, then on the lines no reader flags (as
            `probe_dpi450_alone.py` does): the frozen set is 60% hard lines, so its vote
            gain overstates a witness that only helps where the arbiter already looks.
      - [x] ~~The 450 dpi qwen reading as an extra arbiter reader~~ (dropped 2026-10-23):
            right alone on 0 of 57 quiet lines where it differs, and the 2026-10-09
            bench of the same second look found no gain.
      - [ ] Token probabilities of a reading (Ollama's logprobs) as a per-line confidence,
            calibrated on the reader set; does it rank wrong readings below right ones better
            than the readers' disagreement does?
      - [ ] Only if the first shows a signal: a per-book pre-pass (20–30 pages through the
            variants, the setting with the most agreement kept), learned from the golden
            books' fingerprints, not a hand-written rule.

## Ideas from the deep-research reports (2026-10-23)

The user handed the research brief (`work/research-brief-2026-10-23.md`) to several
deep-research models (DeepSeek, Claude Fable, Google Argon; their reports are with the
user); each idea is checked against what was already measured before it goes here.
Where they disagree it is noted, for the user to pass back. Ordered by what the probe
costs against what it could reach; every reader candidate passes the new-model gate
(HANDOVER, "When a new vision model appears").

- [ ] Crops padded to the vision encoder's grid instead of resized (Argon): Qwen's image
      processor rounds a crop's size to its patch grid by resampling, which may blur a
      two-pixel accent or comma. Check Qwen3.8's patch and merge size first, then pad the
      frozen set's crops with paper colour to an exact multiple and read them again;
      compare per stratum and on the six accent lines (agent, ~30 min of qwen)
- [ ] Small capitals from the descender band (Argon): a word read with g, j, p, q or y but
      no ink below the line's baseline is set in small capitals ("app" against "APD"),
      measured on the scan's binary mask or the rendered crop. No models: of the 31 case
      errors on tuning, how many the test finds, and how many right words it flags (agent, ~1 h)
- [ ] Book-wide consistency for diaereses and letters outside ASCII only (Argon's narrowing
      of the null above): the same probe, flagging a plain reading only where the book
      prints the word with ë, ï, ı, ł, ç … and never for acute accents, which vary by
      emphasis (agent, ~15 min, no models)
- [ ] A per-book character recogniser with no language model, as a witness that fails
      differently (Fable's first idea, Argon's fourth; DeepSeek advised against): Calamari or
      Kraken trained on golden line crops leaving the book out, then fine-tuned on the book's
      lines every reader agrees on (no suspect touching them), a 5-fold ensemble voting on
      character confidences. Judged by the vote simulation on the frozen set: how many of the
      hard lines it reads right where every current reader agrees on the wrong reading.
      The reports' gains (46%, 70–78% over ABBYY) are on early print with far higher error
      (agent, ~1 day; installs asked first)
- [ ] Image-gain as a silent-error signal (Fable): each qwen and glm-ocr token's
      log-probability with the crop against without it, one extra text-only pass; a low gain
      marks a token from the language prior. AUC on the frozen set's silent errors. Argon
      proposes raw runner-up tokens instead (`top_logprobs`, no extra pass) and DeepSeek
      neither; measure both from one run (agent, ~2 h)
- [ ] Two-line crops at each line break as a decision for clef (Fable, Argon): the last
      words of a line and the first of the next as one image, "join or not, hyphen or not,
      comma or full stop", where a trigger fires (a line ending in a stop before a lower-case
      start, a join that forms a word). Targets the 109 unasked errors at line joins
      (agent, ~1 day)
- [ ] New OCR models as witnesses on the frozen set (Fable, Argon): dots.mocr (3B, MLX
      builds), LightOnOCR-2-1B (reported to keep diacritics where Qwen3 drops them),
      Chandra OCR 2 (5.3B), HunyuanOCR (1B), PaddleOCR-VL-1.6. No Dutch accent test exists for
      any; downloads over 1 GB asked first (agent, ~1 h each)
- [ ] Qwen faster on the same output (DeepSeek, Fable, Argon): prefix caching of the fixed
      prompt, batched decoding (mlx-vlm, vllm-mlx), speculative decoding with the text layer
      or glm-ocr as the draft (lossless under greedy decoding); readings must stay identical
      on the frozen set. Speed buys the page-level role pass everywhere (agent, ~1 day)
- [ ] Review: identical questions batched into one card, and same-page reference crops
      (this printer's comma and full stop, a plain i and an accented vowel) beside each
      punctuation, accent or small-capital question (Argon); answers propagated to every other
      occurrence of the word (Fable). The user's time: a design, then the user's say
- [ ] Speck labels harvested from the golden pairs (Fable, Argon): every reader's character
      absent from the reference, aligned to an ink blob, is a speck; every mark the reference
      confirms is ink. Labels from all 30 books for the speck classifier (agent, ~1 day)
- [ ] Line-end compound hyphens learned from the compounds the books print unbroken mid-line
      (Argon): self-supervised, for the 24 of 27 the book itself can't settle (agent, ~half a day)
- [ ] Glyph-level checks, later (Argon's pairwise classifiers for confusable letters, Fable's
      glyph clusters with one label each): only after the cheaper glyph probes above
- [ ] Paragraph starts by a model that knows the book's indent regime (Argon), and heading
      tags from Granite-Docling-258M (Argon): after the page-level role pass, which already
      finds every heading in its probe
- [x] ~~Gated language-model scoring of words with a visual twin~~ (Argon's PLLR with
      RobBERT; Fable and DeepSeek against): parked behind the glyph and image-gain probes,
      which ask the scan rather than the language
- [x] ~~Constrained LLM post-correction~~ (all three call it low value at this error rate)

- [x] ~~Book-wide consistency as a suspect~~ (DeepSeek 5; NOT TAKEN 2026-10-23,
      `probe_book_consistency.py`): a word spelled one way once and a close variant three
      times or more flags 4,802 words over the tuning slices (3 a page), 34 of them errors;
      it catches 17 of 184 unasked one-word errors, about 6 of them real, the rest emphasis
      accents the print has and the reference drops, which it would remove
- [ ] The JBIG2 text mask as the image (DeepSeek 6, speculative, no report found of it
      working): crops of the scan's own binary mask, without the JPEG2000 layers, for the six
      known emphasis-accent lines and the small-capital ones, read by qwen; compared with the
      composited crops (agent, ~30 min)
- [ ] Questions ranked by expected errors fixed per second (DeepSeek 8; already in the
      outlook as untried): replay saved benches offline with the arbiter's probabilities and
      a severity per cause learned from the error logs, against today's threshold (agent,
      ~2 h, no models)
- [x] ~~Character-level ROVER with a diacritic-restoration vote~~ (DeepSeek 1, not taken
      on reading): suspects are already made at character level where any reader differs;
      the silent errors are where every reader gives the same characters, which a vote
      can't open, and a dictionary-driven accent restoration would invent Dutch emphasis
      accents, which are optional
- [x] ~~PaddleOCR-VL-1.5 as one more reader~~ (DeepSeek 2): screened 2026-10-20, unfit
- [x] ~~LLM post-correction under a learned edit budget~~ (DeepSeek 4, parked): only on
      the places the consistency test flags, if that probe earns it
- [x] ~~A small graph network for paragraph breaks~~ (DeepSeek 7, parked): learned, which
      fits, but tuning books set 0.06 breaks a page wrong; the weak books are validation

## Before the user reviews another book (2026-10-16)

What Ex-minnaar's first review questions showed. The user reviews only after these
(AGENTS.md, "The user's review comes last"); Ex-minnaar's review is paused.

- [x] Elision spaces (2026-10-16): our curling made glm's "nog 's" an opening ‘; now ’.
      Ex-minnaar glued elisions 9 → 3, apostrophe-only doubts 40 → 25; benches no change
- [x] ~~Small capitals read in lower case~~ (2026-10-16, dropped): cut at x-height in
      Ex-minnaar, and already read as capitals but for three "xm"; a reader hint for every
      book breaks more than it fixes
- [x] One OCR question per line (2026-10-16): whole-line options from every source,
      "Something else" from any option; benches better, questions fewer
- [x] Ex-minnaar's questions sampled again (2026-10-16): 234, sound; its review is the
      user's (restart the review server)
- [x] Misprints (2026-10-16): the review's `m` writes the book's errata; answers stay as
      printed, so the readers that read the misprint aren't marked wrong

## From the codebase review (2026-10-13, first)

The user, 2026-10-13: the review's bug fixes come first, then its bench and structure
steps; building Ex-minnaar and Stella has no urgency. The findings are in decisions.md.

- [x] One cold A/A rerun of `bench tuning` (2026-10-15): 0.32 → 0.33 after review
      [+0.00, +0.01], no book apart; rebuilding the caches moves the score 0.01 at most
- [x] Book-wide statistics on the whole body (2026-10-16): tried and reverted; a
      raw repeat count over 564 pages took a dialogue tag for a running head
- [x] The line-role trainer's data and saving into `src/` (`sorterdata.py`, 2026-10-16)
- [x] One cache helper (`files.read_cache`, `write_cache`) for the nine copies
      (2026-10-16): formats unchanged on disk, benches identical and warm
- [x] The judges' crop settings and the second vision judge's readout in their cache
      keys (2026-10-16): older answers stand for the crop they were made at, so nothing
      ran cold; benches identical
- [x] `ocrcheck.py` split into `readers.py` and `ocrdoubts.py`; one `roles.is_body`
      (2026-10-16, benches identical)
- [x] `reflow.py` split: joins and hyphens into `hyphens.py`, quote mending into
      `quotes.py` (2026-10-16, benches identical)
- [x] `typography.py` split: scan measurements into `scanstyle.py`, one `ink.threshold`
      (2026-10-16, benches identical)
- [x] Prune `experiments/` (2026-10-16/17): 53 scripts named only in the logs deleted
      (the user: results recorded, git keeps them), `probe_orientation.py` mended;
      AGENTS.md cut to rules and the map (manifest keys to golden-notes.md, model setup
      to models.md, the review page to how-it-works.md); decisions.md a heading a day
- [x] Line roles learned (2026-10-13): the trees are on by default after warm benches no
      worse on both sets (decisions.md); running-text and numeral-slot retired (2026-10-16,
      `probe_retire_rules.py`, bench no change); the other rules still earn their place.
      Next: a book with text wrapped around pictures for Dolittle's case
- [x] Trust data for the 20 books on qwen3.8:27b-nvfp4, then the arbiter and `bench
      tuning` (2026-10-12): 0.31 after review over 17 tuning books, Monterosso read whole
- [x] ~~FKA USA's fixes from its first bench (note marks as LaTeX, a dropped epigraph,
      a missing part heading)~~ (2026-10-13, dropped): the pair was retired as a suspect
      (30% of its body lines unplaced) and its files deleted
- [ ] A lighter feedback loop (agreed 2026-10-13; its two rules are in AGENTS.md): the quick
      tier is built (2026-10-17, `bench quick`: 15 tuning books, 10–25 pages each,
      282 in all, each ending where the next chapter opens a page); left: check that it
      ranks changes as the full bench does, by running it beside `bench tuning` before
      and after the post-queue merges (agent, minutes warm)
- [x] `golden derive` keeps text before a book's first heading (2026-10-17, `leading_text`):
      Normal People's reference and scan start on p. 9, its slice now chapters 23–31
- [x] A sampled review of Ex-minnaar (2026-10-16): false quote questions on Flemish
      ’m fixed (308 → 261 questions); its blanked place names ("het __plein") need one
      setting for the book (the user)
- [ ] Ex-minnaar's review by the user, then the fixes it teaches
- [ ] Stella rebuilt with those fixes and diffed against its dated copies in
      `work/stella/epubs/` (the user, 2026-10-12: not before the Ex-minnaar review)

- [x] The epigraph stage took noise for a motto (2026-10-16): a word of four letters is
      now required; benches no change

## 1. Accuracy before Stella (~half a day)

About 85% of the wrong words left after review were never suspects: every reading agreed
on them, so no judge and no question saw them. The rules have taken the groups with one
cause; what is left needs new suspects where the readings agree, which today's models
don't yet give at a price worth the reviewer's time.

- [ ] A detector for errors every reading shares (the user, 2026-10-12): a small model
      over every word, trained leave-one-out on the golden books' silent errors (word
      list, letter confidence of tesseract and IA's ABBYY, a smudge on the crop, the
      book's other spellings), raising suspects where the readings agree. Guarded
      against regressions: its suspects are only asked at first, never fixed
      unasked; it ships only when `bench tuning` improves with no book's veto and
      `bench validation` doesn't worsen, and the questions it adds are counted
      against the errors they catch. Labels first, from tonight's trust data (agent,
      ~half a day). Lost spaces: the word list alone is useless (9 errors to 4,417 right
      compounds, 2026-10-16); the gap at the split, measured on the scan, is the feature.
      Tesseract's confidence and accent variants: null too (2026-10-16); wait for a
      stronger reader (the ceiling probe) before building it
- [ ] A reader of the finished text (the proofreader), for errors every reading shares:
      probed twice, about one catch per 100 paragraphs against as many false questions
      (2026-10-11, qwen3.8 proposing, clef filtering): rerun the probe
      (`experiments/probe_text_reader.py`, ~25 min) whenever a stronger text model comes,
      build it only if the catches outnumber the false questions
- [ ] Smaller groups, by size, only where one cause covers several: quotes (~35 words;
      nested quotes need the book's own habit, learned from the book rather than assumed
      as the outer mark's opposite; De tuin sets “ alone 147 times), word breaks
      (~70, scattered), small capitals read in lower case (7, visual)

## 2. Stella, the target book

- [x] Stella's errors estimated against Claude's reading (2026-10-16): 4 wrong words in
      67 pages before review, 2 asked; 6 questions. Unasked: two words joined after a
      tight f ("grofwerk", "trofik")

- [x] Stella's review (2026-10-16): 6 questions answered, two accents corrected
      ("íéts", "ís"); rebuilt, epubcheck clean (`epubs/stella-2026-10-16-0859.epub`)
- [ ] **user** reads the EPUB through, noting each error with a few words around it; no spot-check (the read covers every page). Each noted error is fixed as an answer and checked against the build's suspects: was it asked, settled wrongly, or never a suspect ("Errors no question asks about"): what the bench can't see
      (layout, italics, front matter)

## 3. The user's books after Stella

Four Dutch books the user wants as EPUBs, none with a reference EPUB, each an IA Scribe
scan with its own hidden layer (Stella's format), in `work/<name>/` with a `book.toml`.
In this order:

| Book | Directory | Pages (body) | Scan | Watch for |
| --- | --- | --- | --- | --- |
| Herman Brusselmans, *Ex-minnaar* (Ooievaar 1998, 6th printing) | `ex-minnaar` | 284 (7–279) | 360 ppi | motto on p. 7 ("It's closing time", Leonard Cohen), set as an epigraph; drop cap; an OmniPage OCR of the same scan beside it (`omnipage.pdf`, worse: the motto's "It's" reads "h's") |
| Herman Brusselmans, *De kus in de nacht* (Prometheus 2002) | `de-kus-in-de-nacht` | 620 (7–616) | 300 ppi, large pages | parts ("Deel een", "Proloog" on p. 7), small-capital openings |
| Emmanuel Carrère, *Andere levens dan het mijne* (De Arbeiderspers, tr. Floor Borsboom) | `andere-levens` | 248 (9–244) | 360 ppi | library copy; French names and accents |
| Emmanuel Carrère, *Een Russische roman* (De Arbeiderspers, tr. Marianne Kaas) | `een-russische-roman` | 276 (7–271) | 360 ppi | library copy; seven parts, each a small number atop its own page (pp. 7, 47, 131, 169, 233, 259, …) with pencil marks the layer reads as noise (pre-check, no OCR check: part "1" read "I" and dropped as a page number; the marks kept as running text, "Fyarvin er pan ee Ka": see what the full build asks, then decide on a rule); p. 272 show-through only |

- [ ] Each book in turn: check its front and back matter and `body_pages`, build (cold
      ~1 min a page: Ex-minnaar ~4 h, De kus ~10 h), sample the questions, **user**
      reviews, rebuild, epubcheck, a **spot-check** (5 random pages drawn by a script,
      the **user** marks every wrong word, break and italic against the scan, ~15–20
      min: the book's own error estimate with its interval), **user** reads the EPUB
- [ ] Other editions as an error finder (the user, 2026-10-18): not a pipeline stage but
      an instrument for a book with no reference, so its errors are found and fixed by
      pipeline changes measured on the golden books. The built EPUB's paragraphs are
      aligned with the other editions' by length and by the names and numbers they share
      (1:1, 1:2, 2:1, and a paragraph with no counterpart); a thinking model reads each
      Dutch paragraph beside its counterparts and flags reading errors with their
      evidence, each flag checked on a crop (`experiments/probe_translation_check.py`;
      `work/probes/stella-editions/`). Stella, hosted (qwen3.8-27b on DeepInfra, German,
      Danish and English, ~$1.7 with paid cut-off calls): 46 flags, one reading error
      ("trofik", scan p. 53), one likely misprint for the user's errata ("de hete zomer",
      p. 7), the rest the translator's wording. Its recall, on 37 errors planted in Stella's text
      (`experiments/edition_recall_plant.py`, $0.14): 29 of 31 word errors caught, 0 of 6
      lost accents or diaereses; so the build is clean, not the check deaf. Accents need
      another instrument: the word list knows only some bare forms as non-words
      ("geergerd", not "financiele", "client", "loge"), and finds none in Stella. Next: the
      Carrère books (`work/<book>/editions/`, French and English, ~$3 each) once built
- [x] ~~Small capitals as a version for the judges~~ (null on its short test, 2026-10-20: decisions.md; branch `small-caps` unmerged; found by the edition check, 2026-10-19):
      Andere levens' one silent error is "LC1" for "LCI" set in small capitals, where no
      reading had the capitals; in the latest benches 18 errors are capitals read in
      mixed case ("vTM", "voc", "ocMw", "xTc", "cr" for CT), 7 unasked. The judges'
      prompt already knows the pattern but can only pick among the readings: add a
      reading's all-capitals form (letters only, 1 → I, 0 → O) as one more version where
      it mixes case inside a word, and let them choose. Upstream of the OCR check's
      caches: short test on the pages it touches, then a cold bench
- [x] Line-end hyphens inside hyphenated chains (done 2026-10-19, merged; 55 of 60 right on the chain probe, warm bench no change: decisions.md; found by the edition check):
      Een Russische roman prints a chant, "geen-verandering-in-de-toestand-van-de-
      patiënt", broken at its own hyphens ("in-de-" / "toestand", "van-" / "de"), and the
      build joins both as break hyphens ("in-detoestand-vande"), silently; the next line
      prints the chant whole. The latest benches hold five more, all unasked:
      "neem-jehuisdier", "doe-hetzelfbouwdozen", "muzieken-lichtshows",
      "topaasen-amberkleurige", "glas-inloodramen". A hyphen at a line end in a word that
      has another hyphen is mostly the word's own, but not always ("Noord-Hol-" /
      "landse"): give the joiner the chain as evidence (and the book's spellings of
      chain pieces), its counterexamples tested first
- [x] A Dutch word broken at its diaeresis gets it back when joined (done 2026-10-19, merged: decisions.md; low; found by the
      edition check, 2026-10-19): Dutch drops the diaeresis where it breaks a word
      ("democratieën" as "democratie-" / "en"), so the join must try the ë or ï form
      against the word list. Een Russische roman's became "democratie- en", taken for a
      word left open before "en" (`hyphens._suspended`, "voor- en nadelen"). True by
      definition, so code; no other case in the latest benches
- [ ] A comma at a line's end turned into a stop by the check (2026-10-20: decisions.md; the two arbiter features below were tried and NOT taken, tuning 0.29 → 0.30, glued or split words worse; look for another handle, or a rule true by definition): add
      "the next line opens in lower case" and "the span ends its line" as arbiter features at
      the next trust-data rebuild; 22 unasked errors in De vergelding and De kerk van de dode
      meisjes, 7 certain (a stop before lower case). Resolution doesn't help the readers.
- [ ] A per-book alphabet from the scan (the user, 2026-10-21; decisions.md has the assessment and the first test): glyph blobs from the line crop, clean ones (a third of lines) as labelled templates, then (1) can the dot of an i be told from an acute mark by shape against the book's own dots (the six real accent cases); (2) do odd glyphs (the dotless ı of "Sıla", five times in one book) cluster without labels, in about 30 questions a book at most; (3) as a detector over all glyphs, weighed by the arbiter. Kill after (1) or (2) if they don't separate.
- [ ] Lost lines mid-block read before they are asked (2026-10-20: a gap or ink rule can't find them, decisions.md; the reader must look at line starts and gaps; found by the edition check,
      2026-10-19): Een Russische roman's text layer drops whole lines inside a text block
      (p. 133 "te filmen terwijl jij uitstapt, of heb je liever dat de camera laat zien",
      p. 175 "raam te springen en jij lijkt niet veel meer mans dan zij, dus als je"),
      where `missing.py` doesn't look (it reads empty layout regions and a block's top and
      bottom strips). The gaps meet `flags._lost_lines`' rule, so they become questions
      the reviewer must type in full. Read each such gap with the missing-line reader
      first, so the question proposes the line (or it is trusted); confirm both pages
      are asked today, then count lost-line questions over the golden books
- [x] A footnote whose mark the layer misreads (done 2026-10-19, merged: decisions.md; its notes lost or made are still to count on the golden books with notes; found by the edition check):
      Een Russische roman p. 270's translator's note "*Erik Orsenna (1947)…" stays in the
      running text, spliced mid-sentence into the paragraph that runs on, because the
      layer reads its "*" as "“" and `footnotes._MARK` decides on the layer's text; the OCR
      check corrects the mark to "*" afterwards. Decide on the checked text, or take a
      quote glyph at a small-type foot line's start for a misread mark; then count notes
      missed over the golden books with notes
- [ ] What the pipeline should do with a PDF's embedded images (the user, 2026-10-19,
      when taking up Een Russische roman again: "have a good think"). Found: its
      washed-out pages (46, 47, 259) and Afscheid's (p. 32) are lost in the PDF itself:
      the JBIG2 mask holds speckle or letter outlines, the 120 ppi background grey
      smudge, so rendering the mask alone rescues neither (decisions.md, 2026-10-19).
      To think through, each a cheap probe first: (1) readers get the composited render;
      would the 360 ppi mask alone (sharp, binarised) read better or worse on ordinary
      pages (the frozen reader set)? (2) A washed-out page in the PDF may be fine in the
      Internet Archive's full-resolution originals (`_jp2.zip`, public on public-domain
      items, `golden fetch` already takes them; a lending item's reader serves them to a
      borrower): fetch and read those pages instead, and say so in the review rather
      than asking the reviewer to type guesswork. (3) Whether `faint.py` should say
      "lost in this PDF" against "faint in print", and what the review offers for each
- [ ] Ex-minnaar: whether OmniPage earns a place as another reading (it fails
      differently from the layer); only if the questions show the readers stuck together

## 4. The reviewer's time

- [x] The book teaches itself, first half (2026-10-16): a book's answers join its
      arbiter's substitution table (`trust.with_answers`); Ex-minnaar's review showed the
      signature (wc, stress accents, ’s)
- [x] The book teaches itself, second half (2026-10-16): one question per pattern,
      replayed on Ex-minnaar's answers (`probe_patterns.py`), saves 12–17 of ~140
      questions and settles one skipped line in eight to twelve wrong; not built
- [x] Questions with no readings (headings, missing lines) get Qwen's reading as an
      option, and a typed answer is checked against it (2026-10-17): Ex-minnaar 170 of
      199 questions; benches identical

## 5. Errors no question asks about

- [x] 2026-10-17 Lines the text layer lacks at a text block's top or bottom: a strip of a
      text region above its first layer line or below its last is a candidate
      (`missing.edges`); Vuurspel p. 19's two lines read right. With Bruna's references
      re-derived without markup spaces: validation BETTER 0.49 → 0.38 after review
- [x] 2026-10-17 The Stranger's Child's nested-quote spacing: the print sets a thin gap
      between nested marks, some e-books write it as a space; folded in the score
      (`evaluate._NESTED_GAP`), validation BETTER 0.38 → 0.36. Its "think—’" against our
      "think –’" is the print's after all: a dash breaking speech off sits close to its
      word there (scan crops, 2026-10-18), where its other dashes are spaced
- [x] ~~A closing dash keeps the layer's spacing on its open side~~ (2026-10-18, not
      taken, branch `cutoff-dash`): tuning fixed 5 and made 10, all Goede dochter. Its
      print spaces a sentence broken off after a word ("ik –’") and closes up a word cut
      off ("directeursk–’"), and the layer reads both closed. Only each gap measured on
      the scan could tell them apart: ~10 places in 1,900 pages, left
- [ ] Verdicts on the unasked errors that look like the reference's (the user, ~20 min;
      after the first looks): of 289 left unasked in the latest benches, about a quarter
      look like the e-book departing from its print, not the build: spaces no print sets
      ("gezicht .", "properly. ’", "BBS ’en"), words run together ("’snachts",
      "Rookjij"), a print line-end hyphen left in ("na-iviteit", "ge-identificeerd").
      Each verdict mends a reference, so every later bench measures the machine more
      truly. Listed in work/probes/unasked/rows.txt
- [ ] Line-end hyphens as questions where the judge is unsure (low): 34 of the 41 unasked
      compound-hyphen errors sit at a line's end, 0.02 wrong words a page; a question
      pays only in a band where the judge is wrong more than about one time in seven
- [x] De eerlijke vinder's unasked errors (2026-10-15): 28 of 38 were page numbers the
      layer joins to a body line; split off (`pdf._apart`), wrong words 0.88 → 0.42 a page
      on the short test; `bench tuning` 0.32 → 0.30 after review, no book worse

## 6. Structure

- [x] Metro's lost closing quote after a spaced ellipsis (2026-10-16): the layer drops
      it, the readers write `. . . '`, curled as opening or not at all; now closed at a
      line's end and curled by the book's style, Metro 0.42 → 0.33 wrong words a page
- [ ] Verdict page: a place where one side has something the print lacks (Metro p. 61's
      stray `>` in the e-book) says so in words: done on branch `verdict-words`
      ("the publisher's e-book has “>” here, our text nothing"), to merge after the slice
      growth
- [x] Monterosso's capital T read as an opening quote (2026-10-16): one case left in the
      build ("‘Lieve ‘Tiziana,’ zegt"), asked at the paragraph's end ("open at end"), not
      where the ‘ stands, since quotes nest in their own mark; not worth a rule for one
- [ ] Scene breaks the build still misses: 23 of 295 (Reis 14, De eerlijke vinder 7).
      Reis's are page tops after a full page whose last line ends a sentence at the
      margin, the next opening flush: the same geometry as a paragraph running on, so
      only the text can tell (a sorter question, "a new scene?", for later). Het heft
      (`P_plat`), Villa (`Tekst_6-Na-witregel`), Artemis (`noindent_topspace1`)
      undeclared, unsure on the scan
- [ ] De eerlijke vinder's part numerals I–IV (0/4): read from the drawing
- [ ] You're Never Weird's headings (5/16: bracketed sections, "- 1 -" numbers) and p. 47's
      picture text read into the body
- [ ] Dolittle's captions scored: derive them into the reference, or leave caption lines
      out of the score as footnotes are

## 7. Better pixels: Internet Archive's own files

Public on public-domain items only (Crime, Dolittle); private on lending-library items.
Sharper pixels lower the readers' errors at the source, the other way at the errors every
reading shares: many are specks and faint marks.

- [ ] JP2s as the image source for public-domain books (a borrowed item offers no
      downloads, so not for Stella or the user's books): on Crime's 50 reader-set lines
      both readers err about a fifth less (glm-ocr hard CER 1.57% → 1.26%, Qwen 1.78% →
      1.36%; `experiments/probe_ia_images.py`, 2026-10-11). Later, with public-domain books
- [ ] ABBYY's letter confidence as an arbiter feature: first check the PDF's layer is
      ABBYY's reading, then does a low one separate the real errors? ~1 h, no models

## 8. Beyond the golden books' kind

- [ ] **`init` names both page numbers whenever it shows or asks for a page** (the user, 2026-10-21): the PDF's page (the document's own index, which `body_pages` and every
      `--pages` use) and the number the scan prints, e.g. "PDF page 9 (the page prints 7)", never a bare "page 9"; where a page prints no number say so. The confirmation of the
      text's two ends on the review page shows the first and last page of the text proper this way, with the crops.
- [x] **`init`, first version** (2026-10-21; `bookinit.py`, `pagekinds.py`): language, page kinds (signals in the
      middle, clef-flash on the 8 pages at either edge), the two ends of the text proper, the cover and
      the title page's lines, written as `book.toml` (or a draft beside it), `init/report.md` and a contact
      sheet `init/ends.png`, every page named by both numbers. Ends right on 22 and 21 of 27 books;
      a rewording of the question changed nothing. Title, author and translator are drafted from the title and
      copyright pages (2026-10-22: title 26, author 25 right of 27). `build` and `review` run it
      when book.toml is missing, given a PDF or a folder holding one (2026-10-23). Still open below:
      the confirmation on the review page.
- [ ] **`roboscriptorium init <pdf>`, the rest** (agreed 2026-10-11): drafts book.toml and asks the
      user only what it can't settle, on the review page; `build` and `review` run it first
      when book.toml is missing. Steps: (1) each page's **kind** (cover, blank, scan noise
      or library stamp, half title, title page, colophon, contents, dedication, motto,
      foreword or introduction, dramatis personae, text, epilogue or afterword, notes,
      appendix, bibliography, index, acknowledgements, about the author, also by / ads,
      back cover) and a fixed rule from kind to *in the EPUB*, *metadata* or *left out*
      (the list in decisions.md, 2026-10-11, What goes into the EPUB: everything but
      what it leaves out); the contents page read for the book's structure and its
      chapters' names. (2) Labels: every golden scan's pages by kind (the old
      body ranges follow the references, which leave forewords and afterwords out, so
      they aren't labels for this). (3) Signals without models first (words on the page,
      page number, short centred lines, ©/ISBN, headings like "Woord vooraf", "Proloog",
      "Inhoud"), clef-flash's page-kind question on the doubtful pages. (4) Title,
      author, translator, language from the title page and colophon. The earlier screen
      put 227–231 of 252 edge pages on the right side, missing forewords and afterwords
      that the ranges of then left out (design.md, Where the body starts and ends).
- [ ] An image-only scan through the whole pipeline (Goede dochter with its layer removed:
      tesseract 0.35% CER against the layer's 0.20%): does the OCR check close the gap?
      ~1 h cold. Then italics from tesseract's word boxes

## 9. Golden books and housekeeping

- [ ] **user** More golden pairs when convenient: Koning Wilders (Atlas Contact) and Het
      laatste bevel (Manteau) came in 2026-10-11; De Arbeiderspers, Prometheus/Ooievaar or
      Vrijdag next; a Kosmos book for later, beyond prose
- [ ] **user** Settle verdicts on the tuning books (`review` on each), the disagreements
      the arbiter's labels sit on first: hours, spread out, whenever convenient
- [ ] Remove the `baseline` and `qwen2` worktrees when convenient

## Later

- [ ] Python 3.15 once PyTorch publishes cp315 wheels (pytorch/pytorch#184352): with
      nightly torch every test passes and the spotter's regions match 3.13 exactly
      (2026-10-11); bump `.python-version`, `uv lock`, bench once
- [ ] Qwen on fewer lines (quote marks, disagreements), for speed: only if cold runs
      become the bottleneck (a new book's ~100 pages take ~2 h)
- [ ] MiniCPM-V 4.6 as a faster reader: the readers already cover nearly every line, so
      it pays only by speed
- [ ] Surya's layout model as a second spotter: screen it on the drawn numerals
      DocLayout-YOLO misses and the figure pages
- [ ] Block quotes and verse: find golden pages that have them first (epigraphs on a
      page of their own done 2026-10-11; De eerlijke vinder's mottos at its part
      openings, beside a drawn numeral, are not caught)
      Ex-minnaar p. 50 (2026-10-16): a poem, "Gemis", short indented lines; its title
      taken for a chapter heading and its lines joined into one paragraph
- [ ] Per-book image tuning for pale or tinted scans: null on normal pages so far
- [ ] Het Kindeken Jezus as a golden book, only if the image probe looks
      language-dependent
- [ ] `golden check <pdf> <epub>` writing a draft manifest, once a batch of candidates comes
- [ ] French, the user's idea (2026-10-09); **not yet** (2026-10-10: no French books to
      make yet). It brings its own typography
      (« », a thin space before `; : ! ?`, dialogue dashes) that `quotes.py`,
      `typography.py` and the arbiter's training data would all need, and Gallica is
      mostly older print. If it comes: one French Wikisource book proofread page by page
      against its scan, a first look like any new pair. Proposed first instead: count the
      accent errors Dutch already leaves unasked (`knieén`, `hé` for `hè`, lost stress
      accents, Stella's `scenes`), by book

# Done

By area, newest first within each; one line a step. Dates and numbers are as recorded in
[decisions.md](decisions.md) on the day.

## Measurement

- [x] 2026-10-13 What a perfect reader could still gain (`probe_reader_ceiling.py`): 53
      of 186 wrong words left after review (29%) are undoubted reading errors, under the
      half agreed as the bar; fine-tuning a reader dropped for now
- [x] 2026-10-13 `bench validation` finished with the ellipsis measured on the scan: BETTER
      1.10 → 0.59 after review (The Stranger's Child 4.59 → 0.53); tuning BETTER 0.52 → 0.50
- [x] ~~2026-10-11 `_scandata.xml` page types as labels for page classification~~:
      dropped, they mark the cover and title page (Dolittle also contents and
      copyright) and call every other page Normal, colophon, motto and ads included
- [x] 2026-10-11 Scene breaks scored: derive reads them (thought breaks, ornaments,
      break, opening and closing classes, each checked on the scan) in 10 references;
      the build finds 255 of 295 and sets 20 more where they are recorded
- [x] 2026-10-11 A page opening flush left after a finished paragraph is a scene break
      where paragraphs indent: found 255 → 272 of 295, 2 more set; words unchanged
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

- [x] 2026-10-11 Validation from 5 books to 7 (Monterosso and De stilte van de hel, cold):
      **0.76** wrong words a page after review by the rules
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

- [x] 2026-10-18 Winnow-12B the text judge, asked through token probabilities: right
      alone 81% (winnow-ollama:e4b 67%), its arbiter tuning 0.30 → 0.28 after review,
      better; validation 0.37 → 0.39, no change; the Ollama pin's reason gone
- [x] 2026-10-18 `experiments/rebuild-trust.sh` builds every book's trust data, the two
      labelled by review answers (Stella, Ex-minnaar) at their body pages too, and
      trains without `--partial`
- [x] 2026-10-11 Training code for the shipped models in the package: `trust.train`,
      `trust.training_matrix` and `sorter.train` were there already, with feature-count
      tests for trust; the sorter's feature names now tested with regions and styles
- [x] 2026-10-11 The pair prior's own ablation (an empty table, retrained): without it
      tuning 0.31 → 0.34, validation 0.70 → 0.73, both worse; it stays
- [x] ~~2026-10-11 Bad pages by the readers' disagreement~~: the 5% densest pages hold
      32 of 319 unasked words; dropped
- [x] 2026-10-11 Whether a borrowed item's JP2s can be had: no, its download options are
      empty while on loan (the user, on Stella)
- [x] ~~2026-10-11 The book's own consistency as new suspects~~: 13 catches against 17
      false alarms, 10 of them in one bad scan; dropped
- [x] 2026-10-11 Ask threshold 0.7 / 0.8 / 0.9 on tuning: 0.74 / 0.92 / 1.11 questions
      a page for 0.351 / 0.344 / 0.343 after review; stays at 0.8 (yield falls off past it)
- [x] 2026-10-11 ~~De tuin's four questions no longer asked~~ dropped: it no longer loses
      (0.64 → 0.59 with `bughunt`)
- [x] 2026-10-11 Branch `bughunt` merged: the hunt's 22 fixes and its seven open
      findings, trust data rebuilt warm (MODEL_VERSION 6), arbiter retrained; tuning
      **better** 0.50 → 0.48, six books clearly better, none worse; validation no change

- [x] 2026-10-11 Trust data for Thief-Taker and the five new books (567 pages, 525 min),
      arbiter (~10,400 suspects) and trees retrained: **the new baseline**, tuning 0.50,
      validation 0.74 wrong words a page after review; trees 0.48 / 0.67, no change

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

- [x] 2026-10-13 One review for a golden book: its places that differ from the e-book
      are questions in `roboscriptorium review`, answers stored as verdicts; `golden
      review` and the page's verdict mode are gone. Each side's words shown as written.
      Walked on Dolittle (89 questions, 15 of them places): choose, type (warned once),
      caption from our words, page-break crops
- [x] 2026-10-11 Stella built with today's build (every stage cached, under a minute,
      epubcheck clean): 7 questions, 3 answered before, 80 of 83 old answers applied (the
      other 3 lie inside a line another answer retyped whole)
- [x] 2026-10-11 Stella's 4 new questions reviewed (p. 19 "íéts", the other three as
      the text had them), rebuilt, epubcheck clean
- [x] 2026-10-11 English line-end hyphens nothing else decides settled by the judge, not a
      question: tuning **better** 0.36 → 0.34 (Dolittle 0.52 → 0.44, Metro 0.26 → 0.22)
- [x] 2026-10-11 A quote left open at a paragraph's end asked whatever follows: tuning
      0.37 → 0.36, De tuin's unasked 0.24 → 0.16, no book worse
- [x] 2026-10-11 No paragraph starts on a line that continues a word broken with a hyphen:
      tuning **better** 0.32 → 0.31, validation **better** 0.74 → 0.70
- [x] 2026-10-11 A quote mark left open right after a word asked where it stands, not at
      the paragraph's end: tuning **better** 0.33 → 0.32, no more questions
- [x] 2026-10-11 A section opening on a word in capitals flagged as a lost drawn initial
      too: Dolittle 0.44 → 0.40, pooled no change
- [x] 2026-10-11 A section opening in lower case below a heading flagged as a lost drawn
      initial: Het ijzige land 0.25 → 0.20, pooled no change, no book worse
- [x] 2026-10-11 Speech closed on a letter at a paragraph's end asked as a quote question
      (De tuin kerns the stop under the mark): tuning **better**, De tuin 0.46 → 0.41
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

- [x] 2026-10-17 Paragraph starts: a line beginning in lower case after one not ending a
      sentence carries on (no model); the vision judge (`parabreaks.py`) off, as it broke
      more than it fixed; breaks tuning 0.19 → 0.15, validation 0.21 → 0.13 a page
- [x] 2026-10-11 Footnotes out of the running text, linked to their marks (`footnotes.py`):
      Reis 7 of 8 found and linked (the eighth's mark read "ie"), no false ones on the
      benches after a stroke-weight limit; Reis paragraph breaks 0.07 → 0.06, BETTER
- [x] 2026-10-11 Paragraph breaks in unindented books (Bruna's): justification judged on
      lines that stop mid-sentence, a page's short last sentence carried over; validation
      breaks 1.97 → 0.21 a page (Vuurspel 7.91 → 0.44), tuning 0.26 → 0.22, no book worse
- [x] 2026-10-11 A dropped line that reads as running text kept and flagged
      (`roles.running_text`): tuning **better** 0.43 → 0.37, validation **better** 0.82 →
      0.76. The trees on top of it: no change (0.37 → 0.40, 0.76 → 0.72), Thief-Taker and
      Vuurspel clearly worse; ~~trees on by default~~ dropped, they stay off
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

- [x] 2026-10-13 Third review of the codebase, four reviewers: eight bugs fixed with tests
      (a typed verdict could write its context into the reference twice, a word left
      open before "en" lost its hyphen, a typed line took the identity of the one below
      it, notes scored on the wrong version of the pages, answers saved at once could cut
      each other, no cache knew its source PDF, the arbiter read its judges by the order
      of their votes, the docs put copyrighted books' verdicts in git); the rest planned
      above
- [x] 2026-10-13 Three suspect pairs retired (the user): 11/22/63, FKA USA, Koning
      Wilders; the arbiter retrained without 11/22/63
- [x] 2026-10-13 The bench prices the reviewer's time (20 questions = one wrong word, the
      user) and its verdict is worse when any slip rate is, a veto on breaks too: this
      morning's tuning run stays better, 0.57 → 0.55
- [x] 2026-10-13 The bench counts typography where the words agree, a measure of its own:
      0.0–2.0 words a page, Dolittle 8.7, nearly all straight quotes kept from the layer
- [x] 2026-10-13 The trust data and the arbiter's saving into `src/roboscriptorium/trustdata.py`,
      tested; its book list kept in step with `bench.NO_TRUST_DATA` by a test; retrained
      from the cached data with the old code and the new: the same models
- [x] 2026-10-13 The measurement code out of `cli.py`: `golden.scoring` (a golden slice
      built and scored) and `bench.run`; 25 experiments and the tests use them, not the
      CLI's private helpers
- [x] 2026-10-13 Straight quotes and apostrophes left from the layer curled
      (`quotes.curl`): typography 0.00–0.09 a page on every tuning book, the verdict
      unchanged

- [x] 2026-10-09 Fable's second review: what the bench couldn't see and leaks in the OCR
      check, each change benched alone; the ledger of probe against verdict is in
      outlook.md
- [x] 2026-10-09 Strict review of the codebase: six reviewers, every finding checked,
      fixes with tests in seven commits; trust data rebuilt, tuning 1.00 → 0.96,
      validation no change. Qwen's read prompt (five variants) and crop (dpi, upscale,
      contrast, sharpen, margin) can't be improved: each fixes as many lines as it breaks
