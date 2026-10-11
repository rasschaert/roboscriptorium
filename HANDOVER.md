# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session.

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

1. **Done, on branch `review-display` (worktree `../roboscriptorium-review`), not yet on
   main: the review display fix.** Merge it (`git merge --ff-only review-display`) once
   the validation bench ends, so the bench's record names the code it ran; then remove
   the worktree. Checked on Ex-minnaar (54 of 390 questions show other places).
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
