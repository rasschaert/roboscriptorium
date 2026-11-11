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
review**, the target book, then the user's own books. After them, the open
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
- [ ] The bench's italic count without the words' spelling (found 2026-11-11): an italic
      word set italic but misread counts as an italic error, so the count rises with the
      questions (an asked suspect keeps the layer's text: 1,278 → 1,304 between asking
      below 0.9 and 0.95 with the same slants) and flipped the verdict on three arbiter
      runs. Count a word's slant by its place, whatever its letters. Agent, short
- [ ] Grow the tuning slices further whenever the machine is idle (the user, 2026-10-25,
      until told to stop; the user's other work comes first). Done 2026-10-26: eleven slices,
      ~860 pages (13 h cold), tuning now ~3,100 pages. Paused 2026-10-26 at the user's
      request: batch two (thirteen slices to about 220–270 pages, ~925 pages, ~14 h) had
      started on Goede dochter. Its ranges are in commit 3e6177c (`git show 3e6177c --
      src/roboscriptorium/bench.py src/roboscriptorium/trustdata.py`); reapply them, run
      `work/runs/grow3.sh`, and the read caches resume. Resumed 2026-11-02 (the user away,
      "do whatever you think is productive"), one book at a time, against today's baseline;
      done 2026-11-03. Batch three 2026-11-05: nine books whole (~512 pages, ~6 h cold),
      tuning ~4,500 pages. Batch four 2026-11-07: Goede dochter, De cipier and Het heft
      whole (~720 pages, 11 h cold), tuning ~5,200 pages. Room left (~915 pages): Au pair
      219, Metro 201, De vergelding 134, Thief-Taker 127, De tuin 120, Vals alarm 114 (each
      to end on a chapter, `experiments/chapter_pages.py`). Gain: the bench's interval, about
      ±0.010 at 2,271 pages, narrows with the square root of the pages (about ±0.007 at
      ~4,000); more pages did not make a better arbiter (decisions.md, 2026-10-25).

8. The next set review (AGENTS.md, "Reviewing the sets"): done 2026-10-24 (no suspects,
   nothing retired; decisions.md). The gaps in docs/golden-notes.md go to the user as the
   books to look for.

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
- [x] ~~One more reader?~~ Answered 2026-10-24 by the quiet set (`quiet_set.py`): the layer and both readers are wrong together on 23 lines of the tuning slices, so a new reader can add a handful; LightOnOCR-3 found 1. Before: taking readers away costs the most of any block (without qwen3.8
      silent errors 12 → 75 at a question a page; `probe_subtract.py`), so adding one
      may pay where nothing else reaches: layer errors no reader doubts. Measure on the
      frozen reader set's hard lines the errors a candidate reads right where every
      current reader is wrong ("unique catches"); dropped if it adds none beyond noise,
      whatever its own score. Candidates: qwen3.8 with another prompt or crop, a vision
      model not yet screened. Locally in a gap (agent, ~1 h)
- [x] ~~Winnow subtracted?~~ Done 2026-10-24: WORSE without it (tuning 0.282 → 0.316, 79 fixed, 164 made; decisions.md); Winnow stays. Before: the context judge reads the whole paragraph where winnow reads
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
- [x] ~~A context judge~~: stays off (the user, 2026-10-19, shown it passing both sets with fewer questions but more unasked errors: "then i'm against it"; decisions.md). Before (the user, 2026-10-17: "if it cuts down on questions being asked
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
      (counted 2026-10-24: 14 of the 78 paragraph-break errors on tuning sit on a page's first
      line; low priority)
- [x] ~~The whole-page reading as one more reader~~: answered 2026-10-14/15 (decisions.md): the page readers point at about 60 errors no question asks, mostly at line joins a line reading can't carry; added as readers for the arbiter, tuning no change (outlook.md, "Tried")
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
      headings found 126/126 against 110, 3 false. 25 s a page. The short answer (only
      the heading and furniture line numbers, `--short`) keeps it: 4 wrong, 126/126 headings,
      3 false, 1 page unparsed, at ~6 s a page. **As an input to the trees (2026-10-24,
      `pageroles.py`, `ROBO_PAGE_ROLES`, off): role errors left one book out 186 → 146 on
      tuning, 128 → 120 on validation, but `bench tuning` made 60 wrong words for 30 fixed
      (19 unasked made, 10 fixed): not taken.** Qwen fails on picture pages, which the probe's
      certain pages left out: on Dolittle p. 74 it calls every line furniture, the text
      beside the drawing too (48 of the words made); it also drops an epigraph's attribution
      (De vergelding) and keeps a motto as text (Bananen). It gains where the trees miss a
      date heading or a chapter's first line (Het heft, Thief-Taker, Reis). Its heading call
      is ignored for narrator names in small capitals (De geruchten "DOLF", 1 of 20 found):
      no tuning book has them. **With the lines inside a picture marked (2026-10-24): role
      errors 137, tuning 30 fixed / 27 made (5 unasked), NO CHANGE; not taken.** Left: mottos
      and an epigraph's attribution (Bananen, De vergelding), which a next try would have to
      tell qwen about
- [x] ~~The text layer as a second reader only~~: closed 2026-10-24 on the evidence above: a
      whole-page reading starts from more errors than the pipeline (Qwen 76 wrong words over
      19 pages against 27, glm-ocr 103) while the layer reads 0.21% CER on modern Dutch, so the
      page would start from the worse reading. Reopen when a page reader beats the layer
- [x] ~~Page kinds for `init` by Qwen from the page image~~: done 2026-10-24, no better than
      clef-flash (ends right 20 and 23 of 27 against 22 and 21, 3 ends cut against 2); not taken
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
      - [ ] (Capped 2026-10-24: the quiet set has 23 lines every reader gets wrong, so a
            witness can add a handful; screen a variant there first, in minutes.) Variants
            as extra *witnesses* for the vote simulation, not a choice: contrast
            stretch, tighter and wider crop, a second prompt wording, each through
            `vote_sim.py`, then on the lines no reader flags (as
            `probe_dpi450_alone.py` does): the frozen set is 60% hard lines, so its vote
            gain overstates a witness that only helps where the arbiter already looks.
      - [x] ~~The 450 dpi qwen reading as an extra arbiter reader~~ (dropped 2026-10-23):
            right alone on 0 of 57 quiet lines where it differs, and the 2026-10-09
            bench of the same second look found no gain.
      - [x] ~~Token probabilities of a reading as a per-line confidence~~: done 2026-10-24
            (`probe_image_gain.py`): AUC 0.78 over all lines, 0.57 where glm-ocr agrees, so it
            marks only what the readers' disagreement already flags; not taken
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

- [x] Is the scan's text mask lossy? (Fable's review; 2026-10-23, no): Internet Archive's
      Scribe scans (Stella, Goede dochter, Het schaduwhuis) code their mask as JBIG2 generic
      regions, an exact bitmap with no symbol dictionary, so no letter can be substituted;
      Dolittle's older scan uses symbol dictionaries. At a known emphatic accent
      ("vríénden", Het schaduwhuis PDF page 56) the accent shows plainly in both the mask and the
      composited render the readers get: the loss is the readers', not the scan's, and the mask
      shows an accent no better than the render
- [x] ~~Crops padded to the vision encoder's grid instead of resized~~ (Argon; NOT TAKEN
      2026-10-23, `probe_grid_pad.py`): Qwen3.8 takes 16-px patches merged 2×2, so its
      processor scales the frozen crops' heights by 0.8–1.2 to a multiple of 32. Padded with
      paper colour instead, qwen read 427 of 480 hard lines right against 436 and 311 of 320
      control lines against 319 (9 fixed, 26 broken; the 68 most squashed lines 64 → 65);
      re-reading the crops as they are changed none, so it is the padding. It invents marks:
      "nògal", "dië", "én", "Ârtyôm"
