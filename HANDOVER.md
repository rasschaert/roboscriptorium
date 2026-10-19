# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-19 ~21:15 by the session that queued the evening.

## Running

Started 2026-10-19 ~20:30, each with a watcher; `screen -ls` lists them:

1. **`au-pair-look`**: Au pair's cold build (pp. 7-99, ~3 h), then its single first-look
   scoring; the three reads (`vergelding-read`, `glazuur-read`, `vanille-read`) wait behind
   it, in that order (`work/runs/*.sh`; their wait lines had a doubled `robo-` prefix, fixed).

Done today: the judge's validation rerun (WORSE, after review 0.44 -> 0.46) and the
chains bench (NO CHANGE, 0 fixed 0 made): both in decisions.md.

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

1. **The context judge at sureness 0.6 passes both sets** (merged, off by default): questions
   -12% (tuning) and -16% (validation), after review level (0.277 / 0.441 against 0.281 /
   0.442), unasked errors +0.011 / +0.016 a page. Turning it on is the user's call (asked in
   the session): `ROBO_CONTEXT_MODEL=qwen3.8:27b-nvfp4 ROBO_CONTEXT_MIN=0.6`, defaults in
   `config.py` if yes. Cost: the judge's thinking time on a cold build (the full tuning run
   took ~4 h cold).
2. **Merged into main 2026-10-19** (tests 508 pass, pushed): `cj-cap`, `review-find`, `cj-min`,
   `hyphen-chains` (chains, diaeresis join, footnote star; its warm benches no change).
   **Still to merge**: `au-pair` last, when no read runs from main (its four manifests sit
   untracked in main and are identical to the branch's: remove them, merge, check with
   `git diff --stat`; the reads need them present while they run), then regenerate
   docs/golden-books.md and tick the checklist's diaeresis, footnote-star and chains steps
   (the checklist lives on `au-pair`). `small-caps` (`5fb536c`) waits for its cold bench.
3. **Au pair's first-look score** in decisions.md, then its set (checklist).
4. **`small-caps` short test** on the pages with the 18 known errors, then a cold bench with
   the trust data rebuilt (needs Ollama free: after Au pair).
5. The edition check's other silent gaps: lost lines read before asked; two-letter words
   beside a chain's break (probe: `experiments/probe_chain_breaks.py`, 2 of 11 wrong, too
   few to set a rule). Not yet counted: notes lost or made by the footnote star, on the
   golden books with notes (the chains bench shows it).

6. **Screen Nemotron-3.5-Bolt-74B-A9B** (the user is pulling
   `hf.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF`, 2026-10-19; never tried: only
   `nemotron3:33b` was, as an OCR reader, unfit). When Ollama is free of the Au pair build:
   `ollama show` for its capabilities (vision? thinking? a plain GGUF without the
   `decision` capability is asked through token probabilities, `tokens:<model>`,
   docs/models.md Setup); then the two questions in AGENTS.md: as a **judge** (replace or
   sit beside clef:27b / Winnow-12B / the qwen3.8 context judge; an A9B should be faster than
   a 27B thinker) with `experiments/tryout.py run judge <model>`, and as a **reader** if it
   sees images (`tryout.py run reader <model>`). Time a few calls first (small probes). Record
   the verdict in docs/models.md, Setup in the same place.

## Waiting on the user

- Andere levens' eight printer's errors for the errata, when they review it (listed in
  `work/probes/carrere-editions/andere-levens-checked.md`).
- **Een Russische roman is on hold entirely** (the user, 2026-10-19): they are getting a
  library copy and will photograph the three washed-out pages (46, 47, 259; not in the
  PDF's layers, decisions.md 2026-10-19). No builds, reviews or probes on it until the
  photos arrive. The chains, diaeresis and footnote-star fixes were found on it and are
  judged on its next build, which waits.
- Ex-minnaar's 6 new questions, then its read-through.
- A verdict batch (~20 min): the unasked errors that look like the references'
  (checklist, "Verdicts on the unasked errors").
- One Ollama model nothing in the pipeline uses: `hf.co/mindchain/imajev-4b-GGUF:Q8_0`
  (5.2 GB; the others on the old list are pruned, checked 2026-10-19). Whether imajev on
  `llama-server` reads this copy is not checked (docs/models.md, Setup): the user's call.

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
