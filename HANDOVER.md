# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules,
docs/decisions.md the dated decisions, [docs/checklist.md](docs/checklist.md) the
whole plan with times; this file only covers the state of play. Replace it at the end
of each session.

## State at the end of 2026-10-09 (night)

On `main`. Lint and tests green (285 passed, 2 xfailed). **Two runs going**, both in
`screen`:

- `robo-reread` (the user's go, overnight, ~12 h): Qwen reads again, locally, every bench
  book line the hosted build read (30,572), then the trust data is rebuilt, the arbiter
  retrained and both bench sets scored (`work/runs/reread-chain.zsh`, logs in
  `work/runs/reread-*.log`). Until it ends, **don't run a bench or build**: the caches
  lack the hosted readings and a second process would read the same lines. The hosted
  readings are backed up beside each cache (`third-reading.hosted-backup.json`).
  `experiments/reread_local.py` isn't committed yet.
- `robo-slipreview`: 32 questions on a copy of Goede dochter pp. 9–64
  (`work/slip-review--goede-dochter`) on http://127.0.0.1:8766/, for the user to answer
  (~20 min). Then score the answers against the publisher's text, picks and typed apart,
  and update `quality.SLIPS`/`ANSWERS` if the rate differs.

Bench now (rules' line roles): tuning 0.56, validation 0.77 wrong words a page after
review; paragraph breaks set wrong 0.33 and 0.21 a page. The bench is stricter than
this morning's, so 0.48 then is 0.56 now on the same build.

### Done this session (Fable's second review, checklist 6g)

What paid off, and what didn't, is in docs/outlook.md (a table, with the probe's
prediction beside each bench verdict) and docs/decisions.md. In short:

- **Paid off:** paragraph starts in dialogue runs and after white space (breaks −28% /
  −34%, the one clearly better verdict); the bench's honesty fixes.
- **Promising, not significant:** line roles by trees (`ROBO_SORTER=1`, off by default:
  −0.04 / −0.07, three books clearly better, Crime p. 97 worse); lost-line questions;
  the ellipsis fold (Reis's questions to a third).
- **No gain, kept for other reasons:** the arbiter's calibration; scene breaks (unscored);
  the bench's record of the hosted share; italics (Metro's reference is wrong, You're
  Never Weird's manifest lacked its class).
- Fixed on the way: the bench's record loop gave every book the last book's footnotes;
  derive split a word set in two italic spans ("Hors e").

### Next

1. When `robo-reread` ends: read its bench verdicts against the runs before it (the
   chain compares with the previous run of each set). Commit `reread_local.py` and the
   results (docs/design.md's Qwen section, outlook, decisions, run-times).
2. Bench the sorter on the local readings (`ROBO_SORTER=1`, ~10 min warm); if it holds,
   make it the default. Look at Crime p. 97 and De cipier p. 49 first: a last line dropped.
3. Score the slip review (above).
4. Score scene breaks: derive keeps blank-line paragraphs as a break mark.
5. The earlier list stands: IA page images and ABBYY confidence (6f), headings still
   lost, bad pages by the readers' disagreement.

### Working with the user (also in memory)

- Cheap experiments are encouraged, unasked; record null results too.
- Hosted Qwen: ask again next session (nothing hosted was used this session).
- 1Password locked: stop and ask for it to be unlocked (global instructions).
- The user pulls every model download themselves.
- Long runs through `experiments/detached.sh` and `experiments/timed.sh` (its arguments:
  label, pages, log file, command). `bench --against <record>` compares with a chosen run.
- Questions the bench's test can't weigh (reviewer time against wrong words) are the
  user's call: ask in one short sentence.

### Waiting on the user

- `/doctor` (2026-10-09) proposed, unanswered: move AGENTS.md's Models table, golden-books
  notes and module tour to `docs/` (~8k est. tokens a session; AGENTS.md is 66.6k chars,
  past the large-file warning), switch off 10 unused claude.ai connectors in `/mcp`, and
  make auto mode the default in `~/.claude/settings.json`. Nothing applied.
- **French**, the user's idea (2026-10-09), undecided. Proposed instead for now: go
  after the accent errors Dutch already has (De cipier's `knieén`, `hé` for `hè`, lost
  stress accents; Stella's `scenes`): count the accent errors the bench leaves unasked,
  by book, on the golden books we have. (Not on the old-spelling pairs in 6f: their
  accents, Couperus's `zoû`, `weêr`, are the old spelling's.) French brings its own typography (« », a thin space before `; : ! ?`,
  dialogue dashes) that `quotes.py`, `typography.py` and the arbiter's training data
  would all need, and Gallica is mostly older print unlike the target books. If French
  comes, start with one French Wikisource book proofread page by page against its scan
  (same edition by construction), held out as a stress set like the test set, never
  trained on. Two extra worktrees can go when convenient: `../roboscriptorium-baseline` and
`../roboscriptorium-qwen2`.
