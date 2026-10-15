# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-15 ~09:15, at the end of the session of
2026-10-14/15 (morning, evening and the night's queue).

## Running tonight (2026-10-15/16): `work/runs/queue-20261015.sh` in screen `robo-queue`

Started ~23:55, log `work/runs/queue-20261015.txt`. In order: `bench validation` and
`bench tuning` as the regression guard for the page-number split (text layer v8, commit
e386ee2; its short test already passed), then Stella's cold build (~75 min) for the
comparison with Claude's whole-page reading of its 67 body pages
(`work/probes/claude-stella/readings/`, notes on doubtful places in `notes.txt`).
Ollama is back on 0.40.3 (0.40.4 breaks winnow: AGENTS.md, Environment).

## Before tonight: nothing running. Ollama's context is at 32k.

**The caches:** warm in `work/<book>/stages/`, as every build expects. The 16 tuning
books (`work/runs/tuning-books.txt`) also keep a cold set in `stages.cold/`, from the
A/A; keep both until the user says which to drop. Both page readings of every tuning
and validation page are cached in `stages/page-reading-{glm,qwen}-page.json`.

**Baselines (trees on, page readers off):** tuning
`work/bench/tuning-20261013T210052-1cc82e3-dirty.json` (0.32 after review), validation
`validation-20261013T210233-1cc82e3-dirty.json` (0.50). The page readers' runs:
`tuning-2026101[45]*` and `validation-20261015T031320-fdabf21-dirty.json`, made with
`ROBO_PAGE_READERS=1` and `work/models/ocr-trust-page.pkl` (trust data in
`work/probes/ocr-trust-page/`).

## What this session did (numbers in docs/decisions.md, 2026-10-14 and 15)

- **Page readers built** (`pagereader.py`, `ROBO_PAGE_READERS`, off): glm-ocr and Qwen
  read each page whole, the reading split into the layer's lines as two more readers
  for the arbiter, which now records the readers it was trained on. Benched overnight:
  tuning no change (0.32 → 0.32), validation 0.50 → 0.43 after review but worse before
  it on two books (the arbiter takes their versions wrongly on unseen books). They stay
  off as line readers. **The night mostly went to the wrong design**: the evening's
  probes had already shown the gain sits at line joins and page numbers, which a line
  split can't carry. What it left: every tuning and validation page's two readings.
- **Where the gain is** (probes, no models): a line no page reader reads isn't text 250
  times in 254 (a feature for the line-role trees); both readers' spelling of a
  line-end compound fixes 11 of reflow's wrong hyphens and breaks 5 (on 40% of pages).
- **The cold A/A**: rebuilding every cache moves `bench tuning` by 0.01 at most (0.32 →
  0.33, [+0.00, +0.01]). The noise floor for cache-invalidating changes is as narrow as
  for warm ones.
- **Readers**: every line reader earns its place today (unasked errors 15; 21 without
  tesseract, 43 without glm-ocr, 55 without Qwen); with the page readers in, tesseract
  adds nothing. Qwen's mxfp8 build reads pages no better (not taken); ornith-1.5:35b
  rejected as a reader, the 9b crashed Ollama.
- **Low Power Mode** measured: half the speed or worse.
- **Wasted**: the page-kinds slot, on a book retired two days before (the probe now
  skips it; not rerun).

## Next, in order

**Ask the user at the start of the session** which cache set the 16 tuning books keep:
the warm one in `stages/` only, or the cold one in `stages.cold/` too (and whether the
unused Ollama models listed under "Waiting on the user" can go).

1. **The line-role trees with "no page reader read this line" as a feature**, on the
   cached readings: a warm bench (checklist, "Assumptions to test").
2. Both page readers' spelling of a line-end compound in a learned hyphen decision
   (rerun `probe_page_hyphens.py` on all pages first, no models).
3. Page kinds for `init` (`probe_page_kinds_model.py`, ~70 min of model time; its
   inputs checked, the two retired books skipped): when the user has a slot.
4. Drop tesseract only if the page readers ever go in.
5. The rest of the checklist's "Assumptions to test"; retire `roles.py` rules the trees
   make redundant; Dolittle's wrapped text.
6. From before, still open: the quick bench tier (checklist), a sampled Ex-minnaar
   review, then Stella (the user: no urgency), `roboscriptorium init`.

**Remind the user of the daily backup of `work/`** at session start and before long
runs. Last one: 2026-10-15, at the end of this session.

## What this session taught (the rules are in AGENTS.md)

- **Sort a probe's catches by where they sit, and change the plan when they move**,
  before spending a night on the design chosen before the probes.
- **Check every input of a queued run, not a sample**: one book's test passed, the
  queue failed on a retired book. The user's compute time is scarce.
- **Check the clock before writing a time down**: a start time written from memory
  (12:15 for 16:00) made a healthy run look broken and nearly sent the session after a
  bug that wasn't there.
- **Short jobs first in a night's queue, the long one last and safe to stop**: the A/A
  now swaps its caches back when stopped (`work/runs/queue-20261014.sh`).

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen);
  never a background shell command (it times out). Say the estimate first
  (docs/run-times.md: a cold build ~1.1 min a page; Ex-minnaar took 306 min).
