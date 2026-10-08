# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules,
docs/decisions.md the dated decisions; this file only covers the state of play.
Replace it at the end of each session.

## Added on 2026-10-08 by a second session (Fable), on top of the state below

Three commits on `main`, each measured, lint and tests green, Opus's uncommitted
files (`experiments/probe_text_reader.py`, `probe_remaining_errors.py`) untouched:

- `52ea4d3` line-end hyphens by evidence (`reflow.join`): book spelling, word list,
  capital, the parts beside an inner hyphen. 29 → 15 wrong of 1,574 breaks on six
  slices (`experiments/probe_hyphen_breaks.py`).
- `fbf1925` trust's substitution-pair prior (`trust.pair`, model version 3, 23
  features, priors saved with the model, ≥ 2 books, leak-free training rows).
  Leave one book out: silent errors at 0/.25/.5/1 a page 153/87/44/23 → 117/50/31/11
  (`experiments/probe_trust_pair_prior.py`). **The saved model is still version 1**:
  every build with trust on still stops until `train_ocr_trust.py --save`.
- the reviewer's answers checked before saving (`review.doubtful`, `regions.html`),
  warned answers in `review/warnings.jsonl`.

Checklist section 6b holds the numbers and what is left (the hyphen question route,
the prior's own bench step, the per-book posterior). Notes and probe outputs in
`work/probes/thinker-2026-10-08/`.

## State at the end of 2026-10-07 (night)

On `main`, pushed. Another Claude session works on the review page
(`regions.html`, `review.html`); stay out of those files and commit only your
own files by name. The user asked for **no local model inference until they say
so** (battery); the one job left running was allowed to finish.

An outside review (Fable) said the weak part is measurement, not code. Its
points taken on, in the order they landed:

- **A stale or missing trust model stops the build** (`trust.Mismatch`), no more
  silent fallback to the fixed rule. `ROBO_OCR_TRUST=0` asks for the rule.
  **Right now every build with trust on stops**: the OCR check has a third
  reading (Qwen, told the book's style), the trust features grew (version 2,
  `FEATURES = 21`), and the saved model is version 1. Retrain (below) first.
- **eval-history records** the decider (`fixed rule` / `trust <hash>`), the
  settings and each model's Ollama digest or Ollaya release.
- **`roboscriptorium bench [tuning|validation]`** (`bench.py`): pinned golden
  slices, one JSON per run in `work/bench/`, compared with the previous run page
  by page (a `*` where the paired bootstrap interval excludes zero). "After
  review" adds the reviewer's slips (8 of 68 answers on Stella) per question.
  Each tuning book is scored with the trust model trained without it
  (`ocr-trust-without-<book>.pkl`). **Never run yet**: needs the retrained
  trust model.
- **The four "held-out" books are validation books** now: earlier choices were
  made on their scores. To have a real test, add a new golden book and leave it
  unscored until the end.
- AGENTS.md slimmed: the decision log is `docs/decisions.md`, the architecture
  section lists the stages `pipeline.run` really runs.

## Uncommitted, on purpose

- **The OCR check reads short lines too** (`ocrcheck.py`: `MIN_LINE_CHARS` and
  `shortest` gone; `pipeline.proposals` no longer passes `shortest=1`;
  experiments keep 12 locally). The 12-character gate skipped "keek." and
  "merkt.", where closing quotes are lost. Unmeasured: rebuild Goede dochter's
  trust data with it and compare the new short-line suspects' labels before
  committing. Readings are cached per line, so only short lines are read anew.
- `experiments/probe_remaining_errors.py`: which remaining errors the cached Qwen
  reading gets right.

## Trust data rebuild, in progress

`experiments/ocr_trust_data.py --rebuild <book>` (now pinned to the fixed rule,
its baseline), one book per run, logs in `work/probes/ocr-trust/logs/`, the
earlier data in `work/probes/ocr-trust/before-qwen/`. Done: Goede dochter
(327 → 401 suspects), Vals alarm (267 → 320), Crime (236 → 248; settled
205 → 217, the layer wrong on 62 → 65 of them). Left: Dolittle, Reis, Lady into Fox, De tuin, Grand Hotel Europa,
Stella (`answers`), ~1 h each. If the short-line change is committed first,
Goede dochter, Vals alarm and Crime need a top-up rebuild (cheap).

Then: `PYTHONPATH=experiments uv run python experiments/train_ocr_trust.py`
(leave-one-out against the rule, compare with the before-qwen data), `--save`
(writes the model and the without-each-book copies), `roboscriptorium bench`,
`bench validation`. Keep the Qwen third reading only if the bench says so.

## Next steps, in order

The full list, with estimates and status, is [docs/checklist.md](docs/checklist.md).

1. First `bench` run with `ROBO_OCR_TRUST=0` once the rebuilds have filled the
   caches (a baseline from the fixed rule), then retrain trust and bench again
   (tuning, validation). Also: re-ask ~200 cached clef states and count flips,
   the answer variance that a cold re-ask freezes into the cache.
2. **Measure the slip rate where truth exists**: the user answers the review on
   Goede dochter pp. 9–64 (~70 questions), scored against the aligned truth, per
   question kind (choosing a reading vs typing); it doubles as verdict settling.
   A book-quality feature for trust (winnow's alarm is worthless on Goede dochter,
   see docs/design.md) goes with the retrain after that.
3. **Settle verdicts on the tuning books** with the user (`golden review`): 17%
   of suspects can't be labelled (no single version matches the aligned truth),
   so trust never trains on them. Sort the disagreements so those the trust
   labels sit on come first; it needs the user's time.
4. **Line-role classifier into the package**, behind a switch: features from
   `experiments/train_line_roles.py` into `src/`, Thief-Taker's lines added,
   saved with without-each-book copies like trust, scored with `bench`.
5. One crop reader on tesseract's line boxes, not the layer's (glm-ocr and Qwen
   share the layer's crops, so they miss the same cut-off marks).
6. `quality.catches` credits any flag overlapping an error's lines (a heading
   region "catches" an OCR error on its lines); match by span where flags
   have one.
7. Training code for shipped models into the package, with a test that a
   retrain matches the saved model's feature count.
8. Later: proofreading answers with Qwen, the paragraph language judge.

Not taken on from the review: dropping winnow outright (the trust model already
weighs it; the fixed rule that leans on it is now only an explicit fallback).
The book-wide question budget is deliberate and now documented as such.
