# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session.

## Nothing running

`bench validation` finished 2026-10-13 20:02: BETTER 1.10 → 0.59 (decisions.md), mostly
The Stranger's Child. Its builds are warm for the line-role trainer.

Last warm `bench tuning`: 2026-10-13 17:25, NO CHANGE (0.33 → 0.32), three pairs retired.
De tuin van de avondnevel got significantly worse under the retrained arbiter (0.38 → 0.43;
questions 1.05 → 1.37 a page); worth a look once Stella's trust data is rebuilt.

The three retired books' files are deleted from `work/` (in the user's backups).
Afscheid van verspilde tijd stays: its proposed retirement misread the all-lines
overview (decisions.md 2026-10-13).

**Line roles:** `work/probes/sorter/` was lost with `work/`, so `train_sorter.py` rebuilds
its lines from warm builds (ROBO_SORTER=0 is the default) once the validation bench is done.

After the codebase review (2026-10-13): the user put its fixes first and said building
Ex-minnaar or Stella has no urgency. Done and pushed: eight bugs fixed with tests
(9e67c24); the bench prices the reviewer's time, 20 questions = one wrong word (the user),
and its verdict rule is symmetric (99ed76a); a typography count of its own (034bc7c), whose
first run found straight quotes kept from the layer in curly books, now curled (45aeca0, 3782e7e). Then 11/22/63, FKA USA and Koning Wilders were retired (the user) and the arbiter retrained without them (3371ddc; bench NO CHANGE). Their files in `work/` wait on the user's yes to delete. The user's direction: learned decisions, not hand-written rules (AGENTS.md). **Next, in order:** line roles by the trees (retrain, bench on top of the rules), then
the rest of the checklist's "From the codebase review" section (the cold A/A rerun goes
overnight), then what is below.

If the validation bench above was cut off, restart it with:

```sh
experiments/detached.sh bench-validation experiments/timed.sh "bench validation, ellipsis measured on the scan, after a halt" 916 work/runs/bench-validation.log uv run roboscriptorium bench validation
```

Compare against `work/bench/validation-20261013T082508-d4c197e.json` (The Stranger's Child
4.57; set mean 1.06, 0.62 without it).

**The feedback loop, agreed with the user 2026-10-13:** (1) a change upstream of the
caches (a prompt, a crop, a model, the arbiter) is decided on the frozen line sets
(`experiments/tryout.py`), the bench only confirms; (2) a quick bench tier: each tuning
book's first chapter or two (~10–20 pages, ending on a chapter so the reference lines
up; tuning books only, as it is chosen on), ~5 h cold, checked once overnight that it
ranks changes as the full bench does; `experiments/chapter_pages.py <golden> <scan>` gives
the chapters' pages (was being run over the tuning books when halted); (3) cold runs only
overnight or while the user is away. Rules (1) and (3) still to be written into AGENTS.md;
(2) still to be built (checklist).

**Remind the user of the daily backup of `work/`** at session start and before long runs
(they back up with Duplicati, ~9 min; last run 2026-10-13 morning, before this session).

**Tuning, warm, 2026-10-13** (`work/bench/tuning-20261013T085119-e8ff4b4.json`): BETTER,
0.52 → 0.50 [−0.03, −0.01] after review over all 17 (0.29 over the 16 without FKA USA,
against 0.31): De eerlijke vinder 0.91 → 0.68 (its minus-sign dashes undone), Goede dochter
0.28 → 0.24 (the user's verdicts), Monterosso 0.50 → 0.47. FKA USA is named a suspect pair
(30% of its body lines unplaced). Koning Wilders too (validation, layer CER 2.45%).
Whether to retire them is parked by the user, but must be decided (checklist).

**The single review is in** (merged 2026-10-13): `roboscriptorium review` on a golden
book asks its places that differ from the e-book in the same list as its flagged regions,
answers stored as verdicts; `golden review` is gone; each side's words shown as written.
Walked on Dolittle (89 questions, 15 places). Verdict rounds can resume on it: Dolittle,
Crime and De tuin are unanswered; pass the bench's slice (`--pages`, `--chapters`). A
place on a line with an OCR doubt is still its own question right after the doubt, not one
more row in it (decisions.md 2026-10-13).

**Tuning baseline (2026-10-12, `work/bench/tuning-20261012T190056-…json`): 0.31** wrong
words a page after review over 17 books (FKA USA left out till its fixes). Since then:
the user's verdicts (Goede dochter 46, Metro 24, Monterosso 19, De eerlijke vinder 14,
Dolittle 3) and De eerlijke vinder's minus-sign dashes undone in its reference; a warm
`bench tuning` (~3 min) after the validation run shows what they move.

**Slice size, measured:** more pages a book teach the arbiter little (about 0.01 wrong
words a page from 10 pages to all) and narrow the bench some; short slices stay short
(decisions.md 2026-10-12).

**Then, in order:** De eerlijke vinder's 25 page numbers kept in the running text (rules
and sorter model, Stella's scan format); its error analysis; Monterosso's T read as a
quote; Metro's lost quote after an ellipsis; FKA USA's fixes and trust data; then the
checklist.

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

1. The ellipsis fix and both benches warm; then the line-role trees
   (`experiments/train_sorter.py --save`); Verminkt joins validation whole with the first
   looks (checklist).
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
