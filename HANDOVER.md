# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Rewritten 2026-10-21 ~03:00 by the session that screened the downloaded models.

## Running

Nothing (`screen -ls` is empty). 22 commits on `main`, not pushed (the user was asleep; a push over 1Password's SSH key could have stalled the session).

**Models.** Weights live in `~/.cache/huggingface/models/` (never under `~/code`, which is backed up hourly), environments in `~/.cache/huggingface/envs/` (`h2o-env`); `work/models/mlx-env` stays. Every download the user asked for is screened (decisions.md, 2026-10-20 and 21): PaddleOCR-VL unfit (deleted); olmOCR-2-7B helps a plain vote (801 → 809) but not the arbiter (9 → 12 silent errors) nor whole pages; Qwen2.5-VL-72B unfit (vote 801 → 793, 42 GB still on disk: delete when the user says); H2O-Lightning-Omni-4B and fonles-decision-1 as detectors of the unasked errors, AUC 0.62 and 0.57: not taken; Fusion imported as `fusion-27b:q5km` (text only, no vision through Ollama), not screened (the judge set `work/tryout/judge-v1` is missing: a new set is a version bump and a warm build). Ask before any download over 1 GB.

**Arbiter.** Unchanged: the earlier one, restored (tuning 0.29, run `tuning-20261021` of the sanity bench). The line-end features (span ends its line, next line's case) were tried and not taken: tuning 0.29 → 0.30, glued or split words worse.

## Done today (decisions.md, 2026-10-20)

- **Sets**: De vergelding and Glazuur are tuning (no trust data yet, `bench.NO_TRUST_DATA`),
  Vanille en andere smaken is validation; `bench first-look` is empty. The line-role trees
  were retrained on the larger tuning set (`train_sorter.py --save`); every tuning bench from
  now on is against those trees, so older bench records aren't paired with new ones.
- **The OCR check keeps a line end's break hyphen where the joined word is known**
  (`ocrcheck.fixed_text`, both writers): tuning fixed 20 wrong words (18 unasked), made 0, all
  in De vergelding; validation 0 and 0. 13 such fixes exist in all the books' caches.
- **Null results, recorded**: the `small-caps` all-capitals version (0 of 11 known errors
  fixed; branch `small-caps` stays unmerged), lost text by ink in a gap or uncovered ink
  (the "lost lines" are mostly runs of dots and one-word drops; only a dot-led line is findable
  by ink, left of a line's start), a higher-resolution crop for line-end commas.
- **Looked at**: Vanille's headings 1 of 15 (non-fiction sub-heads no tuning book teaches; a
  non-fiction pair is in the gaps to hunt, golden-notes.md); De vergelding's unasked errors.
- Andere levens reviewed through `--find` (one erratum), Ex-minnaar's questions answered
  and rebuilt, the unused imajev model removed from Ollama.

## Next, in order

1. **Emphasis accents and rare glyphs** (the largest unasked class together with them): half of the 42 stress-accent errors are real (an acute accent on an i for emphasis: "zíjn", "níét"), the rest the reference's slips (decisions.md, 2026-10-21); no prompt or reader tried keeps them at 300 DPI (a 450 DPI crop keeps 2 of 6). The dotless ı of "Sıla" (five times in Het geluid van bananen) is the same kind. The next step is a reader that sees the accent: a word crop at high resolution, only where a word is a likely target; learned, not a list.
2. **A verdict batch for the reference's slips: not worth the user's time.** The 46 unasked stress-accent places of the latest benches (`work/probes/unasked/candidates-stress-accent-20261021.json`, commands from `experiments/review_batch_commands.py`) span 20 books; on the reference's half our text already matches the print, so a verdict only tidies the measure and changes no book. Ask only if a cleaner measure is wanted.
3. **A line-end compound the join closed** (the mild class): done for what the book itself shows (hyphen spellings now count the whole body: compound hyphens 0.023 → 0.020 on tuning); 24 of 27 have no other evidence in the book (the word occurs once), for the word list or a judge. The hyphen judge asks only English books; Dutch closes 355 of 361.
4. **Lost lines** (about half are held by the whole-page readers but not as clean inserts; the rest are decorated openings no whole-page reader reads): an opening-line reader (`missing.py` on line starts and gaps).
5. **A non-fiction pair with numbered chapters and sub-heads** for tuning (the user supplies candidates); De geruchten's headings; the checklist's remaining steps.

## Waiting on the user

- Andere levens: the other seven candidate misprints
  (`work/probes/carrere-editions/andere-levens-checked.md`) were saved as printed with no
  erratum; the user says which, if any, are misprints. Pages 135 and 153 span a line
  break, so their entries are written by hand.
- **Een Russische roman is on hold entirely** (the user, 2026-10-19): a library copy and
  photographs of three washed-out pages (46, 47, 259). No builds, reviews or probes on it
  until they arrive; the chains, diaeresis and footnote-star fixes are judged on its next build.
- **No full read-throughs of any book soon** (the user, 2026-10-20): don't schedule them.
- Stella's review server (port 8765) may still run from `../roboscriptorium-find`: stop it.

## Worktrees

Every branch but `small-caps` is merged: `../roboscriptorium-cjcap`, `-cjmin`, `-find`, `-chains`,
`-aupair`, `-w12b`, `-lead`, `-spans`, `-breaks`, `-py315`, `-mis`, `-only`, `-ux` can go. `-caps`
holds the unmerged `small-caps` branch (null result).

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen),
  each with a watcher. Warm benches take 2–5 minutes (tuning), ~10 (validation).
- A bench of a change: `git worktree add ../<name> HEAD --detach` for the "before", then
  `uv run --project ../<name> roboscriptorium bench tuning` from this directory (so `work/` is
  reached by path, never linked) and the same from main for the "after";
  `bench-diff <old.json> <new.json>` compares them place by place. `--against` takes a path.
- Check every writer of what you change: the scored text is built from `corrections.apply`,
  the question view from `ocrcheck.apply`; a fix to one alone showed no change at all.
- Stopping a run: `experiments/stop-run.sh <name>`; a job waiting on another's screen
  starts the moment that screen goes, so stop the waiters first.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
