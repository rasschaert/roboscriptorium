# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what; decisions.md has every
result with its numbers, and git history every earlier version of this file). Rewrite it
at the end of every session.

**Written 2026-11-25, late evening, before the user's holiday of several weeks.** The
user reviews Pieter Daens first, then is away. This file is complete on its own.

## Coming back: start here

1. Read the plan below (also at the top of docs/checklist.md, "The plan now"), then this
   file's "Open threads" in order.
2. Bring the machine up and check it (each line its own command):
   ```
   experiments/queue.sh status
   experiments/gpu-now.sh
   uv run roboscriptorium doctor
   experiments/detached.sh battery-guard experiments/battery_guard.sh
   ```
   `doctor` first if Ollama updated itself while away (it does, unpinned): a new Ollama
   has broken the decision models before (docs/models.md, Setup). The battery guard also
   frees memory (below); start it before any model run. If a guard is already running,
   quit its screen first (`screen -S robo-battery-guard -X quit`); a new guard ends an old
   one itself.
3. Make fresh baselines before measuring anything (the sets changed on 2026-11-25, and a
   few weeks of Ollama and model updates may move scores):
   ```
   experiments/queue.sh add gpu baselines -- zsh work/runs/baselines.sh
   ```
   (`work/runs/baselines.sh`, one book at a time; it writes the bench files' names to
   `work/probes/baselines-latest/`.)

## The plan (agreed 2026-11-25)

The user, after a day spent on small capitals for about 3% of the silent errors: "i
wonder if you don't get lost in the weeds and lose the big picture sometimes". Agreed
order:

1. **The user's books.** Each rebuilt with the machine as it stands, its questions sampled
   and read by the agent first, then reviewed by the user; kept moving as a pipeline.
2. **Poor scans** are the one improvement theme: the first looks of 2026-11-25 put clean
   scans (Flemish ones included) at the tuning books' 0.09–0.12 silent places a page and a
   browned paperback scan at 2.41.
3. Small kinds (small capitals, scene-break columns, set polish) only where a wanted book
   needs them.
4. One progress number a week: silent places a page on the newest pairs and the user's
   books, not on tuning.

## What runs at handover

Job queue (Pueue, group `gpu`; `experiments/queue.sh status`):

- Job 52 `edge-crops-3` finished: edge crops TAKEN on all three benches (thread 2).
- **Job 53 `pieter-daens-rebuild`** (after 52): Pieter Daens rebuilt with production as it
  stands (its first pass of the accent and speck offers: clef had judged 301 of 781 pages
  when it was stopped at the user's word; about 6 hours left, every answer saved), then
  its questions sampled to `work/probes/questions/pieter-daens/`.

The session's last steps, if it reaches them (check decisions.md for what was done):
merge `edge-crops` once job 53 ends (thread 2); read Pieter Daens' sample and tell the
user the review is ready (they review in their evening, not during their day).

## Open threads, in order

1. **Pieter Daens' review** (the user's, before the holiday): command once the sample is
   read and found fit: `uv run roboscriptorium review work/pieter-daens`. If the user did
   it, rebuild with their answers and check the rebuild diff
   (`experiments/rebuild_diff.py`) before calling it done.
2. **Edge crops** (`readers.grown_to_ink`): a line's crop grows to the ink its text-layer
   box cut off past the crop's margin; boxes on the same printed line bound it; two
   tangled boxes grow on neither side. TAKEN on all three benches (decisions.md), held
   back only until Pieter Daens' rebuild ends. If `git log main` doesn't show it merged:
   ```
   git -C ../robo-edge-crops rebase main
   uv run --project ../robo-edge-crops pytest -q
   git merge --ff-only edge-crops
   git push origin main
   ```
   then docs/design.md (what it catches, the benches), docs/modules.md (`readers`) and
   docs/how-it-works.md (the readers' crop) in the same change. Its follow-up (checklist, "Edge crops
   meeting the lost-line reader"): on the Bantam scan it still makes 79 wrong words, some
   where the text layer lost a page's last lines; read those one by one (`bench-diff`)
   before building anything.
3. **Fresh baselines** (step 3 above, `work/runs/baselines.sh`): every later bench is read
   against them.
4. **Poor scans, next**: after edge crops, what is left on the Bantam scan by cause
   (letters misread, missing text, words); then the user's scans that look like it.
5. **The user's other books**, each rebuilt overnight, never during the user's day: those
   built before 2026-11-19 pay a one-time first pass of the accent and speck offers (about
   an hour per 300 pages more): Hoe wij verdwijnen (waits on the user's read-through),
   Ex-minnaar, Andere levens (seven candidate misprints wait on the user), De kus in de
   nacht. Een Russische roman is on hold for three photographed pages.
6. **The learned models retrained with the four new tuning books** (`bench.NOT_YET_LEARNED`;
   checklist): until then the bench scores them with the full models.
7. **Heldere hemel's headings**: the build finds 2 of 8; its sections open at an italic part
   line over a three-line title, as its e-book has them (checklist).

## Waits on the user

- Pieter Daens' review (thread 1), when the agent says it is ready.
- Golden pairs: none needed. If one comes up, a second poor scan with its publisher's
  e-book would let poor scans validate too (none does yet).
- Disk housekeeping (checklist, **user**: disk).

## How the machine behaves (learned on 2026-11-24 and 25)

- **Memory.** Ollama's MLX runner grows with every request (qwen3.8 27B from 27 GB to 86
  GB, past the machine's 64 GB; the context size isn't the cause, decisions.md). The
  battery guard (`priority.guard`) unloads Ollama's models under 35% free, checking every
  30 seconds, at most every three minutes; requests in flight get a minute first, and a
  server error from an unload is retried (`clients/retry.patiently`). It can't help when
  several runs reload models at once: **one book at a time** for anything that may ask a
  model, including a "warm" bench on code that changes a stage's cache.
- **Estimates.** Only from a matching row in docs/run-times.md or a run's own measured
  rate: `uv run python experiments/eta.py` gives a running bench's time left from its log.
  Otherwise say "unknown" and measure ten minutes in.
- **The user's day.** No long rebuild of a book the user will review during their day; no
  review offered during it. Ask the user only what the machine can't settle; read the
  reference e-book before asking how a book should look; show crops (their paths) with
  any question about the print.

## Branches and worktrees

Live: `edge-crops` (`../robo-edge-crops`). Kept as the record of tried ideas, unmerged or
merged, none needed: `render-columns`, `render-kern`, `quote-closing` (parked at its quick
test), `render-differ`, `render-caps`, `seeing-judges` (not taken), `shisa-seat` (merged),
`smallcaps-size` (not taken), `speck-offers` (off), `trust26-ctl`, `trust26-caps`, `py315`.

## Today's record

Everything done on 2026-11-24 and 25 is in decisions.md under those dates: the small
capitals probes (all null), the set review (seven references' scene breaks declared), five
new golden pairs (In haar schoenen, Heldere hemel, Vele hemels, The Illustrated Man twice)
and their first looks, Au pair's small capitals in its reference (`capital_words`), the
memory guard, the reordered plan, and edge crops.