- [x] ~~Small capitals from the descender band~~ (Argon; dropped on reading the errors,
      2026-10-23): of the 27 unasked case errors on tuning, 15 are Au pair's reference writing
      small capitals in lower case (verdicts, golden-notes), and the other 12 are short acronyms
      in small capitals ("ss", "wa", "voc", "usb", "cv", "v-hals", "u-boten") with no letter that
      descends: the test reaches none. What is left needs a shape classifier (the glyph-level
      checks below), and a small-capital S is nearly a lower-case s
- [x] ~~Book-wide consistency for diaereses and letters outside ASCII only~~ (Argon's
      narrowing; 2026-10-23, `probe_book_consistency.py --marks`): one flag over every tuning
      slice, and a right one ("geinteresseerd" for "geïnteresseerd"), but 1 of 184 unasked
      one-word errors: most such words occur once in a book, so the book can't vouch for them
- [x] ~~A per-book character recogniser with no language model, as a witness that fails
      differently~~ (Fable's first idea, Argon's fourth; DeepSeek advised against; NOT TAKEN
      2026-10-24, `kraken_lines.py`, `kraken_eval.py`): Kraken 7 trained from scratch on 22k
      golden line crops (the reader set's other half of books held out), 99.73% characters
      right on its validation lines after 8 epochs. On its 400 frozen lines it reads 169 of
      240 hard lines right (qwen 216) and 142 of 160 control (qwen 160); of the 6 lines where
      the layer, qwen and glm-ocr agree on the same wrong reading it reads 1 right (a stray
      full stop left out), and it shares the others' errors ("some one", a colon for a full
      stop); right alone on 3, breaking 74 qwen reads right. The other fold not trained:
      half the set settles it. The per-book fine-tune and the ensemble were not tried
- [x] ~~Image-gain as a silent-error signal~~ (Fable; Argon's runner-up margin; NOT TAKEN
      2026-10-24, `probe_image_gain.py`): on the 800 frozen lines, qwen wrong on 45, the
      weakest token's log-probability marks them with AUC 0.78 and the runner-up margin 0.77,
      image-gain 0.47 (no better than chance). Where glm-ocr reads as qwen does (676 lines,
      qwen wrong on 12, the errors no disagreement flags) the three are 0.57, 0.57 and 0.44:
      qwen is as sure of its silent errors as of its right lines
- [x] ~~Real-word confusion pairs mined from the golden pages~~ (Fable; NOT TAKEN
      2026-10-23, `probe_book_consistency.py --pairs`): pairs from the other tuning books'
      errors flag 216 word types whose partner occurs in the book, mostly common words with an
      emphatic twin ("mijn"/"míjn", "ik"/"ík"), thousands of occurrences, for 2 unasked catches
- [ ] Two-line crops at each line break as a decision for clef (Fable, Argon): the last
      words of a line and the first of the next as one image, "join or not, hyphen or not,
      comma or full stop", where a trigger fires (a line ending in a stop before a lower-case
      start, a join that forms a word). Targets the 109 unasked errors at line joins
      (agent, ~1 day). Recounted 2026-10-24 on `tuning-20261024T063416`: of 236 unasked
      errors, 2 span a join; the 31 compound hyphens sit at line ends, where the scan
      can't show whether the hyphen is the word's (the qwen and clef probe above); the
      join's commas read as stops are a glyph the readers miss at any resolution. Little
      for a crop to see; low priority
- [ ] New OCR models as witnesses on the frozen set (Fable, Argon): dots.mocr (3B, MLX
      builds), LightOnOCR-3 1B and 4B done 2026-10-24 (unfit: weaker than olmOCR-2,
      `lighton_read.py`), Chandra OCR 2 (5.3B), HunyuanOCR (1B), PaddleOCR-VL-1.6.
      Deprioritised 2026-10-24: the layer and both readers are wrong together on only 23
      lines of the tuning slices, so a line witness can add a handful at most; screen a
      candidate on the quiet set (`quiet_set.py`, minutes) before the reader set, and only
      for a reason beyond its benchmark (agent, ~1 h each)
      - [ ] LightOnOCR-3's grounding mode (labelled page blocks: header, footer, page
            number, footnote, title, with boxes) as an input to line roles. Qwen's page
            roles, tried so on 2026-10-24, cost more words than they saved; try only on
            the pages where the trees err, first (agent, ~2 h)
- [ ] (Measured 2026-10-24: a line is 52% prefill, 23% decode, so speculative decoding buys little; batching was ruled out; the lever is fewer image reads, decisions.md. Low priority.) Qwen faster on the same output (DeepSeek, Fable, Argon): prefix caching of the fixed
      prompt, batched decoding (mlx-vlm, vllm-mlx), speculative decoding with the text layer
      or glm-ocr as the draft (lossless under greedy decoding); readings must stay identical
      on the frozen set. Speed buys the page-level role pass everywhere (agent, ~1 day)
