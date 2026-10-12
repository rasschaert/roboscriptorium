# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session.

## Running, 2026-10-12 ~11:10: the trust-data rebuild on nvfp4, 15 books to go

**Remind the user of the daily backup of `work/`** at session start and before long runs
(they back up with Duplicati, ~9 min; last run just before this restart).

**What runs:** screen `robo-rebuild`, `experiments/rebuild-trust.sh`, reader
`qwen3.8:27b-nvfp4` (final: the user). Trust data for each of the 20 books in
`work/probes/ocr-trust/<book>.json`, one book at a time; a line per finished book in
`work/runs/rebuild/progress.txt`, each book's log in `work/runs/rebuild/<book>.log`.
Done: Vals alarm, Crime, Dolittle, Afscheid (its screen vanished ~11:46 with no exit
line, cause unknown; restarted 12:50 on the stage caches). At ~13:30 the slices were
capped at ~90 pages (the user; decisions.md 2026-10-12): the chain was stopped mid-Metro
and restarted, so Goede dochter and Reis are redone on their new slices from cache
(minutes; their long-slice data kept as `*.long-slice.json`) and Metro goes on with its
new slice. The 14 left take ~17 h. Its bench step's timing label still says 1792 pages
(the running script wasn't edited): correct that line in docs/run-times.md to 1455, as
the bench also scores FKA USA, the new footnote book (90 pages cold, ~1.7 h more, with
the full arbiter; its trust data comes after, checklist). When every book has succeeded the chain trains the arbiter
(`work/models/ocr-trust.pkl`) and runs `bench tuning`, the new baseline.

- **Check on it:** `tail work/runs/rebuild/progress.txt`; `screen -ls`.
- **Pause after the book under way:** `touch work/runs/rebuild/STOP` (delete it before
  restarting). **Stop now:** `experiments/stop-run.sh rebuild` (quitting the screen
  leaves the step running). **Restart:** `experiments/detached.sh rebuild
  experiments/rebuild-trust.sh`; it skips books whose trust data exists, and a stopped
  book's stage caches stand.
- A failed book is logged and the chain goes on, but then trains nothing: rerun the
  chain once the cause is fixed.
- Keep other model work off Ollama meanwhile; a probe beside it sends the chain's
  options (AGENTS.md).

**The reader is settled** (docs/models.md, decisions.md 2026-10-12): the nvfp4 build on
MLX stays. Screened on reader set v2 (850 lines) against its 463/510 hard and 338/340
control at 1.20 s a line: Ollama's q8_0 458/333 at 2.06 s; Unsloth's UD-Q6_K_XL 457/334
at 1.71 s and UD-Q8_K_XL 460/334 at 1.76 s (both through Unsloth Studio). The three GGUF
builds make the same control-line errors word for word, which the nvfp4 doesn't: the
llama.cpp runtime, not precision, sets them apart. More precision is worth testing only
as an MLX build (`qwen3.8:27b-mxfp8`, pulled; screen it after the chain). Unsloth Studio passes requests to its
llama-server one at a time, so its slots don't speed anything; it switches quant when a
request names one (`unsloth/Qwen3.8-27B-GGUF:UD-Q8_K_XL`). Its run settings' Extra
Arguments box shows example text that isn't passed: read the running `llama-server`
command line instead.

**Stella's dated EPUBs** (`work/stella/epubs/`): 2026-10-07 1221 and 1547 (from the
backup) and 2026-10-11 1202 (the user's Calibre copy, our build before that evening's
fixes). Diff the next build against them.

### Next, in order (after the chain's bench)

Regenerate docs/golden-books.md after the bench: its last-bench column says "none yet"
for every book since the loss.

1. Correct anything the bench shows; then the line-role trees (`experiments/train_sorter.py
   --save`), then `bench validation`, with Verminkt joining validation as a slice (~90
   pages, agreed).
2. Stella: rebuild, diff against the dated copies, then the user reads it through.
3. A sampled Ex-minnaar review, 10–20 questions, to find lessons with wide effect before
   the user faces its full ~390 (the user asked for it; blocked by the loss).
4. `roboscriptorium init <pdf>` (agreed; checklist, "Beyond the golden books"): each
   page a kind; what goes in the EPUB is decisions.md 2026-10-11 (a list of what's left
   out); runs on its own when `book.toml` is missing. Labels: `tryouts/page-kinds-v1.json`.
   Next is clef-flash's page-kind question with the page image (~1 h), then the build.

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

## The bench before the loss (2026-10-11), to compare the rebuilt one against

Tuning is 17 books (De eerlijke vinder and Monterosso had just moved in, arbiter and trees
retrained): **0.36** wrong words a page after review over all 17 (0.31 over the 15 it
shares with the set before; De eerlijke vinder 0.99, Monterosso 0.50). Validation
was 0.64 on its 5 books before Koning Wilders (Atlas Contact) and Het laatste bevel
(Manteau, slice 9–100) joined; neither was benched. Paragraph breaks ~0.2 a
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
- Stopping a run: `experiments/stop-run.sh <name>` (quitting its screen leaves the step
  running); `ollama stop <model>` frees the memory.

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
