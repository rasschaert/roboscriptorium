# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State on 2026-10-05 (end of day)

Milestones M0–M2 are done and M3 is in progress (decision models in the pipeline).

- `roboscriptorium build <book>`: PDF text layer → line roles (decision model)
  → reflow → IR → EPUB 3 with one file per chapter and a TOC. epubcheck clean
  as of M1. The chapter split hasn't been re-run through epubcheck: **do that first**.
- `roboscriptorium eval <book> [--pages 7-45 --chapters 1-9] [--no-models]`
  scores against the golden reference and appends to `work/<book>/eval-history.jsonl`.
- Golden book: `golden/sense-and-sensibility/` (Standard Ebooks with `[Editorial]`
  commits undone). Scans in `work/` (gitignored): `tauchnitz-1864` (same edition
  as the reference), `everyman-dent`, `everyman-1992`. Run `golden fetch` to
  restore them; the Everymans have to be placed by hand.
- Stella (`work/stella/`) has no golden text; `build` only.

### Scores, Tauchnitz chapters 1–9 (the quick loop)

| Step | CER | WER | Paragraph F1 | Headings |
| --- | --- | --- | --- | --- |
| Heuristics only | 7.30% | 5.18% | 0.592 | 0/9 |
| + `winnow:e4b` line roles, repetition feature, punctuation spacing | **4.23%** | **3.48%** | **0.697** | **9/9** |

Full book with winnow roles: FULL_BOOK_RESULT

### Model findings (details in the AGENTS.md model table and decision log)

- `laya:*`: unusable for layout questions.
- `winnow:e4b` (Ollaya): good at body vs other, but reads "2 SENSE AND
  SENSIBILITY" (page number first) as a chapter heading, and ignores numeric
  features. The code demotes "headings" that repeat on 5+ pages.
- **`clef-flash:9b` (Ollama, GPU, `/v1/systemone`) looks best**:
  - Line roles: 60/60 at P(body) ≥ 0.5, including the signature mark "Sense and 15"
    that winnow misses.
  - Page types: 19/23 (the same as `decider:2b-vision`), but with better-calibrated
    confidence. Stella p5 (an opening with no heading) comes out as body at only
    0.53, against decider's confident 0.95.
  - Timings so far (~0.8 s/line, ~3.9 s/page) were measured while another model
    run competed for the machine, so re-time it alone.
- Use `experiments/probe_line_roles.py` and `experiments/probe_page_types.py`
  to compare models. `clef-*` names route to Ollama automatically.

## Next steps, in order

1. Run epubcheck on a fresh Tauchnitz build (chapter split).
2. Try clef-flash for line roles: add a runtime/endpoint setting for the role
   model (e.g. `ROBO_ROLE_MODEL=clef-flash:9b` plus an Ollama endpoint),
   with the role threshold `KEEP_BODY_AT` at 0.5. Compare on chapters 1–9
   against the table above. Clef's state changes the cache key, so the first
   run is cold (~2–3 min).
3. If clef wins, make it the default and record that in AGENTS.md.
4. Try one call per page: clef takes up to 64 questions per request. Check its
   accuracy on a few pages first.
5. Page classification stage (vision): replace the hand-entered `body_pages`
   and `cover_page` in `book.toml`. Low-confidence pages get flagged for review.
6. Remaining known defects, from `eval`'s most frequent differences:
   - Paragraph precision is ~0.59, so there are still false paragraph starts.
     Look at where they come from.
   - Some headings lose a line: "IV." without "CHAPTER" (p21), and "CHAPTER" without "IX." (p40).
   - "Digitized by Google" fragments at page bottoms, if any survive.
7. After that: OCR candidates (a vision LLM via Ollama alongside the text layer),
   then the review UI (M4).

## Working with the user

- Run small probes first (10–60 items), state how long a big run will take
  before starting it, and run it in the background.
- Ask the user to install or pull things when the docs don't cover how. Don't
  guess APIs.
- Commits are signed through 1Password. If signing fails because 1Password is
  locked, stop and ask the user to unlock it.
