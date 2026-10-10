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
