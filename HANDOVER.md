# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session.

## Paused, 2026-10-12 09:23: the rebuild on nvfp4, after Reis (the user)

Trust data done for 5 of 20 books: Goede dochter, Vals alarm, Crime, Dolittle, Reis
(`work/probes/ocr-trust/`; progress in `work/runs/rebuild/progress.txt`). Restart with
`experiments/detached.sh rebuild experiments/rebuild-trust.sh`: it skips books whose
trust data exists. To pause after the book under way: `touch work/runs/rebuild/STOP`
(delete it before restarting). Reader `qwen3.8:27b-nvfp4` (the user: stick with it; they
test other builds themselves). `qwen3.8:27b-mxfp8` is **not** pulled. The worktree
hazard below is gone (`../roboscriptorium-review` and branch `review-display` removed).

## State, 2026-10-12 ~00:40, session end: nothing runs; the reader question is half answered

**Remind the user of the daily backup of `work/`** before any long run. Nothing runs: no
screen, Ollama idle (0.40.3; 8k context in the app; `OLLAMA_NUM_PARALLEL=4` by
`launchctl setenv`, which doubled glm-ocr and changed nothing else: AGENTS.md Environment).
Lint and tests green (370).

**The rebuild chain is stopped**, at Goede dochter's Qwen stage (22:12, the user's go),
and waits on the reader choice below. Its caches stand (Goede dochter's layout, roles,
glm-ocr and tesseract readings); `experiments/detached.sh rebuild
experiments/rebuild-trust.sh` resumes from them: ~28 h of trust data at the measured rates
(2,188 pages × ~48 s, Qwen ~22 h of it), then the arbiter and `bench tuning`
(docs/outlook.md, "Inference speed"). The user is unhappy with two days of fan noise:
run it in nights if that's their wish (the chain does one book a step, so stop it between
books with `screen -S robo-rebuild -X quit` and `pkill -f ocr_trust_data.py`, restart later).

