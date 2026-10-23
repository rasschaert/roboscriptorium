# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Updated 2026-10-23 ~17:00 by the session that trimmed the sets (decisions.md, 2026-10-23).

## Running

- `robo-page-roles-short` (queued behind it, ~20 min): the role probe's short answer (heading
  and furniture line numbers only) on the same 208 pages; `probe_page_roles.py score --short`.
  The long answer scored 3 wrong lines against the pipeline's 22 (decisions.md, 2026-10-23).

**Night of 2026-10-21/22, in one paragraph.** The read model at 450 dpi is the best vote witness found so far on the reader set (+12 lines, none broken; 300 dpi adds 4, 600 dpi 9, so it is resolution), and glm-ocr alone gains 54 lines at 450 dpi. But swapping the pipeline's readers to 450 dpi (`ROBO_READER_DPI=450`, cold `bench quick`, earlier arbiter) made 18 wrong words and fixed 11: not taken. As an extra witness it was closed on 2026-10-23 without a run: right alone on 0 of 57 lines no reader flags (`probe_dpi450_alone.py`). `init` now drafts title, author and translator (title 26, author 25 of 27 right). clef:27b is no better than clef-flash for the page-kind ends (21/21 against 22/21). All in decisions.md, 2026-10-22.

**Models.** No model weights live outside Ollama any more (the user, 2026-10-21: `~/code` is backed up hourly, so weights never go under it, and every download over 1 GB is asked first). Every model the user asked for was screened (decisions.md, 2026-10-20 and 21) and deleted: PaddleOCR-VL, Qwen2.5-VL-72B, H2O-Lightning-Omni-4B, fonles-decision-1, Fusion and, last, olmOCR-2-7B (it helped a plain vote, 801 → 809, but not the arbiter, nor whole pages). `work/models/mlx-env` (809 MB, the MLX runtime for `mlx_read_set.py` and `mlx_read_crops.py`) stays for a future MLX candidate; `experiments/h2o_triage.py` and `fonles_triage.py` need their environments built again. The gate for a new vision model is below.

**Arbiter.** Unchanged: the earlier one, restored (tuning 0.29, run `tuning-20261021` of the sanity bench). The line-end features (span ends its line, next line's case) were tried and not taken: tuning 0.29 → 0.30, glued or split words worse.

## Done 2026-10-23 (decisions.md)

- Reader set v3 (v2 less the retired 11/22/63; `tryout.py prune reader`), the probes pointed at it.
- The 450 dpi witness closed without a run: never right alone on lines no reader flags.
- Ollama is 0.40.9 (an unrecorded update): the decision models answer as cached
  (`probe_judge_drift.py`, new, for the judges).
- Set review: Afscheid's breaks unscored (`breaks_unlike_print`), The Nature of a Crime out of
  tuning and quick but still arbiter training (its removal from training was worse:
  unasked fixed 7, made 16). New tuning baseline `tuning-20261023T133740`. The arbiter
  files before the test retrain are in `work/models/ocr-trust-backup-20261023/` (restored;
  the folder can go).
- Flint skipped on its card (text-only coding model). Laya fine-tuned for line roles on MLX
  (Unsloth's `FastDecisionModel` trains Laya and Clef on this Mac, ~15 min) on rows whose labels
  can't be wrong (`laya_roles_data.py`): alone 75 wrong of 19,422 clean validation lines
  against the pipeline's 30; not pursued (`~/models/roboscriptorium/laya-roles/full`).
- Paragraph starts by qwen from the page image: fixes 53 of 78 on error pages but sets 0.11–0.15
  a page wrong on clean ones (the reflow 0.06): not taken.
- Verminkt scored on 7–100 (`scoring.cut_to_pages`: a slice without chapters cut to its
  paragraphs). `build` and `review` start from a PDF alone, `init` drafting book.toml.

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

## When a new vision model appears

The line reader is the lever, and models change fast (the user, 2026-10-21: Qwen3.8-27B is two months old and beats the January 2025 state of the art by a wide margin). Gate for a candidate that fits 64 GB, in order: `experiments/screen_reader.sh <label> <model dir or ollama name>` (its score on the reader set, then the vote simulation), `probe_accent_readers.py` (emphasis accents, the dotless ı: the open class), then, if it earns it, a trust-data rebuild with it as a reader and a bench. Ask before a download over 1 GB.

## Waiting on the user

- **Specks** (parked, the user has no time for it now): the speck classifier ranks well on three labelled Thief-Taker pages (`probe_speck_blobs.py`, `--no-position`) but needs labelled pages from other scans before it is trusted; sightings are in `work/probes/specks/sightings.jsonl`. A "speck" kind in the review UI was not built.
- **Push**: 19 commits ahead of `origin/main`; a push needs 1Password unlocked.
- `work/models/mlx-env` (809 MB, MLX readers) stays until the user says it can go.

## Loose ends found at the end of the 2026-10-21/22 session

- **The trims are done**: Na die nacht held back rather than retired (the user, 2026-10-23),
  Verminkt sliced to 7–100.
- **Worktrees**: the twelve merged ones were removed with their branches (2026-10-23, the user
  approving). `-py315` holds two untracked scratch files; `-caps` the unmerged null result.
- **Run-in-screen traps hit tonight**: `experiments/screen_reader.sh <label>` treats the label as an Ollama model (it fails for a readings-file label such as `…+dpi450`: run `tryout.py`'s reading step yourself, then `vote_sim.py <stem>` directly); a watcher's `Monitor` expires after 30 minutes however long its timeout, so a long run needs it re-armed.
- **Per-book settings and extra witnesses** is a new checklist item ("Assumptions to test"): start with the agreement probe.
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

`../roboscriptorium-caps` holds the unmerged `small-caps` branch (null result); `-py315` two
untracked scratch files. The rest were removed on 2026-10-23.

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
