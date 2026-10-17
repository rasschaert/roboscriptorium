# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-17 ~10:30 by the main session (the helper session
has ended; only the main session works on).

## Running (2026-10-17, evening)

1. **Done this evening:** the slice growth (all seven, 17:55); stage (a) merged and its
   baselines (quick; tuning on the long slices 0.28 after review; validation 0.41 over
   seven books, Villa Toscane out); stage (b) merged (`number-lookalikes`) and the role
   trees retrained (18:46). Every bench now saves its errors (`*.errors.jsonl`) with
   their causes; `bench-diff` compares two runs place by place.
2. **Stage (b) done** 19:09: trust data, arbiter, the three benches (decisions.md).
3. **`robo-context-judge`**: the local qwen3.8 on 100 asked suspects without counts
   (`work/runs/context-judge.log`), to set beside the hosted run
   (`probe_context_judge.py score --no-counts` both ways). If it agrees, `bench quick`
   with `ROBO_CONTEXT_MODEL=qwen3.8:27b-nvfp4` against stage (b).
4. **Winnow probe done** (805 suspects): Winnow-12B by tokens 77.9% right against
   winnow's 66.5% by systemone, and a sharper alarm on clef (decisions.md).
5. **`robo-first-look-reads`**, waiting behind `robo-context-judge` (the hold is
   released, the trees match), then ~14 h: builds (no scores) of Het geluid van bananen
   9–101, Het schaduwhuis 9–91, Steve Jobs 9–100, De geruchten 9–97, Verminkt whole
   (notes `work/runs/first-look-reads.txt`). Then `bench first-look --first-look`, and
   the books into their sets (checklist, "First, after the slice growth").
6. **The page-kinds probe** still runs as `robo-queue`'s last step (clef-flash).
7. **`robo-w12b`**, waiting behind `robo-first-look-reads`: Winnow-12B as the text judge
   through token probabilities (`tokens:` client, merged, off by default): every book's
   trust data rebuilt in `work/probes/ocr-trust-w12b`, an arbiter of its own
   (`work/models/ocr-trust-w12b.pkl`), `bench tuning` and `validation` against stage
   (b) (`work/runs/w12b.sh`, progress `work/probes/ocr-trust-w12b/runs/progress.txt`).
   If no worse: `check_model` becomes Winnow-12B by tokens, winnow-ollama:e4b and the
   Ollama pin go (AGENTS.md Environment, docs/models.md Setup, docs/design.md).
   **Stage (b) results**: validation 0.41 → 0.37 BETTER, tuning NO CHANGE (decisions.md).
8. **`robo-cj-bench`**, behind the reads and `robo-w12b`: `bench quick` with the context
   judge on (`ROBO_CONTEXT_MODEL=qwen3.8:27b-nvfp4`) against stage (b)'s quick run
   (`work/runs/cj-bench.sh`, log `work/runs/cj-bench.log`, ~2 h). If no worse, the
   tuning and validation benches with it, then on by default.
7. **This morning, merged and benched** (decisions.md, 2026-10-17): the paragraph-break
   judge off, its lower-case check kept (validation breaks 0.16 → 0.13, better); lines
   missing at a text block's edge read (`missing.edges`) and Bruna's references derived
   without markup spaces (validation 0.49 → 0.38 after review, better, mostly the
   references); a space between nested quote marks folded in the score (0.38 → 0.36).
   Tuning 0.27 throughout. `ROBO_BREAK_JUDGE=1` turns the judge back on; the user may veto.
8. Worktrees: `../roboscriptorium-spans` (the main session's code checkout while the queue
   runs; on `verdict-words`; branches `heading-pairs`, `number-lookalikes` there too), `../roboscriptorium-breaks`
   (checked out on `scene-after-judge`; `longer-slices` is on origin), `../roboscriptorium-lead` (`weekend-merge`), `../roboscriptorium-py315`
   (stale, left as is).
9. Probes: `experiments/probe_break_conditions.py` (where the break judge helped and
   hurt, `work/probes/break-conditions/`), `experiments/probe_break_context.py` (a taller
   crop: no gain), `experiments/probe_break_judge.py`.

**Ollama is on 0.40.3; keep it there** with the app's automatic updates off: 0.40.4
refuses winnow (AGENTS.md, Environment).

**Baselines now:** the latest `work/bench/tuning-*` and `validation-*` runs (0.27 and
0.36 after review). After 23:00: the judges' cache key holds the crop (nothing cold),
readers' quotes are curled by the book's style and closed at a line's end (Metro 0.42 →
0.33 wrong words a page), and paragraph starts from the text were tried and reverted
(decisions.md). Tonight's module splits (readers, ocrdoubts, hyphens, scanstyle,
sorterdata, ink, the cache helper) changed no score; the whole-body statistics were
reverted (decisions.md).

## Ex-minnaar: reviewed (2026-10-16)

The user answered every question (206 answers; misprints in `work/ex-minnaar/errata.toml`).
Built with them, epubcheck clean (`work/ex-minnaar/epubs/`). The arbiter was then retrained
with its answers and Stella's (benches no change), and asks 6 more, each a real error the
earlier build left silently: the user may answer them (restart the review server).

The day's review fixes are in decisions.md (2026-10-16): the book teaches itself (its
answers in the arbiter's table and by reader), answered questions stay listed, titles
asked whole, specks unasked, questions shown as their difference with combinations.

## Next, in order

1. Ex-minnaar's 6 new questions by the user (rebuild first: the role trees were
   retrained since), then its read-through.
2. Checklist: the next open step (docs/checklist.md).
3. Stella's read-through by the user (checklist).

## Waiting on the user

- Remove the Ollama models nothing uses: `gemma4:latest`, `deepseek-ocr:3b`,
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`,
  `ornith-1.5:9b`, `ornith-1.5:35b`, `qwen3.8:27b-mxfp8` (not in the way, the user said).
- More golden pairs when convenient.
- **French**: undecided (checklist, Later).

## What this session taught (the rules are in AGENTS.md)

- **A reviewer's answers must teach the book at once.** Ex-minnaar asked "we → wc" 13
  times and stress accents a dozen; the per-book table and reader buckets now learn them.
- **Check a probe's matching before reporting its count**: "7 quote questions settled"
  were questions a probe failed to match to their paragraph.
- **Compare against the day's start, not only the last run**: two changes each within
  noise moved validation the same way (0.48 → 0.50); only the four-way probe showed
  which lines they lost.
- **Test the click, not only the key**: the misprint button crashed with no reading
  chosen (`null >= 0` is true in JavaScript); the key test had chosen one first.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen).
  Warm benches take 2–5 minutes.
- Don't edit `src/` while a bench or build runs; park a change as a patch.
- Nothing reads a first-look book (`bench.FIRST_LOOK`) until its single scoring.
- Stopping a run: `experiments/stop-run.sh <name>`; `ollama stop <model>` frees memory.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
