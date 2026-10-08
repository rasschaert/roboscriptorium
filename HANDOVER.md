# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules,
docs/decisions.md the dated decisions, [docs/checklist.md](docs/checklist.md) the
whole plan with times; this file only covers the state of play. Replace it at the end
of each session.

## State at the end of 2026-10-08 (evening)

On `main`, pushed. Lint and tests green (173 passed, 1 xfailed). No runs going: every
`screen` session has ended. The user is restarting Claude Code and Ollama for an update.

### Done this session

- **Trust data complete** for every tuning and validation book (Qwen via hosted, the
  user's go for that queue): Afscheid, Reis, De eerlijke vinder, You're Never Weird,
  and Dolittle's and Metro's crop re-reads (Metro: glm-ocr CER 2.24% → 0.27% on the new
  crops). Stella's re-read was dropped (its labels are answers; few suspects move).
- **Arbiter retrained and saved** (`train_ocr_trust.py --save`, 3,841 suspects); the
  leave-one-out copies too. Builds with trust on work again.
- **Bench tuning**: fixed rule (baseline) against the retrained arbiter. Better over the
  set (after review 1.80 → 1.53, questions 3.1 → 1.6 a page) but **vetoed by Metro**
  (4.08 → 4.63; unasked word breaks 342 → 441). Results in `work/bench/tuning-20261008T2034*`
  and `…T2035*`.
- **Docs**: `docs/how-it-works.md` (the models by role: spotter, readers, sorter,
  judges, arbiter, reviewer), the diagram labelled with roles, AGENTS.md's model-roles
  table. Write prose against `~/code/ai-library/conventions/writing/claudisms.md`.
- **Tryouts** (`experiments/tryout.py`, `tryouts/`): frozen, versioned sets; results name
  their set version. Reader set v1 (550 lines). gemma4 lost to qwen3.8 on it (the
  screen's own sanity check). PP-DocLayoutV3 lost as the spotter, scored downstream.
- **Image-only PDFs**: tesseract's first reading (`pdf.first_reading`). Goede dochter
  with its layer removed (`work/image-only/`): CER 0.35% against the IA layer's 0.20%.
- **winnow on Ollama**: the user pulled `hf.co/EldanRing/Winnow-E4B:Q8_0`;
  `modelfiles/winnow-ollama-e4b.Modelfile` makes it a decision model
  (`winnow-ollama:e4b`, a documented workaround, AGENTS.md Environment). On three
  tuning books' cached suspects it beats Ollaya's build by far: right alone 285/208/265
  against 174 each; right where clef is wrong 78 of 100 against 45.

### Next, in order (checklist sections 3 and 6c)

1. After the Ollama update: check `winnow-ollama:e4b` still answers on `/v1/systemone`
   (`ollama show winnow-ollama:e4b` lists `decision`); recreate it from the Modelfile
   if not.
2. **Metro's word breaks** (no GPU): 342 unasked even under the fixed rule, so something
   systematic, perhaps spacing around its spaced dashes or ellipses. Then rerun the bench.
3. **winnow-ollama:e4b as `check_model`**: re-ask every book's suspects, rebuild the
   trust data, retrain, bench tuning and validation. If it holds, strip Ollaya from the
   code and docs (the user's step 4).
4. **The read model's cache bug**: it holds one prompt, so a slice with another style
   prompt evicts every reading (Dolittle 23–88 wiped its whole-book readings tonight).
   Keep readings per prompt and take the style from the whole body; test through
   `pipeline.run`.
5. Afscheid: washed-out pages (20, 32, 70) kept as body text should be flagged as
   garbled; p. 37 fails to align.
6. `bench validation`, then the call on Qwen and short lines.

### Working with the user (also in memory)

- **The user pulls every model download themselves** (slow line, wants the progress
  bar). Give the exact command and wait.
- Hosted Qwen only with an explicit go for that use. The bench of the winnow
  confirmation needs no new readings.
- At most three pipelines at once; nothing else big on the GPU beside them.
- Long runs through `experiments/detached.sh` (screen) and `experiments/timed.sh`;
  never edit a script a running screen is executing (zsh reads it as it goes).

### Waiting on the user

- Whether to delete the two failed MoE models (qwen3.6:35b-a3b-nvfp4, gemma4:26b-nvfp4,
  39 GB), and now `hf.co/EldanRing/Winnow-E4B:Q8_0`'s raw pull is needed only as the
  base of `winnow-ollama:e4b`.
