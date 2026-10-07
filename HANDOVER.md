# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State on 2026-10-07 (afternoon)

Everything is committed on `main` and pushed. New today:

- **OCR check crops fixed.** A line's crop is its words' boxes together (Crime's
  text layer gives lines boxes twice the print's height, so glm-ocr read the
  neighbouring line too), reaching one em past the line's ends (line-end em
  dashes the layer misses were cut to hyphens). Joining two words needs both
  judges; `¬` equals `-`. Crime: 453 suspects for review → 54; Dolittle WER
  1.92% → 1.81%; Lady into Fox unchanged.
- **Second held-out book, Grand Hotel Europa** (Dutch IA scan, the user's EPUB
  and PDF; copyrighted, all in `work/`). Cold start, chapters 1–3: CER 1.92%
  (text layer alone 2.51%), headings 3/16. Never inspect its errors; score it in
  slices (`--pages 15-44 --chapters 1-16` is chapters 1–3; scan page = printed
  page + 4).
- **Italics** (`italics.py`): each word's stroke slant on the scan, no model.
  References keep `<i>` (`Chapter.italic`), the EPUB sets `<i>`, `eval` prints
  italic precision/recall. Crime 0.952/0.909, Dolittle 0.833/0.814, held-out
  Lady into Fox 0.315/0.895.

## Next steps, in order

1. **Rescore Boze tongen and Sense with the new crops**, in page slices (the
   crops changed for every line, so glm-ocr re-reads them all; Boze tongen has
   ~11k lines). One book per command, results reported before the next.
2. **Italics, open ends:** marks below the word (dash-glued words with one half
   italic: `instead—they'll`); born-digital PDFs have italics in their font
   flags (De aanslag); Dutch publisher EPUBs italicise by CSS class, so their
   references carry no italics yet (a manifest list of italic classes).
   Lady into Fox's low precision is unexplained; it is held out, so don't look
   at its errors: check the stage on tuning books instead.
3. **Headings on unseen books** are the weakest carry-over (Grand Hotel Europa
   3/16). A general signal rather than more rules: the layout model's `title`
   regions, or the italic/size/centring of a line.
4. **A `bench` command**: every job's labelled set scored for any model.
5. **Learned trust** (Dawid–Skene, calibration) from the golden books and the
   user's answers, replacing hand-set thresholds (`SURE`, `SURE_ALONE`).
6. **Metadata stage** with `nuextract3:q6_k`.
7. **Parked sources** (`work/parked/README.md`): Goede dochter as a Dwarsligger, sideways pages with an unusable OCR layer, for when the pipeline can OCR whole pages itself.
8. Smaller: p23's decorated initial is answered "E" but shows an O; some em
   dashes land after a space (`ago —when`) in Dolittle.

## Working with the user

- **One book per long command**, results reported before starting the next; no
  multi-book runs that take long. Run small probes first and say how long a run
  takes; keep outputs under `work/probes/`.
- Held-out books (Lady into Fox, Grand Hotel Europa) are scored, never used to
  find errors. The user cares that improvements carry over to unseen books.
- The user picks no models: choose from measurements and record why. Ask before
  adding a runtime or anything they must install or pull.
- Commits are signed through 1Password; if signing fails, ask for it to be
  unlocked.
- Their connection is slow: avoid large downloads. Golden sources are in
  `work/.cache/` (checked against PROVENANCE.md).