- [ ] Review (counted 2026-10-24: batching identical questions saves 30 of 456 OCR cards on tuning, 7%): identical questions batched into one card, and same-page reference crops
      (this printer's comma and full stop, a plain i and an accented vowel) beside each
      punctuation, accent or small-capital question (Argon); answers propagated to every other
      occurrence of the word (Fable). The user's time: a design, then the user's say
- [ ] Speck labels harvested from the golden pairs (Fable, Argon): every reader's character
      absent from the reference, aligned to an ink blob, is a speck; every mark the reference
      confirms is ink. Labels from all 30 books for the speck classifier (agent, ~1 day)
- [ ] Line-end compound hyphens learned from the compounds the books print unbroken mid-line
      (Argon): self-supervised, for the 24 of 27 the book itself can't settle (agent, ~half a day).
      Measured first (2026-10-24): of 542 undecided Dutch breaks 14 are real hyphens; qwen,
      clef and the cheap cues (a capital first half, a vowel clash, both halves words) tell
      none of them apart. A learner needs a feature none of these has; low priority
- [ ] Glyph-level checks, later (Argon's pairwise classifiers for confusable letters, Fable's
      glyph clusters with one label each): only after the cheaper glyph probes above
- [ ] Paragraph starts by a model that knows the book's indent regime (Argon), and heading
      tags from Granite-Docling-258M (Argon): after the page-level role pass, which already
      finds every heading in its probe
- [ ] Paragraph starts as edge classification on a graph of lines (DeepSeek 7, Wang et al.,
      WACV 2022, a ~100 KB graph network; Fable's review rates it the best fit for unindented
      books): learned, as the principles want; the obstacle is data, since the unindented books
      are validation only. Synthetic unindented pages from the tuning books (indents removed,
      breaks kept) would train it, but they carry the short last line and not the extra lead
      real flush-set books put between paragraphs (Fable): measure that lead on the validation
      books first, to know what the synthetic pages miss (agent, ~2 days). **Measured 2026-10-24
      (`probe_flush_lead.py`): no extra lead (0.99 of the pitch before a start, 1.00 within);
      the short last line is the mark, as in indented books, so synthetic flush pages miss
      nothing; a start after a near-full line (one in ten) needs text cues.** Blocked
      2026-10-24 on a flush-set tuning book (decisions.md): the user's candidates, then the
      synthetic pages and the model
- [x] ~~Gated language-model scoring of words with a visual twin~~ (Argon's PLLR with
      RobBERT; Fable and DeepSeek against): parked behind the glyph and image-gain probes,
      which ask the scan rather than the language
- [x] ~~Constrained LLM post-correction~~ (all three call it low value at this error rate)

- [x] ~~Book-wide consistency as a suspect~~ (DeepSeek 5; NOT TAKEN 2026-10-23,
      `probe_book_consistency.py`): a word spelled one way once and a close variant three
      times or more flags 4,802 words over the tuning slices (3 a page), 34 of them errors;
      it catches 17 of 184 unasked one-word errors, about 6 of them real, the rest emphasis
      accents the print has and the reference drops, which it would remove
- [x] ~~The JBIG2 text mask as the readers' image~~ (DeepSeek 6): the accent is as plain
      in the composited render as in the mask (the lossiness check above); the mask stays a
      geometry channel for the descender band and specks
- [x] ~~A threshold per kind of question~~ (Argon's value of information; DeepSeek 8 as
      ranking; NOT TAKEN 2026-10-24, `probe_kind_threshold.py`): on the trust data, with
      each tuning book scored by the arbiter saved without it, thresholds chosen on the
      other books (accent 0.9, space 0.95, quote 0.7, letters 0.85, in every fold) left
      65 → 58 silent errors for 330 → 318 questions; the warm bench didn't carry it (after
      review 0.290 → 0.290, questions 0.732 → 0.721 a page, unasked 0.174 → 0.176: 9 unasked
      fixed, 10 made). The reviewer-mistake test (does the arbiter's margin predict a wrong
      answer) was not run: 8 mistakes on Stella are too few to choose by
- [x] ~~The arbiter's own silent errors, a feature for them~~ (NOT TAKEN 2026-10-26,
      `probe_accent_mark*.py`, `probe_ask_threshold.py`): of the 97 bench places where a
      version had it right, 39 are accents, specks taken for accents and emphasis dropped;
      the mark's shape adds nothing to the trees, and the rest are suspects the arbiter was
      0.8 sure of; three questions a page caught 8 on De vergelding, tuning no change
- [x] ~~Character-level ROVER with a diacritic-restoration vote~~ (DeepSeek 1, not taken
      on reading): suspects are already made at character level where any reader differs;
      the silent errors are where every reader gives the same characters, which a vote
      can't open, and a dictionary-driven accent restoration would invent Dutch emphasis
      accents, which are optional
- [x] ~~PaddleOCR-VL-1.5 as one more reader~~ (DeepSeek 2): screened 2026-10-20, unfit
- [x] ~~LLM post-correction under a learned edit budget~~ (DeepSeek 4, parked): only on
      the places the consistency test flags, if that probe earns it

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
- [x] ~~A lighter feedback loop~~: checked 2026-10-24 (decisions.md): quick ranks a change that acts everywhere in the same direction with less power, and misses one acting on front matter or pictures (outside its slices); it stays the short test, tuning the verdict. Before (agreed 2026-10-13; its two rules are in AGENTS.md): the quick
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
- [x] **user** read the EPUB through (2026-10-31, `epubs/stella-2026-10-19-0014.epub`):
      no errors. Two sentences queried as odd (p. 41 "Ik weet dat aan…", *wijten*; p. 50
      "met welgevallen") match the scan

## The machine finds what a reader would (the user, 2026-11-01)

Hoe wij verdwijnen's first build came out with its chapter numbers misread or missing
(old-style figures: "Io", "SE", "zi" dropped for 23), its dedication split in two and its
motto as running text, and Pieter Daens' `init` took the publisher's ads for text. An
agent found them by reading the EPUB; the user: "ideally that detection and the fix is
also part of the pipeline itself." Before either book goes to review:

- [x] ~~A scan that repeats or skips pages~~ (2026-11-07, `scanpages.py`): Goede dochter's
      repeated PDF 218–219 left out, its missing printed 286–287 named by `build` and taken
      out of its reference by a verdict; its wrong words 3.22 → 0.48 a page
- [x] Chapter numbers (2026-11-01, `chapters.py`): all 52 of Hoe wij verdwijnen right on
      its warm rebuild; the five dropped ones read right by the readers once kept
- [x] Front matter (2026-11-01, `pagekinds.set_apart`): the page-kind model asked about
      short pages of the text proper; Hoe wij verdwijnen's dedication and motto each one
      block. Their italics too (`italics.uniform`, one type per motto or
      dedication): "Voor" italic, "Zwart" upright, nothing else in the book moved
- [x] A structure check at the end of every build (2026-11-01, `structure.py`): numbers
      out of their run, a title among numbers, sections under 20 words; `build` prints the
      count. On the 44 books built so far: 18 places in 6 books, all errors by eye
- [x] Each structure finding a review question (2026-11-01, `flags.structural`): at its
      first line, or a reason on the question already there. To walk in the review page
      before the next review (every kind, its crop)
- [ ] Structure findings repaired where the book's own evidence settles them, beyond
      the chapter numbers
- [ ] (Benched 2026-11-02: heading errors 102 → 65 on tuning, 50 → 44 on validation;
      Glazuur and Doodskleed mended.) Left: headings found but not set as printed
      (Dolittle 7, Thief-Taker 6, Metro 2, Het ijzige land 2); the extra-heading count
      going negative (fixed 2026-11-02, `headings_extra`); De cipier's lost scene break. The golden builds' heading errors the check found (Vals alarm 5, 11–13; Artemis 8;
      Het schaduwhuis 4; Glazuur "EO"; Vanille's split
      motto): which tonight's changes mend, on the warm bench after Daens; the rest traced
      to their stage. Doodskleed's "```markdown" and "境" headings, and its sentences as
      headings, all from corner specks glm-ocr talked about: now no line (2026-11-01,
      `missing._printed`)
