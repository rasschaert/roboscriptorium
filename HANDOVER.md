# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Top sections rewritten 2026-11-10 (~00:30 and ~07:45); the older sections from
2026-11-09 morning.

## Running

Nothing. **Batch five was stopped at ~06:50 on 2026-11-10** (the user leaving for work): its
cold bench (`night-20261110.sh` step 3, worktree `../robo-grow6`, branch `grow6` rebased on
main) had finished Vals alarm and was on The Thief-Taker's Apprentice; Metro, De tuin, Au pair
and De vergelding remain. Resume it, the next night the user frees the machine, from its
caches with steps 3 and 4 of `work/runs/night-20261110.sh` (the benches of steps 1 and 2 are
done, NO CHANGE): against `work/bench/tuning-20261110T032819-e3e0a01-dirty.json`.

**Branch `small-caps` was rebased on main on 2026-11-10 (local only, by the user's choice not
to force-push):** worktree `../roboscriptorium-caps`, eaf169f, every fix of the night plus
its three commits and a repair (the lower-case doubt passed through both halves of the
split OCR check), 688 tests passing. GitHub still has the old branch: work from the local
one, and don't pull or reset it from origin.

**The quote check as a reader of the OCR check** (`quotes.duel_readings`,
`ROBO_QUOTE_READER=1`, off; checklist "One path for every doubt", decisions.md 2026-11-10).
Short test done on copies of three books (`experiments/probe_quote_reader.py`, results in
`work/probes/quote-reader/<book>.json`): The Loudest Sound and Nothing's quote lines 81 → 12,
Nervous System's 6 → 3, the judges right on every kept place checked by eye. Two guesses
were narrowed after that run (no opened reading on a paragraph that opens on a mark, none
for a mark opening a word), so next, in order: (1) the short test again, warm, ~15 min:

    experiments/detached.sh quote-reader experiments/timed.sh "probe: the quote check as a reader, off and on, after the narrowing (warm)" 780 work/runs/quote-reader.log uv run python experiments/probe_quote_reader.py nervous-system loudest-sound-and-nothing de-tuin-van-de-avondnevel--ia-scan:11-254

