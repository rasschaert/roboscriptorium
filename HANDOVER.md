# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Updated 2026-10-26 evening by the session that probed the arbiter's silent errors (no models;
decisions.md, 2026-10-26).

## Running

Nothing runs. The user needs the machine for other work (2026-10-26): don't start model runs
until they say it's free again.

The baselines are `work/bench/tuning-20261026T075608` (eighteen grown slices, ~3,100 pages:
after review 0.362, every book weighing the same; breaks 0.049) and
`work/bench/validation-20261024T202747` (0.502, 0.196): today's defaults. `bench.SETS` matches
that tuning run, so warm benches take about 15 minutes.

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

`../roboscriptorium-caps` holds the unmerged `small-caps` branch (null result); `-py315` two
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
