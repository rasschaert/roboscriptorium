# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State on 2026-10-07 (end of day)

Everything is merged into `main` and pushed. M0–M2 done, M3 (OCR and
decisions) well along, M4 (review) working, and the first figures in the EPUB.
Direction, now in AGENTS.md: **build the machine, not the book**: compounded
models that fail differently, combined by measured reliability, with new models
benchmarked and plugged in.

### What the pipeline does now

- **Line roles:** clef-flash:9b plus rules in code; the shared layout analysis
  lives in `page.py`, and `LineRole.rule` names the rule that overrode the model.
- **OCR check** (`ocrcheck.py`, scanned books only): two second readings per body
  line (glm-ocr on the line's crop for letters, tesseract on the page for
  dashes). Where either differs from the text layer, clef:27b judges the crop and
  winnow:e4b the sentence. Applied when they agree and clef ≥ 0.3, or, where the
  versions differ only in punctuation, dashes or spacing, when clef:27b alone is
  ≥ 0.5. Quote styles count as one version. Everything else goes to review.
- **Figures** (`figures.py`): the layout model's pictures go into the EPUB at
  300 dpi, trimmed where a caption overlaps, sideways plates turned upright,
  captions from the review or read off a sideways plate. Dolittle: 48 pictures,
  epubcheck clean.
- **Review page:** each region asks "what is this?" (radio buttons, the
  pipeline's call preselected) and, for OCR doubts, "which reading matches the
  scan?" (each reading with the difference marked and the models that picked it).
  One Save button (`↵`). Tested in a browser just before stopping; not yet used
  by the user in this form.

### Scores (latest; the rescore was still running at the end of the day)

| Book | CER | WER | Paragraph P / R | Headings | OCR suspects for review |
| --- | --- | --- | --- | --- | --- |
| Dolittle | 1.89% (was 2.16%) | 1.92% | 0.818 / 0.953 | 21/21 (+1) | 100 of 657 |
| Crime | 0.53% (was 0.63%) | 0.32% | 0.966 / 0.986 | 8/8 (+1) | **453 of 928** |
| Lady into Fox (held out), Boze tongen, De aanslag, Sense | running | | | | |

The rescore crashed on Lady into Fox: under load tesseract once returned its word
table without a header (not reproducible one page at a time; the parser now
reads such a page again). Dolittle's and Crime's scores above come from
`work/probes/rescore-2026-10-07.log`; Lady into Fox, Boze tongen, De aanslag and
Sense were restarted into `work/probes/rescore-2026-10-07b.log`; read the
summary lines at its end. The review server for Dolittle was stopped.

## Next steps, in order

1. **Read the rescore log** and record the scores in AGENTS.md's decision log.
2. **Why Crime sends 453 suspects to review.** Its text layer is good (CER 0.5%),
   so most must be differences that aren't errors (spacing around curly quotes?
   glm-ocr normalising something?). Look at `work/the-nature-of-a-crime--doubleday-1924/stages/ocr-check.json`.
3. **Dolittle's WER rose a hair** (1.83% → 1.92%) with the new decision rule:
   find the wrong automatic fixes.
4. **Italics probe** (`experiments/probe_italic_pages.py`): page-level "are there
   italic words?" with truth from Gutenberg's markup (Dolittle has 62 italic
   phrases on 34 pages). Needs Ollama free; it timed out while clef:27b was busy.
5. **A `bench` command**: every job's labelled set scored for any model, so new
   models are measured and plugged in quickly.
6. **Learned trust**: per-model, per-kind-of-error reliability (Dawid–Skene,
   calibration) from the golden books and the user's review answers, replacing
   the hand-set thresholds. The user's observation: winnow caught a speck read as
   "." after a hyphen ("ani-."), so the text model *does* know some punctuation.
7. **Metadata stage** with `nuextract3:q6_k` (front pages → `book.toml`, the
   human confirms).
8. Smaller: p23's decorated initial is answered "E" but shows an O (the user
   meant to fix it); 16 of Dolittle's 62 italic phrases couldn't be placed on a
   page.

## Working with the user

- Run small probes first, say how long a big run takes, run it in the
  background, and keep its output under `work/probes/` (never a scratchpad).
- Long jobs share Ollama: clef:27b answers one request at a time, so two jobs
  using it run at half speed each. Run them one after another.
- The user picks no models: choose from measurements and record why. Ask before
  adding a runtime or anything they must install or pull.
- Commits are signed through 1Password; if signing fails, ask for it to be
  unlocked.
- Their connection is slow: avoid large downloads. Golden sources are in
  `work/.cache/` (checked against PROVENANCE.md).
- They try the review page while work goes on and report what's awkward; each
  report so far became a general fix.
