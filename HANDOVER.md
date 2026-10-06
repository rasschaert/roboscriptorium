# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State on 2026-10-06 (end of day)

M0–M2 done; M3 (better OCR and decisions) in progress; M4 (review UI) working
for regions of any book.

- **Line roles: `clef-flash:9b`** on Ollama's `/v1/systemone`, plus code rules
  for what clef can't see (sunk chapter pages, bare numerals, section numbers,
  running titles, short last lines, subtitles). See the decision log.
- **Golden books** (references from Gutenberg or a publisher's EPUB; books
  under EU copyright keep their text in `work/golden/`, only the manifest is in
  git): Sense, Crime, Dolittle, Lady into Fox (**held out: score, never tune**),
  De aanslag (born-digital PDF), Boze tongen (Dutch scan, omnibus reference).
- **Region review** (the main new thing): `uv run roboscriptorium review
  work/<book>` → http://127.0.0.1:8765/ (use `--port` if taken). Flags headings,
  doubtful drops and keeps, garbled, centred and set-apart lines, and, from
  the DocLayout-YOLO layout model, pictures, captions, titles and text the text
  layer lacks (drafted by tesseract). Keys `1` text, `2` heading, `3` drop,
  `4` image, `5` decorated initial (letter guessed from the word it begins), `e`
  edit. Answers go to `work/<book>/review/regions.jsonl` and apply on rebuild.
  The user started on Dolittle (a few answers so far).
- **Golden disagreement review** moved to `roboscriptorium golden review`. The
  54 Crime disagreements still have no verdicts.
- **OCR**: every new vision model tried today is unfit (translategemma 4b/12b/27b,
  llava:34b, nemotron3:33b); gemma4 + tesseract with a merge stays the design
  (`experiments/probe_ocr.py`). No OCR stage in the pipeline yet.

### Scores

| Book | CER | WER | Paragraph F1 | Headings |
| --- | --- | --- | --- | --- |
| Sense, Tauchnitz (other edition than the reference) | 2.99% | 1.36% | 0.811 | 49/50 (+0) |
| Crime | 0.63% | 0.44% | 0.976 | 8/8 (+1: the book title) |
| Dolittle | 4.77% | 2.20% | 0.859 | 21/21 (+1: the book title) |
| Lady into Fox (**held out**) | 0.93% | 0.33% | 0.841 | 0/1 (title = running head) |
| De aanslag (born-digital PDF) | 0.15% | 0.17% | 0.951 | 26/26 (+0) |
| Boze tongen (Dutch scan) | 1.36% | 1.15% | 0.749 | 13/18 (+2) |

### Open experiment: turning sideways pages

Landscape plates (Dolittle pp. 25, 57, 83, 87, 200) print picture and caption
turned 90° either way; the text layer reads the caption as scraps. The review
page now handles a region whose lines are a single column of scraps (p25): it
reads the region at 90° and 270°, keeps the turn that gives words, and shows
it upright. Generalising to whole pages was probed and **does not work yet**:
scoring four turns by tesseract word confidence ties 90° with 180°; scoring by
dictionary words picks right on 3/6 pages (drawings read as junk words);
scoring the scrap lines' strip alone also fails where the scraps are spread
over the drawing (p57, p83, p200). Truth for the six pages: 25→90, 57→90,
83→270, 87→270, 198→0, 200→90 (clockwise turn that makes text upright).
Ideas: run the layout model on each turn and keep the turn where it finds a
`figure_caption`; or OCR only thin strips along each page edge, where these
captions sit.

## Next steps, in order

1. Let the user continue the Dolittle region review; then rebuild and check
   the EPUB (drop caps, inserted p97 text, heading parts) with epubcheck.
2. Sideways pages (above), then a figures stage: crop pictures (answered
   `image`), place them with their captions, decorated initials as optional
   artwork.
3. OCR stage in the pipeline (gemma4 + tesseract merge with flags), first for
   regions the review flags and for Boze tongen's I/l and quote errors
   (`lets`→`Iets`, `"Wat`→`‘Wat`).
4. Boze tongen: paragraph recall 0.655, find why (dialogue, play-script
   passages, or omnibus differences); a region review of it.
5. Crime verdicts (`golden review`), when the user has time.
6. Smaller: De aanslag's private-use glyphs (U+E000 "Th", U+E005 "fj"); Sense
   chapter XXV's heading ("» CHAPTER XXV." mid-page) never reaches the model.
7. Page classification stage (vision) to replace hand-entered `body_pages`.

## Working with the user

- Run small probes first (10–60 items), say how long a big run will take,
  run it in the background.
- Ask the user to install or pull things when the docs don't cover how.
- Commits are signed through 1Password. If signing fails because 1Password is
  locked, stop and ask the user to unlock it.
- Their internet connection is slow: avoid large downloads.
- They like to try the review page while work goes on, and report oddities
  one at a time; each so far became a general fix (drop caps, heading parts,
  sideways captions).
