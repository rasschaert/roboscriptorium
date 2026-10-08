# Checklist

What is done and what is left on the current plan: make measurement trustworthy,
then let the bench decide on the OCR check's third reading and short lines. Updated
with each change; times come from [run-times.md](run-times.md). "Who" is the
machine unless it needs the user.

## Done

| Step | What it gives |
| --- | --- |
| A missing or stale trust model stops the build (`trust.Mismatch`) | No silent fallback to the fixed rule |
| `eval` records the decider, settings and model versions | A score can be traced to what made it |
| `roboscriptorium bench [tuning\|validation]` | Pinned slices, one JSON per run, paired page-by-page comparison |
| One primary test, books weighing the same, a per-book veto (99%, ≥ 0.05 words/page) | No verdict from noise or from the three longest books |
| The reviewer's slip rate as an interval (8 of 68, Beta posterior) | "After review" isn't scored as if answers were free |
| Leave-one-out trust models (`ocr-trust-without-<book>.pkl`) | Tuning books aren't scored by a model that saw them |
| The four "held-out" books renamed validation | Honest about having looked at them |
| `docs/design.md` (why each component is there) and `docs/decisions.md` | Nobody rediscovers the reasons from data |
| Qwen (qwen3.8) as a third reading, told the book's style | Committed, **not yet measured** |
| Short lines read too | Committed, **not yet measured** (Goede dochter: +18 suspects, ~3 real errors) |
| Long runs timed (`experiments/timed.sh`, `docs/run-times.md`) | Estimates before a run starts |

## Left

| # | Step | Who | Estimate | Status |
| --- | --- | --- | --- | --- |
| 1 | Trust data: Goede dochter | machine | — | done |
| 2 | Trust data: Vals alarm (short-line top-up) | machine | ~2 min | running |
| 3 | Trust data: Crime (short-line top-up) | machine | ~2 min | running |
| 4 | Trust data: Dolittle, cold | machine | ~75 min | running |
| 5 | Trust data: Reis om mijn schedel | machine | ≤ 3 h (some Qwen readings cached) | to do |
| 6 | Trust data: Lady into Fox | machine | ~2.5 h | to do |
| 7 | Trust data: De tuin van de avondnevel | machine | ~35 min | to do |
| 8 | Trust data: Grand Hotel Europa | machine | ~25 min | to do |
| 9 | Trust data: Stella (labelled by the user's answers) | machine | ~55 min | to do |
| 10 | Baseline bench, fixed rule (`ROBO_OCR_TRUST=0 … bench`) | machine | unmeasured | to do |
| 11 | Retrain trust; compare with the before-Qwen data | machine | minutes | to do |
| 12 | `train_ocr_trust.py --save` (main and leave-one-out models) | machine | minutes | to do |
| 13 | `bench tuning`, then `bench validation` | machine | unmeasured | to do |
| 14 | **Decide**: keep Qwen's third reading and short lines only if the bench says so | machine | — | to do |
| 15 | Re-ask ~200 cached clef answers, count flips (answer variance) | machine | ~15 min | to do |
| 16 | Slip rate per question kind: answer Goede dochter pp. 9–64 (~70 questions) | **user** | ~1 h of the user's time | to do |
| 17 | Settle verdicts on the tuning books (`golden review`), trust's labels first | **user** | hours, spread out | to do |
| 18 | A book-quality feature for trust (winnow's alarm is worthless on clean books) | machine | — | after 16 |
| 19 | Line-role classifier into the package, behind a switch, scored by `bench` | machine | — | to do |
| 20 | A crop reader on tesseract's line boxes (not the layer's) | machine | — | to do |
| 21 | `quality.catches` matches by span where flags have one | machine | — | to do |
| 22 | Training code for shipped models into the package, with a feature-count test | machine | — | to do |
| 23 | Thief-Taker's suspects in the trust data (it is in `bench tuning`, not in `ocr_trust_data.py`) | machine | ~4 h cold | to do |
| 24 | A new golden book left unscored until the end: a real test set | **user** picks, machine derives | — | to do |
| 25 | Later: proofreading answers with Qwen; the paragraph language judge | machine | — | later |