**The reader (docs/decisions.md 2026-10-12).** Nothing on the server makes Qwen faster
without changing what it reads, so the only lever is a different build of the reader,
screened on reader set v2 (`tryouts/reader-v2.json`, 850 lines; the incumbents' readings
are cached under `work/tryout/reader-v2/readings/`, so a candidate costs its own 850
lines, ~17 min at Qwen's pace, through `experiments/timed.sh` in `detached.sh`; the
result goes to `tryouts/results.jsonl` with seconds a line). Done: **`qwen3.8:27b-q8_0`
rejected** (no more accurate, 2.2 s a line at any concurrency: the llama.cpp runner
doesn't batch a 27B). Pulled by the user, **not yet
screened**: `qwen3.8:27b-mxfp8` (Ollama, MLX, so one request at a time: a precision
candidate, not a speed one) and Unsloth's UD-Q6_K_XL and UD-Q8_K_XL through Unsloth
Studio's server on port 8888 (`uv run python experiments/tryout.py run reader
openai-local:<id as Studio names it>`; one model loaded at a time, never beside a build
or bench: memory). Score first, speed second; if none beats the nvfp4 build on both
strata, keep it and restart the rebuild as it is. A winner is pinned in `config.py`
(`read_model`), then the rebuild runs on it; record it in docs/models.md and the roles
table in AGENTS.md.

**What's measured and need not be measured again** is in docs/outlook.md under
"Inference speed": Qwen's 1.2 s a line and its split, no gain from concurrency, crop
size, context or pooled decision calls, the system-turn layout (30% faster, 4 of 64
readings change: a tryout candidate if someone adds a layout setting to
`ocrcheck.transcribe`), what a faster reader must pass.

## Recovery, 2026-10-11 ~20:35: work/ was deleted

A worktree's `work` symlink was committed (`git add -A`) and the merge replaced the
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
every probe. Nothing runs; start no model job without the user's go.

## State, 2026-10-11 ~18:30, session end (the user is about to run a memory-heavy job)

On `main`, pushed, clean. Lint and tests green (370). **Nothing runs**: no screen, Ollama
unloaded. **Ask the user before starting any Ollama or llama job**: they asked for none
for now.

**Running: the page-kind probe** (clef-flash on the labelled pages, ~75 min, screen
`robo-pagekinds`, log `work/runs/pagekinds.log`; answers cached, a rerun resumes).
**The validation bench was stopped again** (memory: 14% free with Qwen and clef-flash
both loaded, swap full). Koning Wilders is done in the cache; Het laatste bevel's Qwen
reading stands at 800 lines. Restart `bench validation` after the probe.

Qwen3.8-Flash-Next (~1 bit, the user's Unsloth Studio) was screened as a
reader and rejected (docs/models.md); `experiments/tryout.py` keeps its `openai-local:`
path for the next model served that way.

### Waiting, in this order

1. **Hazard: the worktree `../roboscriptorium-review` still holds the committed `work`
   symlink** (pointing at the real `work/`), and branch `review-display` (merged in
   1f41e1a) still tracks it, locally and on origin. Nothing may write into, check out
   over or delete through it. With the user's go: `git worktree remove --force
   ../roboscriptorium-review` (git unlinks the symlink rather than following it), then
   `git branch -D review-display` and `git push origin --delete review-display`.
2. **Agreed, in progress: `roboscriptorium init <pdf>`** (checklist, Beyond the golden
   books' kind; what goes in the EPUB is decisions.md 2026-10-11). Labels done:
   `tryouts/page-kinds-v1.json` (31 books, 1,034 pages; per-book files and notes in
   `work/probes/page-kinds/`). Text-layer clues alone don't find the edges
   (`experiments/probe_page_signals.py --score`). Next, after the bench: clef-flash's
   page-kind question with the page image on the labelled pages (~1,000 × ~4 s ≈ 1 h).
   `init` must give front and back pages a kind each, not one range: a dedication or
   motto sits after the title page and colophon.
   Verminkt joins validation as a slice (~90 pages, the user agreed) once the bench ends.
3. **Verminkt: checked, fit, asked the user whether it joins a set.** Its two printings
   print the same text (docs/golden-notes.md, `probe_printing.py`). Proposed: validation,
   with a slice of ~90 pages like Het laatste bevel (the whole book is ~7½ h cold). Its
   layer writes ij as y throughout, which no other pair tests.
4. **Validation bench, stopped at the user's request** (18:25): Koning Wilders' Qwen
   reading is cached at 600 of 2,439 lines; resuming costs ~45 min Qwen + ~25 min judges,
   and Het laatste bevel's slice (pages 9–100) ~1¾ h cold. Only with the user's go.
5. **Ex-minnaar's review, the user, not soon**: 390 questions, all of them (the user's
   choice): `uv run roboscriptorium review work/ex-minnaar`. Built, epubcheck clean,
   dated copy in `work/ex-minnaar/epubs/`. Do the display fix (1) first.
6. **Stella, the user, not today**: read `work/stella/stella.epub` through, note errors.

### The bench (after today's set changes)

Tuning is 17 books (De eerlijke vinder and Monterosso moved in today, arbiter and trees
retrained): **0.36** wrong words a page after review over all 17 (0.31 over the 15 it
shares with this morning's set; De eerlijke vinder 0.99, Monterosso 0.50). Validation
was 0.64 on its 5 books before Koning Wilders (Atlas Contact) and Het laatste bevel
(Manteau, slice 9–100) joined; neither is benched yet (see 4). Paragraph breaks ~0.2 a
page on both.

## What today taught (read before choosing work)

- **The print is canonical** (the user). The output keeps the print's words, accents,
  italics, paragraphs and its own typography (dash and spacing, ellipsis, quote marks);
  no house style (AGENTS.md, Fidelity). Where a reference EPUB differs from its print:
  a systematic gap is undone in derive (manifest settings), a glyph choice is folded in
  scoring, a one-off is a verdict (the user gave "wàs" for Koning Wilders).
- **An old EPUB copy found two regressions** (Stella's 2026-10-07 build): every build
  now keeps a dated copy in `work/<book>/epubs/` (`epub.keep_dated`). Diff them.
- **Pre-check a user book's front matter before its cold build** (a probe copy, pages
  around the start, `check_ocr=False`, minutes): De kus's part label was dropped as a
  page number (fixed: `heading-label`), Ex-minnaar's motto became the first paragraph
  (fixed: epigraphs), Een Russische roman's part number "1" is dropped and its library
  pencil marks read as text (left for its full build to show what it asks).
- **Sample the questions on their crops before sending the user**: Ex-minnaar's
  lost-line questions were a song's stanza breaks (fixed); 390 remain, mostly real.
- **Quote styles at hand**: all 25 books are ‘-dialogue or “-dialogue; « » „ ‚ appear
  only as misreads. Nested (inner) quotes are assumed, not learned (checklist).
- **Most errors left after review were never suspects** (all readings agree): the
  rule-sized groups are done; the proofreader, the book's own consistency and the book
  teaching itself (simulated again today: gain concentrated in De kerk and Vuurspel)
  don't pay yet. Accuracy moves by better readers, trustworthy measurement and review.
- **Gate commits on the test run**: `uv run pytest -q && git commit`, never a filtered
  run (a failing test went in once today, fixed in the next commit).
- **The user wants plain English** in reports: say what a thing does before its name.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen);
  never a background shell command (it times out). Say the estimate first
  (docs/run-times.md: a cold build ~1.1 min a page; Ex-minnaar took 306 min).
- Don't edit `src/` while a bench chain runs; park a change as a patch.
- A probe or eval on a golden book takes the bench's slice, never the bare directory.
- Nothing reads the test set (Het geluid van bananen) until its single scoring; its
  reference must be rederived first (it missed today's derive changes).
- Killing a chain: quit its screen and `pkill -f` the step; `ollama stop <model>` frees
  the memory.

## Waiting on the user, besides the above

- Remove the Ollama models nothing uses: `gemma4:latest`, `deepseek-ocr:3b`,
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`.
- More golden pairs when convenient: De Arbeiderspers, Prometheus/Ooievaar or Vrijdag
  preferred (publishers already used are listed in docs/checklist.md); a Kosmos book
  for later, beyond prose.
- **French**: undecided (checklist, Later).
- The worktree `../roboscriptorium-py315` (branch `py315`) waits for a PyTorch release
  with cp315 wheels (pytorch/pytorch#184352); a stale worktree entry from an old
  scratchpad (`git worktree list`); the remote `origin/bughunt` is merged and can go.