(delete the three copies' folders first only if the books were rebuilt since; the copies
hold the judges' answers); (2) De tuin's changed paragraphs against its reference; (3) a
warm `bench tuning` on main as the baseline, one with `ROBO_QUOTE_READER=1` against it,
then validation: the user's go needed for the benches. Next kinds for the same path, not
started: garbled lines, headings, specks, washed-out pages.

**Two sessions, one machine** (the user, 2026-11-10: this session, on main, schedules model
time; the session `smallcaps` works in `../roboscriptorium-caps`). It was shut down for the
day with its branch at bd1b511 or later, local only, and three short runs approved but not
started: Nervous System whole on a copy with `ROBO_LOWER_CAPITALS` on (~20 min,
`experiments/probe_caps_nervous_short.py`), the short test through the arbiter on the tuning
books (~20 min), the wide-crop probe (~10 min). Its finding from caches: of Nervous System's
30 small-capital acronyms the build has 26 right; "tv" wrong unasked on PDF 43 and 59, "vcr"
on PDF 47, PDF 158 asked; the UK scan has no "RCMP". Both changes want a cold bench on the
same night and baseline: decide the order with the user.

**The user is reviewing Nervous System** (started 2026-11-10 ~06:40, answers in
`work/nervous-system/review/regions.jsonl`). Their first card, PDF 13, was "a mess": fixed
in 47ecbef (washed-out cards read only inked lines; no repeating readings). A review server
started before that commit shows the old cards: restart it (answers are kept). Then Going
into a Dark House and The Loudest Sound and Nothing (checklist, the user's books).

**Done tonight** (decisions.md 2026-11-09/10 has the numbers): Nervous System built and
checked (epubcheck clean; 70 questions after the fixes, sampled; waits on the user's
review); the judges asked one at a time over the book (judging ~10× faster: 585 model
reloads an hour had eaten it); the text layer's cache now hits; the arbiter scores a book
in one call; `init` keeps a page under the running head past the end and starts after the
title page; a table on a text page (a library label) is asked; no lost-initial questions
where a book opens sections in capitals. Nulls: the page-kind model told its neighbours'
kinds; washed-out pages asked their kind (it called faint print blank); the second scan as
a witness (two errors in 756 places on Nervous System).

**Next for these books:** when each build ends, check its ends, story-title headings and
library label (The Loudest Sound and Nothing has Blackpool's on PDF 7), sample its questions
(`experiments/sample_questions.py`), and list them for the user's review. Not yet built:
glm-ocr and tesseract beside Qwen (~10–14 min a cold book, the code review's item); a
cold bench must stay one book at a time (`ROBO_BENCH_WORKERS=1`), or the judges of
parallel books evict each other.

**No heavy work during the user's working day** (the user, 2026-11-09: "the memory
pressure is too great. can we hold off on the heavy work until i get done with my
dayjob?"): builds, benches, probes with models and batch five wait until they say
they're done. Light work only meanwhile (docs, analysis of results on disk, code checked
by unit tests).

**How to work with the user** (2026-11-09, memory `no-foreground-waits`): never wait on a
run in the foreground. Start it detached with its watcher, say so, and end the turn. Keep
turns short and report each result as it comes: "going incommunicative for an hour is not
polite."

## Next, in order, once the user frees the machine

1. **Small capitals, nailed** (the user, 2026-11-09: "the new detected silent errors
   SWAT-team and USB-stick worry me. we need to nail this"; checklist step "Small
   capitals, nailed"). Branch `small-caps`, worktree `../roboscriptorium-caps`, pushed:
   - the capitals version with numbers left alone (562c9b0): tuning NO CHANGE, 4 fixed
     (SWAT-team, USB-stick), 2 made, both asked;
   - doubts on lower-case pieces no reading disputes, behind `ROBO_LOWER_CAPITALS`, off
     (ec6443f): the vision judges, two of three agreeing, call 39 of 57 small capitals and
     0 of 150 lower-case pieces (decisions.md, `experiments/probe_caps_lower.py`).

   Steps:
   a. Resume the short test through the arbiter (stopped at 11 of 19 books; resumes from
      its caches; ~20 min), with a watcher:

          experiments/detached.sh caps-lower-short experiments/timed.sh "probe: lower-case small capitals, short test off and on" 120 work/runs/caps-lower-short.log uv run --project ../roboscriptorium-caps python experiments/probe_caps_lower_short.py

      Compare off and on with the scratch comparison (rewrite it: places keyed by book,
      page, got, want; fixed, made, silent↔asked).
   b. The wide crop for the lone O, U, V all three judges miss ("o-benen", "u-bocht",
      "v-hals"): `uv run python experiments/probe_caps_lower.py ask 150` (copy
      `work/probes/caps-lower/answers.jsonl` aside first; tight answers are cached, ~10 min),
      then `report`.
   c. `bench tuning` with `ROBO_LOWER_CAPITALS=1` on the branch against
      `work/bench/tuning-20261109T072931-39ba40e-dirty.json` (cold for ~1,100 new suspects,
      about an hour), then validation; merge if neither says worse. If the arbiter keeps or
      asks what the judges call capitals, the doubts reach it only after batch five's trust
      data holds them and the arbiter is retrained.
2. **Batch five** (the user said go, 2026-11-09): `work/runs/grow6.patch`, Vals alarm, Metro,
   De tuin, Thief-Taker, Au pair and De vergelding scored whole, ~915 pages, ~14 h cold.
   After the small-capitals merge, overnight. Then retest pass 4 (branch `text-seat`,
   worktree `../robo-text`, arbiter `work/models/ocr-trust-p4*.pkl`, data
   `work/probes/ocr-trust-p4/`) and the vocabulary feature on the grown trust data.
3. Hints for the new judges (which kinds of OCR error to look for, tried only with clef),
   then d3 and autotrust-jev as the line-end hyphen judge; then the whole-page readers
   retested as line readers.

## Production

Since 2026-11-09 (decisions.md): autotrust-jev 35B and d3 9B beside clef, asking below
0.9; the arbiter before kept as `work/models/ocr-trust-p0*.pkl` and
`work/probes/ocr-trust-p0/`. Merged that night: the hyphen rules, pages too poor to read,
heading capitals by the book's run (tuning BETTER, 72 words fixed, none made). Not taken:
pass 4 (validation's unasked places 170 → 178), Mistral-Small 3.2 as a text judge.

## Done 2026-11-06 evening

- **Qwen3.8-Flash-Next UD-Q2_K_XL rejected** as reader and witness (models.md, decisions.md):
  on the quiet set's lines every reader gets wrong, 0 of 5 plain, 4 of 23 with the crop
  doubled (two real), 2 of 12 thinking; it swaps real words; ~15 s a line from the SSD.
- **Taken: a Dutch line-end break between clashing vowels keeps its hyphen**
  (`hyphens.vowel_clash`): tuning 3 fixed, validation 1, none made.
- **Taken, every one benched warm, validation no change on each, no heading of the
  user's four books changed** (decisions.md has the numbers): tuning heading errors
  32 → 22, unasked wrong words 839 → 755:
  - a misread chapter number where the run has a gap read again by glm-ocr
    (`chapters.run_gaps`, `stages/run-gaps.json`): Monterosso 22 of 22;
  - a display line under a heading on a page without running text is part of it
    (`title_lines`, "part-page"): Het geluid van bananen's "Stof", "Jullie", "Wij";
  - a number heading off the run and off the middle is a speck (`chapters.off_run`):
    Doodskleed's "7" and "3";
  - punctuation after a chapter number left out of its value: Thief-Taker's "20 ;";
  - a text block the layer lost whole cut into lines by its ink and read
    (`missing.blocks`): Dolittle's PDF 97, 105 wrong words fixed (81 unasked);
  - the scorer folds subscript digits and the fraction slash (Artemis's "CO₂").
- **Not taken**: a run-on heading measured against the book's full line
  (`work/runs/book-full.patch`): no longer needed once the lost block is read.
- **Lesson**: never edit `src/` while a bench runs; its validation half loads the edit.
- **`experiments/heading_misses.py`** lists each book's missing and extra headings.
- **`doctor` runs again** (4dba7ae, broken since 2026-10-24, now tested).
- **Tests never reach the machine's Ollama** (5afd2b5): `ROBO_OLLAMA_URL` on a closed port in
  every test; one pipeline test had passed only because qwen answered it.

## Done 2026-11-05 evening to 11-06 morning (decisions.md has every number)

- **Taken, all benched, none made an error of its own**:
  - a full stop added mid-line before an undisputed lower-case word, and an "ij" read as
    u, ui, y, ii or i, no versions (`ocrcheck.line_end_stop`, `ij_misread`; 17f5504):
    tuning 5 fixed, validation 5;
  - lines of dots ("‘...’", a silent reply) read from inked slots between layer lines,
    kept as body past the line-role trees, with the quote marks their ink shows
    (`missing.slots`, `slot_lines`, `quoted`), and a quote mark misread from a speck no
    version (`ocrcheck.quote_misread`; 367085c): tuning 8 fixed, validation 5;
  - whole lines of text the layer lost, read from the same slots where as long as a line
    of the page (`missing._fills`; 82c1b39): tuning 103 wrong words fixed (12 unasked,
    most were lost-line questions the reviewer had to type), validation 9.
- **Lessons**: dropping one of two sibling readings strengthens the other in the arbiter's
  eyes (a rule must drop a misread in all its spellings); the line-role trees take any
  line with no letter for a speck; a slot narrowed to its ink needs its length judged
  against a whole line too.
- **Nulls**: the build's 18 accent errors are accent-shaped specks (as 2026-10-26 found);
  a single quote for a double isn't told by the book's quote style; a comma added after a
  word is wrong 13 of 14, no rule.
- **Set review** (87c7dfe): Dolittle past the layer-CER line since scored whole, its errors
  the pipeline's, kept. Primer errors chart regenerated (0f1a9aa).

## Next, for the agent

1. The open steps of docs/checklist.md in its order. The unasked errors left on tuning
   (585 places): stress accents 105 (half the reference's), compound hyphens 86 (line-end
   breaks, 57 a hyphen lost), letters 76, punctuation 59. Extra text's 969 words are
   mostly Afscheid's washed-out pages, asked by design.
2. Idle machine time grows the slices (checklist).

## Waiting on the user

- Hoe wij verdwijnen's **spot-check**: `open work/probes/spot-check/hoe-wij-verdwijnen/index.html`
  (PDF 41, 77, 87, 144, 292; count wrong words, breaks and italics per page); then its
  read-through. The counts are of the build before the "op"/"een" italic fix.
- Pieter Daens' **review**: 292 questions, `uv run roboscriptorium review work/pieter-daens`.
- A read book's rebuild that changes text goes to the user by eye, every difference
  (the user, 2026-11-04): `experiments/rebuild_diff.py <book> <old.epub> [notes.json]`.

## Done 2026-11-03 evening and 11-04 morning (decisions.md has every number)

- **Not taken**: a lone word with a diagonal letter or acute accent held to 12° (tuning
  italic errors 2,445 → 2,588): a capital Z or W leans the whole word ~26°, past any cut.
- **Built: the learned italic decision** (`italics.Trees`): trained on the golden pairs'
  aligned words. Lesson: counts of measured words let the trees memorise single pages of
  other books; without them, and with each book weighing alike, the trees generalise.
- **Built: chapter labels** (`chapters.title_lines`): Het schaduwhuis' narrator names.

## Done 2026-11-01 and 02 (decisions.md has every number)

- **Two new books of the user's, timed end to end** (README, docs/run-times.md): Hoe wij
  verdwijnen 4 h 14 min (300 pages), Pieter Daens 12 h 22 min (804).
- **What reading them showed, now the pipeline's own** (AGENTS.md rule, "What an agent
  finds by eye"): chapter numbers by their run (`chapters.py`); short pages, pages before
  the first heading and listing pages asked the page-kind question (mottos, dedications,
  tables of contents; blank pages left out only when washed out); title-page subtitles;
  a motto's wrapped lines joined; italics uniform in a motto; glm-ocr's talk on specks no
  line; `init` walking inward past the edge (Daens' ads); a structure check and a
  comparison with the last build printed by every `build`; heading errors in the bench's
  verdict; the review's obvious questions out.
- Benches: the 11-01 batch, heading errors 102 → 82 on tuning, 50 → 45 validation; the
  11-02 batch on the grown slices, after review 0.34 → 0.33, heading errors 104 → 72,
  missing text 0.073 → 0.048, validation no change; the dash fix, dash errors to zero.
- Also taken: quotes closed at a paragraph's end where the reading adds only the mark
  (39/39 on tuning); possessives after a sibilant ("Maurice’ moeder") no quote; the
  bench names a book whose unasked errors double (`bench.doubled`); bench in parallel.

## Done 2026-10-25 and 26 (decisions.md has every number)

- **Slices grown twice** (the user: idle machine time may go to it): seven slices on the 25th
  (~585 pages), eleven more on the 26th (~860 pages, 13 h cold). On the pages both runs
  share: no change. Tuning went from ~1,700 to ~3,100 pages, and the after-review interval
  should narrow from ±0.010 to about ±0.008.
- **Batch two paused** at the user's request, minutes into Goede dochter: thirteen slices to
  about 220–270 pages, ~925 pages, ~14 h. Its ranges are in commit 3e6177c, taken back out of
  `bench.SETS` so the baseline and the sets agree. The checklist step "Grow the tuning slices
  further" says how to resume (reapply, run `work/runs/grow3.sh`).
- **Not taken**: the arbiter retrained on the grown slices (more unasked errors; the second time
  more rows haven't helped, so the arbiter needs a new signal, not more data); page roles on
  the grown slices, and withheld on picture pages (no change; the harm is in the line-role
  trees trained with page features).
- **Au pair's 13 small capitals** settled by the user's verdicts (0.286 → 0.277 on the slices
  of the 25th). Lesson: check scan crops before asking; bring a verdict only when it needs a
  human's eye, with crops beside a confident reading.
- **Lessons**: compare against a run made after the latest verdicts; a slice's growth can move
  its old pages a little (the book's own spellings and abbreviations come from all its pages);
  the cold rate is about 0.9 min a page.

## Done 2026-10-24 (decisions.md has every number)

- **Taken**:
  - a full stop for a line's last comma before a lower-case line is no version
    (`ocrcheck.stop_for_comma`: 6 unasked words fixed, none made);
  - readings that accent one letter of a doubled a, o or u, or carry `~ ^ |`, are no version
    (`half_accent`, `garbled`: no change on the bench, never right in the trust data);
  - any short line in justified text ends a paragraph (`reflow._short_end`: salutations and
    datelines before a letter's flush body; breaks 0.057 → 0.045 on tuning,
    0.202 → 0.196 on validation, words unchanged);
  - an image-only scan's dash style measured on the image (`scanstyle.guess` through the first
    reading's words; Vanille's typography 0.56 → 0.00 a page).
- **Not taken**:
  - a sureness threshold per kind of question;
  - Qwen's token probabilities, image-gain included, as a silent-error signal;
  - Qwen as the line-end hyphen judge;
  - Kraken as a witness;
  - Qwen's page roles for the trees, unmarked (more wrong words) and with the lines inside
    pictures marked (half the harm, still no change; code kept, off);
  - the comma rule mid-line (1 fixed, 1 made: an author's stop before a lower-case
    quotation);
  - Winnow subtracted (worse, 0.282 → 0.316: it stays);
  - Qwen for `init`'s page kinds (no better than clef-flash, more ends cut).
- **Screened**: LightOnOCR-3 1B and 4B as line readers, unfit, weaker than olmOCR-2 (the 1B's
  checkpoint needs its weights renamed, a bare crop needs a white margin;
  `experiments/lighton_read.py`).
- **New instruments**:
  - the quiet set (`experiments/quiet_set.py`, 423 frozen lines where the layer, glm-ocr
    and qwen agree): they are wrong together on only 23 lines of the tuning slices, so a
    new line witness can add a handful;
  - `experiments/witness_score.py` for the reader set.
- **Measured**:
  - the trust data's `choice` is the fixed rule's, not the arbiter's: join to a build's
    `ocr-check.json` for the arbiter's;
  - books set flush put no extra lead between paragraphs;
  - `bench quick` ranks a change that acts everywhere as tuning does, with a fifth of the
    power, and never sees front matter or picture pages;
  - batching identical questions would save 7% of cards;
  - an accent told from an i-dot by shape alone: AUC 0.66–0.76, too weak (the per-book
    alphabet parked);
  - ABBYY's letter confidence: private on every lent scan, dropped.
- **Sets reviewed**: no pair past the thresholds, nothing retired.
- **Stella**: rebuilt with all of the above, text and paragraphs unchanged.

## Next, in order

1. **The arbiter's own silent errors: probed 2026-10-26, nothing taken.** They are what its
   0.8 sureness line costs (9–11 questions for each one caught past it), plus De vergelding's
   page budget (three questions a page caught 8 unasked words there, tuning no change). The
   accent half goes both ways (specks read as accents in Doodskleed, Glazuur, Monterosso;
   emphasis dropped in Goede dochter, Het schaduwhuis, Au pair), and the ink's shape over the
   letter adds nothing to the trees. Left: De vergelding's own arbiter (it has the most
   unsure suspects, never trained on); a speck classifier with more labelled pages.
2. **Compound hyphens at line ends** (25 unasked with no suspect): no cue found in qwen, clef
   or the obvious signals; only a learner with a new feature can reach them.
3. **Emphasis accents and the dotless ı** (the quiet set's largest classes after small
   capitals): they need each mark tied to its letter, which the layer's letter boxes can't give.
   A reader that gives letter positions is the way in.
4. **Verse and lists** (Dolittle's poem, Thief-Taker's song, Glazuur's numbered list): most of
   the paragraph errors left on tuning; in scope later, per AGENTS.md.
5. **Qwen faster on the same output**: measured 2026-10-24, a line read is half prefill and a
   quarter decode, so speculative decoding buys little; fewer image reads (whole pages) is the lever.
6. **Page roles need the line-role trees retrained** with picture pages and mottos labelled
   (Dolittle's picture-page lines go wrong under the trees trained with page features, whatever
   qwen says); only then bench page roles again.
7. **Grow the slices again** when the machine is idle (checklist, "Grow the tuning slices
   further"): batch two is ready in commit 3e6177c.

## When a new vision model appears

Gate for a candidate that fits 64 GB, in order:
1. the quiet set: can it read any of the 23 lines every reader gets wrong? A few minutes;
   a slow candidate stops after its first 25 lines unless they show a gain;
2. `experiments/screen_reader.sh <label> <model dir or ollama name>` (the reader set, then
   the vote simulation);
3. `probe_accent_readers.py`;
4. only then a trust-data rebuild and a bench.

Ask before a download over 1 GB. A model outside Ollama gets its own environment in
`~/models/roboscriptorium/` (as `lighton-env`).

## Waiting on the user

- **A flush-set book for tuning** (golden-notes.md, gaps): a scan and the publisher's EPUB of
  a book printed without paragraph indents, not A.W. Bruna's. Every break error left in the
  flush books is a start after a full line, which only a learned model finds, and without a
  flush tuning book no such change can be chosen.
- **Specks** (parked): the speck classifier needs labelled pages from more scans.
- **Disk**: `work/models/mlx-env` (809 MB) and `~/models/roboscriptorium/lighton-env` (767 MB, the
  LightOnOCR runtime; its weights were deleted 2026-10-24, the user agreeing) stay until the user
  says they can go. `work/models/ocr-trust-grown*.pkl` (the arbiter retrained on the
  25th, not taken) can go too.
- Andere levens: seven candidate misprints saved as printed
  (`work/probes/carrere-editions/andere-levens-checked.md`); the user says which, if any, are
  misprints.

## Standing notes

- **Een Russische roman is on hold** (the user, 2026-10-19) until three washed-out pages
  (46, 47, 259) are photographed from a library copy: no builds, reviews or probes on it.
- **No full read-throughs of any book soon** (the user, 2026-10-20) beyond Stella's.
- `experiments/screen_reader.sh <label>` treats the label as an Ollama model; for a readings
  file label run `tryout.py`'s reading step and `vote_sim.py <stem>` directly.
- A Monitor watcher expires after 30 minutes whatever its timeout: re-arm it on a long run.

## Worktrees

`../roboscriptorium-caps` holds the unmerged `small-caps` branch (in progress, see Next); `../robo-text` the `text-seat` branch (pass 4, kept); `-py315` two
untracked scratch files.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen), each
  with a watcher. Warm benches take about 11 minutes (tuning) and 5 (validation); `bench
  quick` 6.
- A bench of a change: run it, then compare against the baseline by path:
  `bench tuning --against work/bench/<run>.json`, `bench-diff <old.json> <new.json>` place by
  place, and `bench.verdict(old, new)` in Python for the paired interval. A change of
  settings only (an environment variable) needs no worktree; a code change's "before" is the
  baseline run.
- Check every writer of what you change: the scored text is built from `corrections.apply`,
  the question view from `ocrcheck.apply`.
- Stopping a run: `experiments/stop-run.sh <name>`; a job waiting on another's screen starts
  the moment that screen goes, so stop the waiters first.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
