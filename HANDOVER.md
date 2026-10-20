# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Rewritten 2026-10-21 ~00:20 by the session that screened the downloaded models.

## Running

`experiments/detached.sh night-chain` (screen `robo-night-chain`, log `work/runs/night-chain.log`, started 2026-10-21 ~00:15): H2O-Lightning-Omni-4B on the unasked-error set (`work/probes/unasked-set`, built by the screen `unasked-set`), scored by `experiments/triage_score.py h2o work/probes/unasked-set`; then, once `qwen72-download` ends, `experiments/screen_reader.sh` on Qwen2.5-VL-72B-4bit (reader score and vote simulation). Everything else is committed on `main`, not pushed.

**Models.** Weights live in `~/.cache/huggingface/models/` (never under `~/code`, which is backed up hourly), environments in `~/.cache/huggingface/envs/` (`h2o-env`); `work/models/mlx-env` stays. Screened: PaddleOCR-VL (unfit, deleted), olmOCR-2-7B (best alone second to qwen, helps a plain vote 801 → 809, but 9 → 12 silent errors as the arbiter's fourth witness and no better on whole pages: not taken), Fusion (imported as `fusion-27b:q5km`, text only, not screened: the judge set `work/tryout/judge-v1` is missing, a new set means a version bump and a warm build), H2O (a line detector: AUC 0.86 on the reader set; on the unasked errors, see decisions.md), fonles-decision-1 (downloaded, custom server not read yet).

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

1. **The arbiter features** (the three new books' trust data is built but NOT used: training on them did not help, decisions.md 2026-10-20; the earlier arbiter is restored and the tuning reference run is `tuning-20261020T182636-f38e636-dirty`): they go in (checklist: a line-end comma turned into a stop
   when the next line opens in lower case, 7 certain errors; and the line-end "span ends
   its line" feature). Say the estimate from docs/run-times.md before starting.
2. **A line-end compound the join closed** (60 unasked errors over tuning and validation, the
   mild class: the user ranks glued words and wrong letters first). The hyphen judge asks only
   English books; Dutch closes 355 of 361. A look at the 18 verdict-batch cases against the
   judge's answers is still model-free work.
3. **The edition check's silent gaps**: lost words read before asked (the reader on a line's
   left end and 1.2-pitch gaps, extending `missing.py`: Vanille and Verminkt hold the dot lines;
   the five in Vanille's slice don't earn a stage yet); two-letter words beside a chain's break
   (`experiments/probe_chain_breaks.py`, 2 of 11 wrong); notes lost or made by the footnote
   star, to count on the golden books with notes.
4. **A non-fiction pair with numbered chapters and sub-heads** for tuning (the user supplies
   candidates; golden-notes.md, gaps to hunt).
5. De geruchten's headings, the checklist's remaining steps (its top section is out of date).

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
