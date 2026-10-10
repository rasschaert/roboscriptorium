# Checklist

The plan: what is left, in the order it runs, with who does it and how long it takes;
below it, everything done or dropped, by area, as a record. Every step is the machine's
unless it says **user**. A time is an estimate until the run is timed through
`experiments/timed.sh` ([run-times.md](run-times.md)); then the measured time replaces
it. A dropped step stays, struck through, with why. Updated in the same change that
ticks, adds or drops a step: a step done moves to the record.

## Where we are (2026-10-10)

The bench can be trusted (paired, leave-one-book-out, the reviewer's slips counted) and
measures the build that is run: every reader and judge local, Qwen included. After
review, tuning 0.56 and validation 0.79 wrong words a page; Stella's kind of book 0.2–0.35.
What [outlook.md](outlook.md) ranks as the room left: structure (line roles, breaks,
headings), the errors no question asks about, and the reviewer's time.

**The plan now:** more training data (longer slices tonight, then new books), settle the
line-role trees, then **Stella end to end with the user's review**, the target book.
After it, the open areas below in order, and the test set scored once at the end.

## Running now

- [ ] Longer slices, each ending on a chapter (the user's go, 2026-10-09; `robo-next`, in
      the `next` worktree, started 08:50): Goede dochter 9–162 (done, 2 h), Reis whole,
      De cipier 9–174, Metro 7–162, De tuin 11–122 (validation): ~446 new pages, Qwen local,
      ~9 h; then the arbiter and the trees retrained and both benches, rules and trees.
      Done ~19:00–19:30. After it: record the verdicts, merge the worktree's run-times
      rows, remove the worktree

## 1. Right after the chain (~1 h)

- [ ] Line roles by trees on by default if their bench holds (last run: tuning 0.56 →
      0.52, validation 0.77 → 0.70, no change; 11/22/63 and Artemis better, Crime worse).
      Look at Crime p. 97 and De cipier p. 49 first (last lines dropped)
- [ ] De tuin, if it still loses after the retrain: the four questions no longer asked on
      pp. 15, 23, 43 and 46 (local re-read, 0.77 → 0.85), what the arbiter gave them
- [ ] `ROBO_OCR_ASK_BELOW` at 0.7, 0.8 and 0.9 on the retrained arbiter (warm, ~2 min
      each); **user** weighs questions against wrong words

## 2. More training data: new books rather than more pages (~8 h)

- [ ] Thief-Taker's suspects in the trust data, pp. 11–84: a tuning book the arbiter has
      never trained on. ~1.4 h cold
- [x] New golden pairs (the user's hunt, 2026-10-10), each checked with
      `probe_candidate.py`: manifests, derive (two additions: `capital_classes` for small
      capitals written in lower case, a spaced `--` as the print's dash) and scans placed,
      ~1.5 h. Validation: De kerk van de dode meisjes (Ambo|Anthos, layer 0.15%) and
      Vuurspel (Bruna, 0.46%) in place of De tuin, which trains now. Tuning: Het heft in
      eigen hand (9–123), Doodskleed (13–96), Het ijzige land (11–104). The trainer's
      held-out books now come from the bench's sets. Rejected: Cavendon Hall, Alsof het
      niets is, Het spel van de engel (EPUBs made through Word or OCR); De stilte van de hel
      kept unused (Vuurspel's sibling)
- [ ] Tonight, after the chain: trust data for Thief-Taker, Het heft, Doodskleed, Het
      ijzige land, Kerk and Vuurspel (~600 pages, Qwen local, ~9–10 h; the two validation
      books for the record, never trained on); then the arbiter and trees retrained and both
      benches: **a new baseline**, not comparable with earlier runs (the sets changed).
      Check Doodskleed's unplaced lines (6.3%, likely its running heads)
- [ ] ~~The five books whole~~ dropped (2026-10-10, the user): more pages of books already
      trained on add the same errors again; new books, and the areas below, move accuracy more

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

## 4. The reviewer's time

- [ ] The book teaches itself: after the answers, a per-book posterior per substitution
      pair rescores the unasked suspects; on the review page, one question per pattern
      (every `|` read as I) applied to all. Simulated: silent errors at .25/.5/1 a page
      over nine books 50/31/11 → 47/30/11. ~half a day, then `bench`
- [ ] The 15 line-end hyphens reflow still gets wrong, as a question on English books
      only (a break the word list is silent on whose parts are both words: 13 right, 3
      wrong; 0 against 44 on Dutch). ~2 h
- [ ] A typed answer checked against Qwen's cached reading of the line where the question
      had no readings (headings, missing text). ~1 h

## 5. Errors no question asks about

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

## 6. Structure

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

## 7. Better pixels: Internet Archive's own files

Public on public-domain items only (Crime, Dolittle); private on lending-library items.

- [ ] Readers on the page images (`experiments/probe_ia_images.py`, ~15 min): reader set
      v1's Crime and Dolittle lines cut from the JP2s, read by Qwen and glm-ocr. A win
      makes the JP2s the image source where a book has them
- [ ] ABBYY's letter confidence as an arbiter feature: first check the PDF's layer is
      ABBYY's reading, then does a low one separate the real errors? ~1 h, no models
- [ ] `_scandata.xml` page types as labels for page classification (public on every IA
      item). ~30 min
- [ ] **user** Whether a borrowed item's `_jp2.zip` can be downloaded while on loan

## 8. Beyond the golden books' kind

- [ ] Page classification, so `body_pages` needn't be set in book.toml: the page-type
      models so far miss the same pages (prefaces, blanks at the edges); start from 7's
      scandata labels
- [ ] An image-only scan through the whole pipeline (Goede dochter with its layer removed:
      tesseract 0.35% CER against the layer's 0.20%): does the OCR check close the gap?
      ~1 h cold. Then italics from tesseract's word boxes

## 9. Golden books and housekeeping

- [ ] **user** More golden pairs: modern English Scribe scans with the publisher's EPUB of
      the same printing, and a second Dutch validation scan (validation has two; one more
      would let De tuin train)
- [ ] **user** Settle verdicts on the tuning books (`golden review`), the disagreements
      the arbiter's labels sit on first: hours, spread out, whenever convenient
- [ ] The pair prior's own ablation (an empty table, retrained, both benches): it shipped
      inside the arbiter unbenched on its own. ~20 min
- [ ] Training code for shipped models (trust, trees) into the package, with a
      feature-count test

## 10. At the end

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
- [ ] Het Kindeken Jezus as a golden book, only if 7's image probe looks
      language-dependent
- [ ] `golden check <pdf> <epub>` writing a draft manifest, once a batch of candidates comes
- [ ] ~~Proofreading answers with Qwen~~ merged into 4's check of typed answers

# Record: done and dropped

By the sections of the plan they were done under. The plan grew session by session, and a
new batch of work got a letter after the nearest number (2b, 3b, 6g) rather than
renumbering what other notes cite, so the old numbers say nothing about order or kind.
Each heading keeps its old number, because docs/decisions.md and older notes refer to it.

### Measurement that can be trusted (old 1)

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

### Trust data rebuilt with the third reading and short lines (old 2)

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

### New golden pairs (old 2b)

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
- [x] Retirement rule in AGENTS.md, with per-book signals in the bench diagnostics
      (`golden/signals.py`: layer CER and unplaced body lines, a suspect named)

### Baseline, retrain, bench, decide (old 3)

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

### A faster line reader, the crop fix (old 3b)

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
  - [ ] ~~A reading far longer or shorter than its line counting as no reading~~ dropped
        (2026-10-10): after the crop fix readers stray on 1 line in 958, and a version the
        vision judge saw none of is never applied (6g)

### A reader of the finished text (old 3c)

Every check so far starts where the OCR readings disagree; a mistake all readings
share, or one reflow makes, is never looked at. A model reading the built text
paragraph by paragraph can see a sentence that breaks off, a word that makes no sense,
a running head or picture text inside a sentence, a paragraph split mid-sentence. The
danger is that it edits the author. Guards, all of them:

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

### The user's part (old 4)

- [x] **user** Slip rate per question kind (done in 6g, 30 of 32 right): answer the review on Goede dochter
      pp. 9–64, scored against the aligned truth. **After the retrain, with trust on**:
      tried on the fixed rule on 2026-10-08, it asked 215 questions, nearly all obvious
      (`ven eeuwigheid`, `drijthout`, words the word list and clef settle), which would
      measure a near-zero slip rate on questions trust never asks. 6 answers kept in
      `work/probes/slip-rate/`, out of the book's folder so no build applies them
- [x] Review page: the doubt's whole line tinted, its place underlined beneath the print,
      nothing drawn over the letters (the box hid the quote marks it asked about); softer
      colours; `h` turns highlights off, remembered

### More for the trust model (old 5)

- [ ] ~~A book-quality feature~~ merged (2026-10-10) into bad pages by the readers'
      disagreement, the same signal per page
- [x] Per book, clef against winnow on the trust data, printed by `train_ocr_trust.py`,
      a book flagged where winnow is ahead (Lady into Fox: clef 36%, winnow 89%; every
      current book clef ahead)
- [x] `train_ocr_trust.py` uses only data that exists and has every current reading
      (it used to start a cold build of a missing book, and Reis's pre-Qwen data would
      have taught "Qwen never backs a version"); its leave-one-out analysis no longer
      trains on validation books; `--save` refuses while tuning data is missing

### Other components (old 6)

- [x] An ellipsis style in `typography.py` (`326a89d`), read in the text layer or set in
      `book.toml` (the glyph, dots or spaced dots, a space before or not), not measured on
      the page. Bench tuning after review 1.53 → 1.00 (Metro 4.63 → 0.43)
- [x] Italics measured on Metro's typeface: 360 italic words found against the
      reference's 59 in chapters 1–5. The print is right and the eBook isn't: the print sets
      every station name in italics (checked on the scan), the eBook two; not scored now
- [x] Line-role classifier into the package, behind a switch (`sorter.py`, `ROBO_SORTER=1`,
      off by default; `experiments/train_sorter.py`). Leaving one book out: role errors
      tuning 406 → 152, validation 77 → 29. Bench, with two rules enforced in code (a
      heading or edge line repeated on 3+ pages is furniture; a line kept while the trees
      give it P(body) ≥ 0.25): no change by the test, tuning 0.56 → 0.52, validation 0.77 →
      0.70; Artemis 0.76 → 0.53, 11/22/63 1.00 → 0.73, Villa Toscane 0.12 → 0.06, Crime
      0.43 → 0.71 (one lost line, p. 97)
- [ ] ~~A crop reader on tesseract's line boxes (not the layer's)~~ dropped (2026-10-10):
      on an image-only scan the layer is tesseract's, so its boxes are the ones read
- [x] `quality.catches` matches by span where flags have one: a question about one place
      catches only errors sharing a word with it (6g)

### Fable's second review, 2026-10-09 (old 6g)

What the bench couldn't see, and leaks in the OCR check, found in a review of the whole
build. Each change benched on its own.

- [x] The bench counts paragraph breaks set wrong, per page (`disagreements.break_errors`,
      where both sides' words align), and a change that clearly moves them decides like
      the words. Tuning per page: Afscheid 1.73 and Artemis 1.29, the rest 0.01–0.42
- [x] A question about one place in a line catches only the errors at that place; a typed
      washed-out page counts a question per line. Tuning after review 0.48 → 0.56 by this
      alone (Afscheid 0.25 → 0.64, 11/22/63 0.83 → 0.99, Reis 0.24 → 0.32): the new baseline
- [x] The ellipsis glyph is no OCR difference (the typography stage sets it book-wide), and
      the trust labels stop forgiving a space before a quote that no stage removes; trust
      data relabelled (warm, 14 books: see run-times), arbiter retrained. With the next
      step: tuning 0.56 → 0.56, validation 0.80 → 0.80; Reis 0.32 → 0.22 and its questions
      1.09 → 0.34, Thief-Taker 0.55 → 0.46; Goede dochter 0.20 → 0.33, Artemis 0.70 → 0.75
- [x] A version the vision judge saw none of is asked first and never applied (Thief-Taker
      p. 46: a crop of the wrong line, whole sentences applied)
- [x] Paragraph starts in runs of one-line dialogue (the window's margin was the indent),
      after a blank line, and in letters spaced apart: page margin fitted from full lines.
      Breaks a page: tuning 0.46 → 0.33, validation 0.32 → 0.21, words unchanged
- [x] A lost line as a question (`flags.lost-line`): a line's height of white space below a
      line stopping mid-sentence, not around a picture, not above a footnote or a speck.
      No change by the test (tuning 0.57 → 0.56, validation 0.80 → 0.77); De eerlijke vinder
      1.28 → 1.14 from one lost line
- [x] The bench records how much of each book's Qwen reading was the hosted build
      (`read_via`): all but Goede dochter (5%) and De tuin (7%) were read hosted, 97–100%
- [x] The arbiter calibrated (isotonic, on its leave-one-book-out predictions), so the 0.8
      ask threshold means 80% right whatever the retrain. No change by the bench (raw 0.8
      was already right 83% of the time); kept for stability. Training ~1 min
- [x] Italic scores marked unscored where the reference sets italics unlike the print
      (`italics_unlike_print`: Metro's station names). You're Never Weird's EPUB had them in
      a `txit` class the manifest never named: derived now, italics 0.99 / 0.92
- [x] Scene breaks: "* * *" lines and blank-line gaps as a break in the IR and the EPUB
      (`Paragraph.break_before`, `<hr class="break"/>`). Reis 63, De eerlijke vinder 27;
      spot-checked right on the scan. Not scored: the references drop their blank lines
- [x] Budget diagnostics: questions of one reason asked in a shuffled order, not page order
- [x] **user** Re-measure the slip rate on today's questions: 32 questions on a copy of
      Goede dochter pp. 9–64 (`experiments/score_slip_review.py`). 30 of 32 right, each
      judged at its own place: picks 17/18, typed 6/7, roles 7/7. The two misses are one
      choice, p. 36, where the reviewer set the right quote mark and the print (and the
      reference) the wrong one. The old rate was 8 of 68 on Stella's typed questions
- [x] **user** Which slip rate the bench uses: the two samples pooled, 10 wrong of 100
      (Stella's 8 of 68 and Goede dochter's 2 of 32, p. 36 counted), chosen by the user on
      2026-10-09 with the note that it is pooled: the samples come from two kinds of
      question (typed regions then, picks with the difference marked now), so it is a
      middle figure, not either one's rate
- [x] Set `quality.SLIPS, ANSWERS = 10, 100` once the overnight chain is done (mid-chain
      it would move that chain's bench), rerun both benches as the new baseline, and
      update docs/design.md ("8 of 68") and AGENTS.md's bench entry
- [x] Quote questions offered no right reading on 4 of 4 (OCR questions 20 of 21): the
      readings are the raw layer and the layer with Qwen's marks, so (a) offer the
      OCR-checked line itself (p. 36: `Ik` with the print's `’`); (b) take only quote
      marks from Qwen, not its dashes (p. 59: `directeursk-’` for `directeursk—’`);
      (c) nested quotes, a quotation inside dialogue (`‘“…”’`, p. 43, p. 46): the layer
      reads `““` and drops the outer `’`, Qwen reads `‘‘…’’`; in a single-quoted book a
      doubled opening `““` is `‘“` and a mark one reading adds to the other's (`”` + `’`)
      is a reading of its own. Done (`quotes.readings`): 3 of 4 now offer the right line;
      p. 43 also lost the outer ‘ at its first line's start, which no reader saw. Bench
      with the pooled slip rate after the overnight chain
- [x] Quote questions offer the OCR-checked line itself as a reading where it differs from
      the layer: Goede dochter p. 36 offered the layer's `Tk snap` and the checked line with
      Qwen's marks (`Charlie. ‘Waarom`), while the print, and the publisher's EPUB, set the
      wrong mark (`Charlie.’ Waarom`); the faithful line had to be typed. Count, in the
      slip review, how many quote questions sit on a mark the print itself sets wrong
- [ ] ~~A ledger of each probe's prediction beside the bench's verdict~~ dropped as a step
      (2026-10-10): it is a habit, kept in docs/outlook.md's table after each batch
- [x] Qwen's readings of the bench books again locally, so the bench measures the build that
      is run (`experiments/reread_local.py`): 30,572 lines in about 9 h with the judges (1.2 s a line read), with
      the trust data, arbiter and both benches 10 h. Against the hosted readings: tuning
      0.56 → 0.56, validation 0.77 → 0.79, no change; questions fewer on five tuning books
      (Goede dochter 0.58 → 0.44 a page, Reis 0.43 → 0.30), Artemis 0.76 → 0.64; De tuin
      0.77 → 0.85, its own veto

### Where the labelled suspects say the errors are, 2026-10-08 (old 6b)

Measured on the trust data and the golden slices, no models; the scripts and numbers
are `experiments/probe_trust_pair_prior.py`, `experiments/probe_hyphen_breaks.py` and
`work/probes/thinker-2026-10-08/NOTES.md`.

- [x] Line-end hyphens: reflow's decision was wrong on 29 of 1,574 decidable breaks
      (0.02–0.17 words a page, more than the OCR check leaves silent at one question a
      page). Now evidence in order (docs/design.md): the book's spelling, the word list,
      a capital (not a word in capitals), the parts beside an inner hyphen. 29 → 15; on
      warm caches Goede dochter pp. 9–64 WER 0.00211 → 0.00187, De cipier unchanged
- [x] The substitution-pair prior in `trust.py` (model version 3, 23 features): the exact
      (layer → reading) difference, target-encoded from the training books, a pair counted
      when seen in ≥ 2 books, each training book's priors from the other books only (Opus's
      point: with only the row's own label out, [117, 50, 31, 11]). Leave one book out,
      silent errors summed over nine books at 0/.25/.5/1 questions a page: trees [153, 87,
      44, 23] → [110, 48, 25, 10]; at the rule's questions 7 → 7; stable to one more book
      left out (0–3). The trainer's logistic variant with the prior: [94, 43, 29, 15]
- [x] The reviewer's answers checked before they are saved (`review.doubtful`): a typed
      line that matches none of the question's readings, or a straight quote in a book
      set with curly ones, is queried once and saved on the second Save; warned answers
      logged in `review/warnings.jsonl`, so the slip-rate review (4) measures slips before
      and after the check. No model call (Stella: transcribe-and-compare caught 9 of 9
      slips, 3 false alarms in 58). Left: comparing with Qwen's cached reading of the
      whole line for regions that carry no readings (headings, missing text)

### Tryouts: a model screened for a role (old 6c)

- [x] Reader set v1 frozen (`experiments/tryout.py`, `tryouts/reader-v1.json`): 550
      lines of the tuning slices, 30 the layer reads wrong and 20 it reads right a book
- [x] gemma4 on the reader screen, the known-worse check of the screen itself: 9 min.
      Loses on every count: hard lines right 274 of 330 (qwen3.8 302, glm-ocr 294),
      control lines broken 10 of 220 (qwen3.8 3), the only reader right on 3 (qwen3.8 19)
- [x] PP-DocLayoutV3 as the spotter, Dolittle pp. 23–88 scored downstream: worse
      (CER 1.22% → 1.71%), not adopted
- [ ] ~~winnow:12b as the second judge~~ dropped: Ollaya, its only server, was uninstalled
- [x] A judge set like the reader set, versioned the same way (a sorter set dropped on
      2026-10-10: the trees are scored leaving each golden book out, on every line)
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

### Strict review of the codebase, 2026-10-09 (old 6e)

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

### Image-only scans (old 6d)

- [x] tesseract's first reading of an image-only PDF (`pdf.first_reading`); Goede
      dochter pp. 9–64 with its layer removed: CER 0.35% against the IA layer's 0.20%

### Internet Archive's own files (old 6f)

A Scribe item holds more than the PDF: the page images the PDF was compressed from
(`_jp2.zip`), ABBYY's OCR with a confidence per letter (`_abbyy.gz`) and the scan's
page data (`_scandata.xml`: page types, crop boxes; `_page_numbers.json`). Public on
public-domain items only; a lending-library item keeps all but `_scandata.xml` private.

- [x] `golden fetch` takes them from a scan's `[scans.ia]` (item, files with sha256)
      into `work/<book>/ia/`: Crime (300 ppi) and Dolittle (500 ppi), both tuning books
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

### A real test set, and pages left out of the check (old 7)

- [x] A new golden book, left unscored until the end: Het geluid van bananen (2b),
      the `test` set
- [x] Washed-out pages left out of the OCR check (its readers invented ~170 lines on
      Afscheid), the budget counted over the pages it reads
- [x] Scoring: an error over a page break counts on the page holding most of it
      (Afscheid 5.03 → 0.24 after review: its washed-out p. 38 had counted on p. 37)
- [x] Suspects the arbiter gives ≥ 0.8 aren't asked (`ROBO_OCR_ASK_BELOW`): questions
      about halved at the same wrong words after review, 1 h

