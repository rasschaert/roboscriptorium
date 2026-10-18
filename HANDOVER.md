# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-18 ~14:45 by the session that took over the two
chains at 13:00.

## Running

Nothing. Ollama is idle on 0.40.6.

## Done today, afternoon (decisions.md, 2026-10-18)

- **Winnow-12B is the text judge** (`check_model`
  `tokens:hf.co/Piotr1215/Winnow-12B-GGUF:Q4_K_M`): tuning 0.30 → 0.28 after review,
  BETTER; validation 0.37 → 0.39, no change, no veto. Its trust data and arbiter are the
  defaults now (`work/probes/ocr-trust`, `work/models/ocr-trust*.pkl`); winnow-ollama:e4b's
  sit beside them as `ocr-trust-winnow-e4b` (renamed, nothing deleted). Its runs:
  tuning `work/bench/tuning-20261018T102252-ccfd33e-dirty.json`, validation
  `validation-20261018T110345-ccfd33e-dirty.json`: **the baselines from now on.**
- **The context judge, quick tier: BETTER**, 0.30 → 0.26 after review, questions 0.72 →
  0.60 a page, 24 wrong words fixed, none made (`work/runs/cj-bench.log`; it ran against
  stage (b) with winnow-ollama:e4b, so the full benches compare against the Winnow-12B
  runs).
- **Ollama 0.40.3 → 0.40.6** (Homebrew cask `ollama-app`): clef, clef-flash and
  Winnow-12B answer cached questions as before; caches stand. The pin is gone.
- `experiments/rebuild-trust.sh` builds the answers books too.

## Next, in order

1. **The first-look books into their sets** (checklist, "First, after the slice
   growth"): Het geluid van bananen and Het schaduwhuis to tuning, De geruchten and
   Verminkt to validation (`bench.SETS`, `trustdata.SPECS`); the two tuning books' trust
   data with Winnow-12B, the arbiter and the role trees retrained, `bench tuning` and
   `validation` as the new baselines.
2. **The context judge's full benches** against those baselines, overnight (cold for the
   context judge: tuning ~3 h, validation ~1.5 h); on by default only if both hold.

## Waiting on the user

- Ex-minnaar's 6 new questions (rebuild first: the role trees were retrained since), then
  its read-through; then Stella's.
- A verdict batch (~20 min, after the sets move): the unasked errors that look like the
  references' (checklist, "Verdicts on the unasked errors").
- Ollama models nothing uses now: `winnow-ollama:e4b` and `hf.co/EldanRing/Winnow-E4B:Q8_0`
  (9 GB each, the same weights), `imajev:4b` and `hf.co/mindchain/imajev-4b-GGUF:Q8_0`,
  `qwen3.8:27b-q8_0` (29 GB). Not in the way.
- More golden pairs when convenient. **French**: undecided (checklist, Later).

## Worktrees

`../roboscriptorium-w12b` (`w12b-default`, merged), `../roboscriptorium-lead`
(`token-judge`, merged), `../roboscriptorium-spans` (`verdict-words`),
`../roboscriptorium-breaks` (`scene-after-judge`), `../roboscriptorium-py315` (stale); a
prunable one in an old session's scratchpad. None holds unmerged work the plan needs.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen),
  each with a watcher. Warm benches take 2–5 minutes.
- Don't edit `src/` while a bench or build runs from `main`: work in a worktree and bench
  it with `uv run --project ../<worktree> roboscriptorium bench …` from this directory,
  so `work/` is reached by path, never linked.
- Nothing reads a first-look book (`bench.FIRST_LOOK`) until its single scoring.
- Stopping a run: `experiments/stop-run.sh <name>`; `ollama stop <model>` frees memory.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
