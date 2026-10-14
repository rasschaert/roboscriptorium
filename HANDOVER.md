# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-14 ~09:10, at the end of the session of 2026-10-13
evening and night.

## Nothing running. Ollama's context is at 32k (the user, for glm-ocr's whole pages).

## Decided, to build next: the page readers as two more readers for the arbiter (option B)

The session's best finding (decisions.md 2026-10-14, outlook item 0): glm-ocr and Qwen
each read every page whole; where both agree against the build, paragraph breaks aside,
they point at 60 errors over the tuning books that no question asks (about a quarter of
the 0.32 wrong words a page left after review), for ~0.3 more questions a page. **The
user chose B (2026-10-14):** each page reading is split back into its lines and fed to
the OCR check as two more readers, so the arbiter learns how far to trust each per kind
of error, and the review, answers and bench work unchanged. Not A (a question wherever
both agree: a hand-written trigger). About a day of building (a cached page-reading
stage; aligning each page reading to the layer's lines, splitting a word the layer breaks
over a line end as `golden/align.py` does), then the trust data rebuilt and the arbiter
retrained overnight, then the benches.

The probes and their cached readings: `experiments/probe_page_reader.py`,
`probe_page_joins.py` (with `SECOND=`), `probe_page_agreement.py`;
`work/probes/page-reader/` (glm-ocr at full size in `glm-ocr_bf16@1600000/`, Qwen in
`qwen3.8_27b-nvfp4/`). glm-ocr must be streamed: it has no stop token, and Ollama
aborts its repeats with "token repeat limit reached".

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

## What this session did (all pushed; numbers in docs/decisions.md 2026-10-13/14)

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

1. Build the page readers into the OCR check (option B, above), then the trust data, the
   arbiter and the benches (the readings are new: ~18 s a page, ~4 h for tuning; overnight).
2. Finish the cold A/A (above).
3. The rest of the checklist's "Assumptions to test": paragraph breaks and line roles
   asked of a model with the page image; page kinds for `init` by Qwen.
4. Retire `roles.py` rules the trees make redundant; Dolittle's wrapped text.
5. From before this session, still open: the quick bench tier (checklist), De eerlijke
   vinder's page numbers kept (the page readers catch 13 of them), a sampled Ex-minnaar
   review, then Stella (the user: no urgency), `roboscriptorium init`.

**Remind the user of the daily backup of `work/`** at session start and before long
runs. Last one 2026-10-14 ~09:30, after this session's work.

## What this session taught

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