- Don't edit `src/` while a bench chain runs; park a change as a patch.
- A probe or eval on a golden book takes the bench's slice, never the bare directory.
- Nothing reads the test set (Het geluid van bananen) until its single scoring; its
  reference must be rederived first (it missed today's derive changes).
- Stopping a run: `experiments/stop-run.sh <name>` (quitting its screen leaves the step
  running); `ollama stop <model>` frees the memory.

## Waiting on the user, besides the above

- Remove the Ollama models nothing uses: `gemma4:latest`, `deepseek-ocr:3b`,
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`, and the
  rejected `ornith-1.5:9b`, `ornith-1.5:35b`, `qwen3.8:27b-mxfp8`.
- Which cache set the tuning books keep: warm (`stages/`) or also cold (`stages.cold/`).
- More golden pairs when convenient: De Arbeiderspers, Prometheus/Ooievaar or Vrijdag
  preferred (publishers already used are listed in docs/checklist.md); a Kosmos book
  for later, beyond prose. Wanted now: a book with text wrapped around its pictures
  (Dolittle's case), and a retail-EPUB pair with pictures to replace De tunnels' OCR-made
  reference (the user was looking).
- **French**: undecided (checklist, Later).
- The worktree `../roboscriptorium-py315` (branch `py315`) waits for a PyTorch release
  with cp315 wheels (pytorch/pytorch#184352); a stale worktree entry from an old
  scratchpad (`git worktree list`); the remote `origin/bughunt` is merged and can go.

## Recovery, 2026-10-11 ~20:35: an agent destroyed work/

The agent symlinked `work` into a worktree, committed the link (`git add -A`) and merged it, which replaced the
ignored `work/` folder with it (fixed in afd6dd2; `.gitignore` says `/work`; never
symlink data into a worktree, stage by name: the user's global CLAUDE.md). Restored
from the user's Downloads, fingerprint-checked against the manifests: every golden
scan and publisher EPUB, `golden fetch` (book.toml, IA files) and `golden derive` for
all 25 copyrighted references; the user's five books (source.pdf from Downloads,
book.toml rewritten from the docs; Ex-minnaar is the 11 MB PDF); Stella's two dated
EPUBs of 2026-10-07; `work/tessdata/nld.traineddata` and the word lists.

From the user's backup of 2026-10-07 13:34 (a full copy of the project then): Goede
dochter's 23 verdicts and Dolittle's 30 review answers, copied into `work/`. Its stage
caches were left out (older formats and code). **Human work lost for good**: Stella's 83
review answers (given after the backup), Goede dochter's 32 slip-review answers
(`slip-review--goede-dochter`, the bench's slip rate), Koning Wilders' verdict ("wàs" ×2).
**Machine work lost**, to recompute: every stage cache
(days of model time), Stella's review answers, all golden verdicts (none were in git;
Koning Wilders' "wàs" ×2 is in decisions.md), the arbiter and line-role trees
(`work/models/`), the trust data, bench results (`work/bench/`), tryout crops and
readings (`work/tryout/`), the page-kind label files (the frozen set is in git), and
every probe.
