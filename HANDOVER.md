# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-18 ~14:45 by the session that took over the two
chains at 13:00.

## Running

The user is back by 10–11 on 2026-10-19. The queue, reordered at 00:30 so the edition
checks and the context judge's two runs land by then (each job a screen, logs in
`work/runs/`, every one with a watcher):

1. **`robo-carrere-builds`** (`carrere-builds.sh`): Andere levens cold since 21:30
   (~4 h), then Een Russische roman (~4.5 h, to ~06:00).
2. **`robo-robo-carrere-check`** (`carrere-check.sh`, out `robo-carrere-check.out`),
   hosted beside the local work: each book against its French and English as soon as
   its build's row is in docs/run-times.md (Andere levens budget $2, Een Russische roman
   $3.5; balance ~$6.5, a paywall ends OpenRouter use). Flags in
   `work/probes/carrere-editions/`; then every flag checked on a crop, and each book's
   open review questions against the flags, as for Stella.
3. **`robo-robo-cj-validation`** (`cj-validation.sh`, log `cj-validation-2.log`, ~1.5 h,
   to ~07:30): the context judge's validation rerun from branch `cj-cap`, against
   `validation-20261018T134936`.
4. **`robo-robo-cj-unsure`** (`cj-unsure.sh`, log `cj-unsure.log`, ~2–3 h, to ~10:00):
   the judge allowed to answer "the text can't tell", on the probe's 100 items paired
   against today's prompt (66 settled, 8 wrong).
5. **`robo-au-pair-look`** (`au-pair-look.sh`): Au pair's slice read cold (~1.5–2 h),
   then its single first-look score from `../roboscriptorium-aupair`.
6. **`robo-vergelding-read`**, **`robo-glazuur-read`**, **`robo-vanille-read`** last: the
   three waiting pairs' slices read cold (~2, ~2, ~1.5 h), no score.

**The context judge: the user's call** once 3 and 4 are in (reviewer time against wrong
words). Full tuning (decisions.md, 2026-10-18): NO CHANGE after review (0.28 → 0.28),
questions down in all 18 books, 29 wrong words made (17 unasked) against 110 fixed,
mostly the print's spelling normalised ("van binnen" → "vanbinnen").

**Stella: done.** Edition check (hosted, ~$1.8): one reading error, already a question;
recall 29 of 31 planted word errors, 0 of 6 accents. The user answered its last
questions and marked "de hete zomer" a misprint (2026-10-19); the build changes those
words alone, and a copy is in the user's Downloads. Stella's review server runs from
`../roboscriptorium-find` on port 8765 (stop it when done).

## Done today, afternoon (decisions.md, 2026-10-18)

- **Winnow-12B is the text judge** (`check_model`
  `tokens:hf.co/Piotr1215/Winnow-12B-GGUF:Q4_K_M`): tuning 0.30 → 0.28 after review,
  BETTER; validation 0.37 → 0.39, no change, no veto. Its trust data and arbiter are the
  defaults now (`work/probes/ocr-trust`, `work/models/ocr-trust*.pkl`); winnow-ollama:e4b's
  sit beside them as `ocr-trust-winnow-e4b` (renamed, nothing deleted). Its runs:
  tuning `work/bench/tuning-20261018T102252-ccfd33e-dirty.json`, validation
  `validation-20261018T110345-ccfd33e-dirty.json`: **the baselines from now on.**
- **The context judge, quick tier: BETTER**, 0.30 → 0.26 after review, questions 0.72 →
  0.60 a page, 24 wrong words fixed, none made (`work/runs/cj-bench.log`; it ran against
  stage (b) with winnow-ollama:e4b, so the full benches compare against the Winnow-12B
  runs).
- **Ollama 0.40.3 → 0.40.6** (Homebrew cask `ollama-app`): clef, clef-flash and
  Winnow-12B answer cached questions as before; caches stand. The pin is gone.
- `experiments/rebuild-trust.sh` builds the answers books too.

## Next, in order

1. **The first-look books into their sets**: in code (`bench.SETS`, `trustdata.SPECS`,
   232feb9); `robo-sets` above makes the new baselines. Record them in decisions.md,
   outlook.md and the checklist, and regenerate docs/golden-books.md.
2. **The context judge's full benches** (`robo-cj-full`): no worse on tuning and not
   vetoed on validation → `context_model` on by default (config.py), design.md, the
   diagram and the docs follow.

3. **Merge `au-pair`** once the chains are done: `golden/au-pair/manifest.toml` and
   `golden/de-vergelding/`, `golden/glazuur/` and `golden/vanille-en-andere-smaken/` manifests sit untracked in main (derive ran from there) and
   are identical to the branch's; remove them, rebase on main, then fast-forward. Record Au pair's first-look score in decisions.md, then its
   set (tuning if De laatste roker is to train the line roles; checklist).

## Waiting on the user

- Ex-minnaar's 6 new questions (rebuild first: the role trees were retrained since), then
  its read-through; then Stella's.
- A verdict batch (~20 min, after the sets move): the unasked errors that look like the
  references' (checklist, "Verdicts on the unasked errors").
- Ollama models nothing uses now: `winnow-ollama:e4b` and `hf.co/EldanRing/Winnow-E4B:Q8_0`
  (9 GB each, the same weights), `imajev:4b` and `hf.co/mindchain/imajev-4b-GGUF:Q8_0`,
  `qwen3.8:27b-q8_0` (29 GB). Not in the way.
- More golden pairs when convenient. **French**: undecided (checklist, Later).

## Worktrees

Unmerged, both from main, to merge once no run uses main's `src/`:
`../roboscriptorium-cjcap` (`cj-cap`: the context judge's cap, its "can't tell" probe;
the validation rerun and the probe run from it) and `../roboscriptorium-find`
(`review-find`: `review --find`, the misprint answered in one box; Stella's review
server runs from it).


`../roboscriptorium-aupair` (`au-pair`, to merge), `../roboscriptorium-w12b` (`w12b-default`, merged), `../roboscriptorium-lead`
(`token-judge`, merged), `../roboscriptorium-spans` (`verdict-words`),
`../roboscriptorium-breaks` (`scene-after-judge`), `../roboscriptorium-py315` (stale); a
prunable one in an old session's scratchpad. None holds unmerged work the plan needs.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen),
  each with a watcher. Warm benches take 2–5 minutes.
- Don't edit `src/` while a bench or build runs from `main`: work in a worktree and bench
  it with `uv run --project ../<worktree> roboscriptorium bench …` from this directory,
  so `work/` is reached by path, never linked.
- Nothing reads a first-look book (`bench.FIRST_LOOK`) until its single scoring.
- Stopping a run: `experiments/stop-run.sh <name>`; `ollama stop <model>` frees memory.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
