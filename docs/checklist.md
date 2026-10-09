# Checklist

The plan, step by step, in the order it runs: what is done, what is left, who does
it and how long it takes. Every step is the machine's unless it says **user**. A
time is an estimate until the run is timed through `experiments/timed.sh`
([run-times.md](run-times.md)); then the measured time replaces it. A dropped step
stays, struck through, with why. Updated in the same change that ticks, adds or
drops a step.

**The plan now:** make measurement trustworthy, then let the bench decide whether
two unmeasured changes to the OCR check stay: the third reading (Qwen, told the
book's style) and reading short lines too (Goede dochter: +18 suspects, ~3 real
errors). Both are in the build until the bench in 3 decides. First the trust data
for every tuning and validation book (section 2's queue, three at a time, Qwen read
through OpenRouter with the user's go; clef stays local, its hosted builds failed 3b's
test); the faster readers tried in 3b didn't beat Qwen.

## 1. Measurement that can be trusted

- [x] A missing or stale trust model stops the build (`trust.Mismatch`): no silent
      fallback to the fixed rule.
- [x] `eval` records the decider, the settings and the model versions: a score can
      be traced to what made it.
- [x] `roboscriptorium bench [tuning|validation]`: pinned slices, one JSON per run,
      paired page-by-page comparison.
- [x] One primary test, books weighing the same, a per-book veto (99%, ≥ 0.05
      words/page): no verdict from noise or from the three longest books.
- [x] The reviewer's slip rate as an interval (8 of 68, Beta posterior): "after
      review" isn't scored as if answers were free.
- [x] Leave-one-out trust models (`ocr-trust-without-<book>.pkl`): tuning books
      aren't scored by a model that saw them.
- [x] The four "held-out" books renamed validation: honest about having looked at
      them.
- [x] `docs/design.md` (why each component is there) and `docs/decisions.md`:
      nobody rediscovers the reasons from data.
- [x] Long runs timed (`experiments/timed.sh`, `docs/run-times.md`): an estimate
      before a run starts.

## 2. Trust data rebuilt with the third reading and short lines

One book per run, `experiments/ocr_trust_data.py --rebuild <book>`, on the fixed
rule. About 1.1 min per page cold (Dolittle; Crime and Vals alarm ran at 0.8; Metro
1.5, partly in Low Power Mode); a top-up after the short-line change reads only the
short lines. Qwen's reading of every line is 70–75% of a cold run (3b).

