# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-14 ~12:00, during the session of 2026-10-14
morning (until ~13:00).

## Running: `robo-page-mxfp8`, Qwen's bigger build reading whole pages

`experiments/probe_page_reader.py qwen3.8:27b-mxfp8 qwen3.8:27b-nvfp4` on the probe's 19
pages (output `work/runs/page-mxfp8.out`): if mxfp8 reads pages cleaner than nvfp4 (76
wrong words), tonight's chain should read with it (`ROBO_READ_MODEL` covers the line
reader too, so a page-only model setting would be needed). Ollama's context is at 32k.

The trial of tonight's chain on Het ijzige land ran clean (3 min): its trust data with the
page readers is in `work/probes/ocr-trust-page/` (the chain skips it), 70 suspects
against 56 without them, 14 raised by the page readers alone.

## Built, to run tonight: the page readers as two more readers for the arbiter

`pagereader.py` (committed, tests through `pipeline.run`): glm-ocr and Qwen read each
body page whole, cached in `stages/page-reading-{glm,qwen}-page.json`; each reading is
split back into the layer's lines and joins the OCR check as the readers `glm-page` and
`qwen-page`. **Off** (`ROBO_PAGE_READERS=0`) until an arbiter trained with them wins the
bench; the arbiter now records which readers it weighs, and a build whose page readers
don't match its arbiter stops. The probes' readings are seeded into the warm stage
caches (`experiments/seed_page_readings.py`, ~350 pages a reader).

**Tonight's chain** (`work/runs/chain-20261014.sh`, nothing in it touches the current
arbiter or trust data): read the ~1,000 pages left (`experiments/read_pages.py`; glm-ocr
9 s, Qwen 15 s a page, ~5–7 h), rebuild the trust data with the page readers into
`work/probes/ocr-trust-page/`, train `work/models/ocr-trust-page.pkl`, then `bench
tuning` and `bench validation` against the 2026-10-13 baselines. Start it with

```sh
experiments/detached.sh page-readers work/runs/chain-20261014.sh
```

Then: if both benches agree, the page readers go on by default and the diagram, README
and how-it-works follow (checklist). Expect much less than the probe's 60: of the 40 it lists only about 9
sit within a line; line-end hyphens, page numbers and joins can't be carried (design.md,
"Page readers"); those need the page reading in `hyphens.py` and the line-role trees.

## Paused: the cold A/A tuning bench (the noise floor when caches change)

11 of 16 tuning books are built cold (Goede dochter to De tuin van de avondnevel); left:
Het heft in eigen hand, Doodskleed, Het ijzige land, De eerlijke vinder, Monterosso
(~4 h). **The caches now:** warm in `work/<book>/stages/`, cold in `stages.cold/` for the
16 tuning books (list in `work/runs/tuning-books.txt`). To resume (evening or while the
user is away): per book `stages` → `stages.warm`, `stages.cold` → `stages`, then

```sh
experiments/detached.sh bench-tuning-cold experiments/timed.sh "bench tuning, cold A/A rerun, resumed" 790 work/runs/bench-tuning-cold.log uv run roboscriptorium bench tuning --against work/bench/tuning-20261013T210052-1cc82e3-dirty.json
```

`work/runs/chain-20261013.sh` has a `swap` function that does the renames with guards.
The cold part ran first at 8k context, overnight at 32k; its warm baseline ran at 8k.
AGENTS.md records readings as the same either way; say so beside the result. When done,
the paired verdict is the noise floor: record it, then swap the warm caches back and
keep both sets until the user says which to drop.

## What the session of 2026-10-13 evening did (numbers in docs/decisions.md)

- **Line-role trees on by default**: validation 0.59 → 0.50, tuning no change, no book
  worse. Three things got them there: the labeller called specks body (fixed in
  `golden/align.py`), two picture slices joined their training (De tunnels ch. 12, a
  training-only pair with an OCR-made EPUB; Steve Jobs' photo insert pp. 387–402), and a
  body line weighs ten times its share. Left: Dolittle's text set around its drawings
  (wants a book with text wrapped around pictures). Next: retire each `roles.py` rule the
  trees make redundant, one bench each.
- **Bugs fixed with tests**: a dash a fix puts before a line now widens the line's box
  (Dolittle 0.40 → 0.31); derive takes a paragraph wholly inside a heading-class span as a
  heading; `bench` names settings that differ from its baseline (a run had compared
  itself with an experiment's run and read BETTER).
- **Steve Jobs** is a full pair (retail EPUB of the first printing, IA scan of the fifth;
  layer CER 0.47%, OCR slips only); for now only its photo insert is used.
- **Fine-tuning a reader is off**: 29% of what's left after review is misreading no
  reader doubted, under the half agreed as the bar.
- **Afscheid stays** (its retirement misread an all-lines figure; the rule is now
  explicit in AGENTS.md); the three retired books' files are deleted from `work/`.
- **New standing rule** (AGENTS.md): test the pipeline's assumptions, not only its
  settings; the checklist opens with "Assumptions to test".

**Baselines (trees on):** tuning `work/bench/tuning-20261013T210052-1cc82e3-dirty.json`
(0.32), validation `validation-20261013T210233-1cc82e3-dirty.json` (0.50).

## Next, in order

1. Tonight's chain (above), then the benches' verdict on the page readers.
2. Finish the cold A/A (above); not the same night as the chain (both hold Ollama).
3. The page readings where a line can't carry them: line-end compound hyphens for
   `hyphens.py`, lines no page reader has words for (page numbers) for the role trees.
4. The rest of the checklist's "Assumptions to test": paragraph breaks and line roles
   asked of a model with the page image; page kinds for `init` by Qwen.
5. Retire `roles.py` rules the trees make redundant; Dolittle's wrapped text.
6. From before, still open: the quick bench tier (checklist), a sampled Ex-minnaar
   review, then Stella (the user: no urgency), `roboscriptorium init`.

**Remind the user of the daily backup of `work/`** at session start and before long
runs. Last one 2026-10-14 ~09:30, after this session's work.

## What the session of 2026-10-13 taught

- **Test the assumption before tuning around it** (the user, twice). "Local models can't
  read a whole page" took a 30-second test to overturn, and led to the largest gain in
  sight. Fine-tuning and threshold tweaks have diminishing returns.
- **A role error count isn't the bench.** The trees cut raw role errors by a third and
  still made the bench worse until the labels and the weighting were right: which line
  is wrong matters (a dropped caption loses text unasked; a kept speck is asked).
- **Check a bench's baseline**: by default it compares with the last saved run, whatever
  its settings (now printed).
- **A reference made by OCR** (calibre, Sigil, hyphens left in, small capitals as "jfk")
  can still label line roles, but never score words.
- **glm-ocr has no stop token**; on llama.cpp its four slots share Ollama's context.
- **The user wants the what and the why of every run in plain English**, one sentence
  each, before it starts (confirmed 2026-10-14).

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
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`.
- More golden pairs when convenient: De Arbeiderspers, Prometheus/Ooievaar or Vrijdag
  preferred (publishers already used are listed in docs/checklist.md); a Kosmos book
  for later, beyond prose. Wanted now: a book with text wrapped around its pictures
  (Dolittle's case), and a retail-EPUB pair with pictures to replace De tunnels' OCR-made
  reference (the user was looking).
- **French**: undecided (checklist, Later).
- The worktree `../roboscriptorium-py315` (branch `py315`) waits for a PyTorch release
  with cp315 wheels (pytorch/pytorch#184352); a stale worktree entry from an old
  scratchpad (`git worktree list`); the remote `origin/bughunt` is merged and can go.
