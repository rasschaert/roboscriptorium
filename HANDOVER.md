# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules,
docs/decisions.md the dated decisions, [docs/checklist.md](docs/checklist.md) the
whole plan with times; this file only covers the state of play. Replace it at the end
of each session.

## State at the end of 2026-10-09 (evening)

On `main`, pushed. Lint and tests green (264 passed, 2 xfailed). No runs going.
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
- **Artemis's drawn chapter numbers** (in a circle, absent from the layer): `missing.py`
  reads regions up to five lines tall above a sunk page's text. Headings 0/3 → 3/3.
- Probe: Afscheid p. 20's text isn't in the PDF (the mask layer holds traced blobs), so
  no image tuning recovers it. Internet Archive's page images might, but they are
  private on that borrow-only item.
- Gemini's brief on combining models (from the user): mostly built already; two ideas
  kept in the checklist (Surya as a second spotter; block quotes, epigraphs, verse,
  ornaments).
- **Internet Archive's own files** for Crime and Dolittle (checklist 6f): `golden fetch`
  puts them in `work/<book>/ia/` from the manifest's `[scans.ia]`, sha256-checked. The
  page images the PDF was compressed from (`_jp2.zip`; Crime 300 ppi, 42 MB against a
  3 MB PDF; Dolittle 500 ppi), ABBYY's OCR with per-letter confidence (`_abbyy.gz`),
  page types and crop boxes (`_scandata.xml`), printed page numbers. A leaf with
  `addToAccessFormats` true is a PDF page, in order (138 and 208, checked). Pillow reads
  the JP2s. No stage uses them yet. The user is hunting for more, a Dutch one above all;
  Pallieter didn't pair (the public scan is the 30th printing in post-1946 spelling,
  Gutenberg #11355 an older edition in the old spelling).

### Next (checklist; docs/outlook.md ranks the areas with room)

1. **Put the IA files to work (checklist 6f), cheapest first:**
   - Readers on page images: ~50 of Crime's and Dolittle's suspect lines read from JP2
     crops instead of PDF crops (glm-ocr, Qwen), lines right against the reference, a
     probe in `experiments/`, ~15 min. A PDF box in points maps to the JP2 by its page's
     pixel size over the PDF page size; check the crops line up before reading.
     If it gains, make the images a source for `pdf.render` on books that have them,
     then `bench tuning` (both books are tuning books).
   - ABBYY's letter confidence for the arbiter: first check the PDF layer is ABBYY's
     reading, then whether a low confidence separates the trust data's real errors.
   - `_scandata.xml` page types as page-classification labels (public on every IA
     golden book, borrow-only ones too).
   Record null results in docs/outlook.md's "Tried" list.
2. Headings still lost: De eerlijke vinder's part numerals I–IV (0/4, a spurious "de",
   a validation book); You're Never Weird 4/16; Reis 10/11.
3. Bad pages by the readers' disagreement, a label-free alarm beside `faint.py`.
4. You're Never Weird p. 47: picture text read into the body.
5. Section 5: a book-quality feature for the arbiter; Vals alarm's lost full stops.

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

- `/doctor` (2026-10-09) proposed, unanswered: move AGENTS.md's Models table, golden-books
  notes and module tour to `docs/` (~8k est. tokens a session; AGENTS.md is 66.6k chars,
  past the large-file warning), switch off 10 unused claude.ai connectors in `/mcp`, and
  make auto mode the default in `~/.claude/settings.json`. Nothing applied. Two extra worktrees can go when convenient: `../roboscriptorium-baseline` and
`../roboscriptorium-qwen2`.