- [x] `init`: the model walks inward from each edge until three pages in a row go into
      the EPUB (2026-11-02): Pieter Daens now ends at PDF 787; on the 27 labelled books
      starts right 22 → 23, ends 21 → 21 (22 against Het laatste bevel's corrected label,
      where the old setup's 20), no new cut. Left: Thief-Taker's "about the author" page
      (PDF 295) called a back cover, an old miss
- [x] The bench counts headings set letter for letter beside those found, and prints
      the totals over all books when they move (2026-11-01, `bench.heading_totals`)
- [x] Heading errors in the bench's verdict (the user, 2026-11-02): more is worse, fewer
      better, a book gaining any vetoes (`bench.heading_errors`)
- [ ] A golden pair with old-style chapter numbers over sunk openings on the gaps to hunt
      for (golden-notes.md)

- [x] Pieter Daens rebuilt warm with [7, 787] and today's code (2026-11-02, 3 min): the
      table of contents left out, the ads gone, its page of four mottos set apart (asked
      as a page before the first heading). Boek twee to vier's subtitles, dropped by
      the trees, headings again (`chapters.title_lines`). Boek vijf's "Onze doden", absent from
      the layer, read since (2026-11-02): all six part titles whole
- [x] A motto's wrapped lines joined into its paragraphs (2026-11-02, `reflow._wrapped`):
      Pieter Daens' three prose mottos one paragraph each, its song and the Camus motto
      line by line

- [x] Quote questions: a possessive after an s-sound ("Maurice’ moeder") no longer a
      closing quote (2026-11-02): Hoe wij verdwijnen's quote questions 37 → 16
- [x] Pieter Daens' quote questions sorted (2026-11-02): of 159 unpaired places, 101 open
      at a paragraph's end, by the scan real losses (p. 50 prints "zingen.’", we read
      "zingen."): a closing mark after the stop that the readers drop. Fair questions
- [x] The closing mark lost after a paragraph's last stop as a fix where the reading adds
      only that mark (2026-11-02, `quotes.closed_at_end`): 39 of 39 the print on tuning;
      Pieter Daens 38 closed, its questions 338 → 309
- [x] ~~One question per letter quoted over paragraphs~~ (dropped 2026-11-02): where a
      paragraph is left open and the next opens with the same mark, the print closes the
      first 20 times in 45 on tuning: asking once would leave those 20 unasked

- [x] ~~A paragraph the layer lost whole~~ (2026-11-06, `missing.blocks`): Dolittle's PDF
      97, tuning 105 wrong words fixed (81 unasked), 1 made; its title kept with it
- [x] ~~A chapter number with a speck after it~~ (2026-11-06, `chapters.value` leaves out
      punctuation after the number): Thief-Taker's "20 ;", tuning heading errors 24 → 23
- [x] ~~Specks read as a number off the run~~ (2026-11-06, `chapters.off_run`): Doodskleed's
      "7" and "3", tuning heading errors 26 → 24, no word changed
- [x] ~~A part page's title under its "Boek n"~~ (2026-11-06, `title_lines`, "part-page"):
      Het geluid van bananen 32 → 35 of 36, tuning heading errors 29 → 26, no word changed
- [x] ~~Misread chapter numbers where the run has a gap~~ (2026-11-06, `chapters.run_gaps`
      reads them again with glm-ocr): Monterosso 19 → 22 of 22, tuning heading errors
      32 → 29, no word changed on either set
- [ ] Heading errors left on tuning (2026-11-06, `experiments/heading_misses.py` lists them
      by book): De eerlijke vinder's part numerals I–IV, drawn as bars on pages with no
      text (PDF 12, 38, 58, 76): qwen reads the ink "1", "11", "111", "IV", so the run must
      read them as roman, and the page-kind model calls PDF 12 blank (low: of the tuning
      and validation books' body pages, these are the only ones with ink and no text);
      Afscheid's chapters 1 and 2 on openings sunk 0.06 of a page, under
      `page.SUNK_PAGE_DROP` (0.08), so their misread numbers ("l", "e,") count as page edges;
      Het heft's "88" (PDF 92, its own printed number at the foot of a chapter's short last
      page: mended 2026-11-07, `chapters.folios`); Thief-Taker's "V" (PDF 140, a speck 6 pt tall against numbers 14 pt: mended
      2026-11-07, `off_run`'s `SPECK_HEIGHT`); Dolittle's title page a heading, and the drawn initial C
      of PDF 97 left off ("HEE-CHEE"); Het geluid van bananen's "8°" for the ordinal "8e" (4); Metro's
      "CHAPTER 6" read "SRN WEIR", its number lost
- [x] ~~A heading suspect whose versions differ only in case settled by the book's other
      headings~~ (2026-11-09, `chapters.heading_case`): Het ijzige land's six asked headings,
      nothing else in any book's cached suspects; benched with production's tuning run
- [ ] Heading errors the exact count shows (2026-11-02): the first line of text swallowed
      into a heading (Thief-Taker, Dolittle: mended, `chapters.running_text`); Dolittle's chapter subtitles
      missing (13 of 14 mended, `chapters.title_lines`; "THE MONKEYS' COUNCIL" left); Metro's "CHAPTER The
      Rights of the Strong" lacking its 7; Het ijzige land's chapters 1, 3, 7, 8 lost
      (labelled numbers, now flagged by the structure check)

- [x] A short word leaning a little among upright ones no italic (the user's spot-check,
      2026-11-03: "op", "een" in Hoe wij verdwijnen): a lone word measured on fewer than
      three stems needs 12°, slants count from the page's upright, a run keeps its word at
      a line end (`italics._italic`). Tuning false italics 433 → 331, validation 245 → 162
- [x] Italic errors in the bench's verdict (2026-11-03, `bench.italic_errors`): the first
      try lost Het geluid van bananen's italic pages (10,000 words) and the verdict said
      "no change"
- [x] A build's comparison with the last shows italic changes (2026-11-03, `*word*`)
- [x] Het schaduwhuis' reference had no italics (its e-book sets them by class):
      `italic_classes` declared, derived again (2026-11-03)
- [x] ~~A lone word with a diagonal letter or acute accent held to 12°~~ (2026-11-03, not
      taken): tuning italic errors 2,445 → 2,588; a capital Z or W leans the word ~26°
- [x] ~~Learned italics on by default~~ (2026-11-04): `italic_trees = True`; tuning italic
      errors 2,445 → 1,088, validation 328 → 203, BETTER on both, no veto
- [x] ~~Chapter labels recurring under headings~~ (2026-11-04): Het schaduwhuis' headings
      32 → 67 of 68, no extra headings in another book
- [x] ~~Chapter numbers the layer and the spotter both miss~~ (2026-11-04,
      `missing.openings`): six lost numbers in three books read; Vuurspel's headings 5 → 6
      of 6 on validation
