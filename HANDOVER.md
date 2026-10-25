# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Updated 2026-10-24 ~19:00 by the session that screened LightOnOCR-3
and took the day's three OCR-check rules and the paragraph fix (decisions.md, 2026-10-24).

## Running

Nothing runs.

The baselines are `work/bench/tuning-20261025T074616` (the seven grown slices, 2026-10-25:
after review 0.286) and `work/bench/validation-20261024T202747` (0.502, 0.196): today's defaults.
The arbiter retrained on the grown slices was no better (decisions.md, 2026-10-25), so the one
in use stays; `work/models/ocr-trust-grown*.pkl` can go. The image-only ellipsis measurement was vetoed by
validation and reverted (decisions.md).

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

1. **The arbiter's own silent errors** (152 of the 236 unasked errors this morning sat where a
   suspect was raised and the arbiter chose wrong). The biggest groups:
   - a right layer changed: stress accents added or dropped;
   - a shared misreading kept where qwen, both judges and the word list say otherwise
     ("vijt" for "vijf", "cen" for "een" in De vergelding, whose glm-ocr and tesseract share
     the layer's error).

   De vergelding, Au pair and Glazuur aren't trained on (training on them on 2026-10-20 made
   the others worse). A feature, not a retrain, is the next try.
2. **Compound hyphens at line ends** (25 unasked with no suspect): no cue found in qwen, clef
   or the obvious signals; only a learner with a new feature can reach them.
3. **Emphasis accents and the dotless ı** (the quiet set's largest classes after small
   capitals): they need each mark tied to its letter, which the layer's letter boxes can't give.
   A reader that gives letter positions is the way in.
4. **Verse and lists** (Dolittle's poem, Thief-Taker's song, Glazuur's numbered list): most of
   the paragraph errors left on tuning; in scope later, per AGENTS.md.
5. **Qwen faster on the same output**: measured 2026-10-24, a line read is half prefill and a
   quarter decode, so speculative decoding buys little; fewer image reads (whole pages) is the lever.

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

- **Stella's read-through**: `work/stella/epubs/stella-2026-10-19-0014.epub`. Today's changes
  leave its text and paragraphs as they are.
- **A flush-set book for tuning** (golden-notes.md, gaps): a scan and the publisher's EPUB of
  a book printed without paragraph indents, not A.W. Bruna's. Every break error left in the
  flush books is a start after a full line, which only a learned model finds, and without a
  flush tuning book no such change can be chosen.
- **Au pair's small capitals** (13 unasked errors that measure its reference): verdicts, about
  two minutes:
  `uv run roboscriptorium review work/au-pair--ia-scan --pages 7-99 --chapters 1-24 --only work/probes/unasked/au-pair-smallcaps-20261024.json`
- **Specks** (parked): the speck classifier needs labelled pages from more scans.
- **Disk**: `work/models/mlx-env` (809 MB) and `~/models/roboscriptorium/lighton-env` (767 MB, the
  LightOnOCR runtime; its weights were deleted 2026-10-24, the user agreeing) stay until the user
  says they can go.
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
