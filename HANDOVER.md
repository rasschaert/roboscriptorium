# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-18 ~11:00 by the main session, which ended with
the two chains below still running in their screens, unwatched: **the next session
arms a watcher on them first** (AGENTS.md, standing rules).

## Running

1. **`robo-w12b`** (since 10:13): Winnow-12B as the text judge, asked through token
   probabilities (`tokens:` client). Trust data for the 19 golden books in
   `work/probes/ocr-trust-w12b` (progress `work/probes/ocr-trust-w12b/runs/progress.txt`,
   ~15 min a book, done ~14:30), then its own arbiter
   (`work/models/ocr-trust-w12b.pkl`) and `bench tuning` (log
   `work/probes/ocr-trust-w12b/runs/bench-tuning.log`), then `bench validation`
   (`work/runs/w12b-validation.log`), both against stage (b). Script `work/runs/w12b.sh`.
   Trust data, arbiter and tuning done by 12:22: **tuning 0.30 → 0.28 after review
   [-0.03, -0.00]**, a gain (letters misread, quotes, dots, diaeresis down; Artemis and
   De cipier a shade worse, inside noise). Validation running since 12:22, watched by
   the session that took the chains over at 13:00.
2. **`robo-w12b-answers` done** (11:13): Stella's and Ex-minnaar's Winnow-12B trust
   data, which the chain's book list leaves out, are in place before its arbiter trains,
   so it learns from the same books as stage (b)'s.
3. **`robo-cj-bench`**, behind `robo-w12b`: `bench quick` with the context judge on
   (`ROBO_CONTEXT_MODEL=qwen3.8:27b-nvfp4`) against stage (b)'s quick run
   (`work/runs/cj-bench.sh`, log `work/runs/cj-bench.log`, ~2 h).

Baselines (stage (b)): tuning `work/bench/tuning-20261017T170349-89998e2-dirty.json`
(0.30 after review), validation `validation-20261017T170936` (0.37), quick
`quick-20261017T165913`. The tried cut-off-dash run sits in `work/bench/tried/`, out of
the way of default comparisons.

## When they finish

- **Winnow-12B**: no worse on tuning and not vetoed on validation → `check_model`
  becomes `tokens:hf.co/Piotr1215/Winnow-12B-GGUF:Q4_K_M` (config.py), its trust data
  and arbiter become the default ones, winnow-ollama:e4b goes; the Ollama pin goes from
  AGENTS.md (Environment) and docs/models.md (Setup), design.md and the diagram follow;
  tell the user they can update Ollama, then `roboscriptorium doctor` and a warm bench.
  Worse → recorded, winnow stays, the pin stays until ollama/ollama#18882 ships.
- **Context judge**: no worse on quick → tuning and validation with it, then on by
  default (checklist, "A context judge").
- **Then the first-look books into their sets** (checklist, "First, after the slice
  growth"): Het geluid van bananen and Het schaduwhuis to tuning, De geruchten and
  Verminkt to validation; their trust data with the text judge the bench chose, the
  arbiter and role trees retrained, the three benches. Not before: the chains compare
  against stage (b)'s sets.

## Done this session (decisions.md, 2026-10-17/18)

- The first look (10:18): Het schaduwhuis 0.17, Het geluid van bananen 0.47, Verminkt
  whole 0.49, De geruchten 1.59 (0.82 once its reference's double quotes were undone,
  `single_quotes`), Steve Jobs 2.59 (a revised e-book: line-role training only, the user
  approved). Optimism 6.5/10.
- De aanslag and Villa Toscane retired (born-digital); Na die nacht to `bench.WAITING`
  (guarded, held out, never read).
- The 289 unasked errors read one by one: about a quarter look like the references'
  (`work/probes/unasked/rows.txt`, a verdict batch for the user). A cut-off dash rule
  tried and not taken (branch `cutoff-dash`).
- The primer: a visual for every section, `experiments/primer_errors.py` regenerating its
  errors chart; every doc swept for the old test set.
- The Ollama question: 0.40.5 and 0.40.6 still refuse winnow-ollama:e4b; the way out is
  Winnow-12B (above).

## Waiting on the user

- Ex-minnaar's 6 new questions (rebuild first: the role trees were retrained since), then
  its read-through; then Stella's.
- A verdict batch (~20 min, after the sets move): the unasked errors that look like the
  references' (checklist, "Verdicts on the unasked errors").
- Remove the Ollama models nothing uses: `gemma4:latest`, `deepseek-ocr:3b`,
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`,
  `ornith-1.5:9b`, `ornith-1.5:35b`, `qwen3.8:27b-mxfp8` (not in the way, the user said).
- More golden pairs when convenient. **French**: undecided (checklist, Later).

## Worktrees

`../roboscriptorium-lead` (`token-judge`, merged), `../roboscriptorium-spans`
(`verdict-words`), `../roboscriptorium-breaks` (`scene-after-judge`),
`../roboscriptorium-py315` (stale); a prunable one in an old session's scratchpad.
None holds unmerged work the plan needs.

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
