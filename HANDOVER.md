# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-19 ~09:40 by the session that ran the night.

## Running

Each job a screen, logs in `work/runs/`, every one with a watcher. The qwen3.8 runner
(MLX) answers one request at a time, so two jobs on it take turns.

1. **`robo-robo-cj-validation`** (`cj-validation.sh`, log `cj-validation-2.log`): the
   context judge's validation rerun from branch `cj-cap`, against
   `validation-20261018T134936`; on De geruchten, the last of nine, since ~09:45 (cold judge
   answers).
2. **`robo-robo-cj-unsure`** (`cj-unsure.sh`, log `cj-unsure.log`), beside it: the judge
   allowed to answer "the text can't tell", the probe's 100 items paired against today's
   prompt; ~11:00. After 29: today's prompt settles 20 (6 wrong), the new one 17 (6
   wrong), its one "can't tell" a right one: not the fix so far.
3. **`robo-chains-bench`** (`chains-bench.sh`, logs `chains-tuning.log`,
   `chains-validation.log`, warm, minutes), after 1: branch `hyphen-chains`
   (`../roboscriptorium-chains`): a chain's interior pairs count as the book's spellings,
   so a break inside it keeps its hyphen (Een Russische roman's chant now whole; tests
   with counterexamples). Merge if no worse.
4. **`robo-au-pair-look`**, after 1 and 2: Au pair's slice read cold (~1.5–2 h), then its
   single first-look score from `../roboscriptorium-aupair`.
5. **`robo-vergelding-read`**, **`robo-glazuur-read`**, **`robo-vanille-read`** last: the
   three waiting pairs' slices read cold (~2, ~2, ~1.5 h), no score.

## Done overnight (decisions.md, 2026-10-18 and 19)

- **The edition check, on every book with other editions** (hosted qwen3.8-27b on
  DeepInfra, the user's permission; ~$7.3 in all, $0.89 left: done with OpenRouter for
  now). Flags checked on crops in `work/probes/stella-editions/`,
  `work/probes/carrere-editions/*-checked.md`.
  - **Stella**: no silent error; its two open questions answered and its one misprint
    ("zomers") marked by the user; rebuilt, the diff those words alone. Recall on 37
    planted errors: 29 of 31 word errors, 0 of 6 accents.
  - **Andere levens**: one silent error ("LCI" in small capitals), four open questions,
    eight printer's errors (waiting on the user's errata).
  - **Een Russische roman**: silent: hyphenated chains broken at their own hyphen, a
    diaeresis lost at a break ("democratie- en"), a footnote whose "*" the layer reads
    as "“" spliced into the text; asked: "ooo" for 000, two lines the layer lost
    mid-block, three washed-out pages the scan can't give.
  - Each silent gap is a checklist step with its evidence (branch `au-pair`'s checklist).
- **The context judge, full tuning**: NO CHANGE after review (0.28 → 0.28), questions
  down in all 18 books, 29 wrong words made (17 unasked) against 110 fixed, mostly the
  print's spelling normalised ("van binnen" → "vanbinnen"). Validation crashed on a
  runaway thought (fixed on `cj-cap`: answers capped, a capped one asked) and reruns.
- **`review --find "<words>"`** (branch `review-find`): a line the machine didn't ask
  about as a question; the misprint answer typed in one box, the print shown above it
  (the user: "why offer me two text boxes").
- The queue reordered for the user's 10:00 return: the judge's two runs before Au pair.

## Next, in order

1. **The context judge: the user's call** once 1 and 2 are in (reviewer time against
   wrong words): about 20% fewer questions at equal errors after review, but some made
   unasked.
2. **Merge the branches** once no run uses their worktrees, each after `git diff --stat`
   against main: `cj-cap`, `review-find`, `hyphen-chains` (if its bench is no worse),
   then `au-pair` (its four manifests sit untracked in main and are identical: remove
   them, rebase, fast-forward). Regenerate docs/golden-books.md.
3. **Au pair's first-look score** in decisions.md, then its set (checklist).
4. The edition check's silent gaps, in the checklist's order: small capitals as a
   version for the judges; two-letter words beside a chain's break (the riskier half of
   the chain fix); the misread footnote mark; lost lines read before asked; the
   diaeresis at a break.

## Waiting on the user

- Andere levens' eight printer's errors for the errata, when they review it (listed in
  `work/probes/carrere-editions/andere-levens-checked.md`).
- Een Russische roman's three washed-out pages (46, 47, 259): not in the PDF's layers at
  all (decisions.md, 2026-10-19); the Internet Archive's reader serves the full-resolution
  pages to a borrower, else a paper copy.
- Ex-minnaar's 6 new questions, then its read-through.
- A verdict batch (~20 min): the unasked errors that look like the references'
  (checklist, "Verdicts on the unasked errors").
- Ollama models nothing uses now: `winnow-ollama:e4b`, `hf.co/EldanRing/Winnow-E4B:Q8_0`,
  `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`, `qwen3.8:27b-q8_0`. Not in the way.

## Worktrees

To merge: `../roboscriptorium-cjcap` (`cj-cap`), `../roboscriptorium-find`
(`review-find`; Stella's review server runs from it on port 8765, stop it when done),
`../roboscriptorium-chains` (`hyphen-chains`), `../roboscriptorium-aupair` (`au-pair`).
Merged or stale: `../roboscriptorium-w12b`, `-lead`, `-spans`, `-breaks`, `-py315`.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen),
  each with a watcher. Warm benches take 2–5 minutes.
- Don't edit `src/` while a bench or build runs from `main`: work in a worktree and bench
  it with `uv run --project ../<worktree> roboscriptorium bench …` from this directory,
  so `work/` is reached by path, never linked.
- Nothing reads a first-look book (`bench.FIRST_LOOK`) until its single scoring.
- Stopping a run: `experiments/stop-run.sh <name>`; a job waiting on another's screen
  starts the moment that screen goes, so stop the waiters first.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
