# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session.

## State, 2026-10-10 afternoon

On `main`, clean. Lint and tests green. Two chains in `screen`, one after the other,
started by the user's go on 2026-10-09; another session (Opus) runs them and records
their results tonight:

- `robo-next`, in the `next` worktree (`../roboscriptorium-next`): longer tuning slices
  (Goede dochter 9–162, Reis whole, De cipier 9–174, Metro 7–162, De tuin 11–122), Qwen
  local, then the arbiter and trees retrained and both benches, rules and trees. Due
  about 19:00–19:30. Its timed rows go to the worktree's run-times.md and are merged
  when it is recorded.
- `robo-newbooks`, on this checkout, waits for `robo-next` and then builds trust data
  for Thief-Taker and the five new golden books (~567 pages, ~9–10 h), retrains, and
  runs both benches, rules and trees: **the new baseline** (the sets changed, so it isn't
  comparable with earlier runs). It appends to this checkout's run-times.md from about
  17:00 until early morning; leave that file alone meanwhile.

**Until both end, don't run a bench, a build or a trust-data rebuild:** a second process
would read the same lines and compete for Ollama.

Bench before the chains (rules' line roles, the local Qwen readings, slip rate 8 of
68): tuning 0.56, validation 0.79 wrong words a page after review. The pooled slip rate
(10 of 100) and the new quote-question readings were set mid-chain and show up first in
the new baseline.

**Branch `bughunt`** (worktree `../roboscriptorium-bughunt`): 22 bug fixes with tests
from a four-reviewer hunt, kept off `main` so the chains run unchanged code. Bench it
against the new baseline, then merge (checklist). Six findings were left for a decision,
each verified on synthetic input:

- A typed line gets its neighbour's `Line.source`, so `italics.mark` can set it in the
  neighbour's italics and `figures.place` takes the neighbour's height. A fix needs typed
  lines to carry an identity of their own, read by every consumer of `source`.
- `roles.py`'s repeated-title rule demotes a chapter title that recurs (Thief-Taker's
  second "THE THIEF-TAKER"); exempting sunk pages risks keeping a running head on a
  chapter opening. Needs the bench.
- `evaluate.match_headings` counts "CHAPTER 2" found for "CHAPTER 3" when a heading is
  missing (a numeral misread is not a lost heading, but the alignment can slide).
- `typography.styled` with dash spacing "none" merges two tokens, so an italic word
  swallows its neighbour (`<i>Ulysses—een</i>`): italics as word indices can't say it.
- `trust` feature `known` is computed on the raw versions ("dank-"), the word-list vote
  on the joined ones ("dankbaar"); fixing it changes a feature and needs a retrain.
- A disagreement's key takes its context from the sliced reference, so a verdict on a
  chapter's first six words is "unreviewed" under another slice (it still applies).
- Latent: PDF pages with `/Rotate` would be cropped in the wrong place everywhere. No
  book has one.

## Next

The open steps, in order, are in docs/checklist.md; the first ones:

1. Record the chains' verdicts (decisions, outlook's table and totals, run-times merged
   from the worktree, the worktree removed).
2. Line roles by trees on by default if their bench holds; Crime p. 97 and De cipier
   p. 49 first.
3. `ROBO_OCR_ASK_BELOW` at 0.7, 0.8 and 0.9: the user weighs questions against wrong
   words.
4. Stella end to end: agree what "done" means, build, the user reviews, read the EPUB.

## Waiting on the user

- **French** (the user's idea, 2026-10-09): undecided; the proposal and the counter-proposal
  (count Dutch accent errors first) are under "Later" in the checklist.
- Two stale worktrees can go when convenient: `../roboscriptorium-baseline` and
  `../roboscriptorium-qwen2` (branch `qwen-second-look` holds the second-look probe).
- From `/doctor` (2026-10-09), still unapplied: switch off the unused claude.ai connectors
  in `/mcp`, and make auto mode the default in `~/.claude/settings.json`. The third
  proposal, moving AGENTS.md's bulk into `docs/`, was done on 2026-10-10 (modules.md,
  models.md, golden-notes.md).