- [ ] Line-role trees that keep the grown slices' gains without keeping stray lines
      (2026-11-05, decisions.md): retrained on the grown slices they find Monterosso's
      mid-page chapter numbers (7 → 15 of 22) and Reis' (16 → 19), but keep Dolittle's and
      Afscheid's running heads as text. Check each attempt with `experiments/sorter_keep.py`
      (stray lines kept at 0.25: 214 today) before a bench. Ideas: the running head's
      recurrence counted over its chapter rather than the book; the stray lines weighed by
      the words they add, as the bench counts them. Also the trees' own: Het heft's
      datelines under its headings ("Februari 1829", "Maart 1829 / Wadham Gardens,
      Londen") joined to them (the retrain set them back as text), and its "88" mid-page
      on PDF 92 a heading (0.62)
- [ ] De geruchten's section headings (validation, 0 of 21): a narrator's name in capitals
      mid-page ("DOLF"), not under a number, so the label rule doesn't reach it; wait for a
      tuning book that sets headings so
- [x] ~~Stops added after a word before lower case~~ (2026-11-04, `line_end_stop` widened):
      4 of the 7 fixed on tuning; "the. ground" (Artemis) is no suspect, from another stage
- [x] ~~A stop added mid-line right before a lower-case word no version~~ (2026-11-05,
      `line_end_stop`, the next word undisputed): tuning 2 fixed, validation 5, none made
- [x] ~~An "ij" read as u, ui, y, ii or i no version~~ (2026-11-05, `ij_misread`): De
      vergelding's names, tuning 3 fixed, none made
- [x] ~~Lines of dots both layer and spotter lose~~ (2026-11-06, `missing.slots`,
      `quoted`, `slot_lines`): tuning 4 fixed (Het geluid van bananen), validation 5
      (Verminkt), none made; Het geluid van bananen's p. 25 and 76 and Vanille's leaders
      stay lost
- [x] ~~A quote mark misread from a speck no version~~ (2026-11-06, `quote_misread`):
      "keek’en" fixed; "de’schaft" (two letters before) stays
- [x] ~~Whole lines of text lost inside a block, found in the same inked slots~~
      (2026-11-06, `missing._fills`): nine lines read right by glm-ocr, tuning 103 wrong
      words fixed (12 unasked), validation 9 (all unasked), none made; Dolittle's short
      last line of a paragraph stays a question
- [ ] Small capitals, nailed (the user, 2026-11-09: "the new detected silent errors SWAT-team
      and USB-stick worry me. we need to nail this"). Merged 2026-11-11 (design.md, "Small
      capitals get an all-capitals version"; decisions.md): the capitals version of a
      mixed-case word is on (tuning no change, unasked 524 → 521, validation no change);
      the doubts on lower-case pieces no reading disputes and the capitals of a disputed
      lower-case reading (`ROBO_LOWER_CAPITALS`) are on since 2026-11-11, the user's call. With them: tuning no
      change, unasked 524 → 512, none made unasked, questions +1.6%; validation no error
      place changed, nine more questions (its verdict WORSE for those); Nervous System's
      "tv" twice and "VCR" asked, "SF" fixed. Left:
      - the arbiter fixing where the judges agree on capitals instead of asking: a
        retrained one does, but one retraining differs from the next by some fifteen
        unasked errors on tuning for 72 changed suspects (decisions.md, 2026-11-11), so
        first bring the arbiter's variance down, also before batch five retrains: ten
        seeds averaged cut the churn to a third (2026-11-11), and the number asked moves
        with the calibration, to be measured and steadied next
      - a lone small capital with the lower case's shape ("v-hals", "u-bocht", "o-benen"):
        no judge tells it, tight crop or wide; retest with a new vision judge
- [x] ~~autotrust-jev 9B as a second text judge~~ (2026-11-09, pass 4): not taken. Tuning
      unasked 551 → 535, validation 170 → 178 (decisions.md); failed on the arbiter's 23
      books, branch `text-seat` kept for a retest after batch five
- [x] ~~The book's own vocabulary as an arbiter feature~~ (the user's idea, 2026-11-08):
      null on today's arbiter (decisions.md, 2026-11-08). Its signal is real on readers'
      real-word swaps ("wegkwijnen" over "wegwijken"), but the trees pay for any extra
      columns about as much; retest when the arbiter's training data grows or it changes kind
- [x] ~~The line-end join's book spellings counted from the text after the OCR check~~
      (2026-11-08): already so (`pipeline._book_spellings`: the pages being built after the
      check and the answers; only a bench slice's other pages as the layer reads them, which
      no build checks). The join asks the book first ("Númen-" / "or" joins where the book
      prints "Númenor" inside a line)
- [ ] Past nulls the judge panel may turn (2026-11-08; the ones whose stated bottleneck was
      the judges or the arbiter), after the small-capitals retest: the hints about kinds of
      OCR error (`tryout.py --prompt kinds|targeted`) on autotrust-jev, d3 and pplx-decider,
      untested so far (~15–30 min each, judge set v2); d3 and autotrust-jev as the line-end
      hyphen judge on the 542 undecided Dutch breaks and the English ones (Qwen found none of
      14 real Dutch hyphens, 2026-10-24; offline probe); more labelled suspects for the
      arbiter (null 2026-10-25 for lack of new features) comes with batch five; then the
      page readers as line readers (null 2026-10-14/15: the arbiter trusted their versions
      wrongly on unseen books), queued after the others (the user, 2026-11-08): their
      readings are cached, so the cost is the panel's judges on the new suspects they raise,
      a trust-data rebuild with `ROBO_PAGE_READERS=1` in its own folder, the arbiter retrained
      and both benches against the winning panel
- [x] ~~New vision decision models as judges~~ (2026-11-09): autotrust-jev 35B and d3 9B
      taken beside clef, asking below 0.9 (decisions.md); pplx-decider on the wide crop not
      taken (pass 3); the rest screened and set aside on the panel test (models.md). Still
      open from it: the hints for the new judges and line roles for the small ones, under
      "Past nulls the judge panel may turn"
- [x] ~~Pages below the quality the build supports~~ (2026-11-08, `scanpages.poor`, branch
      `poor-pages`, merged after the panel's benches, which run against today's scoring):
      1.5 or more OCR-check suspects a line on a page of ten lines or more; De vergelding's
      nine blurred pages (1.54–6.0), the next page anywhere 1.24 (Verminkt's Polish). Named
      by `build`, out of the bench's score
- [x] ~~What the review shows of a contested place~~ (2026-11-07): already the whole line
      and one line either side (`review.CROP_CONTEXT_LINES`); only the judges see the
      suspect alone, which the panel's wide-crop judge tests
- [x] ~~The judges told the kinds of OCR error~~ (2026-11-07, judge set v2): not taken.
      clef:27b weighted 91.3% → 89.9% (91 hard picks fixed, 16 right ones broken, all at
      low confidence); Winnow-12B worse on both halves, stopped at 525 of 995
- [ ] The rest of the errors the build makes where the layer was right (51 unasked on
      tuning, 2026-11-06): accents (18) are accent-shaped specks, no cheap signal
      (decisions.md, 2026-11-06); punctuation swapped (about 10: commas added, 13 of 14
      wrong, no rule), quote glyphs (6: not by the book's quote style)
- [ ] (Low) An accent told from an i-dot or a speck by its shape over its own letter,
      with tesseract's per-letter boxes (`hocr_char_boxes`, real since checked
      2026-11-03); ~50 real accent errors left on tuning
- [x] ~~A Dutch line-end break between clashing vowels keeps its hyphen~~ (2026-11-06,
      `hyphens.vowel_clash`, a word of four letters or more after the break, no glide
      before it): tuning 3 fixed, validation 1 ("mini-jurk"), none made
- [x] ~~(Low) Line-end compounds by definition~~ (2026-11-08, branch `hyphen-rules`, merged
      once `src/` is free): an all-capitals part before a lower-case one keeps the hyphen
      ("NSB-leden"), a stem left open before "en" where the word after is a compound whose
      end joins the stem ("voor- en achterbank"); tuning 8 fixed, validation no change

## One path for every doubt (the user, 2026-11-10, first)

The user, reviewing Nervous System: "when you ask me for review, it's to settle who is right.
i should be offered everyone's opinion and they should already have 'duked it out'. only when
their differences can't be settled, it goes to me. that's the whole point, no?" The OCR check
works so; the quote check, garbled lines, headings and washed-out pages raise questions on
side paths that skip the judges and the arbiter, and their cards show one or two readings.

- [ ] Every doubt becomes a suspect on the OCR check's path: unpaired quote marks (the lines'
      readings by every reader, the marks judged), a garbled line (its readings judged as
      any other), a heading (asked only where the role evidence is split), a speck (read as
      a hyphen, a second stop, a quote mark). The arbiter learns the new kinds from labels:
      the user's answers of 2026-11-10 and the golden books' places of each kind
      The quote check first (design, 2026-11-10, not yet coded): reflow the layer early (no
      models), find `quotes.problems` per paragraph, and turn each into a reading of its line
      for the OCR check as reader `quotes`: open at the end → the last line with the closing
      mark; a closing mark with nothing open → the line without it (a speck), and the first
      line with an opening mark as a second reading; speech ending on a letter → a stop before
      the closing mark. The judges vote on the crop, the arbiter decides; a quote problem that
      went through the duel is no longer asked by the quote check (`quote_lines` less the lines
      with a `quotes` suspect). Arbiter features see `quotes` only through votes until retrained
      **Coded 2026-11-10, off** (`quotes.duel_readings`, `ROBO_QUOTE_READER=1`; design.md,
      Quote questions). Short test (`experiments/probe_quote_reader.py`, decisions.md): The
      Loudest Sound and Nothing's quote lines 81 → 12 with the judges right on 14 of 14
      checked, Nervous System's 6 → 3. **Benched 2026-11-11: tuning WORSE** (75 asked
      error places go unasked: a paragraph whose marks all became readings loses its
      quote question whatever the arbiter decides; decisions.md). Left: a paragraph the
      OCR check leaves unpaired is asked all the same, through the OCR check's question;
      short test on De tuin, Het heft and Au pair, then `bench tuning` and validation
      again; on by default if neither says worse. A wrong silent fix seen on the way: `quotes.closed_at_end` added a ’ the print
      lacks (The Loudest Sound, PDF 235); with the reader on that paragraph skips it, so
      check whether `closed_at_end` is still needed at all once the reader is on. Then the trust data
      rebuilt with the two readers and the arbiter retrained to weigh them
