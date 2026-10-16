# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. Written 2026-10-16 ~17:40, during the session of 2026-10-16.

## Running

- `robo-keep-spelling` (screen; `work/runs/keep-spelling.log`, ~20 min): Qwen on the
  frozen reader set told to keep the author's spelling (`experiments/probe_keep_spelling.py`).
  If it breaks nothing, the sentence goes into `quotes.style_prompt` and every book's Qwen
  readings are redone cold, overnight, then the benches.

**Ollama is on 0.40.3; keep it there** with the app's automatic updates off: 0.40.4
refuses winnow (AGENTS.md, Environment).

**Baselines now:** the latest `work/bench/tuning-*` and `validation-*` runs (0.28 and
0.48 after review).

## Ex-minnaar's review: stopped by the user at question 119

The user, 2026-10-16: "this is a waste of my time and a violation of the rule we
established". Their 123 answers are kept. Since then (decisions.md, 2026-10-16):

- The book's answers join its arbiter's substitution table (`trust.with_answers`) and
  settle by reader (`trust.by_book`: tesseract read 12 of 12 stress accents right).
  Open questions 102 → 76; ~25 accents the build dropped silently are now in.
- Review page: misprints to `work/<book>/errata.toml` (`m`), sources under each reading,
  look-alike marks named, the base reading marked too, a lost line's box and draft read
  clear of the line above, Cyrillic letters in readings transliterated.
- What's left (76): 50 OCR doubts (Qwen standardising Flemish is several; the
  keep-spelling run is for those), 27 quote alarms (the print leaves many speeches
  unclosed; the user keeps most), 7 others.

**Don't send the user back to the review** until the keep-spelling decision is made
and its build is in (AGENTS.md, "The user's review comes last"). Then restart the
server (`uv run roboscriptorium review work/ex-minnaar`).

## Next, in order

1. The keep-spelling result; if it holds, the cold Qwen re-read overnight and benches.
2. Ex-minnaar's remaining questions sampled again; the user resumes.
3. Checklist: the book teaches itself, second half (one question per pattern).
4. Stella's read-through by the user (checklist).

**Remind the user of the daily backup of `work/`** at session start and before long
runs: it now also holds `work/ex-minnaar/errata.toml`.

## Waiting on the user

- Remove the Ollama models nothing uses: `gemma4:latest`, `deepseek-ocr:3b`,
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`,
  `ornith-1.5:9b`, `ornith-1.5:35b`, `qwen3.8:27b-mxfp8` (not in the way, the user said).
- More golden pairs when convenient.
- **French**: undecided (checklist, Later).

## What this session taught (the rules are in AGENTS.md)

- **A reviewer's answers must teach the book at once.** Ex-minnaar asked "we → wc" 13
  times and stress accents a dozen; the per-book table and reader buckets now learn them.
- **Check a probe's matching before reporting its count**: "7 quote questions settled"
  were questions a probe failed to match to their paragraph.
- **Test the click, not only the key**: the misprint button crashed with no reading
  chosen (`null >= 0` is true in JavaScript); the key test had chosen one first.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen).
  Warm benches take 2–5 minutes.
- Don't edit `src/` while a bench or build runs; park a change as a patch.
- Nothing reads the test set (Het geluid van bananen) until its single scoring.
- Stopping a run: `experiments/stop-run.sh <name>`; `ollama stop <model>` frees memory.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
