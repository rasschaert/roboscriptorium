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
  Gutenberg #11355 an older edition in the old spelling). Dutch pairs that do match, with every IA file
  public, are in checklist 6f (Het Kindeken Jezus in Vlaanderen first).

### Next (checklist; docs/outlook.md ranks the areas with room)

1. **Put the IA files to work (checklist 6f), in this order:**
   - **Image probe** (`experiments/probe_ia_images.py`, ~15 min). The reader set
     `tryouts/reader-v1.json` already holds 50 Crime and 50 Dolittle lines (30 the layer
     reads wrong, 20 it reads right, per book), with crops and printed text in
     `work/tryout/`. Cut each of those lines again from the JP2: its PDF box in points
     times the JP2's pixel size over the PDF page size, at the zoom the OCR check uses
     (`ocrcheck.CROP_ZOOM`). Save a few PDF/JP2 crop pairs side by side and look that
     they line up before reading. Then read both crops with Qwen and glm-ocr, prompts as
     in `tryout.py run reader`, and count lines right per stratum.
     **What it tests:** the PDF isn't low-resolution; its letters are a 1-bit JBIG2 mask
     at the full 300 ppi (`pdfimages -list`). It lacks grey levels: every letter edge is
     thresholded, which is where a faint comma, an accent or a quote mark goes. Expect
     any gain in punctuation and accents, not whole words.
     **A win:** more hard lines right, no control line broken, for both readers. Then
     make the JP2 the image source for rendering on books that have one, rebuild Crime's
     and Dolittle's trust data (~1.5 h each, cold) and run `bench tuning`. Otherwise
     record the null result in docs/outlook.md's "Tried" list and stop here.
   - **ABBYY's letter confidence** (no models, ~1 h; doesn't depend on the probe):
     first test whether Crime's text layer is ABBYY's reading (the same words and boxes
     on one page). If it is, see whether a low confidence or a `suspicious` mark
     separates the real errors among the trust data's suspects.
   - `_scandata.xml` page types as page-classification labels (public on every IA
     golden book, borrow-only ones too), and a Dutch golden book from the 6f list: only
     once one of the two above is worth extending.
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
  make auto mode the default in `~/.claude/settings.json`. Nothing applied.
- **French**, the user's idea (2026-10-09), undecided. Proposed instead for now: go
  after the accent errors Dutch already has (De cipier's `knieén`, `hé` for `hè`, lost
  stress accents; Stella's `scenes`; Couperus's `zoû`): count the accent errors the
  bench leaves unasked, by book. Hilda and Extaze (checklist 6f) are a free accent
  stress set. French brings its own typography (« », a thin space before `; : ! ?`,
  dialogue dashes) that `quotes.py`, `typography.py` and the arbiter's training data
  would all need, and Gallica is mostly older print unlike the target books. If French
  comes, start with one French Wikisource book proofread page by page against its scan
  (same edition by construction), held out as a stress set like the test set, never
  trained on. Two extra worktrees can go when convenient: `../roboscriptorium-baseline` and
`../roboscriptorium-qwen2`.