- [ ] Every card shows every reader's reading and every judge's vote, as the OCR check's do
- [ ] Measure: the questions a book like Nervous System leaves, by kind, and the silent errors
      on the benches before and after; the user sees the count and why each kind is still asked
      before reviewing again

## 3. The user's books after Stella

Books the user wants as EPUBs (Dutch, and since 2026-11-09 three English), none with a reference EPUB, each an IA Scribe
scan with its own hidden layer (Stella's format), in `work/<name>/` with a `book.toml`.
In this order:

| Book | Directory | Pages (body) | Scan | Watch for |
| --- | --- | --- | --- | --- |
| Herman Brusselmans, *Ex-minnaar* (Ooievaar 1998, 6th printing) | `ex-minnaar` | 284 (7–279) | 360 ppi | motto on p. 7 ("It's closing time", Leonard Cohen), set as an epigraph; drop cap; an OmniPage OCR of the same scan beside it (`omnipage.pdf`, worse: the motto's "It's" reads "h's") |
| Herman Brusselmans, *De kus in de nacht* (Prometheus 2002) | `de-kus-in-de-nacht` | 620 (7–616) | 300 ppi, large pages | parts ("Deel een", "Proloog" on p. 7), small-capital openings |
| Emmanuel Carrère, *Andere levens dan het mijne* (De Arbeiderspers, tr. Floor Borsboom) | `andere-levens` | 248 (9–244) | 360 ppi | library copy; French names and accents |
| Emmanuel Carrère, *Een Russische roman* (De Arbeiderspers, tr. Marianne Kaas) | `een-russische-roman` | 276 (7–271) | 360 ppi | library copy; seven parts, each a small number atop its own page (pp. 7, 47, 131, 169, 233, 259, …) with pencil marks the layer reads as noise (pre-check, no OCR check: part "1" read "I" and dropped as a page number; the marks kept as running text, "Fyarvin er pan ee Ka": see what the full build asks, then decide on a rule); p. 272 show-through only |
| Mirko Bonné, *Hoe wij verdwijnen* (Querido 2011, tr. Elly Schippers; added 2026-11-01) | `hoe-wij-verdwijnen` | 300 (9–295, by `init`) | IA Scribe | dedication (p. 9) and a Camus motto (p. 11) before the text; timed end to end, `init` to EPUB |
| Jan Lars Jensen, *Nervous System* (Icon Books UK 2007; added 2026-11-09), the first English one | `nervous-system` | 296 (11–290, by `init`, the end moved one page) | IA Scribe, 360 ppi, Milton Keynes library copy | a library label on the dedication page (p. 11); four part pages; small capitals (RCMP, TV, CBC); "A Note to Readers of the UK Edition" (pp. 285–288) only in this edition; a second scan of the same setting (US Carroll & Graf 2005, 500 ppi, ABBYY layer) in `work/nervous-system--scan2/`, four PDF pages earlier, a few words localised ("RCMP" → "police", "page" → "shelver", "May" → "November") |
| Jane Gardam, *Going into a Dark House* (Abacus 1997 printing; added 2026-11-09) | `going-into-a-dark-house` (scan in `work/candidates/incoming/`) | 196 | IA Scribe 5.2 | short stories: story titles as headings, a contents page |
| Clare Wigfall, *The Loudest Sound and Nothing* (Faber 2007; added 2026-11-09) | `loudest-sound-and-nothing` (scans in `work/candidates/incoming/loudest-{1,2}/`) | 244 | built from scan 2 (IA Scribe 4.4, first printing 2007); scan 1 (Lura-recoded, ABBYY layer, paperback 2008) the same setting at the same PDF pages (190 of 194 text pages match) as a witness | short stories |
| Louis Paul Boon, *Pieter Daens* (Singel Pockets 1997; added 2026-11-01) | `pieter-daens` | 804 (body about 9–787: foreword to sources) | IA Scribe, Leeds library copy | six parts ("Boek een" … "Boek zes") and chapters headed by years; a motto (p. 7); a two-page table of contents (pp. 11–12) to leave out; the layer lacks "Boek vijf / Onze doden" (p. 527, printed 525); show-through read as text on pp. 8, 14; verse (p. 354); a sources list at the end; timed end to end |

- [x] Hoe wij verdwijnen reviewed by the user (2026-11-02, 53 answers in two rounds; the
      review smartened between them); rebuilt with them, epubcheck clean
- [ ] **user**: Pieter Daens' review, 292 questions (rebuilt 2026-11-03 with every change of the 2nd)
- [ ] **user**: Hoe wij verdwijnen's spot-check, PDF pages 41, 77, 87, 144, 292
      (`experiments/spot_check.py`, work/probes/spot-check/hoe-wij-verdwijnen/index.html):
      wrong words, breaks and italics counted per page, the book's own error rate
- [ ] Each book in turn: check its front and back matter and `body_pages`, build (cold
      ~1 min a page: Ex-minnaar ~4 h, De kus ~10 h), sample the questions, **user**
      reviews, rebuild, epubcheck, a **spot-check** (5 random pages drawn by a script,
      the **user** marks every wrong word, break and italic against the scan, ~15–20
      min: the book's own error estimate with its interval), **user** reads the EPUB
- [x] Nervous System built cold (2026-11-09, judging finished on the new judge order;
      epubcheck clean): 520 OCR suspects, 285 fixed, 23 asked. The second scan as a
      witness found two of our errors in 756 disagreements (decisions.md): not a stage
- [ ] **Nervous System's review, paused by the user after 10 of 70** (2026-11-10: "this is
      wasting my precious time with something i expect roboscriptorium to handle deftly and
      confidently"). Before asking again, every question sorted by what raised it, and each
      kind the machine could settle fixed at its source: the arbiter's pick bringing a
      straight quote into a curly book and the quote check then asking (PDF 37, 120, 201,
      235); a typed in-word apostrophe warned about; the 21 heading questions on a book whose
      headings are all right; the 22 OCR doubts. Then the count per kind, shown to the user
      with why each is still asked. The same for Going into a Dark House and The Loudest
      Sound and Nothing before they are reviewed
- [ ] **Short-story collections: a running head per story** (found 2026-11-10 on Going into
      a Dark House, 165 questions): each story's title stands atop its odd pages, the book's
      on the even ones. The line-role trees, trained on novels only, call the story heads body
      at 0.5–0.75 ("Blue Poppies", "Bevis" kept, some glued to a story's first words), and
      took the book's title as a story heading on PDF 128; the layout model calls every
      story head a title (64 "layout-title" questions). The review catches them, a key each.
      Needs labels: a golden pair that is a short-story collection (gaps to hunt), then the
      role trees retrained. The Loudest Sound and Nothing is the next to show it
- [ ] Going into a Dark House: **user** reviews (165 questions; the dedication's "- For" has
      a speck before it, and PDF 90's show-through stands as a garbled motto, not asked:
      the page-kind model calls show-through a motto)
- [ ] The Loudest Sound and Nothing: **user** reviews (built 2026-11-10 04:24, epubcheck
      clean, 136 questions sampled: 61 OCR doubts, 35 quotes, 20 headings). Its headings
      are all asked where wrong: Blackpool's label ("BLACKPOOL LIBRARIES", "00430050" as a
      heading, PDF 7, a table at 0.95), the half-title (PDF 11), "The Numbers / NUMBERS",
      a story's first line in capitals swallowed into its heading ("Caro at the Pool / SHE
      FOUND HER AT THE SWIMMING POOL."), show-through on PDF 182. Its running heads (author
      and book title) stayed out of the text
- [ ] A story's first line set in capitals taken into its heading (The Loudest Sound and
      Nothing, PDF 57): the heading's lines and the opening's should split where the type
      changes from the title's to the text's capitals; check the heading-title rules
      (`chapters.title_lines`) against it
      Traced 2026-11-10 from the caches, no models: no rule does it. The line-role trees call
      "SHE FOUND HER AT THE SWIMMING POOL." a heading at 0.68 (the sorter alone said heading
      at 0.22), where they call "THEY STARTED TO DISAPPEAR IN FEBRUARY." (PDF 111, the same
      type and place) body at 0.89; the openings that run on mid-sentence are caught by
      `chapters.running_text`, these two end their sentence. So it is the trees' to learn: a
      line in small capitals at the text's leading above body, flush right, as the book's
      other openings are. It joins the short-story labels the step above waits for
- [x] Washed-out cards (the user, 2026-11-10, reviewing Nervous System: "what a mess"):
      the read model reads only lines holding ink, and a reading repeating a sentence is
      never offered (decisions.md); whether `faint.pages` should tell mottled paper from
      faint print is left open: contrast can't (both under 17 grey levels)
- [ ] **Line boxes off their ink** (the user, 2026-11-10, reviewing Nervous System PDF 92:
      "the yellow box is drawn wrong"). The layer puts "“Okay.”" at y 179–190 where the
      scan prints it at ~186–195, 6 points high, so the review's box and the crops the
      readers and judges see cut through the line: glm-ocr and Qwen dropped its full stop,
      and every judge and the layer agreeing on "“Okay.”" still left a question. Measure how
      often (a first count with a shifted-box test found none, so the test is wrong: fit
      each box to the ink band nearest it instead), then fit boxes to the ink before
      cropping; upstream of every reader, so through the frozen tryout sets and a bench
- [ ] **The arbiter asks where every judge and the layer agree** (same card: text layer,
      tesseract and all four judges on "“Okay.”", only glm-ocr and Qwen without the stop):
      read the arbiter's sureness on Nervous System's 22 asked suspects, and whether English
      books have too little trust data
- [ ] **Bulleted lists** (the user, 2026-11-10, reviewing Nervous System PDF 117: "should i
      use a ■ here?"). The book sets lists with small square bullets (PDF 117, 259); the layer
      reads each bullet as "e", "¢" or "*", one line is asked and the rest go into the text
      silently ("e new organs in the body…"). Detect a list from the scan (a small mark left of
      an indented run of lines), build it as an EPUB list, and drop the misread markers; the
      reviewer answers the text without the marker meanwhile
- [ ] **A speck read as a hyphen before a line's first word** (labels from the user,
      2026-11-10: Nervous System PDF 118 line 2, "- I followed", a speck before the I; Going
      into a Dark House PDF 7, "- For"). glm-ocr and Qwen read the line without it, and the
      arbiter still asked (Nervous) or the line was never checked (Going's dedication). A
      hyphen alone before a line's first word is never print in a book whose dashes are long
      and spaced and whose lines never open on a dash elsewhere; a book that opens dialogue
      with a dash (Dutch) keeps it. Counterexamples first: dialogue dashes in the tuning books
- [ ] **A speck read as a second full stop** (label from the user, 2026-11-10: Nervous System
      PDF 119 line 25, "system.. He added", the layer, glm-ocr, tesseract, clef and d3 all read
      ".."). The book sets one stop or its measured ellipsis (". . .", `typography`), never two
      dots: a ".." that isn't the ellipsis with a dot lost is a stop and a speck. Counterexamples
      first: an ellipsis read short, an abbreviation's stop ending a sentence
- [ ] **A speck read as a quote mark after a word** (label from the user, 2026-11-10: Nervous
      System PDF 138 lines 8–10, "disaster’" where the print has "disaster" and a speck; the US
      scan's layer reads "disaster", so the witness agrees). It unbalanced the paragraph's
      quotes, so the quote card asked. With the stray hyphen and the second stop: specks the
      readers turn into marks, the pairs of quotes the book's paragraphs must make (an extra
      closing mark where nothing opens) and the witness are the evidence to settle them
- [ ] **A quote card shows only the OCR check's line and the read model's marks** (the user,
      2026-11-10, Nervous System PDF 120: "where are the other model's readings?"). By design
      (`pipeline.proposals`, `quotes.readings`), but glm-ocr's and tesseract's readings of the
      same lines are cached: offer them as witnesses of the marks, with their votes. The same
      card kept a speck read as " ." after the closing quote ("notice.” .")
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
- [x] ~~A comma at a line's end turned into a stop by the check~~: done 2026-10-24 as a rule true by definition (`ocrcheck.line_end_stop`, widened 2026-11-04 to a stop added after the last word; tuning 0.290 → 0.286, 6 fixed, none made). Before it (2026-10-20: decisions.md; the two arbiter features below were tried and NOT taken, tuning 0.29 → 0.30, glued or split words worse; look for another handle, or a rule true by definition): add
      "the next line opens in lower case" and "the span ends its line" as arbiter features at
      the next trust-data rebuild; 22 unasked errors in De vergelding and De kerk van de dode
      meisjes, 7 certain (a stop before lower case). Resolution doesn't help the readers.
- [ ] A per-book alphabet from the scan (the user, 2026-10-21; decisions.md has the assessment and the first test): glyph blobs from the line crop, clean ones (a third of lines) as labelled templates, then (1) can the dot of an i be told from an acute mark by shape against the book's own dots (the six real accent cases); (2) do odd glyphs (the dotless ı of "Sıla", five times in one book) cluster without labels, in about 30 questions a book at most; (3) as a detector over all glyphs, weighed by the arbiter. Kill after (1) or (2) if they don't separate. **(1) done 2026-10-24 (`probe_accent_shape.py`): AUC 0.66–0.76 at line level, too weak; parked until per-letter positions exist (decisions.md).**
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
      pays only in a band where the judge is wrong more than about one time in seven.
      From the 2026-10-24 hyphen-judge probe: Dutch real hyphens are 14 of 542 undecided
      breaks (3%), so no band pays; English 6 wrong of 30, near the price; not worth building
- [x] De eerlijke vinder's unasked errors (2026-10-15): 28 of 38 were page numbers the
      layer joins to a body line; split off (`pdf._apart`), wrong words 0.88 → 0.42 a page
      on the short test; `bench tuning` 0.32 → 0.30 after review, no book worse

## 6. Structure

- [x] Metro's lost closing quote after a spaced ellipsis (2026-10-16): the layer drops
      it, the readers write `. . . '`, curled as opening or not at all; now closed at a
      line's end and curled by the book's style, Metro 0.42 → 0.33 wrong words a page
- [x] ~~Verdict page: a place where one side has something the print lacks says so in words~~:
      merged 2026-10-17 (`review.py`: "the publisher's e-book has “>” here, our text nothing")
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
      out of the score as footnotes are (2026-10-24: 19 words on tuning, all asked: a caption
      is the one a reviewer gives, `figures.py`, so the bench counts them until answered; low)

## 7. Better pixels: Internet Archive's own files

Public on public-domain items only (Crime, Dolittle); private on lending-library items.
Sharper pixels lower the readers' errors at the source, the other way at the errors every
reading shares: many are specks and faint marks.

- [ ] JP2s as the image source for public-domain books (a borrowed item offers no
      downloads, so not for Stella or the user's books): on Crime's 50 reader-set lines
      both readers err about a fifth less (glm-ocr hard CER 1.57% → 1.26%, Qwen 1.78% →
      1.36%; `experiments/probe_ia_images.py`, 2026-10-11). Later, with public-domain books
- [x] ~~ABBYY's letter confidence as an arbiter feature~~: dropped 2026-10-24 without a
      probe: only the public-domain items (Crime, Dolittle) have their `_abbyy.gz`; a
      lending-library scan (Stella, the user's books, every other pair) keeps it private,
      so the target books could never have the feature

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
- [x] ~~The dash style of an image-only scan, measured on the image~~: done 2026-10-24 (the first
      reading's words, the stroke cropped on its line's height; Goede dochter without its layer
      23 of 26 dashes against 5, Vanille's typography 0.56 → 0.00). The ellipsis the same way
      was vetoed by validation (the readers told ". . ." read Vanille worse; decisions.md):
      measuring it for typography alone, not the readers' prompt, is left. Before (2026-10-23):
      tesseract glues most dashes to their neighbours, so its words can't be measured as the
      PDF's own are; a long thin component at mid x-height between word gaps is a dash, and
      its length and gaps measured on the page image. Today an image-only scan falls back to
      the style read in the text (agent, ~half a day)
- [x] ~~An image-only scan through the whole pipeline~~: done 2026-10-23 (`work/goede-dochter--nolayer`,
      decisions.md): 0.84 wrong words a page against the layered 0.33, the gap tesseract's reading;
      italics from the first reading's word boxes since (323 of 364). Dashes wait on the item above

## 9. Golden books and housekeeping

- [ ] **user** More golden pairs when convenient: Koning Wilders (Atlas Contact) and Het
      laatste bevel (Manteau) came in 2026-10-11; De Arbeiderspers, Prometheus/Ooievaar or
      Vrijdag next; a Kosmos book for later, beyond prose
- [ ] **user** Settle verdicts on the tuning books (`review` on each), the disagreements
      the arbiter's labels sit on first: hours, spread out, whenever convenient
- [x] ~~Remove the `baseline` and `qwen2` worktrees~~ (gone by 2026-10-24)

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

- [x] 2026-11-06 Qwen3.8-Flash-Next UD-Q2_K_XL (Unsloth Studio, part on SSD) as a reader or
      witness: rejected, on the quiet set's 23 lines every reader gets wrong 0 of 5 plain,
      4 of 23 with the crop doubled (two real), 2 of 12 thinking, contradicts 3 of 170
      right lines plain, ~15 s a line (models.md)
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

- [x] 2026-11-09 `init` carries the text on over a page under the book's running head
      (`pagekinds.run_on`): Nervous System's last end right (PDF 290), the 27 labelled books
      unchanged (23 first, 22 last); the neighbours' kinds told to the model were null
- [x] 2026-11-09 `init` starts the text proper after the front's title or copyright page
      (`pagekinds.after_title`): first ends right 23 → 26 of 27, Going into a Dark House's
      author blurb before its title page left out

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
