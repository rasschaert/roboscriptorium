# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State on 2026-10-07 (night; the user is asleep, the agent works on)

Everything is committed on `main`. New today:

- **OCR check crops fixed** (word-union crops, one em past line ends). Crime
  review 453 → 54; Dolittle WER 1.92% → 1.81%.
- **Italics stage** (`italics.py`): stroke slant on the page image, no model,
  for scans and born-digital PDFs. A word is measured only if it has an upright
  stem; ink is darker than each page's Otsu threshold (pale scans print grey).
  Italic precision / recall: Crime 1.000 / 0.886, Dolittle 0.850 / 0.791,
  De aanslag 0.987 / 0.855, Goede dochter (pp. 9–64) 0.958 / 0.828.
- **Golden books reshaped** with the user's EPUB/PDF pairs (AGENTS.md's table
  and decision log):
  - Tuning, Dutch scans: **Goede dochter** (clean publisher EPUB, same
    translation) and **Vals alarm** (48 chapter headings).
  - Held out: Lady into Fox (EN scan), **Grand Hotel Europa**, **De tuin van
    de avondnevel** (NL scans), **Villa Toscane** (NL born-digital). Score
    them, never inspect their errors.
  - Retired to `work/retired/`: Boze tongen, De dode kamer, Sense's Everyman
    scans, Goede dochter's 8th printing (reasons in the decision log).
  - Parked (`work/parked/README.md`): Goede dochter as a Dwarsligger, sideways
    pages with an unusable OCR layer, for when the pipeline can OCR whole
    pages itself.
- Publisher manifests can list `italic_classes`, `roman_classes` and
  `blank_classes`.
- `experiments/probe_big_diffs.py` lists the largest differing stretches.
- **Missing lines** (`missing.py`, commit 77625ab, *not yet measured on the
  golden books*): layout regions about one line tall with no text-layer line
  in them are read by glm-ocr and added before the line roles. Vals alarm's
  layer drops its single-digit chapter numbers (7 of 48 headings); the probe
  (`experiments/probe_missing_lines.py`) read all 15 Vals alarm candidates
  right and invented nothing on Dolittle's 73.

Scores (chapters or pages in brackets):

| Book | Text layer only (`--no-models`) | Full pipeline |
| --- | --- | --- |
| Villa Toscane (held out, born-digital, ch. 1–12) | — | CER 0.04%, F1 0.993, headings 0/12 |
| De tuin van de avondnevel (held out, ch. 1–3, pp. 11–52) | CER 0.72%, F1 0.931, headings 0/3 | CER 0.41%, WER 0.25%, F1 0.946, headings 3/3; 389 suspects: 179 fixed, 148 review |
| Goede dochter (ch. 1–4, pp. 9–64) | CER 0.40%, F1 0.957, headings 0/4 (with the quote rule) | CER 0.29%, WER 0.24%, F1 0.958, headings 2/4, italics 0.973 / 0.838 (before missing lines and the quote rule) |
| Vals alarm (whole book) | CER 0.74%, F1 0.918, headings 0/48 (with the quote rule) | not run yet |

`--no-models` scores headings without the role model, so 0/n there says little:
compare headings on full runs.

## Next steps, in order

1. **Measure the missing-lines stage**: Vals alarm pp. 11–60 (chapters 1–10,
   which hold the missing numbers), with and without the stage
   (`missing.candidates` patched to return nothing gives the "without"), then
   Dolittle and Crime for regressions. Running now:
   `work/probes/vals-alarm-missing-on.log`.
2. **Quotes in Dutch IA OCR layers**: openings misread as “ are fixed (commit
   b0f4254, see the decision log). Still open: a ‘ the layer drops altogether,
   and a period lost before a closing ’.
3. **Headings on unseen books**: Villa Toscane 0/12 and Grand Hotel Europa
   3/16 with models. Work on the tuning books only, then check the held-out
   ones. First look at what the missed headings have in common on the page,
   then a general signal rather than more rules.
4. Scene-break lines (`*****`) are dropped.
5. A `bench` command; learned trust (Dawid–Skene) replacing `SURE`/`SURE_ALONE`;
   the metadata stage with `nuextract3:q6_k`.
6. Italics: marks below the word (dash-glued words with one half italic).
7. Smaller: p23's decorated initial (Dolittle) is answered "E" but shows an O;
   some em dashes land after a space (`ago —when`).

## Working with the user

- **Before every long run, say why, what it should show, how long it takes and
  what each outcome would mean.** Post updates while it runs. Answer every
  question, even mid-task.
- **One book per long command**, results reported before the next.
- Be honest about the value of the books the user brings; retire what doesn't
  help and say what would (Dutch 1960s–90s scans with a same-edition ebook;
  real publisher print PDFs with their EPUB; another typesetting of a text we
  already have). English same-scan Gutenberg pairs the agent finds itself.
- Held-out books are scored, never used to find errors.
- The user picks no models: choose from measurements and record why. Ask before
  adding a runtime or anything they must install or pull.
- Commit after every step and keep this file current: the laptop may lock.
  Commits are signed through 1Password; if signing fails, stop and ask for it
  to be unlocked.
- Their connection is slow: avoid large downloads. Golden sources are in
  `work/.cache/` (checked against PROVENANCE.md).
