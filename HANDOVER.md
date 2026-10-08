# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules,
docs/decisions.md the dated decisions, [docs/checklist.md](docs/checklist.md) the
whole plan with times; this file only covers the state of play. Replace it at the end
of each session.

## State at the end of 2026-10-08

On `main`, pushed. Lint and tests green (168 passed, 1 xfailed); nothing uncommitted.

**Where the plan stands:** checklist section 2's queue (trust data for every tuning
and validation book, with the third reading and short lines) is nearly done; then
section 3: `train_ocr_trust.py --save`, the baseline bench, the substitution prior's
own bench step, `bench tuning`, `bench validation`, and the call on Qwen and short
lines.

### Runs going in `screen` (they outlive the session)

`screen -ls` shows `robo-afscheid`, `robo-dolittle-crops`, `robo-metro-crops` while
they run; their output is in `work/runs/<name>.out`, a finished one adds a row to
`docs/run-times.md` and prints its suspects line. All caches survive interruption, so
if one died, the same command (below, through `experiments/detached.sh`) picks up where
it stopped.

- Afscheid, `ocr_trust_data.py --rebuild afscheid-van-verspilde-tijd--ia-scan`
- Dolittle's crop re-read and check, `work/probes/crop-reread.sh
  the-story-of-doctor-dolittle--stokes-1920 23 202 1-21 180`
- Metro's crop re-read and check, `work/probes/crop-reread.sh metro-2033--ia-scan 7
  111 1-10 105`

The trust-data runs read Qwen through OpenRouter: source `~/.openrouter.env`, export
`OPENROUTER_API_KEY="$KEY"` and `ROBO_READ_VIA="openrouter:qwen/qwen3.8-27b@deepinfra/bf16"`
(the crop-reread script does this itself). The user allowed hosted Qwen for the whole
remaining queue and the crop re-reads, nothing else. **At most three pipelines at
once**, and nothing else on the GPU beside them: Ollaya shares its memory. A winnow:12b
probe (13 GB) beside three runs ran Metal out of memory at 19:36 and killed Afscheid and
Dolittle's re-read; both were restarted (resuming from their caches).

### Still in the queue after those

Reis (11–110, tuning), De eerlijke vinder (12–95, validation), You're Never Weird
(13–94, validation), and Stella's crop re-read (its labels come from answers, so
`crop-reread.sh`'s check against a golden reference needs adapting). Then `--save`.

### Learned today (details in docs/decisions.md)

- **Crop fix kept, ink crop rejected.** A line's crop now stops at its neighbour's box
  (`ocrcheck.crop_span`); re-reads were neutral to positive. Crops fitted to the ink
  read worse (`experiments/ink_crop.py`).
- **Hosted Qwen is interchangeable** with local (DeepInfra bf16, measured on Metro's
  new crops).
- **Hosted clef is not.** OpenRouter's `/api/alpha/decisions` serves it; on Goede
  dochter's 419 suspects Cloudflare's build fails the criteria fixed beforehand (96.2%
  the same pick, 348 of 377 right against local's 352, confidence shift 0.063);
  PrimeIntellect's barely reads the image. `ROBO_JUDGE_VIA` and `ollaya.HostedClient`
  stay for a later build.
- **11/22/63's layer** is wrong on 188 of 319 settled suspects (its capital I); winnow
  is right on 31 of clef's 46 misses there, the most of any book.
- Fable's commits (hyphens by evidence, the trust pair prior, answer checks) are on
  `main`; the saved trust model is still the old version, so every build with trust on
  stops until `--save`.

### Probe stopped: winnow:12b as the second judge (run it with no pipelines going)

`experiments/probe_second_judge.py <book> <spec> winnow:12b` asks the cached
suspects' text questions of winnow:12b beside winnow:e4b and scores both against the
trust labels, overall and where clef is wrong. Logs in `work/probes/second-judge/`,
answers cached there (50 of 11/22/63's so far). If it catches more of clef's misses, try it as `check_model`
before the retrain (checklist section 3b's list).

### Waiting on the user

- The slip-rate review comes after the retrain, with trust choosing the questions;
  show a sample first (they rightly refused obvious questions).
- Whether to delete the two failed MoE models (qwen3.6:35b-a3b-nvfp4,
  gemma4:26b-nvfp4, 39 GB).
