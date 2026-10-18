# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-18 ~14:45 by the session that took over the two
chains at 13:00.

## Running

**`robo-sets` done** (~13:45–15:50): role trees and arbiter retrained with the two new
tuning books; **the new baselines**: tuning `work/bench/tuning-20261018T121943-b1d19e5-dirty.json`
(0.28 → 0.27 against Winnow-12B's, no change; Het schaduwhuis 0.17, Het geluid van bananen
0.57 against 0.47 at its first look, to look into), validation
`validation-20261018T134936-b1d19e5-dirty.json` (0.39 → 0.38, no change; Verminkt 0.47,
De geruchten 0.87, 2 of 21 headings).

**`robo-cj-full` done**: tuning with the context judge NO CHANGE after review (0.28 →
0.28), questions down in all 18 books, 29 wrong words made (17 unasked) against 110 fixed
(decisions.md). Validation died on Vuurspel (a thinking answer past the client's 10 min);
fixed on branch `cj-cap` (`../roboscriptorium-cjcap`: answers capped at 10,000 tokens, a
capped or timed-out answer leaves the question asked), not yet merged: merge once no run
uses main's `src/`. **`robo-robo-cj-validation`** (`work/runs/cj-validation.sh`, log
`work/runs/cj-validation-2.log`) reruns validation from that worktree after the local
chains below. Then **the user's call** (reviewer time against wrong words): the judge on
by default saves ~20% of questions at equal errors after review, but makes errors
unasked; to try first, its "can't tell" answer: **`robo-robo-cj-unsure`**
(`work/runs/cj-unsure.sh`, log `work/runs/cj-unsure.log`, ~2–3 h) after the validation
rerun, the probe's 100 items paired against today's prompt (66 settled, 8 wrong).

**The queue, in order** (the user, 2026-10-18: the edition checks matter more than the
first looks): **`robo-carrere-builds`**, running since 21:30
(`work/runs/carrere-builds.sh`: Andere levens ~4 h, Een Russische roman ~4.5 h, cold), then
the four first-look jobs below, each waiting on all of those.

**`robo-au-pair-look`**, behind both (`work/runs/au-pair-look.sh`): Au pair's slice
(pp. 7–99) read cold (~1.5–2 h), then its single first-look score, run from the
`../roboscriptorium-aupair` worktree (branch `au-pair`, which lists it in
`bench.SETS["first-look"]` and adds the `hidden_classes` reference key). Log
`work/runs/au-pair-look.log`.

**`robo-vergelding-read`**, last (`work/runs/vergelding-read.sh`): De vergelding's slice
(pp. 9–107) read cold (~2 h), no score: it waits in `bench.WAITING` (branch `au-pair`).

**`robo-glazuur-read`**, last (`work/runs/glazuur-read.sh`): Glazuur's slice (pp. 11–101)
read cold (~2 h), no score, likewise waiting.

**`robo-vanille-read`**, last (`work/runs/vanille-read.sh`): Vanille en andere smaken's
slice (pp. 9–79) read cold (~1.5 h), no score: the first image-only scan, so tesseract
gives the first reading.

**Stella's edition check: done** (hosted, ~$1.8; decisions.md, 2026-10-18): all 244
paragraphs against the German, Danish and English; one reading error ("trofik", p. 53), already a review question, so no silent one,
one likely misprint for the user's errata ("de hete zomer", p. 7), 47 false flags. Its
recall on 37 planted errors: 29 of 31 word errors, 0 of 6 accents. Balance left ~$6.5.
**`robo-robo-carrere-check`** (`work/runs/carrere-check.sh`, output
`work/runs/robo-carrere-check.out`), behind `robo-carrere-builds`: Andere levens against
the French and English (budget $2), then Een Russische roman ($3.5), hosted; flags in
`work/probes/carrere-editions/`. Then every flag checked on a crop, and each book's open
review questions against the flags, as for Stella.

**Stella's translation-check pilot, local** (stopped: hosted answered it;
`experiments/probe_translation_check.py`, output `work/probes/stella-editions/pilot.out`
and `pilot.jsonl`): 20 paragraphs of today's Stella build read by qwen3.8 beside the
German original and the Danish translation, ~1–3 min each beside the context judge. Next:
check every flag on a crop of the scan, rerun the same 20 with the English translation
added and with each edition asked apart, then the whole book overnight in the best
setting (checklist, "Other editions as an error finder"). Already found: "trofik" for
"trof ik" (scan p. 53), unasked, still in today's build. The editions are in
`work/stella/editions/` (German Ullstein, Danish Gyldendal 2025, English New Directions
2025) and the Carrère books' French and English in `work/<book>/editions/`.

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

- Stella: whether "de hete zomer" (p. 7) goes in the errata as a misprint for "zomers"; its questions are answered (2026-10-19).
- Ex-minnaar's 6 new questions (rebuild first: the role trees were retrained since), then
  its read-through; then Stella's.
- A verdict batch (~20 min, after the sets move): the unasked errors that look like the
  references' (checklist, "Verdicts on the unasked errors").
- Ollama models nothing uses now: `winnow-ollama:e4b` and `hf.co/EldanRing/Winnow-E4B:Q8_0`
  (9 GB each, the same weights), `imajev:4b` and `hf.co/mindchain/imajev-4b-GGUF:Q8_0`,
  `qwen3.8:27b-q8_0` (29 GB). Not in the way.
- More golden pairs when convenient. **French**: undecided (checklist, Later).

## Worktrees

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
