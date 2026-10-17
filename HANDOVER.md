# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-17 ~09:20, during the night run; the user may reset the sessions.

## Running, and what the night left (2026-10-17)

1. **Nothing running** (since 09:40). The paragraph-break judge v2 (`parabreaks.py`) was
   benched on both sets (decisions.md, 2026-10-17): words unchanged, paragraph breaks
   tuning 0.19 → 0.16 and validation 0.21 → 0.16 a page (NO CHANGE, just short). Clearly
   better on books with lines set apart (Dolittle, You're Never Weird, Normal People),
   clearly worse on Goede dochter 0.00 → 0.10, De stilte 0.34 → 0.47 and The Stranger's
   Child 0.02 → 0.08; no gain on Vuurspel. Log: `work/runs/break-bench2.log`.
2. **The break judge is off by default** (`ROBO_BREAK_JUDGE=1` on); the lower-case check
   it came with runs on every build. Measured line by line, the check fixed 75 starts and
   broke none, the model 43 fixed and 63 broken; benches validation BETTER (breaks 0.16 →
   0.13), tuning no change (0.16 → 0.15) (decisions.md, 2026-10-17). The user may veto.
3. **Slice growth not started** (the user's break): `robo-queue` was stopped while it
   waited. To resume: `experiments/detached.sh queue work/runs/queue-20261017.sh` (it waits
   for `robo-break-bench`, then `eval`s the seven short tuning slices to their
   pre-2026-10-12 ranges, ~450 pages cold, ~8 h with the judge, fewest new pages first,
   then the page-kinds probe; notes in `work/runs/queue-20261017.txt`). Every page read is
   cached, so a stop loses nothing. Then merge branch **`longer-slices`** (on origin;
   worktree `../roboscriptorium-breaks`): the bench SETS and trust-data specs on the long
   ranges. Then rebuild trust data and the role trees on them, and bench.
4. Other worktrees: `../roboscriptorium-spans` (branch `reference-spaces`, the main
   session's: drops the space Bruna's e-books set before punctuation in derived references;
   to merge after the validation bench, which it would change mid-run);
   `../roboscriptorium-py315` (branch `py315`, 2026-10-11, no commits past main, two
   untracked files: stale, left as is).
5. Tested, not merged: nothing else. Probes and their data: `experiments/probe_break_judge.py`
   (`work/probes/break-judge/`, incl. clef-flash and a `--styled` variant never run),
   `experiments/seed_break_answers.py`.

**Ollama is on 0.40.3; keep it there** with the app's automatic updates off: 0.40.4
refuses winnow (AGENTS.md, Environment).

**Baselines now:** the latest `work/bench/tuning-*` and `validation-*` runs (0.27 and
0.49 after review). After 23:00: the judges' cache key holds the crop (nothing cold),
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

**Remind the user of the daily backup of `work/`** at session start and before long
runs: it now also holds `work/ex-minnaar/errata.toml`.

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
- Nothing reads the test set (Het geluid van bananen) until its single scoring.
- Stopping a run: `experiments/stop-run.sh <name>`; `ollama stop <model>` frees memory.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
