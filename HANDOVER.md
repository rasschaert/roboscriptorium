# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules,
docs/decisions.md the dated decisions, [docs/checklist.md](docs/checklist.md) the
whole plan with times; this file only covers the state of play. Replace it at the end
of each session.

## State at the end of 2026-10-09 (night)

On `main`, pushed. Lint and tests green (188 passed, 1 xfailed). No runs going;
llama-server is stopped.

### Done this session

- **Ollaya gone, Ollama only.** winnow-ollama:e4b is the second judge (`check_model`);
  code, docs and the diagram stripped of Ollaya. Trust data rebuilt for 14 books with it,
  arbiter retrained. Bench tuning against the ellipsis run: no change (1.00 → 1.02).
  Bench validation's first run is the baseline (after review 0.81).
- **Metro's veto** was its spaced ellipses squashed by reflow; each book's ellipsis
  style is read in its layer (`typography.py`). The read model's cache keeps readings
  per prompt; the book-wide style comes from the whole body.
- **OpenRouter requests have a 120 s deadline**: DeepInfra's Qwen went down (0% uptime
  on OpenRouter while its status page said operational) and keep-alive bytes kept a run
  hanging for half an hour. Stella's last lines were read by local Qwen.
- **imajev (2B/4B/9B)**, a Qwen3.5 vision decision model, runs through llama.cpp on
  Ollama's blobs with its trained readout (`clients/llama.py`,
  `experiments/llama-serve.sh`). Screened for every use:
  - vision judge in clef's place: 84% weighted against clef's 90%, no;
  - third judge beside clef and winnow (`ROBO_ALARM_MODEL`): bench no change (tuning
    1.02 → 1.01, validation 0.81 → 0.80), **off**;
  - page types / the body's ends: 227 of 252 against clef-flash's 231, same misses;
    `body_pages` stays in book.toml;
  - which way up a plate is: 10/10, decisively, but the caption rule already turns
    every captioned plate; the candidate for an uncaptioned or upside-down one.
- **Washed-out pages** (`faint.py`): ink contrast inside the layer's line boxes; 31
  pages in Afscheid, 11/22/63 and Grand Hotel Europa flagged whole. Bench tuning
  **better** (1.02 → 1.00 [−0.04, −0.01]), validation unchanged.
- **Qwen's third reading stays**: without it, bench tuning 1.00 → 1.33 and validation
  0.81 → 1.01, both worse. The ablation's data and models are in
  `work/probes/ocr-trust-no-qwen/` and `work/models/no-qwen/` (`ROBO_TRUST_DATA`,
  `ROBO_OCR_TRUST_MODEL`); the books' stage files were rebuilt with Qwen after it.
- **clef's answer variance**: judge set v1's 518 questions re-asked: 2 flips, both at
  confidence ≤ 0.1. Cached answers stand for fresh ones.

### Next (checklist)

1. Section 5: a book-quality feature for the arbiter; Vals alarm's lost full stops
   (only its own answers can teach it).
2. Section 3b: a faster line reader than Qwen, should one appear (Qwen is 70–75% of a
   cold run and earns it, see above).
3. The washed-out pages' text: a human types them or a rescan; the flag only says so.

### Working with the user (also in memory)

- **The user pulls every model download themselves.** Give the exact command and wait.
- Hosted Qwen only with an explicit go for that use and that night; the 2026-10-08/09
  permission does not carry over.
- At most three pipelines at once; be mindful of system use before starting tests.
- Overlap hosted Qwen with local non-Qwen work when hosted is approved.
- Every new model: can it replace one, and could adding it anywhere improve things.
- Long runs through `experiments/detached.sh` and `experiments/timed.sh`; the progress
  lines go to timed.sh's log, not the screen's `.out`.

### Waiting on the user

Nothing. The failed MoE models and the 2B/9B imajev copies were deleted (2026-10-09).
