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
errors). Both are in the build until the bench in 3 decides.

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
rule. About 1.1 min per page cold (Dolittle; Crime and Vals alarm ran at 0.8); a top-up after the short-line change reads only
the short lines.

- [x] Goede dochter: 3 min (Qwen readings cached), top-up 2 min
- [x] Vals alarm: 39 min cold, top-up 2 min
- [x] Crime: 81 min cold, top-up 1 min
- [x] Dolittle: 98 min cold (642 → 684 suspects; layer wrong on 374 → 396 settled)
- [x] De tuin van de avondnevel: 51 min cold (389 → 472 suspects; layer wrong on 310 → 350 settled)
- [x] Grand Hotel Europa: 32 min cold (125 → 173 suspects; layer wrong on 79 → 99 settled)
- [x] Stella, labelled by the user's answers: 53 min cold (65 → 66 suspects; layer wrong on 34 settled, unchanged: only answered places are labelled)
- [ ] ~~Lady into Fox: ~1.7 h cold~~ dropped: retired to reserve (its reference's typography differs from the print), so no validation data is needed from it
- [ ] Reis om mijn schedel, pp. 11–110 (chapters 1–11, as in `bench tuning`): ~1.8 h cold

## 2b. Two new golden pairs (Fable's session)

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
      kind (no reference rebuilt so far has spaced dots, so its trust data stands)
- [ ] Afscheid's trust data, pp. 9–70 (chapters 1–11, as in `bench tuning`): ~1.1 h cold. Before the
      baseline in 3, so the baseline includes it
- [ ] Metro's trust data (in `ocr_trust_data.py`, pp. 7–111): ~1.9 h cold. **Running** since 2026-10-08 12:58. Before the
      baseline too
- [x] De cipier, a pair with no known deviations: chapters 1–4 (pp. 9–92) in
      `bench tuning`
- [x] Artemis: chapters 1–3 (pp. 13–80) in `bench tuning`
- [ ] Artemis's trust data (in `ocr_trust_data.py`, pp. 13–80): ~1.2 h cold, after
      Metro
- [x] 11/22/63 (Scribner 2011), the first American scan and the heading test (386
      headings): the prologue and chapters 1–3 (pp. 15–94) in `bench tuning`
- [ ] 11/22/63's trust data (in `ocr_trust_data.py`, pp. 15–94): ~1.5 h cold, after
      Artemis (English first: the line-role classifier is short of English books)
- [ ] De cipier's trust data (in `ocr_trust_data.py`, pp. 9–92): ~1.5 h cold. Before
      the baseline, so it isn't rerun when it joins
- [ ] Retirement rule in AGENTS.md, with per-book signals in the bench diagnostics
- [ ] `golden check <pdf> <epub>`, writing a draft manifest: worth it once a batch
      of candidates comes
- [ ] **user** Hunt for modern English Scribe scans with the publisher's EPUB of the
      same printing (two more unblock the line-role classifier in 6)

## 3. Baseline, retrain, bench, decide

- [ ] Baseline bench on the fixed rule (`ROBO_OCR_TRUST=0 … bench`): unmeasured
- [ ] Retrain trust and compare with the before-Qwen data: minutes
- [ ] `train_ocr_trust.py --save` (the main and the leave-one-out models): minutes
- [ ] `bench tuning`, then `bench validation`: unmeasured
- [ ] **Decide:** keep Qwen's third reading and short lines only if the bench says so
- [ ] Re-ask ~200 cached clef answers and count the flips (answer variance): ~15 min

## 4. The user's part

- [ ] **user** Slip rate per question kind: answer the review on Goede dochter
      pp. 9–64 (~70 questions), scored against the aligned truth: ~1 h
- [ ] **user** Settle verdicts on the tuning books (`golden review`), the
      disagreements trust's labels sit on first: hours, spread out

## 5. More for the trust model

- [ ] A book-quality feature (winnow's alarm is worthless on clean books): after
      the slip-rate answers in 4
- [ ] Thief-Taker's suspects in the trust data, pp. 11–84 (chapters 1–22, its
      `bench tuning` slice): ~1.4 h cold

## 6. Other components, each scored by `bench`

- [ ] An ellipsis style in `typography.py`, measured on the page like the dash style
      (the book's glyph or spaced dots)
- [ ] Italics measured on Metro's typeface: 360 italic words found against the
      reference's 59 in chapters 1–5 (heuristics only)
- [ ] Line-role classifier into the package, behind a switch
- [ ] A crop reader on tesseract's line boxes (not the layer's)
- [ ] `quality.catches` matches by span where flags have one
- [ ] Training code for shipped models into the package, with a feature-count test

## 7. A real test set

- [ ] A new golden book, left unscored until the end: the **user** picks, the
      machine derives

## Later

- [ ] Proofreading answers with Qwen
- [ ] The paragraph language judge
