# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules,
docs/decisions.md the dated decisions, [docs/checklist.md](docs/checklist.md) the
whole plan with times; this file only covers the state of play. Replace it at the end
of each session.

## State at the end of 2026-10-09 (evening)

On `main`, pushed. Lint and tests green (260 passed, 2 xfailed). No runs going.
Bench now: tuning 0.48, validation 0.79 wrong words a page after review.

### Done this session

- **Afscheid's misread chapter numbers** ("l", "e,", "UH"): kept as headings by their
  place and size (`roles.numeral-slot`), fixed by the OCR check. Headings 8/11 → 11/11.
- **Scoring:** an error over a page break counts on the page holding most of it.
  Afscheid's 5.03 after review was its washed-out p. 38 counted on p. 37; it is 0.24.
- **Washed-out pages are left out of the OCR check**: its readers invented ~170 lines of
  fluent dialogue on Afscheid's four. The question budget counts only pages it reads.
- **Suspects the arbiter is ≥ 0.8 sure of aren't asked** (`ROBO_OCR_ASK_BELOW`, the
  user's choice): questions about halved at the same wrong words after review. **A
  figure to revisit** with any new arbiter, judge or reader (checklist).
- Probe: Afscheid p. 20's text isn't in the PDF (the mask layer holds traced blobs), so
  no image tuning recovers it. Internet Archive's original captures might.
- Gemini's brief on combining models (from the user): mostly built already; two ideas
  kept in the checklist (Surya as a second spotter; block quotes, epigraphs, verse,
  ornaments).

### Next (checklist; docs/outlook.md ranks the areas with room)

1. Headings still lost: Artemis's drawn chapter numbers (0/3); De eerlijke vinder's part
   numerals I–IV (0/4, a spurious "de"); You're Never Weird 4/16.
2. Bad pages by the readers' disagreement, a label-free alarm beside `faint.py`.
3. You're Never Weird p. 47: picture text read into the body.
4. Section 5: a book-quality feature for the arbiter; Vals alarm's lost full stops.

### Working with the user (also in memory)

- Cheap experiments are encouraged, unasked; record null results too.
- Hosted Qwen: ask again next session (nothing hosted was used this session).
- 1Password locked: stop and ask for it to be unlocked (global instructions).
- The user pulls every model download themselves.
- Long runs through `experiments/detached.sh` and `experiments/timed.sh` (its arguments:
  label, pages, log file, command). `bench --against <record>` compares with a chosen run.
- Questions the bench's test can't weigh (reviewer time against wrong words) are the
  user's call: ask in one short sentence.

### Waiting on the user

Nothing. Two extra worktrees can go when convenient: `../roboscriptorium-baseline` and
`../roboscriptorium-qwen2`.
