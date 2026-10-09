# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules,
docs/decisions.md the dated decisions, [docs/checklist.md](docs/checklist.md) the
whole plan with times; this file only covers the state of play. Replace it at the end
of each session.

## State at the end of 2026-10-09 (day)

On `main`, pushed. Lint and tests green (253 passed, 2 xfailed). No runs going.

### Done this session

- **A strict review of the whole codebase** (six reviewers, every finding checked
  before fixing; checklist 6e). Fixes in eight commits: hosted errors no longer cached
  as empty readings; settings refuse values they can't mean; `review` refuses the test
  set; answers keep the OCR check's fixes; captions answered on lines kept; dash spacing
  beside numbers; possessives inside quotations; the spaced-dot ellipsis told to Qwen;
  a reader's support over the whole span (a trust feature); lost opening quotes asked;
  chapter labels keep their numbers; tall fragments don't merge lines; the word list
  reads curly apostrophes; scoring on the right pages, without rewriting untouched
  paragraphs, with soft hyphens and „ folded; `detached.sh` refuses a running name.
- **Measured.** A baseline bench on the pre-review code plus only the measuring fixes
  (tuning 1.00, validation 0.81 after review), then trust data rebuilt (Qwen via
  hosted; 11/22/63 pp. 15–94 fully cold, its old stages in
  `work/11-22-63--ia-scan/stages.before-review-2026-10-09`), arbiter retrained:
  tuning **0.96** (better), validation **0.75** (no change by the test).
- **Headings.** The bench now prints headings and paragraph F1 per book and reports
  their changes beside its test. Fixed: 11/22/63 slice 5 → 23 of 24, Villa Toscane
  0 → 12 of 12, De cipier 3 → 4 of 4.
- **Probes, all null for the build:** five read prompts and six crops for Qwen (none
  reads better); Qwen's second look at 450 dpi as a trust feature (branch
  `qwen-second-look`, worktree `../roboscriptorium-qwen2`): strong signal, no bench gain.

### Next (checklist; docs/outlook.md ranks the areas with room)

1. Headings still lost: Afscheid's "1" read as "l"; Artemis's drawn chapter numbers;
   De eerlijke vinder's part numerals I–IV (and a spurious "de"); You're Never Weird
   5 of 16.
2. Section 5: a book-quality feature for the arbiter; Vals alarm's lost full stops.
3. The washed-out pages' text: a human types them or a rescan.

### Working with the user (also in memory)

- **Cheap experiments are encouraged**, unasked: prompts, crops, settings on the frozen
  sets; record null results too.
- Hosted Qwen was allowed for this session's runs and probes (2026-10-09); ask again
  next session.
- 1Password locks while the user is away: keep working, stage, commit when unlocked.
- The user pulls every model download themselves.
- Long runs through `experiments/detached.sh` and `experiments/timed.sh`.

### Waiting on the user

Nothing. Two extra worktrees can go when convenient: `../roboscriptorium-baseline`
(the pre-review baseline) and `../roboscriptorium-qwen2` (the experiment, committed on
its branch).
