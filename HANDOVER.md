# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-17 ~10:30 by the main session (the helper session
has ended; only the main session works on).

## Running (2026-10-17)

1. **`robo-queue`, from 10:28:** the seven short tuning slices grown to their pre-2026-10-12
   ranges (`work/runs/queue-20261017.sh`, 447 pages cold, ~1.2 min a page so ~9 h, ending ~19:30–20:00, fewest new pages
   first, then the page-kinds probe; notes in `work/runs/queue-20261017.txt`, logs
   `work/runs/grow-<book>.log`). Every page read is cached, so a stop loses nothing.
   Don't edit `src/` in the main checkout while it runs: code work goes in a worktree.
   The queue's screen outlives the session; check it with `screen -ls` and the notes file.
   **When it ends, in order** (each branch is on origin; check `git diff --stat` first):
   1. Merge **`quick-tier`** (worktree `../roboscriptorium-lead`; it holds `prune` and
      `leading-text`): no change to what a build does. It adds `bench quick` (a chapter
      or two of each tuning book, 282 pages), derives an epigraph before the first
      heading, and cuts AGENTS.md to rules and the map. Then `golden derive normal-people
      --epub work/.cache/publisher/normal-people.epub`, set `body_pages = [9, 276]` in
      `work/normal-people--ia-scan/book.toml`, and run **`bench quick`** (warm, minutes):
      the quick tier's baseline.
   2. Merge **`longer-slices`**: the bench SETS and trust-data specs on the long ranges.
   3. Merge **`heading-pairs`** (scoring: one found heading for a reference's number and
      title set as two; Metro 3/8 → 8/8, Normal People 4/9 → 8/9) and **`verdict-words`**
      (the review says what one side has where the other has nothing).
   4. Merge **`number-lookalikes`** and retrain the trees at once
      (`experiments/train_sorter.py --rebuild --save`), or the build stops on the feature
      mismatch: it adds a look-alike number feature ("Io" for 10) and counts a repeat only
      at the line's height (chapter titles recurring as running heads). The role model is
      asked again about the ~15 lines whose repeat count changes.
   5. Rebuild trust data on the long slices, retrain the arbiter, bench both sets, and
      `bench quick` again: does the quick tier give the same verdict as `bench tuning`?
2. **`robo-context-judge`**, waiting in a screen for `robo-queue` to end, then ~3 h:
   the context-judge probe (`experiments/probe_context_judge.py run`, log
   `work/runs/context-judge.log`; items frozen in `work/probes/context-judge/`, answers
   cached, so a stop loses nothing). Then `... score`, and the verdict in the checklist
   step "A context judge". It holds qwen3.8 only: warm benches can run beside it.
3. **This morning, merged and benched** (decisions.md, 2026-10-17): the paragraph-break
   judge off, its lower-case check kept (validation breaks 0.16 → 0.13, better); lines
   missing at a text block's edge read (`missing.edges`) and Bruna's references derived
   without markup spaces (validation 0.49 → 0.38 after review, better, mostly the
   references); a space between nested quote marks folded in the score (0.38 → 0.36).
   Tuning 0.27 throughout. `ROBO_BREAK_JUDGE=1` turns the judge back on; the user may veto.
4. Worktrees: `../roboscriptorium-spans` (the main session's code checkout while the queue
   runs; on `verdict-words`; branches `heading-pairs`, `number-lookalikes` there too), `../roboscriptorium-breaks`
   (checked out on `scene-after-judge`; `longer-slices` is on origin), `../roboscriptorium-lead` (`quick-tier`), `../roboscriptorium-py315`
   (stale, left as is).
5. Probes: `experiments/probe_break_conditions.py` (where the break judge helped and
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
- Nothing reads the test set (Het geluid van bananen) until its single scoring.
- Stopping a run: `experiments/stop-run.sh <name>`; `ollama stop <model>` frees memory.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