- [x] Goede dochter: 3 min (Qwen readings cached), top-up 2 min
- [x] Vals alarm: 39 min cold, top-up 2 min
- [x] Crime: 81 min cold, top-up 1 min
- [x] Dolittle: 98 min cold (642 → 684 suspects; layer wrong on 374 → 396 settled)
- [x] De tuin van de avondnevel: 51 min cold (389 → 472 suspects; layer wrong on 310 → 350 settled)
- [x] Grand Hotel Europa: 32 min cold (125 → 173 suspects; layer wrong on 79 → 99 settled)
- [x] Stella, labelled by the user's answers: 53 min cold (65 → 66 suspects; layer wrong on 34 settled, unchanged: only answered places are labelled)
- [ ] ~~Lady into Fox: ~1.7 h cold~~ dropped: retired to reserve (its reference's typography differs from the print), so no validation data is needed from it
- [x] Crime and Dolittle relabelled with the score's fold: under a minute each, warm.
      Labelled before it, their spaced ellipses (`you. . . .`) and spaced colons
      (`listen :`) counted the faithful reading wrong. Settled 223 → 222 and 582 → 561;
      clef right on 85% and 93% of them (was 84% and 91%)
- [x] Metro 2033, pp. 7–111: 156 min cold, partly in Low Power Mode (917 suspects, 801
      settled, layer wrong on 204; clef right on 92%, winnow 38%)
- [x] Metro relabelled the same way: under a minute (settled 852 → 801)

The queue, in run order, before the baseline in 3 so the baseline includes every book.
Local and hosted Qwen proved interchangeable (3b) and the user said go: Qwen reads
through OpenRouter and three books run side by side (the GPU still does glm-ocr and
clef for each, so ~1.3–1.5× rather than 3×; ~$1.40 for all the hosted reading left):

- [x] Artemis, pp. 13–80: 63 min, Qwen via hosted, beside other runs (317 suspects, 273
      settled, layer wrong on 207: its `|` for I; clef right on 87%, winnow 83%)
- [x] 11/22/63, pp. 15–94: 14 + 35 + 46 min over three runs (Ollama stalls), Qwen via
      hosted (357 suspects, 319 settled, layer wrong on 188: its I read as T or |; clef
      right on 86%, winnow 73%, and right on 31 of clef's 46 misses). At most three
      pipelines at once, re-reads included
- [x] De cipier, pp. 9–92, Qwen via hosted, beside other runs (429 suspects, 327 settled,
      layer wrong on 97; clef right on 94%, winnow 52%)
- [x] Afscheid van verspilde tijd, pp. 9–70 (tuning): 40 + 18 min, Qwen via hosted
      (stopped once when a probe beside three runs ran the GPU out of memory). 266
      suspects, 240 settled, layer wrong on 88
- [x] Hosted clef as the judge, measured before any use (user's go, criteria fixed
      first: same pick ≥ 97%, no fewer right, median confidence shift < 0.05), Goede
      dochter's 419 suspects (`experiments/probe_hosted_judge.py`): PrimeIntellect's
      build hardly reads the image (70% same pick, right on 275 of 377 against local's
      352); Cloudflare's 96.2% same, 348 right, shift 0.063. **Fails all three: clef stays
      local.** The client stays (`ROBO_JUDGE_VIA`), for a later build
- [x] Reis om mijn schedel, pp. 11–110 (tuning): 46 min, Qwen via hosted. 480 suspects,
      363 with a clear label, layer wrong on 94
- [x] De eerlijke vinder, pp. 12–95 (validation, held out): 86 min, Qwen via hosted.
      895 suspects, 829 with a clear label, layer wrong on 85
- [x] You're Never Weird on the Internet, pp. 13–94 (validation, held out): 66 min,
      Qwen via hosted. 317 suspects, 283 with a clear label, layer wrong on 87 (lost
      apostrophes, `Fie` for "He", missing spaces, real-word slips); clef right on 268

## 2b. New golden pairs (Fable's session, ended; its steps are this session's now)

Placed under `work/` like the others: the scans in `work/<book>--ia-scan/source.pdf`,
the publisher's EPUBs in `work/.cache/publisher/<book>.epub`.

- [x] `experiments/probe_candidate.py`: a no-model check of a scan and EPUB pair
- [x] Afscheid van verspilde tijd (Wijkmark, Rode Kamer 2011): manifest, derive
      (spaced hyphens as en dashes, `hyphen_dash`), fetch; in `bench tuning`
- [x] Het geluid van bananen (Temelkuran, Van Gennep 2013): manifest, derive, fetch,
      then **untouched**: the `test` bench set, which won't run without a flag, in no
      trust data
- [x] Metro 2033 (Gollancz 2010, transl. Randall), the second modern English scan:
      chapters 1–5 (pp. 7–111) in `bench tuning`
- [x] `evaluate.normalise` folds spaced dots; scores count what the fold forgave per
      kind. The trust labeller now folds through it too (section 2's relabels)
- [x] De cipier, a pair with no known deviations: chapters 1–4 (pp. 9–92) in
      `bench tuning`
- [x] Artemis: chapters 1–3 (pp. 13–80) in `bench tuning`
- [x] 11/22/63 (Scribner 2011), the first American scan and the heading test (386
      headings): the prologue and chapters 1–3 (pp. 15–94) in `bench tuning`
- [x] Grand Hotel Europa retired to reserve, De eerlijke vinder into validation in its
      place (another printing than its EPUB; 9 of 16 reference headings not on the scan)
- [x] You're Never Weird on the Internet (Touchstone 2015, 5th printing, against the
      edition's ebook): validation, pp. 13–94 (sections 1–16), the only English one
- [ ] Dolittle's captions scored properly: derive them into the reference, or leave
      caption lines out of the score as footnotes are
- [x] Retirement rule in AGENTS.md, with per-book signals in the bench diagnostics
      (`golden/signals.py`: layer CER and unplaced body lines, a suspect named)
- [ ] `golden check <pdf> <epub>`, writing a draft manifest: worth it once a batch
      of candidates comes
- [ ] **user** Hunt for modern English Scribe scans with the publisher's EPUB of the
      same printing (two more unblock the line-role classifier in 6)

## 3. Baseline, retrain, bench, decide

- [x] Baseline bench on the fixed rule (`ROBO_OCR_TRUST=0 … bench`): 32 min warm
- [x] Retrain trust and compare with the before-Qwen data: silent errors at 0/.25/.5/1
      questions a page, each book left out: Goede dochter 25/17/13/5 → 5/0/0/0, Crime
      12/6/4/2 → 9/2/1/0, De tuin 24/17/11/6 → 16/12/10/4, Dolittle 31/9/5/2 → 23/10/7/2;
      Vals alarm worse, 5/3/2/1 → 9/7/4/4 (its lost full stop is in no other book)
- [x] `train_ocr_trust.py --save` (the main and the leave-one-out models): 8 s, 3,841
      suspects from 11 books
- [x] `bench tuning` with the retrained arbiter: 1 min warm. After review 1.80 → 1.53
      wrong words a page over the set ([-0.57, -0.09], all three slip rates), with
      questions 3.1 → 1.6 a page. **Vetoed by Metro**: after review 4.08 → 4.63, its
      unasked word breaks 342 → 441 (the arbiter keeps the layer where the rule asked)
- [x] Metro's word breaks: its spaced ellipses (`people . . . The`), which reflow's
      tidying squashed to `people...`; 235 of Metro's 297 remaining differences. Each
      book's ellipsis style is now read in the layer and set on every ellipsis
      (`typography.py`); Crime's reference gets back the space its print sets
      (`ellipsis_space`). Bench tuning, 1 min warm each: with the arbiter 1.53 → 1.00
      after review (Metro 4.63 → 0.43, Artemis 1.18 → 0.68, 11-22-63 2.13 → 1.08, none
      worse); the fixed rule 1.80 → 1.37
- [x] The retrained arbiter against the fixed rule, both with the fix: **better, no
      veto**: after review 1.37 → 1.00 ([-0.66, -0.21]), eight books better, none worse
- [x] Afscheid's slice: pp. 20, 32, 70 are washed-out pages whose layer is noise, kept as
      body text (should be flagged as garbled); p. 37's text fails to align. ~280 wrong
      words each, in both arms. Done as `faint.py`: a page whose ink barely stands off
      the paper (under 30 grey levels; washed-out pages under 10, printed ones 48 or
      more over 18 books) is one `washed-out` region. 31 pages in 3 books (Afscheid's p.
      38 the one meant by "p. 37"). `bench tuning` **better**, after review 1.02 → 1.00
      [−0.04, −0.01]; validation unchanged. The words stay wrong until a human types
      the page
- [x] The read model's cache held one prompt, so a slice whose style prompt differed
      (Dolittle 23–88 against the whole book) evicted every reading. Readings by another
      prompt are now kept aside, and the style is measured on the whole body; tested
      through `pipeline.run`. Vals alarm and Dolittle get a new prompt: their trust data
      rebuilt with hosted Qwen (the user's go for tonight's Qwen reads)
  - [x] `bench tuning` against the ellipsis run, with the winnow switch (Ollaya is gone,
        so the two are measured together): 1 min warm. **No change**: after review 1.00 →
        1.02 [−0.02, +0.07], no veto; 11/22/63 before review 7.23 → 6.08 (the book-wide
        ellipsis style), the arbiter asking those lines already. Trust data first: 61 min
        for 11 books, then Stella stalled on DeepInfra (down, 0% uptime on OpenRouter) and
        was finished by local Qwen in 4 min
- [x] `bench validation`: <1 min warm, the first run, so the baseline (after review: De
      tuin 0.79, De eerlijke vinder 1.28, You're Never Weird 1.07, Villa Toscane 0.12)
- [x] **Decide:** keep Qwen's third reading and short lines only if the bench says so.
      **Qwen stays**: without it (trust data rebuilt, 19 min; the arbiter retrained in
      `work/models/no-qwen/`) `bench tuning` is worse, 1.00 → 1.33 after review [+0.07,
      +0.75], and `bench validation` 0.81 → 1.01 [+0.12, +0.27]. Short lines stay: they
      have no switch to ablate and add a few suspects a book (Goede dochter +18)
- [x] Re-ask ~200 cached clef answers and count the flips (answer variance): all 518 of
      judge set v1 in 12 min (`tryout.py run judge clef:27b`): **2 flips**, both where it
      was all but unsure (confidence 0.02 and 0.1); the median confidence moved 0.001.
      Cached answers stand for fresh ones

## 3b. A faster line reader (Qwen is 70–75% of a cold run)

- [x] Where the time goes, from the stage caches' times: Qwen 70–75%, clef's judging
      20–25%, everything else ~15–20 min per 100 pages
- [x] Hosted Qwen3.8 27B (OpenRouter, Goede dochter pp. 9–20): DeepInfra bf16 reads
      like ours, Darkbloom fp4 worse. Not used: only when the **user** says so
- [x] gemma4:latest (8B) as the line reader: 4.5× faster, worse (quote marks wrong on
      4 lines against 0). Unfit
- [x] qwen3.6:35b-a3b-nvfp4 (MoE, 3B active): 0.37 s a line, but it reads the style
      sentence as an order and wraps plain narration in quote marks (94 lines wrong,
      CER 0.67%). Out
- [x] gemma4:26b-nvfp4 (MoE, 4B active): on Goede dochter the best reading yet (CER
      0.07%, 314 exact, 3.5× Qwen's speed, one invented opening quote); on Metro CER 23%,
      reading whole lines that aren't the cropped one. Out
- [x] Crossover, not only the best model (`experiments/probe_reader_crossover.py`): on
      Goede dochter pp. 9–20 only 1 of 324 lines has no current reading right, so no
      candidate can add much there; the errors left come from choosing, not from missing
      readings
- [x] The crossover on Metro pp. 7–30 (954 body lines, English): again only 1 line has no
      current reading right. gemma4:latest adds 0 there, is wrong on 288 lines the layer
      has right, and writes text that isn't on the line (whole invented clauses)
- [x] The rule, decided before the results: switch only if ≥ 3× faster **and** no
      worse (quote marks wrong on no more lines than Qwen3.8's, CER within a few lines of
      it), confirmed on Metro before the switch; better but not faster: noted; faster but
      worse: out. Every candidate also goes through the crossover on Metro
- [ ] ~~winnow:12b as the second judge~~ dropped: Ollaya, its only server, was uninstalled
- [ ] MiniCPM-V 4.6 (May 2026, 1.3B, `minicpm-v4.6`), the last small candidate: after the
      baseline. A new reader only pays off by speed, since the current ones already
      cover nearly every line
- [x] The two failed MoE models take 39 GB: **user** said remove them; deleted (2026-10-09)
- [x] Hosted Qwen3.8 bf16 on Metro pp. 7–30 (the user's go): the same as local on 97% of
      lines, 935 exact against 934, 14× faster; reads beyond its line on 7 of 958 (local 1)
- [x] **The crop bug.** `ocrcheck._line_crop` pads each line 3 pt above and below its
      layer box; where boxes are as tall as the line pitch, that reaches into the next
      line, and glm-ocr and Qwen read part of it (Metro p17: the line above, readable).
      Share of crops reaching into a neighbour's box: Metro 97%, Dolittle 91%, Crime 87%,
      De tuin 50%, 11/22/63 37%, Reis 28%, Goede dochter 15%; Artemis, Vals alarm,
      De cipier, Thief-Taker and You're Never Weird under 5%
  - [x] `crop_span`: the pad stops at a neighbour's box (half a point of slack); only
        lines whose crop changes get a new cache key, so only they are read again.
        Regression tests on synthetic tight and loose pages
  - [x] Before and after on Metro pp. 7–30 with glm-ocr (`experiments/probe_crop_span.py`):
        738 of 983 crops change; on them CER 1.87% → 0.29%, exact 630 → 639, better on 25
        lines (no longer reading the neighbouring line), worse on 13 (the model's noise on a
        crop moved by a point: the quote it dropped is plainly in the new crop)
  - [x] Committed (`565e9bf`). Hosted Qwen on the new crops (the user's go): on the 737
        changed lines CER 0.04% against local Qwen's 0.20% on the old crops, 722 exact on
        both, no neighbouring clauses read
  - [x] Re-read the affected lines and rebuild the trust data of the books done on the
        old crops, one book at a time, each checked before the next (Qwen via hosted, the
        user's go):
    - [x] Goede dochter: 2 min; 79 of 1,730 crops changed; glm-ocr unchanged (65 exact),
          Qwen 65 → 66; 419 suspects, settled 376 → 377. Neutral
    - [x] Local against hosted Qwen, both on Metro's 738 new crops, against criteria fixed
          before the result: exact 720 / 722 (±5 ✓), quote marks wrong 1 / 2 (±2 ✓), read
          beyond the crop 1 / 1 ✓, the same reading on 97.6% ✓. **Interchangeable.** For
          local Qwen the crop fix is neutral (722 → 720 exact); it is glm-ocr that gains
    - [x] De tuin: 4 min; 101 of 1,440 crops changed (the overlap estimate counted any
          touch; the fix cuts in only past half a point); glm-ocr exact 78 → 83, Qwen 93 →
          90 (noise level); 472 → 473 suspects, settled 454 → 455. Neutral to positive
    - [x] Crime (after two stops: Ollama stalled for all runs at once, then recovered on
          its own): 823 of 2,336 crops changed; glm-ocr 758 → 755 exact, Qwen 774 → 770,
          the worse lines the models' habits (`suredly` → `surely`), not the crop; 257 →
          262 suspects, settled 222 → 231. Neutral
    - [x] Dolittle (resumed after a GPU out-of-memory; 40 + 3 min): 3,279 of 3,658 crops
          changed; glm-ocr CER 0.69% → 0.64%, exact 2,924 → 2,923; Qwen 0.57% → 0.58%,
          exact 2,922 → 2,921; 684 suspects, settled 561 → 570. Neutral
    - [x] Metro: 34 min; 3,067 of 4,285 crops changed; glm-ocr CER 2.24% → 0.27%, exact
          2,643 → 2,683; Qwen 0.39% → 0.03%, exact 2,995 → 3,006; 917 → 835 suspects,
          801 → 745 with a clear label, layer wrong on 204 → 222. A clear gain
    - [ ] ~~Stella~~ dropped: 330 of 1,994 crops change, but only ~10 of its 61 suspect
          lines; its labels are the user's answers, so new suspects would be unlabelled.
          Its next real build reads the new crops anyway
  - [x] **The user's idea, a crop fitted to each line's ink** (`experiments/ink_crop.py`):
        tried and not adopted. Measured with no model (`probe_crop_ink.py`), the box crop
        holds slivers of other lines' ink in 50–87% of crops (1–2.5 pt: descender tips)
        and cuts 1–2.5 pt of its own in up to 37% (11/22/63); the ink crop takes both to
        0–2%. But the readers read no better from it: glm-ocr exact on Metro 830 (box) →
        817 (ink), on 11/22/63 619 → 621; Crime's check read both ways, Qwen 774 → 752
        with the ink crop. Neither slivers nor cut tips trouble a reader; the next line did
  - [ ] A reading far longer or shorter than its line counting as no reading, if readers
        still stray after the fix: measured by `bench`
- [ ] Qwen on fewer lines (dialogue, quote marks, disagreements) or smaller crops:
      after the baseline bench, each measured by it

## 3c. A reader of the finished text

Every check so far starts where the OCR readings disagree; a mistake all readings
share, or one reflow makes, is never looked at. A model reading the built text
paragraph by paragraph can see a sentence that breaks off, a word that makes no sense,
a running head or picture text inside a sentence, a paragraph split mid-sentence. The
danger is that it edits the author. Guards, all of them:

- **It only asks, never changes.** Its output is a place and a kind, never replacement
  text: the reviewer sees the crop and decides.
- **Closed options, no free text.** A decision with declared kinds (sentence broken
  off, word that isn't one, furniture in the text, picture text, paragraph split or
  merged, none), nothing like "could read better". Bounded answer, so a decision model.
- **Told what the text is:** a transcription, whose spelling, grammar, dialect and style
  are the author's and stay; only faults of reading or layout count.
- **The counterexamples first.** A set of places where it must stay silent, written
  before the ones where it must fire: deliberate misspellings and play (`Vidya Gamez!`,
  `Fevah`, `Meeeeee`, `#lookit` in You're Never Weird), fragments ("Raised without
  clocks."), dialogue that trails off, foreign words (De tuin), names. Its silence there
  is measured, not hoped for.
- **Measured as a question source by `bench`:** how many remaining errors its questions
  catch against how many it costs, with the reviewer's slips. A flag where the output
  already matches the reference is an editorial urge, and that rate is reported.
- **Grounded where possible:** a flag counts for more where the machine touched the
  text (a line or page join, a de-hyphenation, a word the readings disagreed on, a
  word the word list lacks), less in untouched running text.

- [x] First probe, the user's free-text prompt ("find technical flaws, not prose"),
      gemma4:latest on Goede dochter's first 200 paragraphs (`experiments/probe_text_reader.py`):
      56 flags, ~4 real errors pinpointed (`we-bril`, `aaN-knop`, `Kedsgympen`, a lost
      closing quote), 46 on correct text (whole sentences as "punctuation"), 3 quoting
      text that isn't there (dropped by the verbatim check). Real catches, far too many
      urges: next, a larger model and a tighter format (a short quoted span, or one
      decision per paragraph)
- [x] The user's idea: a decision model after the generative one, to force a strict
      answer. clef asked of each flag "fault of scanning, or the author's text?": at
      P(fault) ≥ 0.3 it keeps 9 of 45 flags and both clear catches, dropping 31 of 37
      urges; with the line's scan crop it does no better (keeps 5, drops `ALLEs $1`).
      Both drop a real lost closing quote. The weak part is now the proposer
- [ ] Probe: a stronger proposer (Qwen3.8 with thinking on, or gemma4:26b) with clef
      as the filter, on Goede dochter's and Metro's built text, scored against their
      known remaining errors and the counterexample set: catches, false alarms, editorial
      urges. After the baseline bench; roughly a tenth of the line readings' calls
- [ ] If it earns it: a stage after reflow that emits review questions, decided by `bench`

## 4. The user's part

- [ ] **user** Slip rate per question kind: answer the review on Goede dochter
      pp. 9–64, scored against the aligned truth. **After the retrain, with trust on**:
      tried on the fixed rule on 2026-10-08, it asked 215 questions, nearly all obvious
      (`ven eeuwigheid`, `drijthout`, words the word list and clef settle), which would
      measure a near-zero slip rate on questions trust never asks. 6 answers kept in
      `work/probes/slip-rate/`, out of the book's folder so no build applies them
- [x] Review page: the doubt's whole line tinted, its place underlined beneath the print,
      nothing drawn over the letters (the box hid the quote marks it asked about); softer
      colours; `h` turns highlights off, remembered
- [ ] **user** Settle verdicts on the tuning books (`golden review`), the
      disagreements trust's labels sit on first: hours, spread out

## 5. More for the trust model

- [ ] A book-quality feature (winnow's alarm is worthless on clean books): after
      the slip-rate answers in 4
- [x] Per book, clef against winnow on the trust data, printed by `train_ocr_trust.py`,
      a book flagged where winnow is ahead (Lady into Fox: clef 36%, winnow 89%; every
      current book clef ahead)
- [x] `train_ocr_trust.py` uses only data that exists and has every current reading
      (it used to start a cold build of a missing book, and Reis's pre-Qwen data would
      have taught "Qwen never backs a version"); its leave-one-out analysis no longer
      trains on validation books; `--save` refuses while tuning data is missing
- [ ] Thief-Taker's suspects in the trust data, pp. 11–84 (chapters 1–22, its
      `bench tuning` slice): ~1.4 h cold

## 6. Other components, each scored by `bench`

- [x] An ellipsis style in `typography.py` (`326a89d`), read in the text layer or set in
      `book.toml` (the glyph, dots or spaced dots, a space before or not), not measured on
      the page. Bench tuning after review 1.53 → 1.00 (Metro 4.63 → 0.43)
- [ ] Italics measured on Metro's typeface: 360 italic words found against the
      reference's 59 in chapters 1–5 (heuristics only)
- [ ] Line-role classifier into the package, behind a switch
- [ ] A crop reader on tesseract's line boxes (not the layer's)
- [x] `quality.catches` matches by span where flags have one: a question about one place
      catches only errors sharing a word with it (6g)
- [ ] Training code for shipped models into the package, with a feature-count test

## 6g. Fable's second review (2026-10-09)

What the bench couldn't see, and leaks in the OCR check, found in a review of the whole
build. Each change benched on its own.

- [x] The bench counts paragraph breaks set wrong, per page (`disagreements.break_errors`,
      where both sides' words align), and a change that clearly moves them decides like
      the words. Tuning per page: Afscheid 1.73 and Artemis 1.29, the rest 0.01–0.42
- [x] A question about one place in a line catches only the errors at that place; a typed
      washed-out page counts a question per line. Tuning after review 0.48 → 0.56 by this
      alone (Afscheid 0.25 → 0.64, 11/22/63 0.83 → 0.99, Reis 0.24 → 0.32): the new baseline
- [ ] The ellipsis glyph is no OCR difference (the typography stage sets it book-wide), and
      the trust labels stop forgiving a space before a quote that no stage removes; trust
      data relabelled, arbiter retrained (~45 min, done), bench
- [ ] Paragraph starts in runs of one-line dialogue (the window's margin was the indent),
      after a blank line, and in letters spaced apart: page margin fitted from full lines
- [ ] The bench records how much of each book's Qwen reading was the hosted build
- [ ] The arbiter calibrated (isotonic, on its leave-one-book-out predictions), so the 0.8
      ask threshold means 80% right whatever the retrain
- [ ] Italic scores marked unscored where the reference sets italics unlike the print
      (Metro's station names, You're Never Weird has none)
- [ ] Scene breaks: "* * *" lines and blank-line gaps as a break in the IR and the EPUB
- [ ] Budget diagnostics: questions of one reason asked in a shuffled order, not page order
- [ ] **user** Re-measure the slip rate on today's questions (picks with the difference
      marked, typed lines checked), pick and typed apart (~30 min of review)
- [ ] Qwen's readings of the bench books again locally, so the bench measures the build that
      is run (~1.4 s a line, ~12 h for 30k lines; or the user's go to read Stella hosted)

## 6b. Where the labelled suspects say the errors are (Fable's review, 2026-10-08)

Measured on the trust data and the golden slices, no models; the scripts and numbers
are `experiments/probe_trust_pair_prior.py`, `experiments/probe_hyphen_breaks.py` and
`work/probes/thinker-2026-10-08/NOTES.md`.

- [x] Line-end hyphens: reflow's decision was wrong on 29 of 1,574 decidable breaks
      (0.02–0.17 words a page, more than the OCR check leaves silent at one question a
      page). Now evidence in order (docs/design.md): the book's spelling, the word list,
      a capital (not a word in capitals), the parts beside an inner hyphen. 29 → 15; on
      warm caches Goede dochter pp. 9–64 WER 0.00211 → 0.00187, De cipier unchanged
- [ ] The 15 breaks left as a question: on an English book, a break the list is silent on
      whose parts are both words (13 right, 3 wrong on Metro and Artemis; 0 against 44 on
      Dutch, so never there), asked in the joined form the OCR check already has; scored
      by `quality` and `bench` as a question source
- [x] The substitution-pair prior in `trust.py` (model version 3, 23 features): the exact
      (layer → reading) difference, target-encoded from the training books, a pair counted
      when seen in ≥ 2 books, each training book's priors from the other books only (Opus's
      point: with only the row's own label out, [117, 50, 31, 11]). Leave one book out,
      silent errors summed over nine books at 0/.25/.5/1 questions a page: trees [153, 87,
      44, 23] → [110, 48, 25, 10]; at the rule's questions 7 → 7; stable to one more book
      left out (0–3). The trainer's logistic variant with the prior: [94, 43, 29, 15]
- [ ] Its own bench step after the baseline (3): baseline, trust without the prior (an
      empty table), trust with it. The saved model is still version 1: `--save` once the
      tuning data is complete, then both benches
- [x] The reviewer's answers checked before they are saved (`review.doubtful`): a typed
      line that matches none of the question's readings, or a straight quote in a book
      set with curly ones, is queried once and saved on the second Save; warned answers
      logged in `review/warnings.jsonl`, so the slip-rate review (4) measures slips before
      and after the check. No model call (Stella: transcribe-and-compare caught 9 of 9
      slips, 3 false alarms in 58). Left: comparing with Qwen's cached reading of the
      whole line for regions that carry no readings (headings, missing text)
- [ ] The book teaches itself: after the answers, a per-book posterior per substitution
      pair rescores the unasked suspects (`decide`, two passes). Simulated: silent errors
      at .25/.5/1 a page over nine books 50/31/11 → 47/30/11, Vals alarm 7/6/1 → 5/5/1
      (its lost full stop before a closing quote, 47×, is in no other book). After the
      slip-rate review; its review-page form is one question per pattern, applied to all

## 6c. Tryouts: a model screened for a role before the bench

- [x] Reader set v1 frozen (`experiments/tryout.py`, `tryouts/reader-v1.json`): 550
      lines of the tuning slices, 30 the layer reads wrong and 20 it reads right a book
- [x] gemma4 on the reader screen, the known-worse check of the screen itself: 9 min.
      Loses on every count: hard lines right 274 of 330 (qwen3.8 302, glm-ocr 294),
      control lines broken 10 of 220 (qwen3.8 3), the only reader right on 3 (qwen3.8 19)
- [x] PP-DocLayoutV3 as the spotter, Dolittle pp. 23–88 scored downstream: worse
      (CER 1.22% → 1.71%), not adopted
- [ ] ~~winnow:12b as the second judge~~ dropped: Ollaya, its only server, was uninstalled
- [ ] A judge set and a sorter set like the reader set, versioned the same way
  - [x] The judge role in `experiments/tryout.py`: settled suspects of the tuning slices,
        the vision judge's exact questions and crops, 25 it gets wrong and 25 right a book
  - [x] Build judge set v1 once the winnow trust data is in: 518 suspects
  - [x] imajev (mindchain, Qwen3.5 vision decision models, 2B/4B/9B Q8_0) for the vision
        judge against clef:27b. Ollama's systemone takes no images for GGUF models and a
        GGUF lacks imajev's trained readout, so it runs through llama.cpp on Ollama's blobs
        with the readout applied in `clients/llama.py`. Judge set v1 (518
        suspects), weighted right: 2B 80.7%, 4B 84.0%, clef 90.0%; 0.12 / 0.25 s a question.
        No replacement. **A strong alarm**: clef is wrong on 4.6% where the 4B agrees, 34%
        where it disagrees (winnow: 4% / 22%), and the 4B's own pick is right on 139 of the
        150 clef errors it flags. The 9B: 82.4%, weaker as an alarm on English books; the
        4B is the one to try in the pipeline. Decided: off (below); the 2B and 9B deleted
    - [x] As a third judge beside clef and winnow (the screen says it adds): not kept
      - [x] `trust.py` takes three judges by position (`ROBO_ALARM_MODEL`, off by default)
      - [x] Rebuild the trust data with the 4B's answers: 31 min for 14 books; retrain,
            bench: **no change** (tuning 1.02 → 1.01 [−0.04, −0.00], validation 0.81 →
            0.80 [−0.05, +0.02]), so it stays off. Training keeps only the configured
            judges' votes, and the arbiter without it reproduces the two-judge bench exactly
    - [x] Page types from the page image (nothing decides them yet; `body_pages` in
          book.toml): the 23 sample pages, 19 right like clef-flash, 1.4 s a page against
          3.9; then where the body starts and ends (`experiments/probe_body_range.py`,
          252 pages round both ends of 18 books' ranges): 227 right, clef-flash 231, the
          same pages missed (prefaces, forewords, blanks at the edges). **Not used**:
          `body_pages` stays in book.toml
    - [x] Which way a plate is up (the reviewer answers it now): Dolittle's 8 plates and
          2 upright pages, each rendered at four turns and asked "is this upright?"
          (`experiments/probe_upright.py`): **10/10**, P(yes) 0.95–0.97 on the right turn
          and under 0.1 on the others. Not wired in: the caption rule (`ocr.read_sideways`)
          already turns every captioned plate, and no golden book has a plate without a
          caption or one upside down, where the 4B would add. The candidate for that job
- [x] winnow on Ollama: the user pulled the Hugging Face GGUF; a Modelfile makes it a
      decision model (`modelfiles/`, AGENTS.md Environment). Screened on the cached
      suspects of Goede dochter, Vals alarm and Reis: right alone 285/208/265 against
      Ollaya's 174/174/174; right where clef is wrong 78 of 100 against 45
- [x] winnow-ollama:e4b as `check_model`, confirmed (`121b643`)
  - [x] Re-ask every book's suspects (winnow only, clef cached) and rebuild the trust
        data: 14 books
  - [x] Retrain the arbiter (`train_ocr_trust.py --save`)
  - [x] `bench tuning`, then `bench validation`: tuning no change (after review 1.00 →
        1.02, no veto); validation's first run is its baseline (0.81)
  - [x] Ollaya stripped from the code and docs: the user uninstalled it, so it went
        before the bench (winnow on Ollama is the only winnow)

## 6e. Strict review of the codebase (2026-10-09)

- [x] Six reviewers, every finding checked; fixes with tests in seven commits
      (hosted client, docs, answers and typography, OCR check and trust, measuring,
      chapter labels and text layer, detached.sh): ~2 h
- [x] Baseline bench on the code before the review plus only the measuring fixes:
      tuning 1.00, validation 0.81 after review (2 + 1 min)
- [x] Read-prompt variants on reader set v1, hosted Qwen: none beats the prompt in
      use (design.md), 4 min
- [x] Trust data rebuilt after the fixes, Qwen via hosted; 11/22/63 pp. 15–94 fully
      cold, its old stages kept in `stages.before-review-2026-10-09`: 63 min
- [x] Arbiter retrained (`train_ocr_trust.py --save`), then `bench tuning` and
      `bench validation` against the baseline: tuning better 1.00 → 0.96, validation
      no change 0.81 → 0.75 (decisions.md), 4 min
- [x] Report the cold slice's before and after, and what the fixes changed
- [x] 11/22/63's numbered sections: headings 5 → 23 of 24 (a bare number off the
      folio is a section heading mid-page too), every other book unchanged
- [x] The bench is blind to structure: it now prints headings per book and reports
      heading and paragraph-F1 changes beside its test (`bench.structure`)
- [x] Crop variants on reader set v1, hosted Qwen (450/600 dpi, 2× up, contrast,
      sharpen, margin): none reads better; Qwen's instability across them flags its
      errors (decisions.md), 12 min
- [x] Qwen's second reading of suspect lines at 450 dpi as a trust feature: no change
      (tuning 0.96 → 0.99, validation 0.75 → 0.77), not merged; branch
      `qwen-second-look`, 25 min
- [x] Headings each book's build misses, why per book. Fixed: Villa Toscane 0/12 →
      12/12 (a label's number taken for a folio), De cipier 3/4 → 4/4 (a section number
      near the folio). Thief-Taker and Metro count a label and its title as two
      headings where the build makes one heading of two parts (scoring, not text)
- [x] Afscheid's misread chapter numbers ("l", "e,", "UH" for 1, 2, 11): a dropped top
      line boxed like the book's numeral headings is one (`numeral-slot`), and the OCR
      check fixes its text; headings 8/11 → 11/11, nothing else changed, 1 h
- [x] Artemis's chapter numbers, drawn in a circle (0/3 → 3/3): DocLayout-YOLO marks
      them, glm-ocr reads them; `missing.py` now reads regions up to five lines tall
      above a sunk page's text. +3 questions, no other book changed, 20 min
- [ ] De eerlijke vinder's part numerals I–IV (0/4, a spurious "de"): read from the
      drawing
- [ ] You're Never Weird 5/16: bracketed sections and "- 1 -" chapter numbers

## 6d. Image-only scans

- [x] tesseract's first reading of an image-only PDF (`pdf.first_reading`); Goede
      dochter pp. 9–64 with its layer removed: CER 0.35% against the IA layer's 0.20%
- [ ] The whole pipeline on that copy, after the retrain: does the OCR check close the
      gap? ~1 h cold (every line read anew)
- [ ] Italics on an image-only PDF: `italics.py` takes the PDF's word boxes, which
      it lacks; give it tesseract's

## 6f. Internet Archive's own files

A Scribe item holds more than the PDF: the page images the PDF was compressed from
(`_jp2.zip`), ABBYY's OCR with a confidence per letter (`_abbyy.gz`) and the scan's
page data (`_scandata.xml`: page types, crop boxes; `_page_numbers.json`). Public on
public-domain items only; a lending-library item keeps all but `_scandata.xml` private.

- [x] `golden fetch` takes them from a scan's `[scans.ia]` (item, files with sha256)
      into `work/<book>/ia/`: Crime (300 ppi) and Dolittle (500 ppi), both tuning books
- [ ] Readers on the page images (`experiments/probe_ia_images.py`, ~15 min): reader set
      v1's 50 Crime and 50 Dolittle lines cut again from the JP2s, read by Qwen and
      glm-ocr, lines right per stratum against the PDF crops. The PDF's letters are a
      1-bit mask at full resolution, so this tests grey levels (punctuation, accents).
      A win (more hard lines right, no control broken, both readers): the JP2s become
      the image source on books that have them, trust data rebuilt, `bench tuning`
- [ ] ABBYY's letter confidence as an arbiter feature: check first that the PDF's text
      layer is ABBYY's reading (same words, same boxes), then join its confidence and
      `suspicious` marks to the layer's letters; does a low one separate the trust
      data's real errors? ~1 h, no models
- [ ] `_scandata.xml` page types (Cover, Title, Copyright, Contents, Normal) as labels
      for page classification; public even on lending-library items, so every IA golden
      book has them. ~30 min to fetch and compare with `body_pages`
- [x] A Dutch public-domain Scribe item with its files public, paired with Gutenberg:
      70 title matches between Gutenberg's 1,110 Dutch books and IA's 8,169 public Dutch
      Scribe scans, compared word by word on 3,000 words (`work/probes/ia-gutenberg-nl/`).
      Same edition, OCR slips only: Het Kindeken Jezus in Vlaanderen (Timmermans, #58311,
      `hetkindekenjezus00timmuoft`, 26 differences), David Malan (#68192, 18), Van strak
      gespannen snaren (#31297, 32), Hilda van Suylenburg (#65536, 45), Extaze (Couperus,
      #12003, 56–66: the layer reads his "zoû", "weêr" without the circumflex). All 400
      ppi with page images and ABBYY public, but all pre-1934 spelling: no bench book,
      and no help with contemporary Dutch, whose scans are lending-library items with these files
      private. Pallieter doesn't pair: the public scan is the 30th printing
      in post-1946 spelling, Gutenberg #11355 an older edition
- [ ] Make one of them a golden book (Het Kindeken Jezus) only if the image probe's
      result looks language-dependent; ~30 min with `probe_candidate.py`
- [ ] **user:** whether a borrowed item's `_jp2.zip` can be downloaded while on loan
      (Afscheid p. 20's washed-out text)

## 7. A real test set

- [x] A new golden book, left unscored until the end: Het geluid van bananen (2b),
      the `test` set
- [ ] Score it once, at the end of the plan: `bench test --score-test`

- [x] Washed-out pages left out of the OCR check (its readers invented ~170 lines on
      Afscheid), the budget counted over the pages it reads
- [x] Scoring: an error over a page break counts on the page holding most of it
      (Afscheid 5.03 → 0.24 after review: its washed-out p. 38 had counted on p. 37)
- [x] Suspects the arbiter gives ≥ 0.8 aren't asked (`ROBO_OCR_ASK_BELOW`): questions
      about halved at the same wrong words after review, 1 h
- [ ] **Revisit `ROBO_OCR_ASK_BELOW` (0.8)** whenever the arbiter is retrained on new
      readers or judges, or a new arbiter model is tried: bench 0.7/0.8/0.9 (warm, ~2 min
      each), and weigh questions against wrong words with the user
- [ ] Bad pages by the readers' disagreement: a page whose suspects per line far exceed
      the book's median (Afscheid p. 20: 50 against ~8) is read badly whatever the cause
      (faint, smudged, show-through); a label-free alarm beside `faint.py`
- [ ] Per-book image tuning when a book needs it (uniformly pale or tinted scans): try
      variants on sample lines, keep the one where the independent readers agree most
      and the word list knows most; no reference needed. Null on normal pages so far,
      and no use on a washed-out page whose PDF lost the letters (Afscheid). Internet
      Archive's page images (`_jp2.zip`) might still hold them, but on a lending-library
      item they are private (6f)
- [ ] You're Never Weird p. 47: text inside a picture read into the body; picture text
      should stay in the picture

## Later

- [ ] Proofreading answers with Qwen
- [ ] Surya's layout model as a second spotter beside DocLayout-YOLO (a vote, not a
      replacement): screen it first on the drawn numerals DocLayout-YOLO misses (De eerlijke
      vinder) and the figure/caption pages
- [ ] Block quotes, epigraphs, verse, and ornaments used as scene breaks: none is handled
      yet; find golden pages that have them before designing anything
