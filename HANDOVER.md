# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-16 ~06:35, at the end of the session of
2026-10-15/16 (the user away overnight, the agent working on its own).

## Nothing running.

**Ollama is on 0.40.3; keep it there** with the app's automatic updates off: 0.40.4
refuses winnow (AGENTS.md, Environment). clef-flash was pulled again (new digest, checked
to answer as before).

**Caches:** warm in `work/<book>/stages/` (the A/A's spare cold copies deleted,
2026-10-16). Line readings are keyed without line positions (cache v3, converted on
load). Both page readings of every tuning and validation page and Claude's readings
(`work/probes/page-reader/claude-opus-5-5/`, `work/probes/claude-stella/`) are kept.

**Baselines now:** the latest `work/bench/tuning-*` and `validation-*` runs (0.29 and
0.51 after review), after tonight's three changes.

## What this session did (numbers in docs/decisions.md, 2026-10-15 and 16)

- **Page numbers joined to a body line** (`pdf._apart`, text layer v8): De eerlijke
  vinder's layer glued its margin folios to the first line, 28 of its 38 unasked errors.
  `bench tuning` 0.32 → 0.30, no book worse. A first version also split running heads and
  broke Dolittle; caught by the bench, fixed by splitting only beside full-width lines.
- **Cached readings keyed on page, text and box, not position**: an inserted line no
  longer re-reads its whole page (the first bench took 64 min for that). Bench no change.
- **Two line-role rules retired** (`running-text`, `numeral-slot`): switched off for the
  trees' features they cost more errors than they saved; bench no change on both sets.
- **A ceiling for whole-page reading**: Claude (subagents, the user's permission for
  these probes) read 17 golden pages with one real error, right at every place the
  pipeline errs. Whole-page reading is the architecture to aim for; local readers aren't
  there (Qwen 76 wrong words on the same pages).
- **Stella estimated** against Claude's reading: 4 wrong words in 67 pages before review,
  2 of them asked; 6 questions in all, sampled and sound. Expect ~2 wrong words after
  review (quotes, dashes, italics not compared).
- **Ex-minnaar built cold** (283 min, epubcheck clean) and its questions sampled: 105
  unpaired-quote questions were mostly Flemish ’m counted as a quote, now an elision
  (308 → 261 questions; no golden book affected). The rest sound (decisions.md).
- **Nulls, recorded:** page readers' hyphen votes (the judge already settles them); "no
  page reader reads it" as a line-role feature (the trees already handle those lines);
  joins after a tight f (Stella's typeface only).
- **New rule (the user): the shortest test that answers the question**; the full bench
  is the regression guard, batched (AGENTS.md).
- Ollama's 0.40.4 breakage surveyed: deliberate (ollama/ollama#18917), one issue, no fix
  for GGUF-made decision models; a migration PR (#18882) is open.

## Next, in order

1. **Ex-minnaar's review by the user**: ready, 234 questions (308 this morning; 12 of
   theirs already answered), one per line now. Restart the review server
   (`uv run roboscriptorium review work/ex-minnaar`). Where a line shows a blanked place
   name ("—straat", "_-straat"), pick or type it with "__": the book's `blank` setting
   makes it "...".
2. **Stella's read-through by the user** (checklist).
3. Agent, meanwhile: the codebase review's steps (checklist), the detector for errors
   every reading shares (the gap at a lost space measured on the scan).

**Remind the user of the daily backup of `work/`** at session start and before long
runs. Last ones: 2026-10-15 09:34 and that evening.

## Waiting on the user

- Remove the Ollama models nothing uses: `gemma4:latest`, `deepseek-ocr:3b`,
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`,
  `ornith-1.5:9b`, `ornith-1.5:35b`, `qwen3.8:27b-mxfp8` (not in the way, the user said).
- More golden pairs when convenient (De Arbeiderspers, Prometheus/Ooievaar or Vrijdag; a
  book with text wrapped around pictures; a retail-EPUB pair with pictures).
- **French**: undecided (checklist, Later).
- The worktree `../roboscriptorium-py315` waits for PyTorch cp315 wheels; a stale
  worktree entry; the remote `origin/bughunt` can go.

## What this session taught (the rules are in AGENTS.md)

- **Bump a cache's version with every change to what it holds**: the second page-number
  version first ran on the first one's text layer, and its short test looked unchanged.
- **Positions aren't identities, in cache keys too**: a key holding a line's index
  re-read every page a line was inserted on.
- **A pseudo-reference read one page at a time invents paragraph breaks at page turns**;
  check a difference on the scan before counting it.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen).
  Say the estimate first (docs/run-times.md). Warm benches now take 2–5 minutes.
- Don't edit `src/` while a bench or build runs; park a change as a patch.
- A probe or eval on a golden book takes the bench's slice, never the bare directory.
- Nothing reads the test set (Het geluid van bananen) until its single scoring; its
  reference must be rederived first.
- Stopping a run: `experiments/stop-run.sh <name>`; `ollama stop <model>` frees memory.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). **Human work lost for good**: Stella's 83 review answers,
Goede dochter's 32 slip-review answers, Koning Wilders' verdict ("wàs" ×2, noted in
decisions.md). Never symlink `work` into a worktree; stage files by name.
