# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session.

## Nothing running. `bench validation` halted 2026-10-13 07:56, on its last book

**Remind the user of the daily backup of `work/`** at session start and before long runs
(they back up with Duplicati, ~9 min; last run 2026-10-12 21:40, before the bench).

**First thing next session:** finish `bench validation` (started 2026-10-12 21:45, halted
by the user to pack up the laptop). Eight of its nine books are built and cached; Normal
People had its tesseract and second readings done and was about two-thirds through the
qwen3.8 third reading (saved in part). The rerun redoes nothing finished: Normal People's
rest (~25 min reading, ~13 min judges, going by The Stranger's Child), then the other
eight warm (minutes). Say ~45 min, then:

```sh
experiments/detached.sh bench-validation experiments/timed.sh "bench validation, finishing after a halt (8 of 9 books warm)" 916 work/runs/bench-validation.log uv run roboscriptorium bench validation
```

Then report each book and the set against tuning's 0.31, and run a warm `bench tuning`
(~3 min) for the effect of the verdicts and the minus-dash fix. No timing row was written
for the halted run (timed.sh only appends on exit); the overnight part took ~10 h for
eight books, ~830 pages cold.

**Tuning baseline (2026-10-12, `work/bench/tuning-20261012T190056-…json`): 0.31** wrong
words a page after review over 17 books (FKA USA left out till its fixes). Since then:
the user's verdicts (Goede dochter 46, Metro 24, Monterosso 19, De eerlijke vinder 14,
Dolittle 3) and De eerlijke vinder's minus-sign dashes undone in its reference; a warm
`bench tuning` (~3 min) after the validation run shows what they move.

**Slice size, measured:** more pages a book teach the arbiter little (about 0.01 wrong
words a page from 10 pages to all) and narrow the bench some; short slices stay short
(decisions.md 2026-10-12).

**Verdict rounds are stopped** until the single review exists (checklist, "One review for
a golden book"): the user stopped the round after the verdict page kept missing what the
region review has (kinds, a caption's words, a decorated initial). Never serve them a
reduced page again (memory: one review UI). Dolittle, Crime and De tuin are unanswered.

**Next session (Tuesday evening or Wednesday), in order:** the single review; De eerlijke vinder's 25 page numbers kept in
the running text (rules and sorter model, Stella's scan format); its error analysis;
Monterosso's T read as a quote; Metro's lost quote after an ellipsis; FKA USA's fixes and
trust data; then the checklist.

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

### Next, in order

1. Correct anything the bench shows; then the line-role trees (`experiments/train_sorter.py
   --save`), then `bench validation`, with Verminkt joining validation as a slice (~90
   pages, agreed).
2. A sampled Ex-minnaar review, 10–20 questions, to find lessons with wide effect before
   the user faces its full ~390 (the user asked for it; blocked by the loss).
3. The user's Ex-minnaar review, then the fixes it teaches; only then Stella: rebuild
   with those fixes, diff against the dated copies, the user reads it through (the
   user, 2026-10-12).
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
