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
- [ ] De tuin van de avondnevel: ~45 min cold. **Running** since 2026-10-08 10:43
- [ ] Grand Hotel Europa: ~35 min cold
- [ ] Stella, labelled by the user's answers: ~75 min cold
- [ ] Lady into Fox: ~3.3 h cold
- [ ] Reis om mijn schedel: ~4.5 h cold (its quote readings are a separate cache)

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
- [ ] Thief-Taker's suspects in the trust data (it is in `bench tuning`, not in
      `ocr_trust_data.py`): ~4 h cold

## 6. Other components, each scored by `bench`

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
