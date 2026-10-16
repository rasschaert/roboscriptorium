# Decision log

What was learned or decided, dated, oldest first. Add a line with every change that teaches something (see AGENTS.md's standing rules). Scores here are as measured at the time; before 2026-10-07's bench (`roboscriptorium bench`) most were single runs on ad-hoc slices, and differences of a few hundredths of a CER point are noise.

- 2026-10-05: Project started. Python + uv; local only (Ollama + Ollaya);
  scanned PDF first, with *Wij doden Stella* as the first target; Dutch and English;
  faithful text, clean ebook; human review via a local web UI, automation earned by
  measured quality; golden pages for evaluation; copyrighted material kept out of git;
  commits go straight to `main`.
- 2026-10-05: Ollaya smoke test. `laya:multilingual` labelled the bare
  string "Io" (a misread page number) as a heading at 0.93 confidence. Decision
  calls need context, and their thresholds need calibration.
- 2026-10-05: M0 skeleton landed (uv, typer, httpx, ruff, pytest; `doctor`
  command). With a context-rich state ("Io", last line, centred, previous page
  9), `laya:multilingual` answered `page_number` at 0.90. Given "12" with only
  position context and two options, it answered `body` at 0.65. laya is shaky on
  layout questions; evaluate `winnow` and richer state once golden pages exist.
- 2026-10-05: M1 landed. Stella builds from its existing text layer into an
  EPUB that passes epubcheck (244 paragraphs). Footer = short lines after a
  wide gap in the bottom fifth. Left margin = lower quartile of nearby line
  starts (follows skew, works on short pages). A line-end hyphen before a
  capital is kept.
- 2026-10-05: Golden books instead of hand-corrected pages of the target book.
  The reference comes from Standard Ebooks with `[Editorial]` commits undone (458
  of 469 changes; 11 listed in PROVENANCE.md). A "modernisation pass" (the SE
  editorial changes as an optional pipeline stage) is a stretch goal.
- 2026-10-05: M2 baseline, existing text layers only, **no AI in the pipeline yet**:
  tauchnitz-1864 CER 8.05% / WER 5.18% / paragraph F1 0.589; everyman-dent
  5.79% / 4.68% / 0.553; everyman-1992 4.16% / 2.63% / 0.379.
- 2026-10-05: laya can't classify line roles. On 300 Tauchnitz lines (auto-labelled
  against the golden reference) with position and neighbour context:
  `laya:en` got 196/300 body-vs-other right and called most body lines
  "artifact"; `laya:multilingual` got 150/300 and called nearly everything
  "page_number". Next to try: `winnow:e4b`.
- 2026-10-05: Line roles with `winnow:e4b` (laya couldn't do them). Tauchnitz
  chapters 1–9: CER 7.30% → 4.23%, WER 5.18% → 3.48%, paragraph F1 0.592 →
  0.697, headings 0/9 → 9/9. That combines the roles, a cross-page repetition
  feature, the "a chapter heading appears once" rule, and closing spaces before
  punctuation.
- 2026-10-05: `clef-flash:9b` (Ollama) beats winnow on the line-role probe
  (60/60 vs 58/60) and matches decider on page types with better-calibrated
  confidence. It's the next default candidate; see HANDOVER.md.
- 2026-10-05: Full-book Tauchnitz with winnow roles: CER 8.05% → 4.68%, WER
  5.18% → 3.34%, paragraph F1 0.589 → 0.667, headings 28/50.
- 2026-10-06: References switched from Standard Ebooks to Project Gutenberg.
  Undoing SE's `[Editorial]` commits put back spellings from SE's starting
  text, Gutenberg #161 of the 1811 edition: the reference said "shewing" where
  Tauchnitz prints "showing". SE is kept for later style work only. New golden
  books: *The Nature of a Crime* (Gutenberg made from the same scan) and
  *Doctor Dolittle* (same printing). Sense now has no same-edition reference.
- 2026-10-06: `clef-flash:9b` replaces winnow for line roles. Tauchnitz chapters
  1–9 against the (old) SE reference: CER 4.23% → 3.73%, WER 3.48% → 3.04%,
  paragraph F1 0.697 → 0.728, headings 9/9.
- 2026-10-06: Disagreements get human verdicts instead of trusting any
  transcription blindly: `roboscriptorium review` serves a local page with scan
  crops. Garbled output (stray symbols, words in neither the reference nor
  `/usr/share/dict/words`) and whitespace-only differences are auto-resolved.
  Sense chapters 1–9 still leave ~300 for review (another edition), Crime far
  fewer (same scan). Full-book Tauchnitz against Gutenberg: heuristics CER 7.23%,
  winnow 4.98%, clef 4.75% (WER 3.15%, paragraph F1 0.682, headings 28/50).
- 2026-10-06: OCR candidates on 12 pages of *Het ivoren aapje* (Teirlinck, 1909;
  Gutenberg #28068 publishes its page images; the transcribers' corrections are
  reverted to the print via their "Bron:" notes). Vision LLMs modernise old Dutch
  spelling, even when told not to; tesseract doesn't but misreads punctuation
  and drops short lines. Merging them (spelling-reform differences take
  tesseract's form, every other disagreement keeps gemma4's and is flagged)
  gives CER 0.54% against 0.63% (gemma4) and 0.90% (tesseract), 89 flags (56
  real errors) and almost no unflagged wrong words. This is the M3 OCR design:
  several candidates, rules for known biases, flags for the rest.
- 2026-10-06: Full-book headings 28/50 → 50/50. The repetition feature matched
  "CHAPTER II." and "CHAPTER III." as the same text (letters ≥ 85% similar),
  so over 50 chapters every heading looked like a running head and was
  demoted. A trailing Roman numeral must now match exactly. Crime with clef
  roles: CER 0.72%, WER 0.53%, paragraph F1 0.965, headings 5/8.
- 2026-10-06: Tried a page-level feature for line roles ("text begins 26% down
  this page; most pages begin at 8%"), since chapter pages open sunk. clef
  ignored it: Crime headings 5/8 → 3/8, CER 0.72% → 0.82%; reverted. Bare
  Roman numerals ("V", "VI") stay ambiguous to clef (called page numbers at
  ~0.1 confidence). Layout facts like this belong in code, not in the state.
- 2026-10-06: Visual lines now group word boxes by vertical overlap (≥ half a
  fragment's height) instead of tops within 3 pt: OCR layers box each word, and
  one line's tops differ by up to ~5 pt. Sense had 560 fragmented lines,
  Dolittle 1,450. With clef roles, against Gutenberg: Sense full book CER 4.75%
  → 3.02%, WER 3.15% → 1.39%, paragraph F1 0.682 → 0.805, headings 49/50;
  Dolittle CER 21% → 5.48%, paragraph F1 0.43 → 0.839 (but 27 headings for
  21 chapters: its two-line headings split). Crime unchanged (0.72%).
  The text-layer cache now carries a version and rebuilds when it changes.
- 2026-10-06: `eval` now matches headings against the reference chapter
  headings (an order-preserving alignment maximising similarity) and reports
  spurious ones; it used to count headings only. Correction: the "50/50" above
  was 49 real headings plus one false one. Repeats across pages now use an edit
  budget (one edit per 10 letters) instead of a similarity ratio, because
  "THE FIFTH CHAPTER" and "THE SIXTH CHAPTER" were ≥ 85% similar; a heading
  repeated on 3+ other pages is a running head (was 5). Headings now: Sense
  49/50 (+0 spurious), Dolittle 14 → 20/21 (spurious 13 → 5), Crime 4/8 (+1).
- 2026-10-06: Garbled lines (under half the tokens look like words: OCR read
  from a drawing or a smudge) are now line-role candidates wherever they sit,
  and clef calls them artefacts. Dolittle CER 5.48% → 4.82%, paragraph F1
  0.839 → 0.861; Sense 3.02% → 3.00%. Plate captions still end up in the text
  (a caption role belongs with the figures work).
- 2026-10-06: `translategemma:27b` as OCR: CER 0.99% on the 12 Teirlinck pages,
  worse than gemma4 (0.63%), and the merge with tesseract gains nothing (0.99%,
  11 unflagged wrong words). No size of translategemma is worth keeping.
- 2026-10-06: `llava:34b` as OCR: one Teirlinck page took 170 s and came back
  as invented, looping Dutch (CER 406%); not run on the full sample.
- 2026-10-06: Bare Roman numeral headings get a rule in code, since clef calls
  them page numbers: on a sunk page (text starts ≥ 8% of page height lower than
  on most pages), a bare numeral in the first 3 lines is a chapter heading
  ("Ill" read for "III" is normalised). A numeral joins the heading line above
  only after CHAPTER/PART/BOOK (or the Dutch words), so a book title over "I"
  stays separate. Crime headings 4/8 → 8/8 (+1: the book title), CER 0.72% →
  0.71%, paragraph F1 0.965 → 0.972; Sense and Dolittle unchanged.
- 2026-10-06: More chapter-opening rules for Dolittle. The first 3 lines of a
  sunk page always go to the model (a drop cap shortens the median line, so a
  wide centred heading failed the centring gate). Lines between a chapter heading
  and the text are its title (clef called "PUDDLEBY" an artifact, dropping it). A
  heading line containing CHAPTER/PART/BOOK starts a new heading, so the book
  title above it stays separate. A "heading" that carries the page's printed
  number (file page minus the book's usual offset) or repeats an earlier
  heading line is a running head. Dolittle headings 20/21 (+5) → 21/21 (+1: the
  book title), CER 4.82% → 4.80%; Sense 49/50 and Crime 8/8 unchanged.
- 2026-10-06: First held-out golden book, *Lady into Fox* (Chatto & Windus 1922
  = Gutenberg #10337), never to be tuned on. A golden book under EU copyright
  sets `eu_copyright_until` and keeps its text and verdicts in `work/golden/`.
  First score: CER 0.93%, WER 0.33%, paragraph F1 0.841. Most errors: this
  printing spaces opening quotes (`" What`). *De kleine Johannes* was rejected:
  the scan is a 1986 Querido edition in modern spelling, Gutenberg #10819 is in
  the old spelling.
- 2026-10-06: `nemotron3:33b` as OCR: CER 14% on one Teirlinck page with
  thinking off (empty output with it on). Of all the vision models tried,
  only gemma4 is worth pairing with tesseract.
- 2026-10-06: First born-digital PDF, *De aanslag* (calibre's PDF of the retail
  EPUB): CER 0.64% → 0.15%, headings 6/22 → 26/26. Ligatures (ﬁ, ﬀ, ﬃ) are
  spelled out. A bare number opening a page, above body text and not near the
  printed page number, is a section number; a page offset needs ≥ 3 pages and a
  quarter of the edge numbers to agree (one "1945" had set it to −1936). Lines
  under a heading that survives the running-head checks are its subtitle on
  any page. A lowercase line under a body line that stops mid-sentence is body
  (clef dropped short last lines like "kijken."). A line-end hyphen stays in a
  compound that has hyphens elsewhere ("Mens-erger-je-niet"); a spaced dash
  keeps its spaces. Reference fixes: spans join without spaces ("nsb-leider"),
  and every EPUB heading is its own chapter. Crime 0.71% → 0.63%, Dolittle
  4.80% → 4.77%, Sense 3.00% → 2.99%; held-out Lady into Fox unchanged (0.93%).
  Still lost on De aanslag: inscriptions and signs set apart in the text,
  which clef calls artifacts; these need flags for review, not more rules.
  The font's private-use glyphs (U+E000 "Th", U+E005 "fj") come out as junk.
- 2026-10-06: Region review for any book: `roboscriptorium review` flags what
  isn't plain running text and takes a human's answer per region, applied on
  the next build (the golden disagreement page moved to `golden review`).
  Flags per book: De aanslag 48, Crime 12, Lady into Fox 4, Dolittle 85,
  Sense 118 (half of them headings). clef's P(body) doesn't separate page
  furniture from real text (running heads score up to 0.4), so furniture is
  recognised by repetition and page numbers instead. A line counts as centred
  for flagging only with equal margins on both sides and under 80% of a line.
- 2026-10-06: DocLayout-YOLO probe on 20 tricky pages: worth adding as a flag
  source for pictures, captions, titles without a heading, and text the OCR
  layer lacks (Dolittle chapter 9's subtitle is printed, not drawn: the layer
  just skipped it). Not trusted alone: it called Boze tongen's part title
  furniture.
- 2026-10-06: Layout regions feed the review flags. Dolittle: 131 regions, among
  them 51 pictures and 24 captions, and one whole page (p97) whose text the OCR
  layer lacks except its heading; the review page drafts it with tesseract
  (near perfect, bar the drawn initial) for the human to correct.
- 2026-10-06: A heading keeps its label and title as separate lines ("THE FIRST
  CHAPTER" / "PUDDLEBY", written with `<br/>` in the EPUB); a title wrapped over
  two lines stays one. First score for Boze tongen (Dutch scan, omnibus
  reference): CER 1.36%, WER 1.15%, paragraph F1 0.749 (recall 0.655), headings
  13/18 (+2). Most differences: the OCR layer reads ‘ as " and drops closing
  quotes, and reads a capital I as l (`lets`, `leder`, `ledereen`).
- 2026-10-06: Decorated initials: a reviewer answers a picture region with the
  letter it shows; the letter goes back in front of the text beside the
  drawing ("O" + "NCE"), the lines beside it continue the paragraph, and the
  EPUB sets it as a CSS drop cap (`span.initial`). The artwork itself waits for
  the figures work.
- 2026-10-06: Initial-letter guesses: tesseract (single character) and gemma4
  both misread decorated letters (`E`/`J` for an O). Restricting to the letters
  that complete the word beside the drawing, then asking clef with the crop,
  got 8/8 Dolittle initials (0.5–2 s each); with no word beside it (a page the
  text layer lacks) it guesses nothing.
- 2026-10-06: Sideways text (a landscape plate's caption) shows in the text
  layer as a column of 1–3 character scraps. Such a page gets one region; the
  review page reads it turned 90° and 270° and keeps the turn that gives words
  (tesseract's own orientation detection said 180° on a picture page), shows
  it upright and drafts its text.
- 2026-10-06: Whole-page orientation probed on Dolittle's six suspect pages
  (scraps or garbled text layers): scoring four turns by tesseract word
  confidence ties 90° with 180°; by dictionary words it is right on 3/6
  (drawings read as junk words); on the scrap lines' strip alone it fails
  where scraps spread over the drawing. Not adopted; see HANDOVER.md.
- 2026-10-06: Sideways plates found with the layout model. A page with a picture
  (≥ 0.5) and no text is run again turned 90° and 270°: on a landscape plate the
  model then finds the caption, and on blank, stamp or title pages nothing
  (the figure gate removes Crime's bindery stamp and Lady into Fox's half-title).
  It labels the strip under a figure a caption whichever side is up, so the
  review page still picks 90° or 270° by reading the caption box with
  tesseract (tesseract's default mode reads a vertical block on its own, so it
  only separates 90° from 270°, never upright from sideways). Dolittle: 8/8
  plates (pp. 6, 25, 57, 83, 87, 90, 107, 200), all turning 90°; the earlier
  "truth" of 270° for pp. 83 and 87 was wrong.
- 2026-10-06: Specks (a quote mark's second stroke read as "1", "7", "5")
  became one-character lines that the model dropped and the review flagged.
  Letting a fragment join a line when the overlap covers half of the shorter
  of the two glued lines together in Sense (CER 2.99% → 5.99%); rejected. Dropped
  specks are now just not flagged.
- 2026-10-06: Boze tongen doesn't indent paragraphs. In justified text a line
  after one that ends a sentence well short of the margin now starts a
  paragraph (not when it opens lowercase or with punctuation): Boze tongen
  paragraph recall 0.655 → 0.768, precision 0.875 → 0.888; the others
  unchanged. Of its remaining missed breaks, ~160 are mid-line in the scan
  (edition differences) and ~60 follow a full line (undetectable).
- 2026-10-06: A short line holding CHAPTER/PART/BOOK (or HOOFDSTUK/DEEL/BOEK)
  always goes to the role model: Sense's "» CHAPTER XXV." was off centre
  because of a speck. Sense headings 49/50 → 50/50.
- 2026-10-06: Private-use glyphs (a font's own Th and fj ligatures) are
  spelled out by tesseract (eng) reading the rendered word: what it reads
  between the known letters must be a ligature, majority per glyph. Dutch
  tesseract reads Th as "Ih". De aanslag: 7/7 resolved, CER 0.15% → 0.136%.
- 2026-10-06: Old OCR layers (Dolittle, Sense) flatten quotes to straight ones
  and often read a closing ” as `'` ("asleep in his chair'"). In
  straight-quoted text, a word-final `'` while a `"` is open and no `'` is
  now closes the `"`. Dolittle CER 4.76% → 4.60%, WER 2.18% → 2.02%; Sense
  unchanged. Newer layers keep the printed curly quotes.
- 2026-10-06: OCR check probe (`experiments/probe_ocr_check.py`), Dolittle pp.
  30–49: tesseract reads each page; where its reading of a visual line
  differs from the text layer's (widened to whole words), clef picks between
  the two from the crop. 99 suspects (~5/page), 90 with a truth from the
  reference: tesseract right 56, text layer 34, clef 79 (88%). Clef at
  confidence ≥ 0.5: 49/50 right; below 0.5: 30/40. The layer loses em-dashes
  (`up if` for `up—if`) and closing ”; tesseract misreads opening “ as ‘, and
  clef can't tell those apart. ~0.8 s per suspect. Second opinions on the
  same 90: decider:2b-vision (crop) 74 right, winnow:e4b (the line as text, no
  image) 74; each disagrees with clef 13 times, where clef is right only 9.
  Applying only when clef and winnow agree and clef ≥ 0.3: 62 applied, 1
  wrong, 28 left for review. Agreement isn't proof: the wrong unanimous cases
  are the opening-quote blind spot every model shares.
- 2026-10-06: Book metadata from the front pages with `nuextract3:q6_k`
  (vision, JSON template): right on Stella, Lady into Fox and Crime once it
  sees every page before the body and is told to ignore library stamps and
  handwriting and to describe this edition, not the original. The candidate
  for filling `book.toml` and the EPUB's metadata, with a human confirming.
- 2026-10-06: Models per job, chosen from measurements (the user leaves the
  choice to the agent): clef-flash for line roles, clef:27b to judge OCR
  suspects, winnow:e4b as the text-only second opinion, glm-ocr and tesseract
  as the second readings (glm-ocr for letters, tesseract for dashes). A bigger
  model isn't better at everything: clef:27b judges crops far better and line
  roles worse.
- 2026-10-06: OCR check stage in the pipeline (`ocrcheck.py`, tesseract as the
  second reading). Dolittle: CER 4.60% → 2.16%, WER 2.02% → 1.84%, paragraph
  P/R 0.808/0.942 → 0.815/0.951; 624 suspects: 376 fixed, 105 kept, 143 for
  review (~0.7 per page).
- 2026-10-06: Two document-OCR models on the Teirlinck bench: `glm-ocr`
  CER 0.38% with no modernising (best so far, against gemma4 0.63% and
  tesseract 0.90%); `deepseek-ocr:3b` 0.37% but modernises old accents and
  spelling. glm-ocr is the candidate to replace tesseract as the OCR check's
  second reading.
- 2026-10-06: **Quality over speed** (standing rule above). The OCR check's
  second reading is glm-ocr on each line's crop, not tesseract on the page,
  though it is ~10× slower (~30 s against ~3 s per page). On Dolittle pp.
  30–49: 67 suspects instead of 99; the second reading right 93% of the time
  against 62%; clef right 96% against 88%; with clef and winnow agreeing and
  clef ≥ 0.3, 47 fixes applied with none wrong and 8 left for review, against
  62 applied with 1 wrong and 28 for review.
- 2026-10-07: Figures stage. Dolittle: 48 pictures in 2.5 s, all 7 sideways
  plates turned upright, their captions read (6 of 7 verbatim, `Tord` for
  `Lord`) and trimmed out of the picture, the decorated initials answered as
  such left out. Shared page analysis moved from roles.py to page.py, with
  identical roles, reflow and flags on all six golden books; `LineRole.rule`
  names the rule that overrode the model.
- 2026-10-07: OCR check crops fixed. Crime's text layer gives lines boxes about
  twice the print's height (font metrics), so glm-ocr read the neighbouring line
  into its reading; a line's crop is now its words' boxes together. Crops (the
  line's, and a suspect's at a line end) also reach one em past the line, where
  the text layer misses dashes: Dolittle's line-end em dashes were cut to
  hyphens, which the judge then applied ("live on-" + "even" → "oneven").
  Joining two words is no longer a punctuation-only difference the vision judge
  decides alone, and a `¬` line-end hyphen equals `-`. Crime: suspects 928 →
  236, for review 453 → 54, CER 0.53% → 0.52%. Dolittle: CER 1.89% → 1.84%,
  WER 1.92% → 1.81%, applied fixes the reference contradicts 24 → 3, for review
  100 → 107. Held-out Lady into Fox: CER 0.93% → 0.92%, WER 0.309% → 0.305%.
- 2026-10-07: Second held-out book, *Grand Hotel Europa* (Dutch, a scan with an
  OCR layer, like Stella), since every other Dutch golden book has been tuned on.
  `golden derive` now reads a `<div>` holding no other blocks as a paragraph:
  its EPUB has no `<p>`. Boze tongen's and De aanslag's references re-derive
  byte-identical. Cold-start score, chapters 1–3 (pp. 15–44): text layer alone
  CER 2.51%, WER 2.38%, paragraph F1 0.772, headings 0/16; full pipeline CER
  1.92%, WER 1.80%, F1 0.814, headings 3/16 (the 16 count each chapter label,
  title and section number); 146 OCR suspects, 74 for review.
- 2026-10-07: Italics. Page-level "are there italic words?" with clef-flash:
  11/15 italic pages at P ≥ 0.7, no false alarms; clef:27b says yes to every
  page. Better and model-free: each text-layer word's **stroke slant** on the
  scan (shear the ink above the baseline; the angle with the most peaked column
  profile). Dolittle: italic median 16°, roman −1°; at ≥ 8°, 59/61 italic words
  caught, 25 of 20,605 roman words flagged, nearly all of them italic in print
  but unmarked by Gutenberg (running heads, phrases the truth didn't place).
  Below the baseline is left out: a y's descender leans like italic. Crime,
  same thresholds: 23/25, the 9 flags italic foreign words. ~0.2 s/page
  (`experiments/probe_italic_words.py`). References now keep `<i>`/`<em>` as
  italic words (`Chapter.italic`), also through verdict patches; plain text
  unchanged on every golden book. Publisher EPUBs that italicise by CSS class
  (the Dutch ones) don't carry italics yet.
- 2026-10-07: Italics stage (`italics.py`), slant ≥ 8° on words of 2+ letters
  (single letters between italic words fill in). Italic words, precision /
  recall: Crime 0.952 / 0.909, Dolittle 0.833 / 0.814 (7 of 9 misses are
  dash-glued words with one half italic, `instead—they'll`, which need marks
  below the word), held-out Lady into Fox 0.315 / 0.895 (54 marked against 19;
  on the tuned books such extras were mostly italics Gutenberg left unmarked,
  unverified here). CER and the rest unchanged; epubcheck clean.
- 2026-10-07: Italics on born-digital PDFs too, and a word is measured only
  if it has an upright stem: two stems (h, n, u count two, m three), or one in
  a word without diagonal letters. Two-letter words like "zo" and "ze" read as
  italic in any type (De aanslag precision 0.377 at two letters). A line is
  measured only when its words spell it (`pdf.spells`, private-use ligatures
  allowed). Italic precision / recall: Crime 0.951 / 0.886, Dolittle 0.872 /
  0.791, De aanslag (now with italics from its CSS classes) 0.987 / 0.855.
- 2026-10-07: Two more Dutch golden books from the user. *De dode kamer*: a
  scan with a reference of the same first edition, the first such Dutch book,
  so it is tuned on. Text layer alone, chapters 1–4 (pp. 19–57): CER 5.31%,
  WER 5.71%, paragraph F1 0.889, headings 0/4, italics 0.837 / 0.903.
  With the OCR check: CER 5.20%, but 92% of that is ~2 pages of print the
  EPUB lacks (pp. 50–51); without them, text layer ~0.50% → ~0.39%. The
  EPUB itself has OCR errors ("lorras", "sucretaresse"), so it needs
  verdicts. Pipeline misses: `*****` scene breaks, chapter titles.
  `experiments/probe_big_diffs.py` lists the largest differing stretches.
  *Villa Toscane*: born-digital, held out. Boze tongen's italic score (0.13 /
  0.05) is an edition difference: the omnibus sets the diary in italics, the
  2002 print in an upright sans-serif. Boze tongen pp. 11–132 with the new
  crops: CER 1.68% → 1.53% with the OCR check, paragraph F1 0.845 → 0.866.
- 2026-10-07: *De tuin van de avondnevel*, a third held-out book: a Dutch
  scan whose reference is the same translation's retail EPUB. Its EPUB fills
  blank lines with ".." paragraphs, so a manifest's `blank_classes` now leaves
  such paragraphs out.
- 2026-10-07: *Goede dochter* (Dutch translation, first printing, with the
  publisher's own EPUB) becomes the main Dutch tuning book: De dode kamer's
  EPUB was made by OCR and misses text, Boze tongen's is another edition.
- 2026-10-07: Italics: ink is what is darker than each page's Otsu threshold,
  not a fixed grey of 128. Goede dochter's pale scan prints in grey (120–140),
  so most strokes went unseen: italic words 0.617 / 0.245 → 0.958 / 0.828
  (pp. 9–64). Crime 0.951 → 1.000 precision; De aanslag unchanged; Dolittle
  0.872 → 0.850 precision; De dode kamer 0.837 / 0.903 → 0.831 / 0.898.
- 2026-10-07: Golden books culled to those whose reference matches the scan
  closely enough to tell pipeline errors from edition differences. Retired
  (files moved to `work/retired/`, manifests in git history): Boze tongen
  (omnibus reference with revisions, the diary italic in one and not the
  other), De dode kamer (its EPUB was made by OCR and lacks printed text),
  Sense's two Everyman scans (other editions, never scored), and Goede
  dochter's eighth printing (same text as the first).
- 2026-10-07: *Vals alarm*, a second Dutch tuning book (another publisher and
  typesetter). Text layer alone, whole book: CER 0.79%, WER 0.42%, paragraph
  F1 0.891, headings 0/48, italics 0.697 / 0.736. Its errors: opening ‘ read
  as " or lost, a period lost before a closing quote, `zon` for `zo'n`.
- 2026-10-07: First held-out score of *De tuin van de avondnevel*, chapters
  1–3: text layer alone CER 0.72%, WER 0.60%, F1 0.931, headings 0/3; full
  pipeline CER 0.41%, WER 0.25%, F1 0.946, headings 3/3 (389 OCR suspects: 179
  fixed, 148 for review). The OCR check carries over to an unseen Dutch scan.
- 2026-10-07: Dutch print sets dialogue in ‘…’, and Internet Archive's OCR reads
  many openings as “ (Vals alarm 226 “ in the layer against 6 in print, Goede
  dochter 777 against 101). In a book whose text opens with ‘ more than twice
  as often as with “, a “ that the next quote mark (apostrophes aside) doesn't
  close as ” or ’’ becomes ‘. Text layer alone: Goede dochter pp. 9–64 CER
  0.45% → 0.40%, F1 0.943 → 0.957; Vals alarm CER 0.79% → 0.74%, F1 0.891 →
  0.918. De aanslag unchanged (its real “ close with ” or ’’); English books
  are double- or straight-quoted, so the rule doesn't run. Still open: ‘ the
  layer drops altogether, and a period lost before a closing ’.
- 2026-10-07: Missing-lines stage measured. Vals alarm pp. 11–60 (full
  pipeline): 13 lines read back, all printed (7 chapter numbers, 5 page
  numbers, one `'Ja.'`); headings 2/10 → 8/10 (+0 spurious), paragraph F1
  0.929 → 0.937, CER 0.48% either way. Dolittle: 71 lines added, all printed
  (mostly furniture, which the roles drop; four text lines of p97, whose layer
  lacks them), CER 1.84% → 1.80%, headings and paragraphs unchanged. Crime
  unchanged (one page number). Goede dochter pp. 9–64, full pipeline before
  the stage and the quote rule: CER 0.29%, WER 0.24%, F1 0.958, headings 2/4.
- 2026-10-07: Closing quotes in the OCR check. On Vals alarm the layer reads
  `.’` as `’`, glm-ocr as `.`, tesseract as `.'`, so no reading the judges saw
  was right. Readings now take a curly-quoted layer's quote style, and where
  readings of one word each lost a different trailing mark (one a period, one
  the quote) the word with both is offered too; the judges still decide. Vals
  alarm pp. 11–60: CER 0.48% → 0.47%, paragraph F1 0.937 → 0.948; Crime CER
  0.52% → 0.50%, F1 0.976 → 0.983; Dolittle unchanged. Many combined readings
  still go to review: clef often misses the small period and keeps the
  layer's `zijn’`, and winnow can't tell `zijn.` from `zijn.’` without the
  open quote earlier in the paragraph.
- 2026-10-07: The OCR check's text judge (winnow) now reads the lines before
  and after the suspect line, where a quote opens or a sentence goes on. Vals
  alarm pp. 11–60: WER 0.20% → 0.18%, applied 109 → 114, review 110 → 108;
  Dolittle CER 1.80% → 1.78%; Crime unchanged in CER, but one italic word
  lost (winnow now keeps `fiancee.` on p61). Against clef's sure picks (≥ 0.8)
  winnow agrees, with context / without: Crime 56 / 65 of 79, Dolittle 397 /
  379 of 419, Vals alarm 31 / 31 of 44 (`experiments/probe_reader_context.py`).
  15–20% of its answers flip with the added lines: winnow is a noisy judge,
  which argues for trust measured per model and kind of error over fixed
  thresholds. `eval` now prints and records the OCR check's counts (fixed,
  kept, for review). Crime: 236 suspects, 46 fixed, 123 kept, 67 for review.
- 2026-10-07: A number with a short title opening a sunk page ("1 Later") is a
  chapter heading, whatever the page number: a page number with words beside it
  is a running head, and chapter openings carry none. clef called both of Vals
  alarm's titled numbers page numbers (at 0.07). Vals alarm pp. 11–60 headings
  8/10 → 10/10, paragraph F1 0.948 → 0.950; Crime, Dolittle, De aanslag
  unchanged. On Vals alarm the sunk pages are exactly the chapter openings.
- 2026-10-07: Sunk pages are also those whose running text (the first line of
  near full width) starts low, since a chapter label can sit at the usual
  height above a sunk opening (Goede dochter's "EEN"). On a sunk page, a short
  first line set apart from the text (or alone on the page) is the chapter
  heading unless the model calls it body, it repeats on other pages, or it is
  garbled. Goede dochter pp. 9–64 headings 2/4 → 3/4; Vals alarm, Crime,
  Dolittle, De aanslag unchanged. Still missed: the part title "DONDERDAG 16
  MAART, 1989", alone on p9.
- 2026-10-07: Critical review of the approach (see HANDOVER.md). The
  `roles.py` overrides don't carry over to held-out books (Villa Toscane
  headings 0/12, Grand Hotel Europa 3/16), the role model sees no typography,
  errors every reading shares go unflagged, and verdicts are unsettled so
  small CER gains are noise. New direction: no new layout rules; type-size
  features and book-wide heading clusters, learned trust over thresholds, a
  Dutch lexicon, grouped review questions, changes reported as error counts.
- 2026-10-07: Type measured per line from the scan (`typestyle.py`). Headings
  stand apart on every tuning book: Goede dochter 1.5× the body text, Vals
  alarm 1.3–1.7×, De aanslag 1.7–1.9×, Dolittle in letterspaced capitals;
  page numbers are smaller (~0.7×). Crime's bare numerals differ only by being
  capitals (`experiments/probe_type_features.py`). Telling clef the type in the
  state ("larger than the body text (1.5×), in capitals") changed none of its
  answers on Goede dochter pp. 9–64, so it is used book-wide instead: display
  lines in one style and place vote with the model's roles, weighted by its
  confidence, and a group that votes heading makes all its lines headings.
  Goede dochter headings 3/4 → 4/4 (the part title "DONDERDAG 16 MAART, 1989";
  "EEN" now by style, not the `sunk-opening` rule). Vals alarm, Crime,
  Dolittle, De aanslag unchanged. Held-out Villa Toscane still 0/12: a vote
  spreads the model's heading calls but can't make one.
- 2026-10-07: The missing-lines stage added regions that lie inside a
  text-layer line (Dolittle's page number at the end of its running head, read
  again as "II"). Such regions are skipped now: Dolittle CER 1.78% → 1.72%.
- 2026-10-07: Tried asking clef about a whole style group at once ("these lines
  share one type and place: what are they?", `experiments/probe_style_groups.py`).
  Right on every tuning-book group (Crime's numerals 0.9, Vals alarm's "1 Later"
  0.69), but held out it changed nothing (Villa Toscane 0/12, Grand Hotel Europa
  3/16) and added 2 spurious headings to De tuin; not adopted. The plain vote
  stays: De tuin 3/3 (+0).
- 2026-10-07: Second review, agreed with the user (see HANDOVER.md): the
  machine learns nothing yet, and CER isn't what the human experiences. New
  measure, `roboscriptorium quality`: wrong words per page left unasked at a
  question budget. First run (verdicts mostly unsettled): Goede dochter pp.
  9–64 1.53 wrong words/page, 2.24 questions/page, 0.58 unasked with all of
  them; Vals alarm 3.48 / 2.12 / 1.66; Crime 1.15 / 0.78 / 0.83; Dolittle 3.08
  / 1.30 / 1.74. Only 28 of Goede dochter's 116 OCR-doubt questions sit on a
  remaining error. Comparisons now fold `…` to `...` (the print can't tell
  them apart): 11 of Goede dochter's 34 disagreements were only that.
- 2026-10-07: Golden lines labelled by alignment (`golden/align.py`): each
  text-layer line's reference words (as printed, line-end breaks kept) and role.
  `disagreements.patch` now keeps the reference's printed glyphs (it returned
  normalised words, straightening every quote). First per-line bench on modern
  Dutch, Goede dochter pp. 9–64, 1,622 body lines, typesetting folded
  (`experiments/bench_line_readings.py`): text layer CER 0.21% (1,459 lines
  exact), glm-ocr 0.25% (1,154; drops quotes and sometimes whole words),
  tesseract 0.29% (1,403). glm-ocr's lead on the 1909 Teirlinck bench doesn't
  hold here; the readings' errors differ, which is what combining them needs.
- 2026-10-07: Two CPNB Boekenweekgeschenken from the user, the closest match to
  Stella among the golden books (IA Scribe scans, 360 ppi MRC, GlyphLessFont,
  104 pages), each with CPNB's EPUB of the same edition: *De eerlijke vinder*
  (2023) and *Monterosso mon amour* (2022). Different typesetting: one CPNB
  grid (13.2–13.3 pt pitch, 245–252 pt measure) but different designers (Frank
  August; Nico Richter) and typefaces (stroke/height 0.174 against 0.149).
  Text layer alone: De eerlijke vinder CER 0.37%, paragraph F1 0.953, headings
  0/4; Monterosso CER 0.31%, F1 0.868, headings 0/22. Both join the
  leave-one-book-out set.
- 2026-10-07: Line-role classifier probe (`experiments/train_line_roles.py`):
  gradient-boosted trees on line geometry, type, text shape, repetition, sunk
  pages, printed page numbers and clef's answer, labelled by `golden.align`,
  scored leaving one book out over nine books: 153 line-role errors against
  182 for `roles.py`; Villa Toscane headings 0/12 → 12/12, De tuin 1 → 0
  errors; Grand Hotel Europa 34 against 33. Without clef's answer as a feature,
  349.
- 2026-10-07: glm-ocr's token probabilities as review questions
  (`experiments/probe_token_confidence.py`; Ollama 0.40 returns `logprobs` and
  `top_logprobs` from `/api/generate`). Goede dochter pp. 9–64, every line read
  again: a word's least likely token is almost never below P 0.3, so the signal
  is flat. Lines with a word below 0.5: 2.93 questions/page catching 10 of 65
  wrong words; below 0.4: 0.40/page catching 2; the review's own 2.24/page
  catch 47. The unasked errors are mostly quotes the layer dropped, where
  glm-ocr was sure. Not a question source on its own; at most a feature.
- 2026-10-07: Stella through the whole pipeline for the first time: 67 pages,
  44 OCR fixes applied (`vijfjaar`, `scenes`, `knieén`, `Italié`, the stray
  `»`, `viekken` all fixed; `besef een` → `besefeen` wrong), 73 OCR suspects
  for review, 1.06 review questions per page. Of the OCR check's changes to
  word spacing on Stella and Goede dochter, all are right but `besefeen`;
  Goede dochter's `naaije` and `zeize` are the layer's own, left unfixed.
- 2026-10-07: Line-role classifier with the two CPNB books added (eleven
  books, leave one out): role errors `roles.py` 224, trees alone 279, trees with
  clef's answer 272. The trees win on the Dutch books, most on those no rule
  was written for (Monterosso 33 → 6, headings 3/19 → 18/19; Grand Hotel
  Europa 33 → 21, headings 17/17; Villa Toscane 20 → 0; De eerlijke vinder
  9 → 4) and lose on the English picture books (Dolittle 89 → 162–197, Lady
  into Fox 8 → 12–41). Unstable: Dolittle went 83 → 162 when two books joined
  the training set. Not in the pipeline yet; regularise first.
- 2026-10-07: *Reis om mijn schedel* (Karinthy, transl. Frans van Nes), from
  Stella's publisher Van Gennep (2014), with Van Gennep's EPUB of the same
  printing. Measured against Stella: the same leading (15.0 pt), furniture
  (no running heads, folio centred at the foot) and, by eye, typeface; Stella's
  type ~6% larger on a narrower measure (258 against 278 pt, 54 against 60
  characters a line), indent 10.8 against 13.5 pt. The best stand-in for
  measuring Stella. Text layer alone: CER 0.72%, WER 0.59%, paragraph F1
  0.853, italics 0.904 / 0.872. Its footnotes are left out of the reference
  until the pipeline places footnotes.
- 2026-10-07: Sense and Sensibility (Tauchnitz 1864) retired, by the user's
  decision: no reference of the same edition, so its differences are mostly
  edition noise, and it would put bad labels into the training set. Its scan
  and reference moved to `work/retired/`; the manifest and text leave git.
- 2026-10-07: The Teirlinck bench (*Het ivoren aapje*, 1909, pre-reform
  spelling) no longer chooses OCR models, by the user's decision: every target
  book is in modern spelling. OCR models are re-benched on modern Dutch line
  crops of Goede dochter, the two Boekenweek books and Reis om mijn schedel
  (`experiments/bench_line_readings.py`). The Teirlinck scores in the Models
  table stay as history only.
- 2026-10-07: *The Thief-Taker's Apprentice* (Deas, Gollancz 2010), the first
  modern English scan, with Gollancz's eBook of the same edition: English is a
  real target after Stella. Its PDF is an older IA kind (300 ppi, LuraDocument,
  InvisibleOCR font), which `pdf.py` reads. Text layer alone: CER 0.82%, WER
  0.77%, paragraph F1 0.877, italics 0.946 / 0.897, headings 0/90. The layer
  drops apostrophes in some contractions and splits the word (`didn t`, `I
  m`, `priest s`). The tall box of each chapter's large first letter merges the
  two printed lines beside it into one visual line (text order stays right).
- 2026-10-07: Reis om mijn schedel, Stella's stand-in, through the whole
  pipeline: CER 0.72% → 0.51%, WER 0.59% → 0.44%, paragraph F1 0.853 → 0.890,
  headings 0/27 → 24/27 (+3), italics 0.914 / 0.878. For a reviewer: 1.70
  wrong words/page, 1.57 questions/page, 1.33 left unasked; only 53 of 340
  OCR-doubt questions sit on an error. Unasked by kind: footnote text (left out
  of the reference) 194, then quotes 44 (a lost opening ‘). A seam: `uur 's`
  comes out `uur's` (the space before Dutch 's is removed). OCR bench, 6,697
  body lines, typesetting folded: text layer 0.15%, glm-ocr 0.18% (drops
  diaereses, `e` for `ë` 30×), tesseract 0.21%: the same order as Goede dochter.
- 2026-10-07: The space before Dutch `’s` ("uur ’s avonds"). glm-ocr reads
  it tight ("uur’s"), and both judges agreed on 6 of 7 such suspects on Reis,
  all wrong (4 applied). A reading that only lacks the space before an
  apostrophe is no longer a difference; the layer joining them ("ik's") still
  is, and a split at an apostrophe is a word change, not typography. Reis:
  suspects 902 → 895, fixed 306 → 301, review 459 → 458, CER 0.51% → 0.50%.
  No other golden book had such a suspect.
- 2026-10-07: Quote balance as a question source (`quotes.py`). Reis left 42
  quote errors unasked, nearly all a lost opening ‘ or closing ’ in dialogue.
  A paragraph whose quotes don't pair up is now flagged where the mark is
  missing. Reis: questions 1.57 → 1.67/page, unasked wrong words 1.33 → 1.17
  per page, unasked quote errors 42 → 18; 25 of 32 quote questions sit on an
  error (OCR-doubt questions: 52 of 334). Goede dochter pp. 9–64: unasked 0.33
  → 0.27/page, within noise; 2 of 3 on an error. Most of Reis's remaining
  unasked words are its footnotes (194), which the reference leaves out.
- 2026-10-07: tesseract's dictionary as a word list (`lexicon.py`), as a vote
  in the OCR check. Where it knows the words of only one reading it is nearly
  always right on Goede dochter (`hygiëne`, `Iemand`; even against both judges
  on `binnengedrongen`), but not on word breaks (Dutch compounds it lacks split
  into words it has: `martel kamers`), stress accents (`míj`), tiny words
  (`Si` for `Sjjj`), or vowelless entries (`rjg`, `Sh!`); those get no verdict.
  Applied with one judge agreeing: questions down on every book (Reis 458 →
  443, Goede dochter 139 → 134), but held out it added ~2 unasked wrong words
  each on Grand Hotel Europa (−9 questions) and De tuin (−4). Applied only when
  both judges agree, and vetoing their unanimous pick: no measurable change on
  four books. So it decides nothing; its pick is recorded and shown to the
  reviewer, and kept as a feature for learned trust.
- 2026-10-07: Footnotes kept apart from the score. A publisher's EPUB with
  footnote paragraphs names their classes (`note_classes`); `golden derive`
  writes them to `notes.txt`, and the text's links to them ("[*]") read as
  printed ("*"). `eval` and `quality` drop the output's words from text-layer
  lines that print a note (matched by words, not by position). Reis, Stella's
  stand-in, was mostly footnote noise: CER 0.50% → 0.12%, wrong words 1.65 →
  0.73/page, left unasked 1.17 → 0.25/page (at 1.67 questions/page). What it
  leaves unasked now: punctuation 19, quotes 18, letters 12.
- 2026-10-07: Learned trust for the OCR check, probed
  (`experiments/ocr_trust_data.py`, `train_ocr_trust.py`). Each suspect's
  versions labelled from `golden.align`'s printed truth (quote style, dash
  kind, ellipses and spaced quotes folded); features: each judge's pick and
  confidence (now on `Suspect.confidence`), which second readings support the
  version, the word list, the kind of difference. Leaving one book out, at the
  rule's own number of questions, silent errors: rule 57 → logistic 31 →
  shallow trees 15 over seven books (held out: De tuin 15 → 4, Grand Hotel
  Europa 1 → 0); with one more training book left out the trees stay at or
  under the rule (Dolittle 4–11 against 14). A 99%-precision threshold alone
  asks too much (logistic never reaches it); rank by uncertainty to a budget
  instead. Lady into Fox's labels are noisy (rule 70 silent of 149; Gutenberg
  differs from the print in typography), so its score says little.
- 2026-10-07: Learned trust in the pipeline behind `ROBO_OCR_TRUST=1` (budget
  `ROBO_OCR_QUESTIONS`, default 1 per page), scored with `quality`, each book's
  model trained without it. Reis: wrong words before review 0.73 → 0.58/page,
  questions 1.67 → 1.12/page, unasked with every question asked 0.25 → 0.22.
  Goede dochter pp. 9–64: wrong words 1.18 → 1.00, questions 2.24 → 1.20,
  unasked 0.27 → 0.45 (half the questions; at 1 question/page 0.71 → 0.47);
  inside the bootstrap intervals. Not yet the default: score the held-out books
  with it first.
- 2026-10-07: Learned trust held out (model trained on the tuning books only):
  De tuin wrong words 5.38 → 3.07/page, questions 3.43 → 1.57, unasked 1.38 →
  1.43; Grand Hotel Europa 7.77 → 7.57, questions 2.53 → 2.03, unasked 0.77 →
  0.77; Lady into Fox 3.34 → 3.29, questions 1.59 → 1.99, unasked 2.34 → 1.75.
  It is now the default; the fixed rule (SURE/SURE_ALONE) remains as the
  fallback.
- 2026-10-07: Dash style is a book-wide decision (from the user's review of
  Stella: dash questions came one line at a time, which would mix styles). OCR
  layers write every dash as an em dash and space it at random, so the style is
  measured on the scan: on eleven scans the kind matches the reference (Dutch
  books en, ~1.1–1.3 letters long; Crime, Lady into Fox, Dolittle em, ~2.0–2.2),
  and the gaps against the book's word gaps give spacing (Crime 0.07 letters:
  glued; Stella 0.45 against 0.70: thin, as the user saw; the Dutch EPUBs' spaced
  en dashes 0.5–1.0 against 0.6–1.0: word). Every output dash takes the style;
  dash-only differences are no OCR doubts. Quote style may deserve the same.
- 2026-10-07: OCR doubts are asked per place, not per line (from the user's
  review of Stella: two wrong places in one line, each fixed by a different
  reading, left no right option and made the user type, which added an error).
  Each undecided suspect is its own question, cropped to its words, its readings
  the line with only that place changed; answers change only their span, and the
  check's settled fixes elsewhere in the line still apply. Where readings differ
  only in a line-end hyphen, the place is read across the break by the word
  list, the text judge and the human ("dankbaar" / "dank baar"). Stella: 67
  per-place doubts (1/page), 74 of its 81 questions already covered by the
  user's earlier whole-line answers.
- 2026-10-07: Proofreading a human's answers (Stella, 67 answered regions; truth
  proofread against the scan by the agent: 5 typing slips, a speck kept as a
  period, plus the layer's "gedruktom"; `experiments/probe_proofread.py`).
  gemma4 asked yes/no ("does this text match the crop?") is useless: AUC 0.47
  with the image, 0.60 on text alone; it says "no" to 53/60 right answers.
  Asked to transcribe the crop (tight to the line's words) and compared with
  the answer in code, it catches 6/7 with 5/60 alarms, one of them a real
  error both the human and the agent had missed (p. 43 "waarbijj"). Asked
  then, text only, to pick between its reading and the answer
  (`probe_proofread_judge.py`), it is confident on letters (waarbijj 0.98,
  keeps "ís") and undecided on punctuation (~0.5). Transcribe-and-compare is
  the shape to use; a straight quote in a curly-quoted book's answer is a slip
  no model is needed for.
- 2026-10-07: Line-role classifier regularised and given the layout model's
  region classes as features (`train_line_roles.py`, `tune_line_roles.py`).
  Twelve books, leave one out: `roles.py` 256 role errors; trees (balanced
  weights, leaves ≥ 20, depth 4, l2 1.0) 142 without layout features, 111 with
  (Dolittle 89 → 55, Reis 32 → 5, Monterosso 33 → 6; held out Grand Hotel
  Europa 33 → 6, Villa Toscane 20 → 2). Unbounded depth and larger leaves are
  worse (172–260). Not stable enough to wire in: leaving one more training
  book out sends Lady into Fox 9 → up to 71 (rules: 8) and Crime 5 → 20 (rules:
  4); only three English books train it. Next: more English training data
  (The Thief-Taker's Apprentice), then wire in behind a switch.
- 2026-10-07: qwen3.8:27b-nvfp4 on the Stella proofreading test: reading the
  crop and comparing in code caught all of the human's slips and the agent's
  misses (9/9; one more real error found: p. 42's lost opening ‘ in "‘je
  trilt"), with 3 false alarms in 58, its own misreadings (a speck as a
  period, "trofik", "beseffen"). Its text-only judgement between its reading
  and the answer rejects its own misreadings confidently (0.07–0.21) and, with
  thinking on (a free reply read by winnow), prefers the right punctuation
  (0.72–0.88). The candidate for a third reading in the OCR check and for
  proofreading answers; bench its line readings next.
- 2026-10-07: A line-end hyphen is kept when the book itself prints the word
  hyphenated inside lines more often than whole (`reflow.spellings`; words cut
  by a line break don't count). The Thief-Taker's "thief-|taker" had become
  "thieftaker" 12×. WER, spellings off → on: Thief-Taker 0.29% → 0.22%, Crime
  0.33% → 0.29%, Dolittle 1.73% → 1.64%, held-out De tuin 0.17% → 0.15%; the
  other seven books unchanged. Thief-Taker's first full build: CER 0.82%
  (layer) → 0.34%, paragraph F1 0.923, headings 43/90, italics 0.993/0.921.
  Note for comparisons: Villa Toscane is scored with `--chapters 1-12`, and
  with learned trust Dolittle's CER rose 1.72% → 1.91% because agreed dash
  fixes now sit in the question budget instead of being applied.
- 2026-10-07: qwen3.8 line readings benched on Goede dochter pp. 9–64 (1,622 body
  lines, the OCR check's crops, `bench_line_readings.py --extra`): CER 0.17%
  folded, 1,504 lines exact, against the text layer 0.20% / 1,460, glm-ocr
  0.24% / 1,155, tesseract 0.29% / 1,404; it keeps quotes the others drop
  (missing ' 9× against glm-ocr 31×, tesseract 80×). Right where the layer is
  wrong on 119 lines (glm-ocr 114), wrong where the layer is right on 76
  (glm-ocr 87). Its misreadings are plausible words (`doodgaan→doorgaan`,
  `ontspanden→ontspannen`, `wachtte→wartete`), which a word list can't catch:
  a third reading for the judges, not a replacement. ~1 s per line under load.
- 2026-10-07: Four bugs from an outside review (Gemini), each
  reproduced, fixed and tested. `disagreements.patch` finds every verdict in the
  unpatched reference before applying any (a verdict within another's six-word
  context was silently skipped). `ocrcheck.apply` keys fixes on the line's
  index, not its text (identical lines on a page took each other's fixes:
  `zon` → `zo'nn`). `corrections.apply` keeps `Line.source` on a retyped line.
  Lines are grouped by each text-layer line's span without a large initial it
  opens with (first glyph > 1.6× the rest), so a drop cap no longer pulls the
  next printed line into its own: Thief-Taker's chapter openings (25 pages) and
  Lady into Fox p13 now split into their printed lines; the other eleven books
  read identical lines (`experiments/probe_line_grouping_diff.py`). A drop cap
  that is a fragment of its own still joins the line below; only Thief-Taker
  p70 has one (`experiments/probe_tall_fragments.py`).
- 2026-10-07: Quote questions offer a proposed reading (the user's idea: tell the
  model the book's style). qwen3.8 reads each quote-flagged line, told how the book
  sets dialogue, nested quotes, ellipses and dashes; only its quote marks and the
  punctuation beside them are taken onto the OCR-checked line (its letters slip:
  `krimpachtig`, `pijsnelle`, a Cyrillic word), never a changed word break except
  a contraction the layer split (`I m`). Right where the line is wrong / wrong where
  it is right: Reis 51/0 (of 120 questions), Vals alarm pp. 11–60 29/0 (of 60),
  Thief-Taker 76/3 (of 287; `‘’Scuse` loses its elision), held-out De tuin pp.
  11–52 42/1 (of 73). Short lines are read too: `‘Nee.` is where a closing quote is
  lost most. On Reis, without the style sentence: 55/4. Qwen as a vote for the
  trust model (plain prompt, Goede dochter by page folds) showed no gain; rerun it
  with the style prompt before ruling it out.
- 2026-10-07: The OCR check's crop judge (clef:27b) is told the book's typesetting
  and sees its options as `exactly ⟨…⟩` instead of `exactly “…”`, which looked like
  the quote marks the versions differ in. On 200 labelled suspects each
  (`experiments/probe_judge_prompts.py`), right picks: Goede dochter 177 → 182
  (⟨ ⟩ alone) → 183 (with the style), typography 92 → 98 of 102; Vals alarm 162 →
  168 → 169, typography 103 → 109 of 139. The text judge (winnow) told the style:
  Goede dochter 91 → 84, Vals alarm 120 → 129, so it keeps its prompt. clef's new
  answers are trust features: retrain the trust model on re-judged suspects.
- 2026-10-07: An outside review (Fable) found that learned trust had been off
  without notice: the model version was bumped for a new feature, the saved model
  no longer loaded, and the pipeline fell back to the fixed rule with one line on
  stderr. A missing or mismatched trust model now stops the build, and
  eval-history records the decider, the settings and the model versions, since
  runs at one commit had scored differently (Crime 0.634–0.713% CER) with no
  record of why. The OCR check reads each line a third time with qwen3.8 told
  the book's style; the trust model is being retrained on suspects rebuilt with
  it, and the reading stays only if that beats the noise floor. From now on the
  four "held-out" books count as a validation set: earlier choices (the word-list
  vote, the style-group question) were made on their scores.
- 2026-10-08: The OCR check reads short lines too (the 12-character gate is gone):
  on Goede dochter pp. 9–64 that adds 18 suspects and about three real layer errors,
  two of them lost closing quotes; glm-ocr alone raised eight, all of them noise.
  The bench after the retrain decides whether it stays (docs/design.md).
- 2026-10-08: Two new golden pairs, checked without models by
  `experiments/probe_candidate.py` (the text layer against the EPUB: both agree at
  the layer's own error rate, every frequent difference an OCR slip). **Het geluid
  van bananen** (Van Gennep 2013, Stella's publisher and scan format) is the **test
  set**: nothing is chosen on it, no model trains on it, and `eval`, `quality`,
  `golden review` and `bench test` refuse it without `--score-test`; it is scored
  once, at the end. **Afscheid van verspilde tijd** (De Rode Kamer 2011, another
  typesetter) joins `bench tuning` and the trust data before the baseline bench, so
  the baseline, the retrain and the verdict include it. Its EPUB sets dashes as
  spaced hyphens: `hyphen_dash` in the manifest sets them as the print's en dash
  when deriving. A heading without a letter or digit (`******`) is an ornament,
  not a chapter; a note marker `[1.] – [terug]` is stripped like `* – [terug]`.
- 2026-10-08: Retiring a golden book is everyone's job (AGENTS.md): whoever sees a
  reference measuring the edition rather than the pipeline says so and proposes
  retiring it. The signals that need no verdicts are the layer's CER against the
  reference and the share of body lines the aligner can't place; the bench is to
  print both per book (checklist).
- 2026-10-08: **Metro 2033** (Gollancz 2010, transl. Randall; IA Scribe scan of the
  fifth impression against Gollancz's eBook) joins `bench tuning` as the second
  modern English scan, sliced to chapters 1–5 (pages 7–111): the text layer agrees
  with the EPUB at 0.32% CER, every frequent difference a convention (spaced
  hyphens for dashes, spaced ellipses, single quotes) or an OCR slip. The line-role
  classifier wanted more English books.
- 2026-10-08: A golden pair's known deviations are tracked in three places and no
  other:
  the manifest (`hyphen_dash`, undone by derive and listed in PROVENANCE.md), the
  scorer's fold (quote and dash glyphs, an ellipsis glyph or spaced dots, joiners),
  and verdicts. The fold now covers spaced dots (". . .", which Gollancz prints and
  the layer reads both ways) and is counted per kind on each side: `eval` prints
  what it forgave, so a convention gap skews a score visibly, not silently. The
  ellipsis's spacing itself belongs with the dash style in `typography.py`, measured
  on the page like the dashes; a checklist step.
- 2026-10-08: **De cipier** (Van Holkema & Warendorf 2013, transl. Heijman; IA
  Scribe scan of the first printing against the publisher's e-book of the same
  printing and typesetter) joins `bench tuning`, sliced to the foreword and
  chapters 1–3 (pages 9–92). The cleanest pair yet: 0.21% layer CER and no known
  deviation, every difference an OCR slip the layer makes on Dutch (ë read as é,
  stress accents dropped, small capitals read as lower case, numerals missing).
- 2026-10-08: `docs/golden-books.md` (from `experiments/golden_overview.py`, no
  models) lists every golden book with its set, scored pages, estimated cold cost
  and the text layer against the reference, so the cost and the fitness of a pair
  are read from one table. The cost driver is the whole-book bench specs
  (Thief-Taker 282, Reis 245, Dolittle 180, Afscheid 116 pages, the test book 315),
  not deviations: no pair has both many deviations and many pages.
- 2026-10-08: Lady into Fox retired from validation to reserve: out of `bench
  validation` and the trust data, still in every `HELD_OUT` list so nothing trains on
  it. Its reference differs from its print in typography, enough that winnow beat
  clef there on labels alone (docs/design.md).
- 2026-10-08: The bench's whole-book specs sliced at chapter boundaries, the user
  being short of processor time: Thief-Taker pages 11–84 (Part One, chapters 1–10),
  Reis 11–110 (Voorwoord, chapters 1–10; its trust data too, not yet rebuilt),
  Dolittle 23–88 (chapters 1–7, twenty pages with a plate or a drawn initial),
  Afscheid 9–70 (chapters 1–11), and the test book 9–101 (Boek 3, chapters 1–9).
  Tuning drops from 1,212 to 675 scanned pages, about 12 h cold instead of 22;
  the test from 315 to 93. Trust data already built on whole books is kept.
- 2026-10-08: **Artemis** (Del Rey UK paperback 2018 against Penguin's 2026 e-book of
  the same UK text) joins `bench tuning` as the third modern English scan, sliced to
  chapters 1–3 (pages 13–80). The layer agrees at 0.44% CER, nearly all of it the
  sans-serif "I" read as a bar and dropped apostrophes; one known deviation, a name
  the reissue changed (Vetrov), goes to verdicts. Its chapter numbers are images in
  the EPUB: `image_heading` in the manifest takes the heading from the image's alt
  text, so the reference has the "2" the print draws in a circle.
- 2026-10-08: **11/22/63** (Scribner first edition, first printing, against Scribner's
  eBook of the same edition) joins `bench tuning` as the fourth modern English scan,
  sliced to the prologue and chapters 1–3 (pages 15–94). The layer agrees at 0.24–0.59%
  CER per band and every frequent difference is the layer's (the capital I read five
  ways, "in a" merged); no known deviation. Its 345 numbered sections, each a small
  centred numeral and a heading in the reference, make it the heading test.
- 2026-10-08: The retirement signals into the bench (`golden/signals.py`): each book's
  text layer against its reference, CER and unplaced share over the lines the build
  calls body, recorded in the run and a book past 3× the set's median CER or 5%
  unplaced named as a suspect pair. Over all lines, as `golden_overview.py` counts,
  page furniture is unplaced by design and seven books pass 5% (Afscheid 11%).
- 2026-10-08: The trust labeller compares a version to the truth through
  `evaluate.normalise` plus reflow's space-before-punctuation rule, not a fold of its
  own. Its own fold lacked spaced dots and spaced punctuation, so on the 1920s books
  the faithful `you. . . .` and `listen :` were labelled wrong (Crime 20 labels change,
  Dolittle 37, mostly to unsettled: versions that differ only in what the output sets
  anyway carry no label).
- 2026-10-08: Grand Hotel Europa retired from validation to reserve, De eerlijke vinder
  validation in its place (whole, pp. 12–95). Grand Hotel's EPUB was made from the 1st
  printing, the scan is the 11th, and 9 of its slice's 16 reference headings have no
  line on the scan; the build stays at 1.9% CER where the layer alone is 0.4%. De
  eerlijke vinder is CPNB's EPUB of its own edition in Stella's scan format (layer
  0.32%, 0.3% unplaced). It leaves the line-role probes' training set (held out there
  too) and gets trust data as a held-out book. Crime and Dolittle stay: Crime's
  reference was made from its scan and the build reaches 0.34%; Dolittle is the only
  book with plates, captions and drawn initials, and its high CER is partly its
  reference leaving captions out, which is ours to fix.
- 2026-10-08: **You're Never Weird on the Internet** (Day, Touchstone first hardcover
  edition, fifth printing, against the edition's ebook) for validation, pages 13–94
  (sections 1–16): validation had no English book since Lady into Fox left, and this
  one was never consulted. A later printing than its ebook, like Metro, accepted on the
  layer: 0.46% CER in every 20-page band and every frequent difference the layer's own,
  unlike Grand Hotel Europa. Pictures hold their captions and other text, which the
  reference has no words for, so it also tests that picture text stays out of the text.
- 2026-10-08: Hosted models allowed where the user chooses them for speed (the user's
  change to "local only"), through OpenRouter pinned to one provider and precision,
  no fallback, providers that keep prompts refused. Qwen3.8 27B on Goede dochter pp.
  9–20 (326 body lines) against the aligned truth: local nvfp4 0.10% CER, 313 exact, 0
  lines with quote marks wrong; Darkbloom fp4 0.15%, 305, 5 (worse than the layer's
  0.13% and 1); DeepInfra bf16 0.11%, 310, 0, the same reading as local on 94.5% of
  lines, at ~10 lines a second against the Mac's 0.7. fp4 there is not our nvfp4.
- 2026-10-08: OpenRouter only when the user explicitly allows or asks for it, per use:
  it costs money and sends the scans out. No agent starts a hosted run on its own.
- 2026-10-08: Where a cold run's time goes, from the stage caches' times: qwen3.8's
  reading of every line 70–75% (Dolittle 75 of 98 min, De tuin 36 of 51), clef's
  judging 20–25%, the rest ~15–20 min per 100 pages. gemma4:latest (8B, nvfp4) as the
  line reader, told the book's style, on Goede dochter pp. 9–20: 0.31 s a line against
  ~1.4, but CER 0.21% (Qwen 0.10%, layer 0.13%) and quote marks wrong on 4 lines
  against 0, so unfit. The newest open models (DeepSeek V4.1 Flash, GLM-5.3 Flash,
  MiMo V2.6, Step 3.7 Flash) are 200–760B and don't fit in 64 GB; the mixture-of-experts
  models that do, qwen3.6:35b-a3b and gemma4:26b (3–4B active), are being tried.
- 2026-10-08: A reader of the finished text planned (checklist: errors no question asks about), on the user's point
  that nothing reads the output itself: every check starts where OCR readings disagree,
  so shared misreadings and reflow faults go unseen. Guarded against editing the author:
  it only asks, with closed options and no replacement text; it is told the text is a
  transcription; its silence on deliberate oddities is measured on a counterexample set
  first; `bench` scores it as a question source and reports the share of flags on text
  that already matches the reference.
- 2026-10-08: qwen3.6:35b-a3b-nvfp4 (MoE, 3B active) as the line reader on Goede
  dochter pp. 9–20, the pipeline's prompt: 0.37 s a line, but it takes the style
  sentence ("dialogue in curly quotes ‘ ’") as an order and wraps narration in quotes
  (‘Twintig meter. Vijftien. Tien.’): quote marks wrong on 94 of 324 lines, CER 0.67%.
  Out: an invented mark is the worst failure for this job.
- 2026-10-08: A candidate reader is judged by what it adds, not by its own score: its
  unique catches (right where every current reading is wrong) against its noise (wrong
  where the layer is right). On Goede dochter pp. 9–20 only 1 of 324 body lines has no
  current reading exact (layer, glm-ocr, tesseract, Qwen3.8), so the remaining errors
  there come from choosing among readings; the question moves to a harder book (Metro).
- 2026-10-08: Metro pp. 7–30 (954 body lines): only 1 has no current reading exact
  (layer 902, glm-ocr 821, tesseract 872, Qwen3.8 934), so on English too the readings
  cover nearly every line and the errors left are in choosing. gemma4:latest there:
  CER 22.6%, wrong on 288 lines the layer has right, and it writes text the line
  doesn't hold ("discuss the best place to shoot him. I looked at his boss, and it was
  as if…" before the printed line): a model that invents is unfit to transcribe.
- 2026-10-08: A reader of the finished text, first probe: gemma4:latest with the user's
  prompt (technical flaws only, old spelling allowed, no prose review) on Goede
  dochter's first 200 output paragraphs. 56 flags: about 4 real errors pinpointed that
  the OCR check let through (`we-bril` for wc-bril, `aaN-knop`, `Kedsgympen`, a lost
  closing quote), 46 on text that matches the reference, mostly whole correct sentences
  called "punctuation", and 3 quoting text that isn't there, caught by requiring the
  quote verbatim. The task finds what nothing else does; an 8B model's precision (~1 in
  14) would cost more in questions and slips than it catches.
- 2026-10-08: gemma4:26b-nvfp4 (MoE, 4B active) as the line reader: on Goede dochter pp.
  9–20 the best reading yet (CER 0.07% against Qwen3.8's 0.10%, 314 exact against 311,
  3.5× faster, one invented opening quote); on Metro pp. 7–30 CER 23%: on 297 lines the
  layer has right it reads another line than the cropped one or adds invented text. Out,
  and the reason a candidate is confirmed on a second book before any switch.
- 2026-10-08: `ROBO_READ_VIA`: a hosted build reads in place of the local read model,
  its readings cached under the local model's name (so the bench and later runs reuse
  them) and each line listed with the build that read it. The user's reasoning: hosted
  bf16 reads like local nvfp4 (Goede dochter: CER 0.11% against 0.10%, no quote marks
  wrong on either), so keeping them apart only costs re-reading; the marks keep the
  provenance a plain rename would lose.
- 2026-10-08: Hosted Qwen3.8 27B (DeepInfra bf16) on Metro pp. 7–30, English: the same
  reading as local on 929 of 958 lines, 935 exact against local's 934, 0.10 s a line
  (14× faster); but it reads beyond or beside its crop on 7 lines (whole neighbouring
  clauses) where local does on 1, which lifts its CER to 0.64% against 0.16%. gemma4:26b
  does so on 254. Metro's crops hold parts of the neighbouring lines (tight leading), so
  every reader is tempted; such a reading only adds a suspect the judges reject.
- 2026-10-08: Line crops stop at a neighbouring line's box (`ocrcheck.crop_span`, half a
  point of slack); only a line whose crop changes gets a new cache key and is read again.
  The 3 pt margin above and below reached into the next line wherever the layer's boxes
  are as tall as the line pitch: 97% of Metro's crops, 91% of Dolittle's, 87% of Crime's,
  half of De tuin's, 15% of Goede dochter's. glm-ocr on Metro pp. 7–30, the 738 changed
  crops: CER 1.87% → 0.29%, exact 630 → 639. Found because hosted Qwen and Gemma read
  whole clauses of the neighbouring line.
- 2026-10-08: Hosted Qwen3.8 bf16 on Metro pp. 7–30's 737 changed crops: CER 0.04%,
  against local Qwen's 0.20% on the old crops, 722 exact on both, better and worse on 7
  lines each (small: a stray `*`, `Moskvín`, a closing quote) and no neighbouring clause
  read. With the builds equal on Goede dochter and on Metro's old crops, the gain is the
  crop's.
- 2026-10-08: Local (nvfp4) and hosted (DeepInfra bf16) Qwen3.8 27B are interchangeable
  on line crops, by criteria fixed before the result, on Metro pp. 7–30's 738 new crops:
  720 and 722 exact, quote marks wrong on 1 and 2 lines, 1 line each read beyond its
  crop, the same reading on 97.6%. Hosted readings cached under the local name
  (`ROBO_READ_VIA`, each marked) are therefore trained and benched alongside local ones.
  The crop fix itself is neutral for local Qwen there (722 → 720 exact; CER 0.20% →
  0.18%); its gain is glm-ocr's, and hosted Qwen's habit of reading the next line.
- 2026-10-08: `train_ocr_trust.py` trains only on data that exists and holds every
  current reading, and its leave-one-out analysis no longer trains on validation books
  (it did, though `--save` never has: the numbers changes were chosen on had seen De
  tuin's and Grand Hotel's labels). Loading a missing book used to start its cold build;
  `--save` now refuses while tuning data is missing (`--partial` to override).
- 2026-10-08: Review highlights never cover the print: a faint tint behind the lines in
  question, a soft outline around a region, a doubt's place underlined beneath its line;
  `h` hides them. The user found the orange box over the very quote marks they were asked
  about. The slip-rate review waits for trust: on the fixed rule it asked 215 questions
  on Goede dochter, nearly all settled by the word list and clef, the wrong mix to
  measure a reviewer on.
- 2026-10-08: Line-end hyphens decided by evidence, not by rule alone (`reflow.join`;
  `experiments/probe_hyphen_breaks.py`, six golden slices, 1,574 decidable breaks against
  the reference, no models). The rules were wrong 29 times, 0.02–0.17 words a page, more
  than the OCR check leaves silent at one question a page, and nothing asks about a hyphen.
  The book's own spelling was 12/12 right; the word list, where it knows one form only,
  fixed 7 and broke none the book hadn't settled; a capital after the break was right on
  every true capital and wrong on all 3 words set in capitals; "a hyphen already in the
  word keeps this one" was wrong 8 of 10. Now in that order, the inner-hyphen case kept
  only where the parts beside the break are both words and don't make one. 29 → 15 wrong;
  what is left is mostly English compounds the list lacks (`night-vision`), for a question.
  An outside review (Fable), who also found, on the labelled suspects, that each scan's
  errors are three to five signatures (`|`→`I`, a lost `’`, `é`→`ë`) nearly deterministic
  across books, and that a substitution-pair prior in trust cuts silent errors at one
  question a page from 23 to 11 over nine books, leave-one-out.
- 2026-10-08: Trust gets a prior for the exact substitution a version makes (`trust.pair`,
  model version 3, 23 features; the priors saved with the model). On the labelled
  suspects each scan's errors are three to five signatures, nearly deterministic across
  books (a lost `’` the print 223/234, `|`→`I` 59/59, `é`→`ë` 28/28; glm-ocr dropping a
  `’` wrong 232/235), which the kind features can't tell apart. Leave one book out over
  nine books: silent errors at 0/.25/.5/1 questions a page 153/87/44/23 → 117/50/31/11.
  A pair counts when seen in ≥ 2 training books (Opus's caution: one book's reference
  conventions must not teach the rest) and a training suspect is scored without its own
  label (with it in, 76/48/28 at .25/.5/1: worse than no prior). Its bench step waits for
  the retrain. The saved model stays version 1 until `--save`.
- 2026-10-08: A reviewer's answer is checked before it is saved (`review.doubtful`): a
  line typed for a question with readings must match one of them (quote glyphs and
  spacing aside), and a straight quote in a book set with curly ones is a slip; the page
  says why once and saves on the second Save, logging the warned answer in
  `review/warnings.jsonl`. At the measured slip rate (8 of 68) one question a page costs
  about 0.12 wrong words a page, more than trust leaves silent at that budget; the
  question's own readings give the transcribe-and-compare check (Stella: 9 of 9 slips,
  3 alarms in 58) without a model call. Built before the slip-rate review so that review
  measures both rates.
- 2026-10-08: A training book's substitution priors come from the other training books
  only (`trust.training_matrix`), as a scored book's do. Opus's point: scored with only
  its own label left out, a suspect still saw its book's other suspects, so a signature
  common in that book looked surer in training than on a new book. Leave one book out:
  117/50/31/11 → 110/48/25/10 silent errors at 0/.25/.5/1 questions a page. The two
  hyphen cases the word list can't settle (`make-up`, `night-vision`) are a strict
  xfail test naming the open hyphen step, not an assertion of the wrong output.
- 2026-10-08: Line crops fitted to each line's ink (the user's idea, `experiments/
  ink_crop.py`) tried and not adopted. With no model, the box crop (`crop_span`) holds
  slivers of a neighbour's ink (1–2.5 pt, descender tips) in most crops and cuts 1–2.5 pt
  of its own line's ink in up to 37% (11/22/63); the ink crop takes both to 0–2%. The
  readers read no better: glm-ocr exact lines on Metro pp. 7–30 830 with the box crop
  against 817 with the ink crop, on 11/22/63 pp. 15–40 619 against 621, and Qwen on
  Crime 774 against 752. What hurt the readers was reading the whole next line, which
  the box crop already prevents. The box crop's own re-read on Crime is neutral
  (glm-ocr 758 → 755, Qwen 774 → 770, worse on the models' habits, not the crop).
- 2026-10-08: Hosted clef (OpenRouter `cloudflare/clef`) is not used as the OCR check's
  judge. Measured against local clef:27b (nvfp4) on Goede dochter pp. 9–64's 419 cached
  suspects, the same states, questions and crops, against criteria fixed first (same
  pick on ≥ 97%, no fewer right on the settled ones, median confidence shift under 0.05,
  since trust uses the confidence): PrimeIntellect's endpoint barely reads the image
  (69.9% same pick, 275 of 377 right against 352; it picks a made-up line over the
  printed one), Cloudflare's comes close but fails all three (96.2%, 348 of 377, shift
  0.063, 90th percentile 0.150). `ROBO_JUDGE_VIA` and `ollaya.HostedClient` stay for a
  later build; the decisions API takes the image inside `state`.
- 2026-10-08: The models are named by the role they play: spotter, readers, sorter,
  judges, arbiter (the trust model) and reviewer, in docs/how-it-works.md, the diagram
  and AGENTS.md. The user asked for it as a shared vocabulary: a new model is tried
  for a role and measured against the one playing it.
- 2026-10-08: An image-only PDF is read by tesseract first (`pdf.first_reading`), only when
  the whole PDF has no text, so no searchable scan changes. On Goede dochter pp. 9–64
  with its layer removed: CER 0.35% against the IA layer's 0.20%, unplaced lines 2.4%
  against 2.7%. Ollaya serves only winnow:e4b; a session checks whether Ollama offers it.
- 2026-10-08: PP-DocLayoutV3 as the spotter, scored downstream on Dolittle pp. 23–88 with
  the arbiter and qwen3.8 off in both arms: CER 1.22% → 1.71%, wrong words 2.29 → 3.13 a
  page. It marks body lines near pictures as captions and misses the drawn initials.
  Not adopted; the class mapping is ours, but fitting it until it wins would tune the
  screen to the candidate.
- 2026-10-08: winnow on Ollama, to stop depending on Ollaya. Its Hugging Face GGUF pulls
  into Ollama as a completion model, which `/v1/systemone` refuses; a Modelfile adding
  clef-flash's `CAPABILITY decision` lines makes it answer (`modelfiles/`). Ollama then
  builds its own decision prompt, not winnow's trained one (`native/protocol.h` in
  EldanRing/winnow-inference), and on a test question was far surer (0.97 against
  Ollaya's 0.63 for the same pick). Measured against Ollaya's build on cached suspects
  before any use; if it falls short, the fallback is our own client rendering winnow's
  protocol to `/api/generate` and reading the letter's log-probability.
- 2026-10-08: Ollama 0.40.1. `winnow-ollama:e4b` still lists `decision` and answers on
  `/v1/systemone`. Ollaya no longer serves `laya:multilingual`, so `doctor` now
  smoke-tests the models the pipeline asks (sorter, judge, second judge) through
  `for_model`; the unused `decision_model` setting (`ROBO_DECISION_MODEL`) is gone.
- 2026-10-08: Metro's "word breaks" were its spaced ellipses (`people . . . The`), which
  `reflow.tidy` squashed to `people...`. A book's ellipsis style is now read in the
  layer and set on every ellipsis (`typography.py`, docs/design.md); Crime's reference
  gets back the space its print sets (`ellipsis_space`, re-derived: two paragraphs).
  Bench tuning: 1.53 → 1.00 after review with the arbiter, and the arbiter against the
  fixed rule, both fixed, 1.37 → 1.00 with no veto: tonight's Metro veto was this bug.
  The probe that checked the rule on every book's text layer also counted the ellipses
  in Het geluid van bananen's (the test set) by mistake; nothing was scored, and the
  rule was set before.
- 2026-10-08: **Ollaya uninstalled; Ollama only.** The user removed Ollaya, so the one
  winnow is `winnow-ollama:e4b` on Ollama's `/v1/systemone`, now the default
  `check_model`. The client is `clients/decide.py` (`DecisionClient`), always on Ollama;
  `ollaya_url` and `ROBO_OLLAYA_URL` are gone, and `doctor` checks Ollama alone. The
  model keeps its name because the cached answers are keyed on it. Ollaya's models stay
  in the Models table as history. Because the Ollaya winnow can't answer any more, the
  whole-body style change (a43b008) and the winnow switch are benched together against
  the ellipsis run, not apart.
- 2026-10-08: Every new model gets two questions, by the user's rule: can it replace a model in a role, and could adding it anywhere in the workflow improve the application (AGENTS.md, Model roles).
- 2026-10-09: imajev-4b is the second vision judge to try (`alarm_model`, off by default until the bench says so): on judge set v1 the best all-round alarm on clef (2B and 9B screened too; the 9B is better on Dutch, worse on English). It runs on llama.cpp (`clients/llama.py`) because Ollama's systemone takes no images for GGUF models and the GGUF lacks imajev's trained readout. The arbiter takes a third judge (`trust.MODEL_VERSION` 4, 26 features).
- 2026-10-09: winnow-ollama:e4b is the second judge in the trust data and the arbiter (retrained, 14 books). Over 5,412 settled suspects it is right alone on 67% (clef 90%), and as an alarm clef is wrong on 4% where it agrees and 21% where it disagrees; unlike Ollaya's build it lifts on Goede dochter too. `bench tuning` against the ellipsis run, the book-wide style change measured with it: no change (after review 1.00 → 1.02, no veto). `bench validation`'s first run is the baseline.
- 2026-10-09: OpenRouter requests get a 120 s deadline on the whole request, retried: DeepInfra's Qwen went down (0% uptime on OpenRouter while its own status page said operational) and OpenRouter's keep-alive bytes kept each request open past httpx's read timeout, hanging a run for half an hour.
- 2026-10-09: imajev-4b stays off as the third judge. With its votes in the trust data and the arbiter retrained, `bench tuning` 1.02 → 1.01 [−0.04, −0.00] and `bench validation` 0.81 → 0.80 [−0.05, +0.02]: no change, so not worth llama-server beside every build. `train_ocr_trust.py` now drops the votes of judges the settings don't name, so the data can keep them.
- 2026-10-09: Washed-out scan pages are found by their ink contrast (`faint.py`) and flagged whole (`washed-out`): 31 pages in Afscheid, 11/22/63 and Grand Hotel Europa, all under 10 grey levels against 48 and up for printed pages; `bench tuning` better (after review 1.02 → 1.00 [−0.04, −0.01]), validation unchanged. The word list couldn't tell them: their scraps are mostly words.
- 2026-10-09: The body range stays in book.toml: on 252 pages round the ends of 18 books' ranges imajev-4b sorted 227 and clef-flash 231, both missing the same prefaces, forewords and blank edge pages.
- 2026-10-09: imajev-4b tells which way up a plate is (10/10 on Dolittle's plates at four turns, decisively), but the caption rule already turns every captioned plate; it waits for a book with an uncaptioned or upside-down plate.
- 2026-10-09: Qwen's third reading stays, now on the bench: without it (its own trust data, `ROBO_TRUST_DATA`, and arbiter, `ROBO_OCR_TRUST_MODEL`) bench tuning is worse, 1.00 → 1.33 after review [+0.07, +0.75], validation 0.81 → 1.01 [+0.12, +0.27]. Short lines stay with it, unablated.
- 2026-10-09: clef's cached answers stand for fresh ones: re-asking judge set v1's 518 questions flipped 2, both at confidence ≤ 0.1, and moved the median confidence by 0.001.
- 2026-10-09: Deleted from Ollama, at the user's go: gemma4:26b-nvfp4 and qwen3.6:35b-a3b-nvfp4 (failed MoE candidates), imajev:2b and the 2B and 9B imajev GGUFs. The 4B stays.
- 2026-10-09: A strict review of the whole codebase (six reviewers, every finding checked before fixing). Scoring changed with it, so earlier bench runs aren't comparable with later ones: eval, golden review and the footnote removal use the pages with missing lines added; `patch` leaves paragraphs without a verdict as they were (it rewrote spaced dots and shifted 567 italic words on Metro and 11/22/63); soft hyphens and „ are folded; a missing-text question can catch an error; auto-resolution uses the book's own word list and the reference's words (47 of ~880 disagreements move to the review, 7 back). The bench's baseline is rerun on the code before the review with only these fixes, so the pipeline's fixes are measured on their own. The veto is kept as the code has it (mean worse by ≥ 0.05 a page, 99% interval above zero); the docs said it loosely.
- 2026-10-09: A heading's number is part of its identity. `title_key` stripped any trailing number as a folio, so the repeated-title rule demoted "CHAPTER 2", "CHAPTER 3" … after the first (11/22/63 lost all but CHAPTER 1, Metro four of five); only the page's own printed number (one misread digit allowed) is stripped now, and the printed-page-number rule leaves a labelled heading alone. Repeats compare letters and digits, so a running head like "11/22/63" is furniture. A fragment much taller than a line (an initial, a speck) no longer stretches a line's span over the next printed line (Thief-Taker pp. 46, 70; `TEXT_LAYER_VERSION` 6), and the page's last run of body lines gets the word list when de-hyphenating.
- 2026-10-09: Qwen's read prompt stays as it is. Five variants on the reader set (330 hard lines, 220 control; hosted Qwen, DeepInfra bf16, `experiments/probe_read_prompt.py`): telling it to copy words exactly, giving it the lines above and below, both, or the layer's own reading. Against the prompt in use (302/330 hard right), each was better on as many lines as it was worse (exact 2/5, context 5/5, both 4/3; the layer's reading 10/13, the worst: it anchors on the layer). Its remaining misreads are visual, not instructions it ignores.
- 2026-10-09: The crop doesn't make Qwen read better either: rendered at 450 or 600 dpi, upscaled 2×, contrast-stretched or given a margin, each was better on as many reader-set lines as it was worse (sharpened: worse, 2 against 7). But whether its reading *changes* with the crop is a strong signal. On lines where glm-ocr disagrees with Qwen (the arbiter's suspects), Qwen is wrong on 19 of 20 where its readings across variants differ and on 4 of 30 where they agree; with one second reading at 450 dpi, 11 of 12 against 12 of 38. Next: a second Qwen reading of suspect lines only, its agreement as a trust feature, measured by the bench.
- 2026-10-09: The review's fixes, measured: trust data rebuilt (Qwen via hosted; 11/22/63 pp. 15–94 fully cold), arbiter retrained on 4,116 suspects. `bench tuning` against the baseline (the code before the review plus only the measuring fixes): **better**, after review 1.00 → 0.96 [−0.06, −0.01], no veto; 11/22/63 0.99 → 0.82 (CHAPTER 2 and 3 headings again, three of four "11/22/63" running heads no longer headings), Reis 0.32 → 0.26, Dolittle 1.07 → 0.98, Thief-Taker's wrong words 1.23 → 0.84 (merged lines split). `bench validation` 0.81 → 0.75 [−0.19, +0.01], no change by the test; You're Never Weird 1.07 → 0.84. Lost opening quotes as suspects added 4–17% suspects a book.
- 2026-10-09: A bare number that isn't the page's folio is a section heading anywhere above the text's end, where the book's folios are known and it is centred (11/22/63 numbers its 345 sections so, below the running head or between paragraphs); only the folio's own number, one digit misread, is taken for it there. A number under a chapter label that already has its number ("CHAPTER 2" over "1") is a heading of its own. 11/22/63 pp. 15–94: headings 5 → 23 of 24. Kept although `bench tuning` called it worse: after review 0.96 → 0.96 [+0.00, +0.00], from 11/22/63's new heading questions (2.12 → 2.17 a page); every other book is unchanged. The bench counts words, not structure, so a heading fix shows only in `eval`'s heading score.
- 2026-10-09: `bench` prints each book's headings and reports, beside its test, where headings or paragraph F1 changed (`bench.structure`): the primary measure counts words, so structure went unseen. From the morning's baseline to the review's fixes plus section numbers: 11/22/63 headings 2/24 (+4 spurious) → 23/24 (+1), paragraph F1 up on Reis 0.897 → 0.922, Thief-Taker 0.933 → 0.957, Vals alarm 0.959 → 0.970, 11/22/63 0.942 → 0.955; Artemis 0.931 → 0.929.
- 2026-10-09: Qwen's second look stays out. A second Qwen reading of each suspect's line at 450 dpi, as one more reader's support (`ocrcheck.with_support`, branch `qwen-second-look`), carries a strong signal in the trust data (where glm-ocr differs from Qwen, Qwen's version is wrong on 553 of 580 suspects where the second look changes and 374 of 1,843 where it holds), but the retrained arbiter gains nothing from it: `bench tuning` 0.96 → 0.99 [−0.01, +0.11], `bench validation` 0.75 → 0.77 [−0.06, +0.15], no change; the judges already tell it the same.
- 2026-10-09: The bench's new heading count shows structure as the larger gap: headings found Thief-Taker 9/22, Metro 5/10, Artemis 0/3, De eerlijke vinder 0/4, You're Never Weird 4/16, Villa Toscane 0/12, De cipier 3/4, Reis 10/11.
- 2026-10-09: Where the folio is unknown (a born-digital PDF prints none), the number after a heading label stays part of it: "Hoofdstuk 2" and "Hoofdstuk 3" had both become "HOOFDSTUK", so every chapter label counted as a repeat of the others and became a running head. Villa Toscane's headings 0/12 → 12/12, for the first time in any bench run; nothing else changed. And a number opening a page is a section where the page prints its folio on another line, not only when it is more than 10 away from it: De cipier's "1" on p. 11 (folio 7), headings 3/4 → 4/4, after review 0.42 → 0.40; nothing else changed.
- 2026-10-09: docs/outlook.md: how close the build is, where results can still move, what was tried without effect; for an agent choosing what to work on. Linked from AGENTS.md's standing rules.
- 2026-10-09: A line dropped at the top of a page, centred and boxed like the book's numerals heading their pages, is a misread numeral and becomes a heading (`roles.numeral-slot`); the OCR check reads and fixes its text. Afscheid's "l", "e," and "UH" (1, 2, 11): headings 8/11 → 11/11, paragraph F1 0.705 → 0.709; `bench tuning` and `validation` otherwise unchanged.
- 2026-10-09: An error over a page break counts on the page holding most of its words (`disagreements.find`), not its first word's. Washed-out Afscheid p. 38, which the review covers as one region, had scored as 297 unasked words on p. 37; Dolittle's p. 57 plate scraps as 13 on p. 56. `bench tuning` after review 0.96 → 0.50 (Afscheid 5.03 → 0.24, Dolittle 0.98 → 0.77), validation unchanged. A measuring fix: the new baseline.
- 2026-10-09: Washed-out pages (`faint.py`) are left out of the OCR check: on Afscheid's four, Qwen read near-blank crops as fluent dialogue, clef picked it and the arbiter applied ~170 invented lines. Their scraps had also taken 55 of Afscheid's 62 questions out of sight; the budget now counts only the pages the check reads. Alone, the freed budget went to suspects the arbiter was ≥ 0.9 sure of (Afscheid 0.24 → 0.45 after review), hence the next line.
- 2026-10-09: A suspect the arbiter gives ≥ 0.8 is decided, not asked, within the budget (`ROBO_OCR_ASK_BELOW`, chosen by the user). `bench tuning` 0.50 → 0.48, validation 0.75 → 0.79, both no change by the test; questions about halved (Goede dochter 1.24 → 0.75, De cipier 1.18 → 0.44, Crime 1.21 → 0.30). You're Never Weird 0.84 → 1.03 from one picture's text. 0.9: tuning 0.49, validation 0.80. To revisit with a new arbiter, judge or reader. The text of a washed-out page isn't in Afscheid's PDF: its mask layer holds traced blobs.
- 2026-10-09: `missing.py` reads regions up to five lines tall above a sunk page's text (one line elsewhere). Artemis's chapter numbers, drawn in a circle and absent from its layer, are marked by DocLayout-YOLO and read right by glm-ocr: headings 0/3 → 3/3, +3 questions (the headings), no other book changed.
- 2026-10-09: A golden scan's manifest can list Internet Archive's own files for it (`[scans.ia]`: page images, ABBYY's OCR, scan data, each with its sha256); `golden fetch` puts them in `work/<book>/ia/`. Crime's and Dolittle's are listed: their PDFs are compressed about 13× against the page images every reader could see instead. Not used by any stage yet (checklist: Internet Archive's own files). Lending-library items keep these files private except `_scandata.xml`.
- 2026-10-09: The bench counts what it couldn't see (Fable's second review; scoring changed, so earlier runs aren't comparable): paragraph breaks set wrong per page (`disagreements.break_errors`, decided like the words: clearly fewer is better, clearly more is worse); a question about one place in a line catches only errors sharing a word with that place; a typed washed-out page counts as a question per line. On the same build, `bench tuning` after review 0.48 → 0.56 (Afscheid 0.25 → 0.64, 11/22/63 0.83 → 0.99, Reis 0.24 → 0.32, Thief-Taker 0.42 → 0.55), validation 0.79 → 0.80: the new baseline. Breaks a page: Afscheid 1.73 (mostly its EPUB breaking where the print runs on), Artemis 1.29, the rest 0.01–0.42.
- 2026-10-09: The OCR check folds how an ellipsis is set (`ocrcheck._alike`): the typography stage sets it book-wide, yet a glyph against three dots made suspects (Reis 16 of 83 questions) and trust-data ties (208, 44 of them a real lost ellipsis never labelled). The trust labels no longer forgive a space beside a quote, which no stage removes and the score counts (De cipier's 88 ties of `geweest.’` against `geweest. ‘`). Trust data relabelled, arbiter retrained. And a suspect the vision judge saw none of (clef "neither", 23 in the trust data, the layer right on 17) is asked first and never applied: Thief-Taker p. 46's misaligned crop had its whole sentences applied. Together `bench tuning` 0.56 → 0.56, validation 0.80 → 0.80, no change by the test; Reis 0.32 → 0.22 with its questions 1.09 → 0.34 a page, Thief-Taker 0.55 → 0.46, Goede dochter 0.20 → 0.33 and Artemis 0.70 → 0.75 (both inside their intervals). Kept: the fold is right by construction and spares the reviewer.
- 2026-10-09: Paragraph starts (`reflow.indented`): the page's margin, fitted from lines reaching the right margin with the skew their right ends show, takes over where the local window's margin is the indent (runs of one-line dialogue); not after a full line, so indented blocks stay whole. A gap over 1.5 pitches at top and bottom, after a line ending in punctuation, starts a paragraph (Reis's blank lines, Artemis's letters; not Crime's jittery boxes, not a line the layer lost). `bench` BETTER on both sets by paragraph breaks: tuning 0.46 → 0.33, validation 0.32 → 0.21 a page, words unchanged. Afscheid's remaining breaks are its EPUB's paragraphing, not the print's.
- 2026-10-09: The arbiter's sureness is calibrated (`trust.sureness`, isotonic, fitted per saved model on its training books scored leaving each out; `MODEL_VERSION` 5), so `ROBO_OCR_ASK_BELOW` is a chance of being right that holds through retrains. Raw sureness was already near it (0.8 → 0.833, 0.9 → 0.947). `bench` no change on both sets (tuning 0.56 → 0.57, validation 0.80 → 0.80): no accuracy bought, kept for the threshold's meaning.
- 2026-10-09: The bench records, per book, the share of the read model's lines a hosted build read in its place (`read_via`): every tuning and validation scan but Goede dochter (5%) and De tuin (7%) was read 97–100% by DeepInfra's Qwen, so the arbiter trains on, and the bench scores, a reader Stella's build doesn't use (they agree on 94.5% of lines). Metro's italic score is no longer reported (`italics_unlike_print`): its print sets every station name in italics and its eBook two of them, so the build's 0.16 precision measured the eBook. You're Never Weird's EPUB sets italics in a `txit` class the manifest never named; derived, its italics score 0.99 / 0.92 (was 0 / 0), its text unchanged once derive joins italic spans that touch (`Hors` + `e`). The budget diagnostics shuffle questions of one reason instead of taking them in page order. Fixed with it: the bench's record loop gave every book the last-built book's footnotes for its break count.
- 2026-10-09: A line the layer lost becomes a question (`flags.lost-line`): a line's height of white space between two running-text lines, below one stopping mid-word or mid-sentence, with no picture in it, above a line of running text (not a footnote's `*`, not a speck read as "ae"). `bench` no change: tuning 0.57 → 0.56, validation 0.80 → 0.77 (De eerlijke vinder 1.28 → 1.14, one whole line). Answers insert a typed line as for missing text; a missing-text question now catches any error short of words at its place, not only one with no words at all.
- 2026-10-09: Scene breaks (`Paragraph.break_before`): white space over 1.8 line pitches after a sentence, or a line of three ornament marks or more, sets a break before the next paragraph, an `<hr class="break"/>` in the EPUB (epubcheck clean). Reis 63 in its slice, De eerlijke vinder 27, spot-checked right. `bench` unchanged (words and breaks): the references drop their blank lines, so scoring them is a next step.
- 2026-10-09: The line-role classifier is in the package behind a switch (`sorter.py`, `ROBO_SORTER=1`, off by default): regularised trees over layout, type, repetition and the role model's answer, trained on the tuning books and two more golden books by `experiments/train_sorter.py`, with a copy without each tuning book for `bench`. Leaving one book out it makes 152 role errors on the tuning books to the rules' 406, 29 to 77 on validation. Its first bench: no change (tuning 0.56 → 0.54, validation 0.77 → 0.79; 11/22/63 1.00 → 0.73 and Artemis 0.76 → 0.53, but Crime and De cipier lost a body line each at a page's foot and You're Never Weird kept its running heads). Two rules enforce what is true by definition: text repeated at page edges is furniture (346 such labelled lines, none body), and a line the trees would drop is kept, flagged, at P(body) ≥ 0.25 (57 → 33 body lines lost, 26 more strays kept). Rerun pending before it goes on.
- 2026-10-09: The sorter's bench (`ROBO_SORTER=1`), after two rules in code: a heading, or a line of six characters or more at a page's edge, whose text repeats at the edge of three or more other pages is a running head (11/22/63's "STEPHEN KING" came out as 24 headings; none of 346 such labelled lines is body); a line the trees would drop is kept as text, flagged, while they give it P(body) ≥ 0.25 (lost body lines 57 → 33 for 26 stray lines kept, labelled books). No change by the test: tuning 0.56 → 0.52, validation 0.77 → 0.70 after review; Artemis 0.76 → 0.53, 11/22/63 1.00 → 0.73 and Villa Toscane 0.12 → 0.06 clearly better; Crime 0.43 → 0.71 (p. 97's last line dropped), no veto. Stays off by default until the bench reruns on the local Qwen readings, so that run measures one change.
- 2026-10-09: What paid off from the second review, by the bench: paragraph starts (breaks set wrong −28% tuning, −34% validation, clearly better) and the measurement fixes (the bench now sees breaks, per-place catching and typed pages: honest, 0.48 → 0.56). Promising but not significant: the sorter (−0.04 / −0.07), lost-line questions (−0.01 / −0.03), the ellipsis fold (Reis's questions a third, set unchanged). No gain, kept for other reasons: the arbiter's calibration (raw sureness was already near calibrated), scene breaks (the references can't score them yet), the hosted-share record and italics fixes (measurement only). Mixed: the trust relabel moved Goede dochter 0.20 → 0.33 and Artemis 0.70 → 0.75 inside their noise. Wrong in the review: Metro's italics were the reference's fault, as suspected, but You're Never Weird's weren't missing from its EPUB, only from its manifest.
- 2026-10-09: The slip rate measured again, on today's questions (32 on a copy of Goede dochter pp. 9–64, the arbiter trained without it; `experiments/score_slip_review.py`, each answer judged at its own place against the publisher's text): 30 of 32 right, the two misses one deliberate choice of the right quote mark where the print, and the reference, set the wrong one (p. 36). Picks 17/18, typed lines 6/7, roles 7/7: the check against the readings and the marked differences do their job. The questions are the weak side: OCR questions offered a right reading on 20 of 21, quote questions on 0 of 4 (a print error, a hyphen for a dash taken from Qwen, and two nested quotations `‘“…”’` that the layer and Qwen each read wrong in their own way). Which rate the bench uses is the user's call; code changes wait for the overnight chain.
- 2026-10-09: The bench's slip rate is to be the two reviews pooled, 10 wrong of 100 answers (Stella 8 of 68, Goede dochter 2 of 32 with p. 36's corrected print counted), the user's choice. Noted as pooled: the samples are of different questions (typed regions, then picks with differences marked), so 10% is a middle figure and the rate of today's questions alone may be lower (2 of 32). Applied after the overnight chain, as a new baseline.
- 2026-10-09: Quote questions offer the OCR-checked line, the read model's marks on it (marks and punctuation only, no dashes or letters) and, for a nested quotation, both combined (`quotes.readings`); the slip review's four quote questions go from no right reading to three. Bench after the overnight chain, with the pooled slip rate.
- 2026-10-09: Qwen reads locally, for the bench books and Stella alike (the user's choice): one reader everywhere, so the arbiter trains on the build that reads Stella. The hosted builds were no better (DeepInfra bf16 0.11% CER against the local nvfp4's 0.10% on Goede dochter pp. 9–20; they agree on 94.5% of lines); no host serves a matching 4-bit build (OpenRouter lists Darkbloom fp4, measured worse, and ModelRun fp4), and image resizing and arithmetic would differ anyway. The cost is time: about 1.2 s a line, a night per ~500 pages.
- 2026-10-10: The bench books read again with the local Qwen (30,572 lines, about 9 h with the judges), the trust data rebuilt and the arbiter retrained: compared with the same build on DeepInfra's readings (both with the rules' line roles), `bench tuning` 0.56 → 0.56 and validation 0.77 → 0.79 after review, no change by the test; fewer questions on five tuning books (Goede dochter 0.58 → 0.44 a page, Reis 0.43 → 0.30, Metro 0.60 → 0.49, De cipier 0.46 → 0.35), Artemis 0.76 → 0.64 and Metro 0.37 → 0.35 better; De tuin 0.77 → 0.85, a per-book veto, the one book that loses. Which build reads hardly matters to the arbiter; one reader everywhere stays (the user's choice). The chain's own verdict compared with the sorter-on run before it, so it read as worse: the comparison is with the last sorter-off run.
- 2026-10-10: The checklist reordered: open steps first, in the order they run, done and dropped steps below as a record by their old sections. Reviewed on the way: Stella end to end gets its own steps (none existed for the target book), and so do footnotes (the test set has 26), Thief-Taker's missing trust data, De eerlijke vinder's unasked errors, page classification and a second Dutch validation scan. Dropped: a reading far off its line's length counting as none (readers stray on 1 line in 958 since the crop fix), a crop reader on tesseract's boxes (an image-only scan's layer is tesseract's), a sorter tryout set (the trees are scored leaving each book out), the probe ledger as a step (a habit, in outlook.md); a book-quality feature merged into bad pages by the readers' disagreement.
- 2026-10-10: No whole-book trust data (the user): more pages of the books already trained on add the same errors again, so the time goes to new golden books (Vuurspel into validation, De tuin into tuning; Het heft in eigen hand and Doodskleed into tuning, each pair checked with `probe_candidate.py`) and the plan's other areas. Rejected pairs: De dochters van Cavendon Hall (both EPUBs one file made from the print through Word: "wel eens" set as "weleens", stress accents dropped) and Alsof het niets is (a book of fragments, its layer 0.95% off and uneven).
- 2026-10-10: The bench sets change (the user's go on every suggestion). Validation gains De kerk van de dode meisjes (Ambo|Anthos; its e-book "gemaakt naar de vijfde druk, 2012", the scan's printing; layer 0.15% CER) and Vuurspel (A.W. Bruna; layer 0.46%): two publishers nothing trains on. De tuin moves to tuning, with Het heft in eigen hand (HarperCollins/Mat-Zet, like Goede dochter), Doodskleed (Karakter/ZetSpiegel, like De cipier; De Bezige Bij's e-book of the same text) and Het ijzige land (Gottmer: large type, a drawn initial on every chapter, the e-book after the sixth printing against the scan's thirteenth, differences reading slips only). De stilte van de hel, Vuurspel's sibling (same publisher, translator and e-book house style), stays unused: training on it would weaken Vuurspel as a check. Derive learns `capital_classes` (small capitals written in lower case, "vnr", set in capitals as printed and as a reader reads them) and a spaced `--` as the print's dash. `train_ocr_trust.py` took its held-out books from a hand-kept list, which would have kept De tuin out of training and let Kerk and Vuurspel in; it reads the bench's validation and test sets now. Results before and after this aren't comparable: the next bench is a new baseline.
- 2026-10-10: The agent documents tidied, each with one job (the table at the top of AGENTS.md). AGENTS.md keeps the rules, scope and a one-line map (71k → ~30k characters); its module tour, its table of every model tried and its per-book golden notes moved whole to docs/modules.md, docs/models.md and docs/golden-notes.md. The checklist is the plan again: open steps numbered by position, and "Done" one line a step by area, in place of the 540-line record kept under the old section letters (2b, 3b, 6g) that nothing explained; the numbers behind every line are in this log. Steps are cited by their words from now on, never by number (design.md, this log and a test were changed to match). HANDOVER.md holds only the state of play; the working habits it carried are standing rules now.
- 2026-10-10: The user keeps both of the tidy's scope calls: the model roles stay in AGENTS.md with every model tried in docs/models.md, and the M0–M5 milestones stay dropped, the checklist's order taking their place.
- 2026-10-10: A bug hunt over the whole package (four reviewers, each finding reproduced on synthetic input before it counted), on branch `bughunt`, to be benched against tonight's new baseline before it merges. Fixed, each with a test: `str.isdigit` took a superscript footnote mark ("¹") for a page number and `int()` then crashed the build (`page.digits`); a page of under five lines counted its edge lines twice, so two numbered pages met the three-page offset guard; a lone number on a page became a section heading; a heading label's number a digit away from the folio ("Hoofdstuk 12" on page 15) was stripped as the folio, so two such headings collided as a repeated title; `eval`'s CER charged a word split in two about ten letters (an insert beside a replace, costed apart); `signals.measure` raised on a line that normalises to nothing (a soft hyphen alone), which would have ended a bench; `--pages 0-3` sliced from the end; the verdict and region logs stopped every command on a cut-off last line (`files.read_jsonl`, `append_jsonl`); a typed answer that kept a real hyphen across a break ("zee-egel") got a second one; two regions typed above one line landed in answer order; `reflow.tidy` squashed a spaced four-dot run to "...." before the typography stage could keep it; a number range broken at a line's end ("1914-" / "1918") got a space; a lowercase letter beyond Latin-1 ("ĳ", "ç") after a break kept the hyphen; a caption as large as its picture trimmed the picture to an inverted box (a 1 px sliver, or a crash); the OCR check folded a run of opening quotes to one, so a lost "‘" before "’t" was never raised; a failed reading lost its whole batch of up to 200 cached readings; `ROBO_OCR_ASK_BELOW=1.0` never asked a suspect the calibration made exactly sure; a negative question budget asked all but N; two judges by one name would be one vote; the hosted client was made once per thread; a connection Ollama drops under load is retried like a timeout. Also: the document's line references index the pages before answers (`Stages.pages`, what `Line.source` points back to), not the corrected copy; `eval`, `quality`, `bench` and the golden review passed the corrected copy, so a typed line shifted every crop and word weight below it (two tests had encoded the wrong contract). Found and left for a decision, in HANDOVER.md: a typed line shares its neighbour's identity (`Line.source`), so `italics.mark` can set it in the neighbour's italics; the repeated-title rule demotes a real chapter title that recurs (Thief-Taker's second "THE THIEF-TAKER"); heading matching counts "CHAPTER 2" found for "CHAPTER 3" when a heading is missing; a dash closed to "none" merges two tokens and an italic word swallows its neighbour; the word-list feature `known` is computed on the raw versions where the vote uses the joined ones; a disagreement's key takes its context from the sliced reference; PDF pages with `/Rotate` would be cropped in the wrong place (no book has any).
- 2026-10-10: The seven findings the bug hunt left open are fixed on `bughunt` (the user: fix everything), each with a test that fails on the old code. Heading matching: another chapter number is another heading (CHAPTER 2 counted for CHAPTER 3, XXV for XXVI); the layer's look-alikes still match ("4I" is 41, "Il" is II, so one existing expectation rose from 4 to 5). Disagreement keys and verdicts take a slice's edges' context from the chapters around it (`slice_reference`), so a verdict keeps its key under any slice. An unspaced dash no longer makes an italic word swallow its neighbour (`Paragraph.italic_parts`, `<i>Ulysses</i>—een`). The arbiter's `known` feature judges a break as the word-list vote reads it ("dankbaar", not the unjudged "dank-"): MODEL_VERSION 6, so trust data rebuilt and the arbiter retrained before the branch is benched. A title recurring on a sunk chapter opening (its first line sunk, or below the first) is no longer demoted as a repeated title; a running head repeating it on an ordinary page still is. A typed line's reference says it is typed (`SourceRef.typed`), and italics skip it (it took its neighbour's: "en de" before an italic line came out italic). Text boxes on a page with /Rotate are mapped to the shown page (`pdf.page_words`); no golden book has one.
- 2026-10-10: The longer slices (446 new pages in 7.5 h, 1.0 min a page with Qwen local), with the arbiter and the trees retrained on them: `bench tuning` 0.53 → 0.53, `bench validation` 0.77 → 0.76, no change; De tuin 0.82 → 0.78, its veto gone. Before them the pooled slip rate (10 of 100) lowered "after review" a little on most books (11/22/63 0.98 → 0.92), and the quote questions' three readings changed nothing the bench counts (it takes the reviewer's answer as right whatever the readings; the slip review saw 0 of 4 right readings become 3 of 4). The trees on the longer slices against the rules: tuning **better** on paragraph breaks (0.33 → 0.32 a page, words 0.54 → 0.52 [−0.10, +0.05]), validation no change (0.75 → 0.68 [−0.16, +0.00]); clearly better on Reis 0.25 → 0.21, De cipier 0.31 → 0.20, 11/22/63 0.95 → 0.68 and Villa Toscane 0.12 → 0.06, clearly worse on **Thief-Taker 0.47 → 0.97** [+0.12, +1.03], under the veto's 99% line. The trees stay off until Thief-Taker's loss is explained; tonight's benches on the new sets decide again.
- 2026-10-10: Lady into Fox and Grand Hotel Europa retired for good (the user: little value kept in reserve). Their references don't match their prints (typography; another printing), so they could neither train nor measure. Scans, references and trust data moved to `work/retired/`, manifests out of git. Two candidate pairs rejected for the same reason the same day: Bloemen op mijn graf (a Sigil-made copy that strips the print's stress accents, `níet` → `niet`, and turns dashes into hyphens; layer CER 0.66%) and Op drift (a homemade release: double quotes for the print's single, accents stripped, `Jéróme`).
- 2026-10-10: Het ivoren aapje (Teirlinck, 1909) deleted with its probe, `experiments/probe_ocr.py` (the user's call): its pre-1934 spelling had already ended its use as the OCR bench.
- 2026-10-10: The retired books' files deleted (the user's call): Boze tongen, De dode kamer, Sense and Sensibility's three scans, Goede dochter's eighth printing, Lady into Fox and Grand Hotel Europa. `experiments/probe_page_types.py` went with them, its gold labels on Sense's Tauchnitz scan; page classification starts from Internet Archive's own page labels instead. Retiring a book now deletes its files rather than parking them.
- 2026-10-10: Every tuning and validation pair checked for a subpar reference: none. The weak layers (Crime 0.85%, Dolittle 0.93%) are faithful pairs with hard scans, and the high unplaced shares (Dolittle, Afscheid, 11/22/63, Crime) are running heads, plates and washed-out pages. Two clean pairs had no job because of the sibling rule, which forbids training, not validating: Monterosso mon amour and De stilte van de hel join validation (5 → 7 books) after tonight's baseline (the user agreed).
- 2026-10-10: The user's goal, in place of a "done" bar: an EPUB as if the publisher had put it out, faithful to text and typesetting, minimal errors; progress, not a finish line, so builds are made and then measured. No exchange rate between questions and wrong words (the user answers until tired): the ask threshold is chosen where a question's yield falls off. Each target book gets a spot-check of 5 random pages after its review. French: not yet. The stale worktrees `baseline` and `qwen2` removed (their uncommitted diffs saved in `work/probes/old-worktrees/`).
- 2026-10-10: The user's rule: no model run starts with the battery under 30%; wait an hour and check again. `experiments/battery_gate.sh`, called by `timed.sh` before each run, so chains already running obey it from their next step.
- 2026-10-11: The new baseline (the sets of 2026-10-10; trust data for Thief-Taker and five new books, 567 pages in 525 min, Qwen local; arbiter retrained on ~10,400 suspects, MODEL_VERSION 5): `bench tuning` **0.50**, `bench validation` **0.74** wrong words a page after review; breaks 0.26 and 1.72 (Vuurspel 7.84 a page, every other book under 0.8: suspect its pair or derive). On the pages both runs share, against the run before: tuning 0.52 → 0.53 with breaks 0.32 → 0.33 (WORSE by breaks alone), validation 0.66 → 0.74 no change. Unasked errors make 0.39 of tuning's 0.50; by kind: punctuation ~130, letters ~115, word breaks ~75, missing words ~70, quotes ~64. Doodskleed's 6.3% unplaced is over all lines: its body lines are 0.7% unplaced, no suspect pair. Trees against rules on it: tuning 0.50 → 0.48, validation 0.74 → 0.67, no change; clearly better Metro 0.34 → 0.29, De cipier 0.30 → 0.20, Artemis 0.62 → 0.39, 11/22/63 0.91 → 0.64, Villa Toscane 0.12 → 0.06; none clearly worse, Thief-Taker 0.48 → 0.61 [−0.01, +0.38] and Crime 0.42 → 0.69 [−0.10, +0.74] leaning worse.
- 2026-10-11: Branch `bughunt` benched against the new baseline (its trust data rebuilt warm in minutes, MODEL_VERSION 6, arbiter retrained on ~10,500 suspects) and merged: `bench tuning` **better**, 0.50 → 0.48 [−0.03, −0.01], clearly better on Goede dochter 0.47 → 0.41, Vals alarm 0.78 → 0.73, De cipier 0.30 → 0.28, De tuin 0.64 → 0.59, Doodskleed 0.43 → 0.36 and Het ijzige land 0.35 → 0.30, no book worse; `bench validation` no change, 0.74 → 0.73 (breaks 1.72 → 1.74). Its trust data and arbiter replace main's (the version-5 ones kept in `work/probes/ocr-trust-v5/` and `work/models/v5/`).
- 2026-10-11: Where the unasked errors come from, offline on the merged trust data (each tuning book with its leave-one-out arbiter, `trust.decide` at the build's settings): the arbiter settles **0.061** suspects a page wrongly without asking (book-weighted), against ~0.39 unasked wrong words a page in the bench. So about 85% of what survives review was **never a suspect**: every reading agreed, or the OCR check doesn't look there (punctuation, word breaks, missing words, quotes lead the unasked kinds). The ask threshold, 1 question a page as now: below 0.7 asks 0.15 a page and lets 0.094 through; 0.8 (today) 0.29 and 0.061; 0.9 0.46 and 0.038; 1.0 the full budget, 1.00 and 0.023. A question costs the reviewer's slip rate (~0.1), so 0.8 → 0.9 removes 0.023 a page for 0.017 in slips, about even; beyond 0.9 asking costs more than it saves. Raising the threshold can't move "after review" much; the gain is in errors no reading raises.
- 2026-10-11: The unasked errors listed one by one (`experiments/unasked.py`, the tuning books as the bench builds them): punctuation 148 words, letters 117, word breaks 73, missing words 72, quotes 57. Two groups looked fixable. **Line-end hyphens** (75 words: "sailor-song" joined, "every- body" kept): keeping the hyphen when both halves are words and the joined form isn't fixes 24 and breaks 14 of ~980 English line-end hyphens and is clearly worse on Dutch (127 wrong of 4,599, where the current rule errs 14 times); a proper-name rule ("Tokugawa-shoguns") is worse in both (`experiments/probe_line_hyphens.py`). Not pursued: ~0.02 words a page. **Lost lines** (19 places, 72 words): a page's first line called a running head and a short last line an artifact, dropped without a question as furniture is. Kept as text and flagged when it continues an open sentence or opens with a quotation mark and reads as words: 22 body against 3 not over the tuning books (`experiments/probe_continuations.py`; continuation alone was 21 against 173, the repeated running heads) → `roles.running_text`. Bench pending.
- 2026-10-11: Unasked quote errors (57 words): a closing quote lost at a paragraph's end before a paragraph that opens with a quote (De tuin, 9) looks exactly like a quotation running over paragraphs, and a mark lost in a nested quote ('"Er, Goede dochter, 9) needs the readings, not a rule. A speck read as an opening quote mid-sentence ("Green zich ‘schrap zette", De cipier) is excused by the same running-over rule; excusing only an unclosed mark that opens a sentence adds 10 places on the tuning books, and requiring a letter before it and a lowercase one after leaves 4, all real (`experiments/probe_stray_quotes.py`). Precise but ~4 words in 1,600 pages: not built yet.
- 2026-10-11: Of the 117 unasked letter errors, about 20 were the references': De tuin's "CT", "KL", "FMS" and Vals alarm's "BSO", text messages and "TE KOOP" are set in small capitals and written in lower case in their EPUBs with a class (`kk`, `kk1`, `sanskk`) that neither manifest declared. Declared as `capital_classes` and derived again (61 and 33 paragraphs changed; neither book has verdicts). Their bench scores move by measurement, not by the build. The rest: about 25 Dutch stress accents the arbiter settles wrongly ("niét"/"niet", "één"/"een"), 7 drawn initials lost ("et" for "Het", Dolittle's "HAT"), Artemis's slug sign ("ğ") 7.
- 2026-10-11: Unasked word breaks (73 words) are scattered: Reis spaces an ellipsis after a question mark ("doen? ...") but not elsewhere ("Boston...Wat", 6), a space before a quote that opens a new quotation in Metro's and Thief-Taker's references ("offering? '", 6, likely the transcription's), drop caps split from their word ("T oen", "H et"), dash spacing beside quotes. No rule worth its counterexamples.
- 2026-10-11: The running-text rule (`roles.running_text`) benched and kept: `bench tuning` **better**, 0.43 → 0.37 [−0.11, −0.02] (De cipier 0.28 → 0.18), `bench validation` **better**, 0.82 → 0.76 [−0.13, −0.01] (Villa Toscane 0.12 → 0.07, its missing words 11 → 1); breaks unchanged. The trees on top of it: tuning 0.37 → 0.40 [−0.01, +0.09], validation 0.76 → 0.72 [−0.19, +0.08], no change on words; clearly better Reis, Dolittle and 11/22/63, clearly worse Thief-Taker (0.65 → 0.84 wrong words) and Vuurspel (0.76 → 0.88 after review). They stay off: they no longer help where the rules now keep the lost lines. Validation over its 7 books by the rules: **0.76** wrong words a page after review, breaks 1.97 (Monterosso 0.79 and De stilte 1.30, cold; De stilte's breaks 4.90 a page, like its sibling Vuurspel's).
- 2026-10-11: `bench` and `eval` named the commit at the end of a run, not the one whose code ran: Python imports the code at the start. Night2's rules validation started at 02:05, before the running-text rule was committed (02:27), and was saved as de4efd6, after it; so it is the rule's "before" on validation, and its "trees against rules" comparison mixed the two changes (redone from the saved runs above). Both read the commit when they start now.
- 2026-10-11: Vuurspel's 7.84 paragraph breaks a page were the build's, not its pair's: A.W. Bruna sets the book (and its sibling De stilte) without indents, and the short-line test that finds an unindented paragraph judged the text ragged wherever dialogue's short lines made up most of the eleven lines around it. Justification is judged on the lines that stop mid-sentence now, a page's short last sentence starts a paragraph on the next page, and "short" starts at 2% of the line width (`experiments/probe_missed_breaks.py` lists the missed breaks with their context; De stilte's recall 0.54 → 0.90 → 0.935 → 0.965 by those three steps, precision 0.977 → 0.987). `bench validation` **better**, breaks 1.97 → 0.21 a page (Vuurspel 7.91 → 0.44, De stilte 4.90 → 0.36, De eerlijke vinder and Monterosso too), words 0.76 → 0.75; `bench tuning` **better**, breaks 0.26 → 0.22 (Reis 0.17 → 0.07, Artemis 0.75 → 0.46, De tuin, Het ijzige land), words 0.37 → 0.37, no book worse.
- 2026-10-11: The ask threshold (`ROBO_OCR_ASK_BELOW`) benched on tuning at 0.7, 0.8 and 0.9, pooled over pages: 0.735, 0.916 and 1.107 questions a page for 0.351, 0.344 and 0.343 wrong words after review. 0.7 → 0.8 removes ~0.04 wrong words a question, 0.8 → 0.9 ~0.005 (no change by the test, more slips than it saves at the many-slips rate). The yield falls off past 0.8: it stays. 0.7 would cut a fifth of the questions (De tuin 1.53 → 0.74 a page) for +0.007, the place to go if the reviewer tires.
- 2026-10-11: Accent-only errors over the tuning books (`experiments/probe_stress_accents.py`, every difference, asked or not): about 60 accents the print has and the output lacks ("één", "ík", "níét", "zíjn"; Goede dochter 19, Het heft 9, Artemis's "ğ" 7), about 15 the output adds. Nothing to build. Added accents on Doodskleed and De cipier ("té", "niét", "kútverhaal") are specks over letters on those scans: all 32 accent-adding readings labelled wrong on Doodskleed show a speck on the scan, so the labels and references are right. Goede dochter's "één" is right in the text layer and lost when the vision judge votes "een" and the arbiter follows it (3 places). The diaeresis can't be restored from the word list: it holds plain and marked forms alike ("geinteresseerd" and "geïnteresseerd", "moët" for "moet"), and Het ijzige land's reference prints "geinteresseerd" once (`experiments/probe_diaeresis.py`).
- 2026-10-11: The unasked punctuation (150 words): 71 are line-end hyphens in compounds (probed before, not pursued), 26 scattered, and the largest group with one cause is De tuin's and Het heft's lost stop before a paragraph's closing quote ("Frederik’" for "Frederik.’", 8): the print kerns the stop under the mark (seen on the scan), so the layer and clef miss it. Speech closed on a letter at a paragraph's end is now a quote question (`quotes._unstopped`): `bench tuning` **better**, 0.37 → 0.37 [−0.01, −0.00], De tuin 0.46 → 0.41 for 0.08 more questions a page; validation unchanged. The probe that counted references' paragraph endings read every golden reference, the test set's (Het geluid van bananen) among them, against the rule that no probe touches it: it gave one count (0 of 768 paragraphs), nothing was chosen or trained on it, and the rule was set from the other books' 6 of ~33,000.
- 2026-10-11: Of the unasked letter errors left after the accents, two groups: small capitals the layer reads in lower case ("swat-team", "t-shirt", "u-bocht", "uv-licht", "voc"; 7 words, the print's small capitals checked on the scan; telling a small-capital T from a lower-case t is a visual job, not taken on) and drawn initials lost (7). A section whose first text line opens in lower case below a heading is flagged now ("initial-lost": Het ijzige land's "asteel Araluen", "et wolvenschip"): `bench tuning` no change pooled, 0.37 → 0.37 [−0.01, −0.00], Het ijzige land clearly better 0.25 → 0.20 for 0.05 more questions a page, no book worse; validation unchanged. Kept: a question where the text is surely wrong. Dolittle's ("HAT" for "THAT") open in capitals and aren't caught by it.
- 2026-10-11: A quote left open at a paragraph's end was excused when the next paragraph opened with a quote (a quotation running over); the golden references do that in 56 of ~58,000 paragraphs, and De tuin loses about 40 closing quotes in that place. Asked whatever follows now: `bench tuning` 0.37 → 0.36 [−0.02, −0.00] (no change by the test; De tuin unasked 0.24 → 0.16, after review with few slips 0.33 → 0.27, for 1.61 → 1.96 questions a page; 11/22/63 +0.09 questions), `bench validation` 0.75 → 0.75, no book worse. Kept: the questions sit where the text is wrong far more often than not.
- 2026-10-11: The unasked errors listed again on the current build (`experiments/unasked.py`): 362 words over the tuning books, punctuation 136, letters 69, word breaks 69, quotes 47, missing words 20, extra words 19. The largest group with one cause: 52 English compounds whose line-end hyphen was dropped ("halfcooked", "nightvision"), where the book's spellings and the word list are silent. Asked of the decision models how the word is spelled in its sentence (`experiments/probe_hyphen_judge.py`, 438 such breaks with a one-way reference): in English, joining is right on 43 of 77, clef:27b on 63 (1 wrongly hyphenated), clef-flash 59, winnow 46; in Dutch joining is right on 355 of 361 and clef no better (353). A question was the plan, but the scan can't show a spelling, so the judge decides, on English books only (`hyphens.Compounds`). `bench tuning` **better**, 0.36 → 0.34 [−0.03, −0.01] (Dolittle 0.52 → 0.44, Metro 0.26 → 0.22), `bench validation` no change (one English book), no book worse.
- 2026-10-11: A line-end hyphen's parts were the whole next word with its punctuation stripped, so a dash after the break glued the following word on ("cam-" / "pus—that's" looked up and judged as "cam-pusthats", kept hyphenated). Only the letters beside the break count now: `bench` no change on either set (tuning 0.34 → 0.34 [−0.01, +0.00]), no book worse.
- 2026-10-11: A section opening on a word in capitals (two letters or more) below a heading is flagged as a lost drawn initial too: Dolittle sets each chapter's first word in capitals after its drawn initial, and where the initial isn't read the word loses its first letter ("HAT", "HEN"; over the built books only Crime's "YOU" opens so with nothing lost). `bench tuning` no change pooled, 0.34 → 0.33 [−0.01, +0.00]; Dolittle 0.44 → 0.40 for 0.08 more questions a page, no book worse; validation unchanged. Kept.
- 2026-10-11: A quote mark left open mid-paragraph was asked as "open at end", and the question showed the paragraph's last lines, not the mark: a speck read as an opening mark right after a word (De cipier's "zich ‘schrap zette", "Als ‘het"; 8 such unasked words over the tuning books) was never in view. Such a mark is asked where it stands now; speech opened after a comma, a colon or a sentence's end still asks at the end. `bench tuning` **better**, 0.33 → 0.32 [−0.03, −0.00] for no more questions (Afscheid 0.58 → 0.45, De cipier, Artemis, Reis), validation 0.75 → 0.74, no change by the test, no book worse.
- 2026-10-11: "for- est", "hus- band", "intus- sen" in the output were paragraph breaks inside a word: beside a picture or a drawn initial the margin moves, the line after "seen her hus-" read as indented and started a paragraph, and the EPUB set the halves apart. A line that starts in lower case after one ending in a letter and a hyphen continues the word; no paragraph starts there (a dash ending speech before "‘Wat?" is no such line). `bench tuning` **better**, 0.32 → 0.31 [−0.02, −0.00], `bench validation` **better**, 0.74 → 0.70 [−0.08, −0.02] (You're never weird 0.94 → 0.77, Monterosso 0.64 → 0.50); paragraph F1 up on every book that moved, none worse. Of the suspended hyphens ("voor- en"), a conjunction after a line-end hyphen is a Dutch syllable more often ("boei-en", "als-of": 11 against 1); not pursued.
- 2026-10-11: Whole lines missing from the output (20 words over the tuning books): Goede dochter's "‘Gamma.’" at a page's foot is in the layer but was looked up as "Gamma’", which the word list doesn't know, so `roles.running_text` left it dropped; words are read without their end quotes now (`bench` no change, Goede dochter 0.40 → 0.39). Its "‘Ja.’" is read "jas" in a box four points tall, and Het heft's and Reis's datelines ("Februari 1829", "Boedapest, 1936") come out as part of the chapter heading: a structure call, left.
- 2026-10-11: An ellipsis after a question or exclamation mark is spaced in the tuning references 18 times and closed twice, also in books that close it up after a word (Reis 6 of 7, Crime 2 of 2), and the typography stage set it the book's way ("doen?..." for "doen? ..."). After "?" or "!" it keeps the layer's space now: `bench tuning` no change pooled, 0.31 → 0.31 [−0.01, +0.00], Reis clearly better 0.24 → 0.20, no book worse; validation unchanged.
- 2026-10-11: The book's own consistency as new suspects (`experiments/probe_consistency.py`, no models): a word printed once or twice whose OCR-folded form (I/l, 1/l, rn/m, cl/d) the book prints five times or more. Over the tuning books' builds 13 flags on a real error against 17 on correct words, 10 of the 13 in Afscheid (the badly scanned book); the false alarms are real words ("eik" beside "elk", "huls" beside "huis", "clan" beside "dan"), and the word list can't filter them (it knows "Ai", "aile" and "zel" too). Folding accents as well: 31 against 102, Dutch stress accents ("nóg", "wél") the same as specks over letters ("té", "dé"). Null for ordinary books; not built.
- 2026-10-11: A reader of the finished text, second probe (`experiments/probe_text_reader.py`, the bench's slices, the current build): qwen3.8:27b proposing, clef:27b with the line crop filtering, 200 paragraphs each. Metro: 51 flags, 23 quoting text that isn't there, 2 on a remaining difference; clef at P(fault) ≥ 0.5 keeps 5, none on a difference. Goede dochter: 42 flags, 10 invented, 7 on a difference; clef at 0.5 keeps 7, 3 on a difference, two clear ("we-bril" for "wc-bril", "ALI ES" for "ALLES"); the urges are correct Dutch called misspellings ("erkerraam", "gruizig"). About one catch per 100 paragraphs against as many false questions: the reviewer's time would buy more elsewhere. Not built with these models; worth a rerun when a stronger text model comes (the probe takes ~25 min).
- 2026-10-11: Readers on Internet Archive's own page images (`experiments/probe_ia_images.py`): reader set v1's 50 Crime lines cut from the JP2 the PDF was made from (the PDF page placed in its leaf by template matching, 0.94–0.96; the crops line up at the same pixel size, grey and without the PDF's compression noise). glm-ocr: hard lines 22/30 right either way, CER 1.57% → 1.26%; control 18/20 → 19/20, 0.28% → 0.14%. Qwen: hard 22/30 → 23/30, CER 1.78% → 1.36%; control 20/20 both. About a fifth less error from cleaner pixels, on 50 lines of one book. It reaches only books whose JP2s can be had: public-domain items; Stella and the user's four books are lending-library items, their JP2s private. Dolittle (no scandata, 6 more leaves than pages) not placed yet.
- 2026-10-11: A borrowed Internet Archive item offers no downloads while on loan (the user checked Stella: "No suitable files to display here"), so its JP2s can't be had: the cleaner pixels reach public-domain books only, and Stella and the user's four books are read from their PDFs.
- 2026-10-11: Bad pages by the readers' disagreement, probed before building (OCR-check suspects a page against the book's median, the unasked list per page, tuning books): the 5% of pages with the most suspects (78 of 1,567) hold 32 of the 319 unasked words, twice their share but too few to flag whole pages for; the densest pages (Reis 217, Metro 24, 22–29 suspects) hold 0–4. Null; not built.
- 2026-10-11: Stella with today's build (every stage cached, under a minute; epubcheck clean): 7 questions, of which 3 were answered in the first review; 80 of the 83 stored answers apply, the other 3 lying inside lines another answer retyped whole. Of the 4 new questions, sampled on their crops (`experiments/sample_questions.py`), one is real (p. 19, the layer's "féts" for "iéts", the judges split between iéts and íéts) and three are obvious, with the arbiter's text already right: "gestuit" against winnow's "gestuït", "omging" against clef's "omgeving", "Ze" against a lower-case reading no judge picked. Too few to change the arbiter for; noted as a sign that a lone judge's split still reaches the reviewer. The user answered "íéts", clef's reading: the print accents both letters of the stressed ie, as the spelling rules have it (the user found the same in a Volkskrant headline).
- 2026-10-11: Stella against its build of 2026-10-07 (the user's copy; word diff, `work/probes/stella-oct7/diff.py`): 32 word changes, all for the better (split words such as "datik", "trofik", "leefalsofik"; ë for é; closed dashes spaced as printed; closing quotes; "lets" → "Iets"), the same 244 paragraphs and breaks. The diff found two faults in `corrections.apply`, both fixed with tests: a region retyped over several lines was joined with plain spaces, so its line-end hyphen stayed ("ver- wachten", "haas- tig"; now joined as reflow joins); and a later answer about lines a retyped region had taken into its first line set them back to running text, printing p. 36's sentence twice (such lines now stay dropped). Only Stella's answers retype several lines across a break; the bench doesn't apply review answers, so its numbers can't move.
- 2026-10-11: Python 3.15 tried (Homebrew's 3.15.0, a separate worktree and venv): PyTorch 2.14.1 and torchvision 0.29.1 have no cp315 wheels, so `uv sync` stops; every other dependency has them (numpy, scipy, scikit-learn, Pillow; PyMuPDF's abi3 wheel). With PyTorch's nightly (2.16.0.dev20261010) all 337 tests pass, DocLayout-YOLO's regions on 7 pages (Stella, Dolittle) are byte-identical to 3.13's, and the arbiter's pickle loads. Waiting for a stable PyTorch with cp315 (pytorch/pytorch#184352).
- 2026-10-11: The substitution-pair prior, ablated on its own (it shipped inside the arbiter, measured only leave-one-out on labels): the arbiter and its leave-one-out copies retrained with an empty pair table (`MIN_BOOKS` past any count; `work/models/ablate-nopairs/`), both benches against the current build. Worse on both: tuning 0.31 → 0.34 [+0.01, +0.04], validation 0.70 → 0.73 [+0.00, +0.08] wrong words a page after review. Without it the arbiter asks more on some books (Het heft 0.43 → 0.86 questions a page, Artemis 0.66 → 0.91) and fewer on others (11-22-63 3.46 → 3.23, with unasked 0.22 → 0.32). The prior stays. The ablation's bench files are in `work/bench/ablations/`, out of the baselines.
- 2026-10-11: Reis om mijn schedel's reference numbered its 8 footnotes `*`, `**`, … `********` through the book, as its EPUB does, where the print sets one `*` for each (pp. 89 and 167 checked on the scan): 8 of its unasked "errors" were the EPUB's numbering. A `[reference]` key `note_mark` (derive sets every note link and note to it; PROVENANCE lists it) declares the deviation; Reis rederived, only the marks changed. Bench tuning against the current build: Reis after review 0.20 → 0.17 [-0.05, -0.01], unasked 0.16 → 0.13; the set stays 0.31. A measurement fix, not a build change. The unasked list's other groups on the tuning books, looked at for one cause: wrong letters are mostly stress accents lost or invented (~30 of 61: "één" read "een", "té" for "te") and small capitals in lower case; "punctuation" is mostly line-end hyphen choices in compounds ("dealbreaker" against "deal-breaker"); none with a rule-sized single cause.
- 2026-10-11: Scene breaks scored. Derive marks a break before a paragraph (`Section.breaks`, `<hr/>` in the chapter files, `Chapter.breaks`): Gutenberg's `<hr class="tb">`, a paragraph of ornaments alone ("* * *", which was read as text before), and an element of the manifest's `break_classes` holding no letter or digit (Goede dochter's `P_plat` sets both its empty scene-break paragraphs and unindented text). `evaluate` counts the reference's breaks, the output's (`Paragraph.break_before`) and those at the same word; `bench` prints them per book and where they change. Verdict patching carries a break past a paragraph a verdict empties. Every tuning and validation reference rederived (not the test set's): text unchanged but for 6 ornament paragraphs now breaks (De tuin 5, De kerk 1) and two touching italic spans merged in Goede dochter; both benches NO CHANGE (0.31, 0.70). Villa Toscane's reference was older than the rule that a heading of marks alone is no chapter: rederived, its colophon (after chapter 12 in the same file, under an invisible "*" heading) folded into chapter 12, inside the bench slice; its colophon classes are now blank classes and chapters 1–12 match the old files exactly. `witregel`/`break`/`wp-witregel` in Vals alarm, Vuurspel, De stilte and De kerk mark front-matter spacing only (0 breaks) and stay undeclared. First numbers: references hold 1 break in the scored slices (Crime), the build sets 0–163 a book (Reis 163, De cipier 25, De tuin 24); De tuin's checked on the scan are real breaks its EPUB marks only by `standaard-eerste` on the next paragraph, so most "+N" are unrecorded, not false. Opening and closing classes are next (checklist).
- 2026-10-11: Scene breaks marked on a neighbouring paragraph: derive's `opening_classes` (a break before each such paragraph, never before a chapter's first) and `closing_classes` (a break after it). Each candidate class checked on two to five crops of its scan (`experiments/probe_break_classes.py`): a break for Reis `body1rgl` (5 of 5), De tuin `standaard-eerste`, De kerk `wp-platmetwit`, De eerlijke vinder `firstline` (opening), De cipier and Doodskleed `einde-links-ingesprongen`, Artemis `space_after` (closing; its print sets "• • •"); not a break for 11-22-63 `txf` (after numbered sections, already headings), De stilte `normaalinspring` (indented letters), You're Never Weird `noindent` and Monterosso `ff-platmetwit` (after headings); unsure, left undeclared: Het heft `P_plat`, Villa's `Tekst_6-Na-witregel` (born-digital, every paragraph spaced), Artemis `noindent_topspace1`. Seven references rederived, text unchanged. Bench: where breaks are recorded the build finds 255 of 295 (Reis 156/182, De cipier 25/26, De tuin 24/25, Doodskleed 11/12, De kerk 5/6, De eerlijke vinder 27/35, Artemis 7/8) and sets 20 more (Artemis 13, Reis 7); both benches NO CHANGE on words.
- 2026-10-11: Missed scene breaks, located (`experiments/probe_missed_breaks.py`, the 7 books whose references record them): of 40, 20 at a page top (the break at the foot of the page before, no white space to see), 11 inside an output paragraph, 7 elsewhere, 1 unaligned. Reflow now sets a break before a page's first line when the page before ended a paragraph, the line sits flush on the margin and the run indents its paragraphs (books without indents untouched). First try took a line up to 5 points either side of the margin as flush: De tuin got 4 false breaks, page tops the print indents but the layer boxes left of the margin (−6.6 to −1.8 points; Reis's real flush lines −1.0 to +3.8), so the slack left of the margin is 1.5 points. Bench against the build before: found 255 → 272 of 295 (Reis 156 → 168, one each in Artemis, De tuin, Doodskleed, De kerk, De eerlijke vinder), 2 more set where the reference has none (De tuin, De eerlijke vinder), 1–3 more in books whose references don't record breaks (unchecked); words and paragraph breaks NO CHANGE on both sets.
- 2026-10-11: Internet Archive's `_scandata.xml` as page-type labels, null. It is public on a borrowed item too (Ex-minnaar's, `isbn_9057132931`, named on the scan's stamp page), but its page types are Cover, Title, Color Card and Normal for 281 of 286 leaves (Crime alike; Dolittle adds Contents, Copyright and Delete): colophon, motto, body and ads are all Normal, so it can't place `body_pages`. The printed page numbers (`_page_numbers.json`) would, but that file is private on a borrowed item.
- 2026-10-11: The scene breaks still missed in Reis (14) are page tops after a full page: its last line is a full justified line ending a sentence at the margin (p. 24 "…Hij is goed geïnformeerd."), the next page opens flush ("Ik knap een uiltje"). A paragraph running on over the page, its sentence ending on the page's last line, looks the same, so no rule on geometry can set these without setting false breaks; the pages aren't short either (Reis's short pages, text block 1.5 lines under the median of 463 pt, are other pages). Left for a question to the sorter on the text, later.
- 2026-10-11: The user's three books after Ex-minnaar checked for their body pages (no models): De kus in de nacht opens on p. 7 ("Deel een", "Proloog"), not p. 9; Een Russische roman is seven numbered parts, each a small number atop its own page (p. 7 for part 1, then 47, 131, 169, 233, 259) with library pencil marks the layer reads as noise, so it opens on p. 7 too (p. 272 is show-through only); Andere levens stays 9–244, p. 244 being its closing note on sources. Ex-minnaar's motto on p. 7 stays outside the body until epigraphs are handled.
- 2026-10-11: Stella's built text against the Dutch word list (no models): of 3,166 distinct words, 210 rare ones (at most twice) are unknown to the list, nearly all real compounds and inflections it lacks ("kolenkist", "föhnachtig"); the two that looked wrong are printed so ("oomachtigheid" after "een welwillende oom", p. 34; both "lindebladeren" and "lindenbladeren", pp. 65 and 7). Nothing for the reader to be pointed at; the word list is too thin on Dutch compounds to rank suspects by itself.
- 2026-10-11: Artemis's wrong paragraph breaks (`experiments/probe_break_errors.py`): 30 missing, 1 extra. Most are its letters ("Dear Kelvin," alone on a short line ending in a comma, the letter set flush in a sans face: nothing marks the paragraph's end; left). On p. 47 a run of one-line dialogue paragraphs lost every break: the layer split a word and a closing quote off two lines onto their rows, the roles dropped them as artifacts, and each dropped line cut the page into runs whose last held only short indented lines, too few to find the page's margin. Reflow now lets a dropped sliver (one or two marks, narrower than 8 points, on a neighbouring line's row) pass without ending the run. Without the width limit it also passed pictures' garbled readings (Dolittle 28 lines, 11/22/63 7), which made Dolittle, 11/22/63 and You're Never Weird slightly worse. Bench: paragraph breaks tuning 0.22 → 0.21 [-0.02, +0.00], validation 0.21 → 0.21; paragraph F1 Artemis 0.975 → 0.980, Afscheid 0.699 → 0.695 (its breaks are mostly its EPUB's paragraphing, 106 missing); words unchanged.
- 2026-10-11: Footnotes out of the running text (`footnotes.py`, `ir.Note`, `Paragraph.notes`, noteref and `aside epub:type="footnote"` in the EPUB). Reis's notes measure 0.68–0.74 of body type against 1.0 for text and 0.8 for folios; the rule takes the small lines below a page's last body-type line when the first opens on a mark. First bench: Reis 7 of 8 found and linked (paragraph breaks 0.07 → 0.06, BETTER), but false notes in Afscheid (p. 20) and Doodskleed (p. 43): a picture's garbled reading in small type. Requiring most words to be in the word list didn't remove them (the Dutch list knows "hd", "Ld", "vip", "AAS"); their strokes did: 1.6–2.6 times the body's weight against Reis's notes' 0.7–0.8, so a note's lines must be under 1.2. After both guards only Reis gets notes; tuning BETTER on paragraph breaks, validation NO CHANGE; Reis's EPUB passes epubcheck. The note missed is p. 147's, whose mark the layer read "ie": small type without a mark stays text (a caption or a closing line can be small too).
- 2026-10-11: Epigraphs (`epigraphs.py`): a page of at most six short lines set at least 0.15 of a full line in from the book's margin, with no heading, becomes a motto, each line a paragraph marked `epigraph` (scored as text), set as one `blockquote epub:type="epigraph"`. Ex-minnaar's p. 7 ("‘It’s closing time’ / (Leonard Cohen, The Future)") comes out right, the title even italic, epubcheck clean; its `body_pages` now start on p. 7. The first version took false mottos in six bench books (garbled picture text in Goede dochter, De kerk, De eerlijke vinder, You're Never Weird, Thief-Taker; "11/22/63"; "DEEL EEN"), at a small cost on both benches; with three words of two letters or more, no garbled line and some lower case it finds none, both benches NO CHANGE. Not checked against the word list, since mottos are often in another language.
- 2026-10-11: De kus in de nacht's p. 7 checked before its build (pp. 7–12 on a probe copy, no OCR check): "Proloog" a chapter heading, but "Deel een" above it called a page number (confidence 0.06) and dropped. A line the model calls a page number that holds words and no number, directly above a chapter heading, becomes that heading's label (`roles.py`, rule `heading-label`); the heading reads "Deel een / Proloog". Both benches NO CHANGE. The page isn't taken for an epigraph, since a heading is on it.
- 2026-10-11: Een Russische roman's p. 7 checked before its build (pp. 7–10 on a probe copy, no OCR check): its part number "1", read "I", is called a page number and dropped (on a single page the book's numeral slots can't show; seven part pages should in the full build), and the library's pencil marks below it, read as word-like fragments ("Fyarvin er pan ee Ka, An"), stay running text: they aren't at the page's edges, so the role model isn't asked. Left for the full build, whose OCR check should find its readers disagreeing there and ask; a rule waits for what that shows.
- 2026-10-11: The book teaching itself, simulated again on today's trust data (`experiments/probe_trust_pair_prior.py --two-pass`, 20 books, no models): a per-book posterior per substitution pair from the asked suspects' labels, rescoring the unasked, takes silent errors at 0.25/0.5/1 questions a page from 168/106/58 to 159/103/50. Nearly all of it is De kerk (36/30/23 → 33/27/15) and Vuurspel (6 → 3 at 0.25), books with a signature of their own; the tuning books gain 3 errors in all. Kept on the checklist, to build when a user book's review shows such a signature.
- 2026-10-11: A translated book names its translator: `translator` in `book.toml` (optional) becomes a `dc:contributor` in the translator's role (`marc:relators` `trl`) in the EPUB's metadata. Set from the colophons for Stella (Ria van Hengel), Andere levens (Floor Borsboom) and Een Russische roman (Marianne Kaas); Stella rebuilt, epubcheck clean.
- 2026-10-11: De eerlijke vinder and Monterosso mon amour moved from validation to tuning (the user's go): De eerlijke vinder has the most unasked errors of any ordinary book, and studying them is tuning; Monterosso, its CPNB sibling (same series, grid and kind of type), can't validate while it trains, and retiring it would waste a clean pair of Stella's kind. Monterosso's trust data built (467 suspects, layer wrong on 174); the arbiter and the line-role trees retrained with both. Bench against the build before, on the books both sets share: tuning 0.31 → 0.31 NO CHANGE (Reis 0.16 → 0.15); validation BETTER 0.67 → 0.64 [-0.06, -0.01] (De kerk 0.54 → 0.35, You're Never Weird 0.77 → 0.78). New tuning books: De eerlijke vinder 0.99, Monterosso 0.50 a page after review. Validation is now five books, three of them Dutch scans (two Bruna siblings): the user is asked for one or two more Dutch pairs, preferably De Arbeiderspers, Prometheus/Ooievaar, Manteau or Vrijdag.
- 2026-10-11: Every build keeps a dated copy of its EPUB (the user's idea, after the October 7 copy of Stella exposed two regressions): `epub.keep_dated` writes `work/<book>/epubs/<book>-YYYY-MM-DD.epub` (the time added for a second build that day) from `build` and the review's rebuild, skipping a build whose files, the dated package document aside, match the latest copy. Stella's copies of 2026-10-07 (the user's) and 2026-10-11 filed.
- 2026-10-11: Koning Wilders (Van den Brink, Atlas Contact 2017), sourced by the user, joins validation. The scan's colophon ISBN (978 90 450 3486 7) is the printing the EPUB names as its source, and the EPUB is the publisher's own (InDesign export, its fonts obfuscated, its text plain: the candidate probe's "DRM" was the font obfuscation). Derive got two opt-in settings for it: `initial_images` (a drawn initial set as an image without alt text gets its letter from the file name, "letter_D.jpg") and `one_chapter` (a text without headings is one untitled chapter, which the heading count skips). The text layer alone scores 0.63% CER against it, mostly its drawn initials and a quote it invents before "Trump" 11 times (the print has none); the print's "wàs" (2×), "was" in the EPUB, is a known deviation for verdicts.
- 2026-10-11: The fidelity rule names typography (the user: "I'd rather remain faithful to the style in the original work", not a house style as Standard Ebooks applies): each book keeps its printed dash and spacing, ellipsis and quote marks, as the build already measures and sets them; the scoring's glyph folding only keeps a reference EPUB's own conventions from counting against a faithful output. Also asked: whether to learn more of the book's style (guillemets, low quotes, nesting). The quote marks of the 25 books at hand (the user's four, Stella, twenty golden scans) are all ‘-dialogue or “-dialogue; « », „ and ‚ occur only as a few misreads, so those families wait for a book that uses them. The inner (nested) quote is assumed, not learned: on the checklist with the quote group's ~35 unasked words.
- 2026-10-11: Lost-line questions only under a full line. Ex-minnaar's first sample had 27 lost-line questions on 12 pages; 7 pages were verse (a song text, pp. 124–129, and p. 50) whose stanzas leave white space after short lines stopping mid-sentence. Justified prose stops mid-sentence only on a full line, so the line above the gap must reach a right margin at least four of the page's text lines share (reflow's test for justified text); a page without one (all verse) gets none. Bench tuning BETTER (Reis questions 0.33 → 0.32 a page), nothing else moves.
- 2026-10-11: Het laatste bevel (Aspe, Manteau 2013), sourced by the user, joins validation with chapters 1–5 (pages 9–100; the whole book is 304 pages, ~5½ h cold). The scan is the first printing (April 2013), a library copy; the reference is Manteau's e-book with that printing's colophon, as calibre converted it from Mobipocket, which sets every paragraph as a `blockquote`: derive now reads a `blockquote` holding no paragraphs as a paragraph, as it does a `div`. Derived in memory, every bench reference reads exactly as before; the test set's and De aanslag's differ because neither took this afternoon's rederive (the test set is left alone until its single scoring, rederived first). The text layer alone on the slice: 0.31% CER, ordinary slips.
- 2026-10-11: Verminkt (De Bruyn, Manteau 2004), sourced by the user, set up but not admitted: its e-book is made from the fifth printing (2007), the scan is the first (2004), which the candidate rules skip unless the texts match. Its text layer is an older OCR reading ij as y ("hy" 899×, "zyn" 66×): 1.63% CER, word counts within 0.2%. To decide: fold y→ij and look for real-word differences.
- 2026-10-11: Qwen3.8-Flash-Next at ~1 bit (UD-IQ1_S, run by the user in Unsloth Studio with part of it on SSD) screened as a reader on reader set v1: hard lines 276/330 right (qwen3.8:27b 302, glm-ocr 280), easy lines 209/220 (217, 208), right alone on 4 hard lines. Rejected: the squeeze costs more letters than the bigger model gains. 10 min for 550 lines.
- 2026-10-11: Verminkt's first printing (scan) and fifth (e-book) print the same text: with ij and y read alike, every word-level difference left is a reading slip or a word split over a page (`experiments/probe_printing.py`, new, no models, 2 s). The pair is fit; whether it joins a set is the user's call. Its layer writes ij as y, which no other pair tests.
- 2026-10-11: What goes into the EPUB (the user, for `init`): everything of the work, wherever it sits, except what the list leaves out. Left out: scan noise and library marks (stamps, barcodes, handwriting), blank endpapers and cover backs, print furniture (page numbers, running heads, printer and paper notices, "intentionally blank"), "also by" lists and publishers' ads. Taken as metadata, not text: the cover (cover image), title page and colophon (title, author, translator, publisher, year, ISBN, original title), the back-cover blurb (description at most). The table of contents isn't reproduced: it is read to learn the book's structure and what it calls its chapters, which the EPUB's navigation then follows. A back-of-book index waits for non-fiction (its page numbers lead nowhere).
- 2026-10-11: Page kinds labelled by hand for `init` (`tryouts/page-kinds-v1.json`: 31 books, 1,034 pages, every page of the first 16, the last 12 and any under 60 words; the test set left out). Clues from the text layer alone (words, type size, centred lines, a named kind like "Inhoud", colophon words; `experiments/probe_page_signals.py`) settle the long pages inside a book (9,257 in, right) but leave 372 of the short ones unsure and find no book's first page of the text proper: the edge pages need the page image. Next: the sorter's page-kind question on them. A half-title only repeats the title, so it counts as a book detail, not text. Kinds the brief lacked: full-page plates and frontispieces (in, as figures), praise for the book and jacket flaps (out, or the description).
- 2026-10-11: The review page shows a place question's line as it will read: places the OCR check corrected are underlined in their corrected form, places asked in their own question dashed in their likeliest reading (`ocrcheck.Doubt.elsewhere`). Three sampled Ex-minnaar questions looked as if other errors in the line were missed, though each had its own question; 54 of its 390 questions have such places.
- 2026-10-11: `work/` destroyed by the agent: it symlinked `work` into a worktree, committed the link with `git add -A` and merged the branch, which replaced the folder and restored from the user's Downloads and a backup of 2026-10-07; lost for good: Stella's 83 review answers, Goede dochter's 32 slip-review answers, Koning Wilders' verdict; to recompute: every stage cache, the arbiter, the line-role trees, the trust data, bench results. `.gitignore` now `/work`. The user backs up `work/` daily from now on; agents remind them (AGENTS.md).
- 2026-10-11: Ollama's context length was 128k for every model (the app's setting); the user set it to 8k. Each request needs under 1,000 tokens. Readings don't change with it: 100 Koning Wilders line crops read by Qwen and glm-ocr at 128k, at 8k, and at 8k four at a time, identical on all 100 for both (`experiments/probe_num_ctx.py`). glm-ocr loads in 2.3 GB instead of 11 GB and reads ~6× faster (6.6 → 1.1 s a line alongside a build; 0.6 s four at a time); Qwen 2.9 → 2.2 s, 1.3 s four at a time. The judges are still asked one question at a time.
- 2026-10-11: Where Qwen's time goes (`experiments/probe_qwen_speed.py`, Goede dochter's lines, nothing else running): 1.2 s a line at 8k context, of which 0.8 s is prefill (the vision tower ~0.3 s, the ~135 instruction and template tokens ~0.5 s; the image is only ~45 tokens at any resolution, 300 → 150 dpi saves 14 tokens and no time) and 0.35 s writes the ~20 output tokens. Ollama's MLX runner, which serves the nvfp4 build, takes one request at a time whatever `OLLAMA_NUM_PARALLEL` says: 1, 2, 4, 8 and 16 at a time are all 1.16–1.21 s a line, with readings identical (0 of 64 differ at 16 against 1). The runner caches whole prompts (a repeat prefills in 0.05 s, still after five other prompts). With the instructions as the system turn ahead of the image the prefix is reused, 0.80 s a line, but 4 of 64 readings change (one wrong, "GriJze"; one better, a curly closing quote the pipeline's layout set straight; one an ellipsis glyph; one "hielpen"/"helpen" unchecked): a reader candidate for the tryout, not a setting. The 128k → 8k context changed Qwen's speed by nothing; the memory it freed is the gain.
- 2026-10-11: `OLLAMA_NUM_PARALLEL=4` (`launchctl setenv`, app restarted; Ollama had updated itself to 0.40.3 at 22:09): glm-ocr, on llama.cpp under Ollama (`-np 4`), 0.19 → 0.09 s a line at four or eight at a time, 0 of 64 readings differ, and the pipeline's four reader threads get it without a change. The decision models gain nothing (clef-flash 0.55 s a call on llama.cpp with four slots, clef 1.25 s on the MLX runner as an nvfp4 build, one or four at a time alike, choices and confidences identical to four decimals), so their calls stay one after another. A cold page, from these: Qwen ~36 s (30 lines), judges ~5 s, sorter ~3 s (5.4 calls a page), glm-ocr ~3 s, tesseract and layout ~2 s: Qwen is three quarters, and nothing on this server makes it faster without changing what it reads.
- 2026-10-11: The context probe (`experiments/probe_num_ctx.py`) ran beside the rebuild and asked glm-ocr at 128k while the rebuild asked at the 8k default, so Ollama reloaded glm-ocr 40 times in 23 minutes (free memory flipping 50 ↔ 38 GB): its "6.61 s a line at 128k" against 1.11 s at 8k was the reloading, not the context, and the rebuild's glm-ocr stage crawled meanwhile. A probe beside a chain sends the chain's options (AGENTS.md). Ollama's rotated logs (22 GB, llama-server at verbosity 4) were deleted with the user's go.
- 2026-10-12: Reader tryout set v2 (`tryouts/reader-v2.json`): v1's crops and readings were lost with `work/` and its references have been rederived since, so a new set on today's 17 tuning books and references, 850 lines (30 hard and 20 control a book: 510 and 340), Monterosso and De eerlijke vinder in. The tryout now records each model's seconds a line, read one at a time. On it the reader in use, qwen3.8:27b-nvfp4: hard 463/510 right, CER 0.74%, control 338/340, quote marks wrong on 26 and 5 lines, right alone on 74, 1.20 s a line; glm-ocr 409/510 and 321/340, quote marks wrong on 316 and 72. **qwen3.8:27b-q8_0 rejected** as the reader (the same model as a GGUF on Ollama's llama.cpp runner): hard 458/510 (0.76%), control 333/340 (0.04%), quote marks 27/5, right alone on 3 lines, 2.06 s a line one at a time, and 2.2 s a line at 1 to 16 requests at a time alike (`probe_qwen_speed.py`, readings identical): the runner batches glm-ocr (1B) but not this 27B, so a GGUF can't be assumed to batch; a faster reader must be faster on its own. Pulled and not yet screened (no time): `qwen3.8:27b-mxfp8` (Ollama, an MLX build, so one request at a time: a precision candidate) and Unsloth's UD-Q6_K_XL and UD-Q8_K_XL through Unsloth Studio (`openai-local:<id>` in the tryout). Until one wins on both strata, the nvfp4 build stays the reader.
- 2026-10-12: Qwen3.8-27B UD-Q6_K_XL on Unsloth Studio rejected as a reader: 457/510 hard and 334/340 control against the nvfp4's 463 and 338, 1.71 s a line against 1.20. Studio takes several requests but hands them to llama-server one at a time ("1/4 busy · 3 queued"), so 1, 2 and 4 at a time all ran 2.0 s a line; its four slots are reachable only by calling llama-server directly. Its speculative decoding (n-gram and MTP drafts) changed no reading of 107 and saved 16%. Studio readings repeat exactly from run to run. `experiments/stop-run.sh` stops a detached run: quitting its screen left the command running twice.
- 2026-10-12: Qwen3.8-27B UD-Q8_K_XL on Unsloth Studio rejected as a reader: 460/510 hard and 334/340 control against the nvfp4's 463 and 338, 1.76 s a line. Studio loads another quant when a request names it (`unsloth/Qwen3.8-27B-GGUF:UD-Q8_K_XL`, 23 s). On the control lines the Q8_K_XL, the Q6_K_XL and Ollama's q8_0 make the same four errors word for word, which the nvfp4 doesn't: the runtime (llama.cpp against MLX), not the precision, sets them apart. More precision is worth testing only on MLX (mxfp8).
- 2026-10-12: The Stranger's Child (Hollinghurst, Picador paperback 2012, IA Scribe scan; reference Picador's 2011 e-book via calibre) added as a pair, proposed for validation with the bench slice pages 121–208 (part two, chapters 1–7). The text layer against it 0.29% CER over all 564 body pages, 0.32% in the probe, steady across the book. It brings what no other English pair has: a British house (single quotes, spaced en dashes, spaced ". . ."), part labels with titles and mottoes, verse quotations whose prose runs on in the paragraph. It joins validation once the rebuild's `bench tuning` is done.
- 2026-10-12: Normal People (Rooney, Faber & Faber first edition 2018, IA Scribe scan; reference Faber's own 2018 e-book, made from that edition) added as a pair, proposed for validation with the bench slice pages 146–232 (four chapters, 13 scene breaks, emails, a questionnaire). The text layer against it 0.07% CER over the book, steady per band: it tests structure and false alarms more than reading. Its dialogue has no quote marks, which no other pair has. `golden derive` drops text before a book's first heading, so its epigraph is left out of the reference and the scan's body starts after it.
- 2026-10-12: Bench slices capped at about 90 pages, each ending on a chapter (the user: more books give more diversity, smaller slices pay for them). The bench's bootstrap resamples pages within each book, so its power comes from the pages in all, not how they spread over books; the 446 pages added on 2026-10-10 (7.5 h) moved neither bench. Goede dochter 9–162 → 9–99, Reis 11–255 → 11–99, Metro 7–162 → 7–92, De cipier 9–174 → 9–92, De tuin 11–122 → 11–97, Het heft 9–123 → 9–92: tuning 1,792 → 1,365 pages, about 8 h less a cold rebuild, room for four or five more pairs. Done mid-rebuild: Metro was stopped and restarted on its new slice, and Goede dochter's and Reis's trust data redone from their stage caches (the long-slice files kept as `*.long-slice.json`). The arbiter trains on fewer suspects; new pairs give them back.
- 2026-10-12: FKA USA (Reed King, Flatiron first edition 2019, IA Scribe scan; reference Flatiron's e-book of it) joins **tuning** as the first book with real footnotes: 144 at the foot of the page, numbered per chapter in print and EPUB alike. Tuning, not validation, because the footnote stage needs a book to be tuned on. Text layer 0.15–0.47% CER per band. Slice 11–100 (45 notes, two parts' openings, chapter mottos). Scored tonight with the full arbiter (`bench.NO_TRUST_DATA`); its trust data follows the rebuild. King Lear (Folger, S&S 2015) is parked without a manifest: its glosses face the play rather than sit at the foot, the play is verse drama, and its EPUB's apparatus conventions put the play's pages at 6–8% CER.
- 2026-10-12: An audit of the choices behind the scores (bench, quality, signals, the arbiter's settings) for a recorded reason. Most have one in design.md's Measuring section with the numbers: books weighing the same (pooling pages would let three books with 78% of the pages decide), the veto's 99% level, the slip rate, after review, paragraph breaks, `ocr_ask_below`, `MIN_BOOKS`. Seven are picks without a measurement, now listed there as such: slice size, the veto's 0.05, the suspect-pair thresholds, the question budget, headings outside the primary test, footnotes outside the score (its reason expired when footnotes.py came), and quote and dash glyphs folded in the score (blind to a fidelity error the goal counts).
- 2026-10-12, afternoon: For a result tonight (the user can't work on it tomorrow), the slices of the books whose trust data wasn't built yet were cut to their first chapter boundary past about 10 pages (a slice must end on a chapter, as the score compares whole chapters): De cipier 9–33, Artemis 13–34, 11/22/63 15–32, De tuin 11–29, De eerlijke vinder 12–38, Thief-Taker 11–26, Het heft 9–33, Doodskleed 13–22, Het ijzige land 11–21, Monterosso 9–17, FKA USA 11–22; the validation books' trust data likewise (Weird 13–26, De kerk 11–27, Vuurspel 9–29; their bench slices unchanged). Goede dochter, Vals alarm, Crime, Dolittle, Afscheid, Reis and Metro (read in full already) keep theirs. Nothing is deleted: every page read stays cached, so growing the slices later costs only the new pages. Tonight's bench then gives a baseline, and a rescoring of a bench pair on 10, 20, 45 and 90 pages of the seven full books shows what slice size the verdicts need.
- 2026-10-12: Stella's rebuild waits for the Ex-minnaar review and the fixes it teaches (the user): a build before them would be rebuilt anyway.
- 2026-10-12: De eerlijke vinder keeps its whole book (pages 12–95) in tonight's run, not its first chapter: it holds the most errors no question catches (1.02 a page before the loss), the material for the detector of errors every reading shares. About 55 minutes more.
- 2026-10-12: De eerlijke vinder is the book to learn the most from, not only the worst: its reference fits its print (0.3% of lines unplaced, the fewest of any book; layer CER 0.32%, ordinary), so what is left after review is the pipeline's error, not the edition's, and its scan is Stella's format (IA Scribe, 360 ppi, hidden layer, Dutch). Its disagreements (about 7.7 a page) sit in the range of the other books (3–11); what sets it apart is readers agreeing on wrong words. Monterosso is the control for its typeface (checklist, Errors no question asks about).
- 2026-10-12, evening: Monterosso back to its whole book (pages 9–96) in the trust data and the bench. Its chapters run on without a page break, so no chapter ends at a page's foot and a slice short of the whole book cuts one: the 9–17 slice lost chapter 3's end on page 18, and the bench counted its 193 words as errors no question asks about (21.6 a page after review). `chapter_pages.py` gives where a chapter starts, not whether the page before ends with the last one; the slice was chosen without checking that. About 75 minutes of models, then retrain and bench.
- 2026-10-12, evening: The rebuild chain's training step refused to save (Stella's trust data, built from its review answers, was lost with `work/`), the bench failed on the missing arbiter, and progress.txt logged both as exit 0 (the date substitution reset the status). The chain now trains with `--partial`, logs the real status and times the bench with its own page count. First bench after the rebuild (Monterosso cut, FKA USA unchecked): 0.31 wrong words a page after review over the other 16 tuning books, against 0.36 over 17 before the loss on other slices, so not a paired comparison.
- 2026-10-12, evening: Golden verdicts are asked on the region review's page (`VerdictReview`), not a page of their own: each place is a doubt between two readings of its line, ours and the publisher's e-book's, labelled by who claims them; choose or type, Save moves on, arrows move through all. The old page asked in jargon ("output", "scan", "OCR misread", "edition difference"), set its keys in another order than its boxes and had no Save; the user called it a regression of everything the region review had learned. The kind of mistake now follows from the answer. First round on it: De eerlijke vinder, 14 places in about 5 minutes; the e-book was wrong in 7 (`geId` for `geld`, `één` for `een`, `bmx` for `BMX`, a doubled word, two quote marks), so its score counted them against us.
- 2026-10-12, evening: De eerlijke vinder's e-book sets 20 of its dashes as minus signs (U+2212) where the print has spaced en dashes (checked on the scan, p. 62); scoring folds en and em dashes but not a minus sign, so 19 of its 56 unasked errors were this. `hyphen_dash` now also turns a minus sign into the print's dash (a number's sign stays), and the book's manifest declares it. Of the other unasked errors, 25 were page numbers kept in the running text, by the rules and the sorter model (the line-role trees are off by default, `ROBO_SORTER`): a role error in Stella's own scan format, to find.
- 2026-10-12, evening: Bench after the rebuild with Monterosso whole: **0.31** wrong words a page after review over 17 tuning books (FKA USA left out till its fixes; Monterosso 0.17), NO CHANGE against the run before (only the arbiter retrained and six verdicts). The baseline for what follows.
- 2026-10-12, evening: How many pages a book, measured (`experiments/probe_train_pages.py`, output in `work/probes/train-pages-20261012.txt`; `probe_bench_pages.py`). The arbiter trained on each tuning book's first 10, 20, 45 pages or all (777, 1657, 3047, 5357 suspects), each book scored by trees trained without it, lets through 23, 20, 15, 14 errors over the 17 books at one question a page (47, 37, 30, 25 at half a question): more pages teach it, most of the gain by 45, but the whole effect is about 0.01 wrong words a page against the bench's 0.31, since most errors left after review were never suspects. The bench's own interval on the 8 books of 45 pages or more narrows from 0.29 wide at 10 pages to 0.23 at 20 and 0.16 at 45. So the short slices stay short for now: growing them buys a surer bench, not accuracy; the line-role trees and the detector for errors every reading shares come first.
- 2026-10-12, evening: The Stranger's Child (121–208, chapters 15–23) and Normal People (146–232, chapters 22–30) join validation, each slice ending where the next chapter opens a page. Verminkt waits: its e-book has no chapter breaks (`one_chapter`), so it can only be scored whole (417 pages, ~7 h of models).
- 2026-10-13: One review for a golden book (the user, 2026-10-12: "why is it any different at all?"). `roboscriptorium review` on a golden book asks, in the same list as its flagged regions and right after any flag on the same line, each place where the output and the reference differ, as an ordinary question: the line with our words and the e-book's as two labelled readings, the kinds as for any region, the same check on a typed answer (it matches neither reading, or has a straight quote in a curly book). An answer at such a place is a verdict on the reference, never a correction, so it never changes the build; the book's flagged regions are answered as corrections, as Dolittle's 30 already were. `golden review` and the page's verdict mode are gone. Each side's words are shown as written: a place carries them unfolded beside the folded words it is matched and keyed on, a verdict's truth is stored as written and `patch` compares it folded, so the user's `moet –’` no longer reads as `moet —'` on both rows. A place still gets its own question beside an OCR doubt on the same line; folding the e-book's reading into that doubt as one more row waits on mapping its words onto the line.
- 2026-10-13: `bench validation` finished after its halt (`work/bench/validation-20261013T082508-d4c197e.json`, 35 min for the rest; nine books, The Stranger's Child and Normal People new): wrong words a page after review De kerk 0.31, Vuurspel 0.91, You're Never Weird 0.75, Villa Toscane 0.07, De stilte 1.29, Koning Wilders 0.92, Het laatste bevel 0.45, The Stranger's Child 4.57, Normal People 0.23; mean 1.06, 0.62 without The Stranger's Child. Its 4.57 is nearly all one mistake: 370 of 389 unasked errors are "word breaks", the space before an ellipsis. The print sets `Ka . . .’` and `dear . . . ?’` (checked on the scan, p. 134), the text layer reads `Ka...`, and the build takes the book's ellipsis style from the layer ("'...', no space before"), so the e-book's `Well ...` is right. Koning Wilders is named a suspect pair (layer CER 2.45%, over three times the set's median 0.55%).
- 2026-10-13: The ellipsis's gaps are measured on the scan (`typography.measure_ellipses`), not only voted in the text layer: three dots are short runs of ink near the baseline, and the blank before the first and between them is weighed against the line's word gaps (`experiments/probe_ellipsis_scan.py`, 45 s over the golden books, no models). On every golden scan the kinds part widely: before the first dot at most 0.62 of the word gap where the print sets no space (Goede dochter's 0.42 letters against 0.66 the most), at least 0.86 where it does; dots 0.28–0.63 letters apart when tight, 0.91–1.21 when spaced; each agrees with its e-book's space wherever the e-book keeps the print's. The scan sets the gaps, the layer still chooses between the glyph and tight dots (alike on paper), and the layer alone decides with fewer than three measured. With the pipeline's own text layer only The Stranger's Child changes ("..." glued → ". . ." with a space), the one book whose layer lost every gap; its readers' prompt changes with it, so its third reading is redone.
- 2026-10-13: Warm `bench tuning` after the user's verdicts and De eerlijke vinder's minus-sign dashes undone (`work/bench/tuning-20261013T085119-e8ff4b4.json`): BETTER, 0.52 → 0.50 [−0.03, −0.01] wrong words a page after review over all 17 (0.29 over the 16 without FKA USA, against 0.31): De eerlijke vinder 0.91 → 0.68, Goede dochter 0.28 → 0.24, Monterosso 0.50 → 0.47; no tuning book's ellipsis style changed. FKA USA named a suspect pair (30% of its body lines unplaced). The feedback loop agreed with the user: upstream changes decided on the frozen line sets, a quick tier of tuning books' first chapters, cold runs only overnight (checklist).
- 2026-10-13: Third review of the codebase (four reviewers in parallel: the reading half, the writing half, measurement and review, tests with experiments and docs; lint clean, 384 tests, 88% covered). Fixed, each with a test that fails without it: a typed golden verdict that also changed a word of its context took the whole line as the place's words, so `patch` wrote the context into the reference twice (now refused: "change only the marked words"); `reflow.join` dropped the hyphen of a word left open before a conjunction (`voor-` / `en nadelen` → `vooren nadelen`; now `voor- en nadelen` where the word list and the book don't know the closed form); `roles.with_role` and `footnotes.collect` matched a typed line by the `source` it shares with the line below it; a golden book's notes were found on the corrected pages and indexed with positions before answers (`golden.notes.scored`); the review server recorded answers on parallel threads without a lock; no stage cache named its source PDF (`files.check_source`: a build refuses a source that isn't the one its `stages/` were built from); the arbiter read its judges by the order of their votes (`Suspect.judges`). AGENTS.md said every golden book's verdicts are in git: a copyrighted book's (28 of 30) live in `work/golden/<name>/verdicts/`, which only the backup keeps. Found and planned (checklist, "From the codebase review"): the bench folds quote, dash and ellipsis glyphs so it can't see typography; its verdict passes on paragraph breaks alone; book-wide statistics are measured on the slice; measurement logic lives in private `cli.py` helpers that 25 experiments import; the trainers the build needs are unlinted experiments; nine copies of the cache code; `ocrcheck.py`, `reflow.py` and `typography.py` each hold several jobs.
- 2026-10-13: The reviewer's time gets a price in the bench (the user): one wrong word left in a book is worth 20 questions, so each question costs 1/20 of a wrong word besides the chance it is answered wrong (about 1 in 9, `quality.slip_rates`). Until now a question cost only that chance, so anything catching an error more than about one time in nine passed however many questions it added. A comparison now recomputes "after review" from each page's unasked errors and questions, so older runs compare at the new price: this morning's tuning run (`tuning-20261013T085119-e8ff4b4`) against the one before stays BETTER, 0.57 → 0.55 [−0.03, −0.01] (0.52 → 0.50 at the old price). The verdict rule is symmetric now: worse when any slip rate is clearly worse (a change adding questions could be better at the low rate, worse at the high, and pass on fewer paragraph breaks), and a book vetoes on its paragraph breaks as on its words.
- 2026-10-13: The bench counts typography (`disagreements.glyph_errors`, a measure of its own, not in the verdict): words whose quote marks, dashes or ellipsis differ from the reference's where the folded words align, a kind only where the reference sets it in its own glyphs; "…" and "..." alike, as on paper. Warm `bench tuning` (`tuning-20261013T110651-034bc7c`, with the review's eight fixes and the question price): NO CHANGE, 0.55 → 0.55; typography 0.0–2.0 words a page, Dolittle 8.7. Sampled on four books, nearly all of it is one mistake of ours: straight quotes and apostrophes kept from the text layer in curly books (Metro 124 `'` for `’` in its slice, Artemis 32, Vals alarm 28, Dolittle 541 words, its layer straight throughout); nothing in the pipeline curls them. Also named again: 11/22/63 is a suspect pair (6.7% of its body lines unplaced, as on the morning's run), beside FKA USA and Koning Wilders.
- 2026-10-13: Straight quotes and apostrophes curled (`quotes.curl`, before the typography stage, after the answers): opening after a space, bracket, dash or opening mark, closing elsewhere; `’` inside a word and eliding letters (`’s`, `’t`, `’n`, `’em`, `’tis`, `’60s`); a double quote as the book's own opening mark (“ or „, by majority); a mark after a digit or spaced on both sides stays. Counterexamples tested first. Warm `bench tuning` (`tuning-20261013T111434-45aeca0`): NO CHANGE in the verdict (0.55 → 0.55, the words fold quotes), typography to 0.00–0.02 a page on every book but two (Dolittle 8.73 → 0.00, Vals alarm 0.98 → 0.00, Goede dochter 0.41 → 0.00); it cost Goede dochter two wrong words on p. 81, a quote after a dash ending the speech it broke off (`minderjarige –’`) taken as opening, now closing. The two left (Crime 0.22, Artemis 0.45) were the references' own: they set every ellipsis tight where the print spaces its dots, so ellipses now count only where a reference sets spaced dots somewhere.
- 2026-10-13: Warm `bench tuning` after the dash-quote fix and spaced dots scored only where a reference sets them (`tuning-20261013T111904-3782e7e`): NO CHANGE (0.55 → 0.55); typography 0.00–0.09 a page on every tuning book (Crime 0.22 → 0.00, Artemis 0.45 → 0.05), from 0.0–8.7 before the curling.
- 2026-10-13: Three suspect pairs retired (the user: "let's drop the books that are hurting our data"): 11/22/63 (tuning; 6.7% of its body lines unplaced), FKA USA (tuning; 30%, its footnotes among them) and Koning Wilders (validation; its layer at 2.45% CER, over three times the set's median). Their manifests leave git, their bench specs and 11/22/63's trust data go; the arbiter is retrained without it from the cached data (5,306 suspects; Stella's data, lost with work/, still missing, so `--partial`). Their files in work/ stay until the user confirms deleting them. The frozen tryout sets keep their lines.
- 2026-10-13: Learned, not hand-written (the user): "let's not continue with hand-written anything, if we can help it". No new hand-written rule where a learned decision can do the job; existing rules are replaced once the bench says the learned decision is as good (AGENTS.md). First: line roles, where the trees (`sorter.py`) sit off beside the rules.
- 2026-10-13: Warm `bench tuning` with the three pairs retired and the arbiter retrained without 11/22/63 (`tuning-20261013T172537-3371ddc`, paired on the pages both runs share): NO CHANGE, 0.33 → 0.32 after review. The retrained arbiter moves books both ways: Het ijzige land 0.18 → 0.06 (fewer questions, no slips left), Monterosso and Het heft a little better; De tuin van de avondnevel 0.38 → 0.43, the one book significantly worse (questions 1.05 → 1.37 a page), Dolittle 0.34 → 0.40 (unasked 0.15 → 0.21) and Artemis 0.17 → 0.20 not significant.
- 2026-10-13: The feedback loop's two rules written into AGENTS.md's standing rules: upstream changes are chosen on the frozen line sets and the bench confirms; cold runs only overnight or while the user is away. The quick bench tier is still to be built (checklist).
- 2026-10-13: Afscheid van verspilde tijd stays. Its retirement was proposed on docs/golden-books.md's 11.2% unplaced, which counts all lines (running heads, washed-out pages); the rule counts body lines, where the bench measures 0.4% (`tuning-20261013T172537-3371ddc`), and its layer CER (0.20%) is among the set's lowest. It holds most of the bench's washed-out pages now that 11/22/63 is retired. AGENTS.md and the overview's header now say the retirement signal is the bench's, over body lines.
- 2026-10-13: The retired pairs' files deleted from `work/` (11/22/63, FKA USA, Koning Wilders: scans, IA files, caches, references and verdicts, ~87 MB), with the user's yes; they remain in the user's backups.
- 2026-10-13: `bench validation` after the three retirements, the arbiter retrained and The Stranger's Child's re-reading finished (`work/bench/validation-20261013T180141-e04eede.json`, against `validation-20261013T082508-d4c197e`): BETTER, 1.10 → 0.59 [−0.62, −0.40] wrong words a page after review over 8 books, nearly all The Stranger's Child (4.59 → 0.53, its spaced ellipsis now measured on the scan; paragraph F1 0.955 → 0.993). Without it 0.62 → 0.60. Worse within noise of a retrained arbiter: De kerk van de dode meisjes 0.35 → 0.38 (questions 0.75 → 1.02 a page) and You're Never Weird 0.82 → 0.86. 34 min, partly in Low Power Mode.
- 2026-10-13: Fine-tuning a reader considered (the user asked about RLHF): about 140 human answers are too few for learning from preferences, and reading has one right answer, which the golden references give for tens of thousands of lines, so the fitting methods are supervised fine-tuning or reinforcement learning scored by CER. Planned first: a no-model probe of how many wrong words left after review no reader doubted, which bounds what a better reader can gain (checklist). Reinforcement learning is ruled out: it reads every line many times (days at 1.2 s a line), training the 35 GB reader likely won't fit in 64 GB, and with the right text known, supervised fine-tuning gives the same signal for less. Supervised fine-tuning (LoRA on glm-ocr) goes ahead only if about half or more of the wrong words left were never doubted; its costs are few teaching lines (risk of learning the books, not the reading) and a trust-data rebuild, retrain and cold bench whenever the reader changes.
- 2026-10-13: Line-role trees retrained on the warm builds (`experiments/train_sorter.py`, labels from the references; 10 min, De aanslag cold): role errors against the rules, each book scored by trees trained without it, tuning 304 → 179 and validation 116 → 65. Worse on three: Dolittle's headings 14/14 → 6/14 (+4 spurious), Vuurspel's body lines lost 4 → 15, Crime's 0 → 3. Saved (`--save`, one model per left-out tuning book) and benched warm with ROBO_SORTER=1.
- 2026-10-13: Warm `bench tuning` with those trees on (ROBO_SORTER=1): WORSE, 0.32 → 0.34 [+0.01, +0.04] after review; Dolittle 0.40 → 0.61, Thief-Taker and Doodskleed paragraph breaks worse, Afscheid and Crime better. `experiments/probe_sorter_diff.py` (each slice's disagreements with the trees against the rules) showed why: the trees keep one-character lines (a lone "...", "&", a quote mark) as running text, because the labeller (`golden.align`) called every line without a letter or digit body (a share of zero words always "matched"). Fixed: such a line is other unless the reference prints the same marks there. The labels also feed the trust data and the retirement signals; both were counting these specks as body too.
- 2026-10-13: Line-role trees on the fixed labels (`train_sorter.py --rebuild`, warm, 1 min): tuning 275 → 196 role errors against the rules, but validation 90 → 111, worse: Vuurspel loses 43 running-text lines to the trees (3 to the rules), mostly short lines whose measured type size reads 1.2–1.8× body (a short line's size is noisy), and Dolittle's headings fall to 7/14 (+7). The gain on tuning books doesn't carry over, so the trees stay off (ROBO_SORTER=0) and weren't saved on these labels; the rules stay the decision. Validation wasn't used to tune anything here; a fix chosen by looking at Vuurspel would make it a tuning book.
- 2026-10-13: What a perfect reader could still gain (`experiments/probe_reader_ceiling.py`, warm, all 16 tuning slices, output in `work/probes/reader-ceiling/`): 186 wrong words left after a perfect review (no question catches them). Undoubted reading errors (letters, words, punctuation, quotes, no suspect on the place) 53 (29%), of which punctuation 31, letters 9, words 11; doubted reading errors 46 (the arbiter chose wrong without asking); undoubted other 46 (extra words 22, word breaks 14, missing words 10: roles and reflow); doubted other 41 (word breaks 34). Under the agreed bar of about half, so fine-tuning a reader is dropped for now. The biggest single groups are line-end word breaks the readers did doubt (34) and kept specks or furniture (extra words 22). A better reader would also cut questions, which this probe doesn't count.
- 2026-10-13: A fix that puts marks before a line's first word (a dash or quote the layer missed: "the" → "—the") now widens the line's box by their width, an em dash two letters, anything else one (`pdf.spliced`, shared by `ocrcheck.apply` and `corrections.apply`). The box began after the missed dash, so the line looked indented by it and started a paragraph mid-sentence (Dolittle pp. 27, 32, 65: "town" / "—the same"). Warm benches against the rules' runs: tuning NO CHANGE 0.32 → 0.32, Dolittle 0.40 → 0.31 (wrong words 1.76 → 1.63, real), no book worse; validation NO CHANGE 0.59 → 0.59. The first tuning bench compared against the trees-on run (the last saved), which made it look BETTER: `bench` compares with the last run whatever its settings.
- 2026-10-13: `bench` names the settings a run and its baseline differ in (`made with other settings, sorter: True → False`), after a run compared itself by default with the trees-on experiment and read BETTER where the change was NO CHANGE. After an experiment with other settings, pass `--against` the baseline with today's settings.
- 2026-10-13: The line-role trees on fixed labels, benched warm with ROBO_SORTER=1 against the rules' runs: tuning NO CHANGE 0.32 → 0.32 [−0.01, +0.02] (Goede dochter, Metro, Monterosso better; paragraph F1 up on most; Dolittle 0.31 → 0.47, a picture's garbled reading and a running head kept as body unasked, where the rules asked about them: its plates are the only ones among the tuning books, so its left-out trees never saw one); validation WORSE, Vuurspel vetoes (after review 0.86 → 1.02, paragraph breaks 0.45 → 0.59) though the mean moves 0.59 → 0.56 and You're Never Weird's wrong words fall 3.17 → 1.02. The trees stay off. What they lack is coverage (a tuning book with plates, short dialogue lines like Vuurspel's), not a setting; Vuurspel is validation, so nothing was tuned on it.
- 2026-10-13: De tunnels (De Arbeiderspers 2017, IA lending scan, the user's find) joins as a line-role training book only, never scored: the trainer's `EXTRA` takes chapter 12 (pp. 238–270, twelve photo pages with captions), the plates the tuning books lack beside Dolittle's. Its EPUB is an OCR of a print (179 line-end hyphens with a space, small capitals as "jfk"/"BrD", "i/nUr 320" for the scan's "1/NUR 320"), unfit to score words but close enough to label lines. Derive now also takes a paragraph wholly inside a span of a heading class as a heading (its headings are bold spans); checked on the 17 other publisher EPUBs with heading classes: no new heading in any. That check read the markup of the test book's EPUB too (heading counts only, nothing scored or trained).
- 2026-10-13: The user asked again for experiments that test the pipeline's assumptions, not only tuning inside it ("fine tuning has diminishing returns"). A rule in AGENTS.md and a list, "Assumptions to test", at the top of the checklist; the page-level screen moves there from Later. First result: Qwen 3.8 read Dolittle p. 27 whole into paragraphs in 11 s, 2 wrong words and 1 break (the running head taken for a heading).
- 2026-10-13: Whole-page reading (`experiments/probe_page_reader.py`, 19 tuning pages of 7 books, `work/probes/page-reader/`): the pipeline 27 wrong words and 7 paragraph breaks wrong over 18 pages; Qwen 3.8 nvfp4 reading each page whole at 1.6 Mpx, 76 and 32, 12 s a page: letters doubled at page resolution ("gejaank", "doodsbanige", "emotioneel" for "emotieloos"), dialogue paragraphs merged (Goede dochter p. 31, 15 breaks), running heads kept as headings; no replacement, at most one more vote. glm-ocr at 0.7 Mpx (its llama.cpp slots share the 8k context, ~2k each): 845 and 20 over 16 pages (3 failed on context), 4 s a page; near-exact on plain text pages (Reis p. 24 1 word, Metro p. 60 1, breaks right) but it invents text on near-empty and picture pages (part title 158 words, Dolittle's plate 519). Next: glm-ocr at full resolution with a larger context.
- 2026-10-13: glm-ocr whole pages at full resolution (1.6 Mpx; Ollama's context raised to 32k by the user; streamed, since without a stop token it rereads the page until Ollama aborts on "token repeat limit reached", which was every earlier "failure", not the context): 103 wrong words over 18 text pages (plus 304 invented on a part title), 6 s a page; the pipeline 27. Its errors are ones the pipeline already handles (running heads and page numbers kept, line-end hyphens glued in, "veront-schuldigend", lost spaces, "Inzekere") plus a few misreads; but of the pipeline's 9 error places on these pages it reads 5 right, nearly all line joins ("by-the-bye,every", "Well. ...", "Chump?...", Dolittle p. 51's breaks, a page number "26" kept). Both read Monterosso's "B&B" as "B & B": the print may be spaced, a verdict to settle. Next: glm-ocr's page reading as a reader at line joins (spacing, punctuation, breaks) for the arbiter.
- 2026-10-13: Steve Jobs (Isaacson, Spectrum 2011, translated by Rob de Ridder; the user's find) joins as a pair: a lent IA Scribe scan of the fifth printing against the retail EPUB of the first (Elgraphic; layer CER 0.47%, OCR slips only, 89/89 headings). For now its photo insert (pp. 387–402, captions) is a line-role training slice in the trainer's `EXTRA`, not a bench book: the user chose pictures over a text-heavy slice, which keeps its first build to minutes.
- 2026-10-13: Line-role trees on by default (`ROBO_SORTER` defaults to on; tests run on the rules unless they switch the trees on, since the trees are trained on work/'s books). Trained with the two photo slices and a body line weighted ten times its class's balanced share (`sorter.train(body_weight)`, `SORTER_BODY_WEIGHT`, default 10 in the trainer): role errors, rules against trees, tuning 343 → 252 and validation 90 → 66 at weight 1; weight 10 takes Steve Jobs' dropped caption lines 38 → 3. Warm benches against the rules: at weight 1 tuning WORSE (Dolittle 0.31 → 0.88 vetoes: its text set around its drawings dropped), validation NO CHANGE 0.59 → 0.51; at weight 10 tuning NO CHANGE 0.32 → 0.32 (Goede dochter, Metro, Monterosso better), validation NO CHANGE 0.59 → 0.50 [−0.23, +0.00] (Normal People 0.20 → 0.13), no book worse. At least as good, so learned replaces hand-written (AGENTS.md); Dolittle's wrapped text is what's left (design.md).
- 2026-10-13: glm-ocr's whole-page reading as one more reader (`experiments/probe_page_joins.py`, 266 tuning pages with a pipeline error plus 40 clean, pipeline output before review, 28 min): of 473 pipeline error places it reads 226 right (48%: extra words 46, paragraph breaks 42, letters 41, punctuation 41, quotes 35, missing words 21) and 247 wrong too; but it is wrong in 910 places where the pipeline is right (paragraph breaks 303, letters 235, extra words 111, punctuation 110, missing words 101), about 3 a page. As a question source on its own it would cost four false questions for each catch; it can only count as one more vote the arbiter weighs, or where a second page reader agrees with it.
- 2026-10-14: Two page readers against the pipeline (`probe_page_joins.py` with SECOND=qwen3.8:27b-nvfp4, 305 tuning pages, Ollama at 32k, 82 min): where both glm-ocr and Qwen read a place right that the pipeline got wrong, 194 places (paragraph breaks 42, extra words 41, letters 35, punctuation 31, quotes 26, missing words 19); where both read a place wrong alike that the pipeline got right, 208, of which 143 paragraph breaks. Outside paragraph breaks their agreement is right 152 times to 65 (70%: quotes 26 to 5, missing words 19 to 1, punctuation 31 to 11, extra words 41 to 24, letters 35 to 24), about 0.7 such places a page. Paragraph breaks from page readers aren't worth trusting. Not yet known: how many of the 152 the review already asks about; the next probe restricts to the errors left after review.
- 2026-10-14: The two page readers' agreement against the build, on the errors left after review (`experiments/probe_page_agreement.py`, cached readings, no models, 316 tuning pages: all 266 with a pipeline error plus 40 clean and those the first probe read): paragraph breaks aside, they agree on 60 errors no question catches (extra words 27, punctuation 14, letters 13; plus 21 errors not matched to a known disagreement), 71 the review already asks, and 68 places where the build is right. The 60: compound hyphens dropped at a line end ("night-vision", "sea-voyages", "all-suffering", "Flying-serie"), words glued at a join ("by-the-bye,every", "beacknowledged"), De eerlijke vinder's 13 page numbers kept, punctuation across a join ("Well. ..."). As questions: about 0.08 fewer wrong words a page after review against 0.32 (a quarter), for about 0.3 more questions a page, at about 18 s a page of reading (glm-ocr 6, Qwen 12). The largest gain measured in a while; next, the page readers as a stage that raises these places as questions, then the bench.
- 2026-10-14: The page readers go in as two more readers for the arbiter, not as a question of their own (the user's choice between the two): each whole-page reading is aligned back to the layer's lines and fed to the OCR check, so the arbiter learns per kind of error how far to trust each, and fixes, keeps or asks as it does for the line readers. The fixed trigger (ask wherever both agree) would have been quicker but hand-written, and about one question in three needless.
- 2026-10-14: Page readers built (`pagereader.py`, `ROBO_PAGE_READERS`, off): the reading aligned to the layer's words page-wide and split back into lines; on the probe's cached readings it splits Goede dochter's pages (1,123 lines) and Dolittle's (546) line for line; glm-ocr's readings differ from the layer in 201 and 195 places, Qwen's in 181 and 99. A word is cut after a dash that runs on ("interesting—very"): uncut, the reading's word swallowed two of the layer's and pushed a word onto the next line. Split into lines, the readings can't carry most of the 60 errors the probe counted (of the 40 it lists, about 9 sit within a line; 8 are compound hyphens at a line end, 12 kept page numbers, about 10 words glued or split across a join): compound hyphens at a line end and words glued at a join split back to what the layer has, and a kept page number gets no reading. Those need the page reading in the hyphen and line-role decisions. The arbiter now records the readings it was trained on (`Trust.readings`), and a build whose page readers don't match its arbiter stops.
- 2026-10-14: The page readers as a vote on line-end hyphens (`experiments/probe_page_hyphens.py`, no models, the 16 tuning books, the readings cached so far: about 40% of their pages). Reflow is wrong on 34 of 3,184 decidable breaks. Where both page readers write the word whole and alike, they fix 11 of reflow's wrong calls and would break 5 right ones (730 agree with a right call); Qwen alone fixes 14 and breaks 19, glm-ocr alone fixes 13 and breaks 127 (it reads Dutch breaks as hyphenated words: "ont-snapt", "uit-zicht"). Worth having only as evidence a learned hyphen decision weighs beside the word list and the judge, never as a rule; rerun once tonight's reading covers every page.
- 2026-10-14: Lines no page reader reads, as a sign of a line that isn't text (`experiments/probe_page_unread.py`, no models, tuning pages both page readers have read so far). Of the lines neither reading has words for, 250 are not running text (page numbers, running heads, specks) and 4 are (one-word lines: "zin.", "'Ja.'" twice, a smudge "ae es"); of the body lines, 9,926 are read by both. A feature for the line-role trees, where De eerlijke vinder's kept page numbers are; it needs the page readings before the role stage. The trial of tonight's chain on Het ijzige land (3 min): 70 suspects where the data without page readers has 56; 14 raised by the page readers alone, one of them a real error the line readers missed.
- 2026-10-14: Qwen's 8-bit MLX build reading whole pages (`probe_page_reader.py qwen3.8:27b-mxfp8 qwen3.8:27b-nvfp4`, 19 tuning pages, 7 min): 65 wrong words and 9 paragraph breaks wrong against the nvfp4's 76 and 32, the pipeline 30 and 6. The word gap is mostly Goede dochter p. 55 (5 against 14); on Reis p. 40 it is worse (13 against 6). At 19 s a page against 12 and 31 GB against 18, the page reader stays on the nvfp4 (models.md).
- 2026-10-14: A rule in AGENTS.md's engineering practices: sort a probe's catches by where they sit, and check which the planned integration can carry, before building on its total (the page readers' 60, of which about a quarter fit the line-split design).
- 2026-10-14: Each line reader still earns its place (`experiments/probe_reader_ablation.py`, no models: the arbiter retrained without one reader, each of the 16 tuning books held out in turn, one question a page; a version only the removed reader read is gone, and the suspect with it when none is left). Errors left unasked: all three readers 15 (5,306 suspects), without tesseract 21 (3,973), without glm-ocr's lines 43 (4,038), without Qwen's lines 55 (4,557). Tesseract adds least but a quarter of the suspects (judge calls). Approximate: the arbiter still trains on versions the removed reader alone read. Rerun with the page readers' data: can Qwen's page reading stand in for its line reading, 70–75% of a cold build's time?
- 2026-10-14: Low Power Mode measured, roughly: Qwen's page reading (`experiments/read_pages.py`) read about 200 pages an hour on the charger, 113 an hour over 21:59–23:35, a stretch only partly in Low Power Mode, so it costs at least 45% of the speed (run-times.md, AGENTS.md).
- 2026-10-15: The night's queue (`work/runs/queue-20261014.txt`). Page readers: `bench tuning` NO CHANGE 0.32 → 0.32 after review [−0.03, +0.02] (De eerlijke vinder better 0.74 → 0.64, Metro worse 0.27 → 0.36, Monterosso's questions 0.47 → 0.86 a page); `bench validation` printed NO CHANGE at 0.50 → 0.43 [−0.15, −0.01], but wrong words before review up on Het laatste bevel (1.03 → 1.50) and The Stranger's Child (0.79 → 1.15): the arbiter takes page-reader versions it shouldn't on unseen books. Off for now. Reader ablation on the page readers' data: without tesseract 12 → 12 unasked and 1,286 fewer suspects; without both line readers 32, so Qwen's page reading doesn't replace its line reading; the ablation's 83 without the page readers isn't comparable with the bench (errors only they raise count as unasked). ornith-1.5:35b on reader set v2: hard 416/510 (Qwen 463), control 299/340 (Qwen 338), quotes wrong 80/26 (Qwen 26/5), right alone on 4; 0.46 s a line; rejected (models.md). ornith-1.5:9b crashed Ollama (HTTP 500) mid-set. The page-kinds probe failed on its first book, 11/22/63, whose scan was deleted with its retirement on 2026-10-13: the probe now skips a book without a scan, and AGENTS.md has a rule to check every input before queuing a run.
- 2026-10-15: The night spent on the page readers as line readers was mostly the wrong run. By the evening of 2026-10-14 two cheap probes had shown where their gain sits (lines no page reader reads are not text 250 times in 254; line-end compounds), and the line-split design had been shown to reach only about 9 of the probe's 40 listed catches; the queued chain still ran the line-reader design, and the bench came back no change on tuning. Building the line-role feature first would have aimed at the gain and read the same pages. What the night did gain: both readings of every tuning and validation page, cached, which the next two steps need. A rule in AGENTS.md: when a probe moves where the gain is, change the plan before the long run.
- 2026-10-15: The cold A/A of `bench tuning` (`work/bench/tuning-20261015T065429-fdabf21-dirty.json` against `tuning-20261013T210052-1cc82e3-dirty.json`; every cache rebuilt, the first 11 books built 2026-10-13 at 8k and 32k context, the last 5 on 2026-10-15 at 32k): NO CHANGE, 0.32 → 0.33 after review [+0.00, +0.01], no book's interval apart from zero. A cold rebuild moves the score by 0.01 a page at most, so the noise floor for a change that invalidates caches is no wider than for a warm one (design.md, Measuring). Against it, the page readers' validation move (0.50 → 0.43) is beyond rebuild noise. Both cache sets kept: warm in `stages/`, cold in `stages.cold/` of the 16 tuning books, until the user says which to drop.
- 2026-10-15: The page readers' spelling of a line-end compound, on every tuning page and with the hyphen judge's cached answers as the build uses them (`experiments/probe_page_hyphens.py`, no models; the 2026-10-14 run left the judge out). NULL: the build gets 19 of 3,184 decidable line-end hyphens wrong (34 without the judge: it already settles the English compounds the earlier count credited to the readers). Where glm-ocr and Qwen write the word whole and alike they fix 9 (pass-book, sea-voyages, make-up, e-mail, …) and break 10, of which 4 are the probe misjudging words with several hyphens (Zuid-Lon-den, kop-je-onder), so about 9 against 6: a few words over 16 books, under the bench's 0.01 noise floor. Not built; the step is dropped.
- 2026-10-15: Ollama updated itself to 0.40.4, which refuses clef-flash:9b and winnow-ollama:e4b on `/v1/systemone` ("downloaded in a format that is no longer supported"). clef-flash pulled again works; winnow, a Hugging Face GGUF made a decision model by our Modelfile, fails however it is rebuilt, and the library has no `winnow:e4b`. Back to 0.40.3 (the user). Winnow's own server (EldanRing/winnow-inference, the same `/v1/systemone`, in the layout it was trained on) was the alternative, set aside as a judge change needing its own retrain. The new clef-flash build (`0a2a05d6`) against the cached answers on Vals alarm (`experiments/probe_decider_drift.py`): same role on 78 of 80 questions, |Δ P(body)| median 0.003, max 0.07; the two flips are artifact → page number, both dropped.
- 2026-10-15: New rule (the user): validate an idea or fix with the shortest test that answers it, on the pages it touches; the full bench is the regression guard, batched (AGENTS.md). Five-page slices for the bench itself were weighed and not taken: at 0.3–0.9 wrong words a page after review, 80 pages would see one or two of the errors a typical change moves, with a noise band about three times wider; and unchanged pages already cost a paired bench nothing.
- 2026-10-15: De eerlijke vinder's unasked errors (0.59 a page, the most of any tuning book): 28 of 38 were printed page numbers its text layer joins to the body line at their height, six inside a word broken across the page (`experiments/unasked.py`). Fix: `pdf._apart` splits a bare number more than 1.5 line heights from the rest of its line into a line of its own. First version split every such number: `bench tuning` (`tuning-20261015T211317-20b775e-dirty.json`, 64 min, the OCR check redone on every changed page) after review 0.32 → 0.30 [−0.05, −0.01] and De eerlijke vinder 0.74 → 0.28, but WORSE on paragraph breaks 0.19 → 0.21: Dolittle's running heads lost their numbers, their titles became 33 chapter headings, its breaks 0.39 → 0.68 and questions 1.26 → 2.10. Second version splits only beside a line of 0.8 of the page's full width; short test on the two books: Dolittle exactly at baseline, De eerlijke vinder wrong words 0.88 → 0.42, unasked 0.59 → 0.16. Full bench as the regression guard tonight. A cache lesson: the second version first ran on the first one's text layer, as the layer's version wasn't bumped (now 8).
- 2026-10-15: A ceiling for whole-page reading: Claude Opus 5.5 (subagents, the user's permission for this probe only; never a pipeline stage) read the page-reader probe's pages with the same prompt (`experiments/probe_page_reader.py claude-opus-5-5`, readings in `work/probes/page-reader/claude-opus-5-5/`). 17 of 19 pages: both Metro 2033 pages were refused by the content filter (a well-known translation); the in-copyright Dutch pages went through. Wrong words 19 against the pipeline's 29, Qwen's 76 and glm-ocr's 856; breaks 4 against 6, 32 and 35. Read word by word, Claude's one real error is "L*," for "L***,"; the rest are page-edge words and Dolittle's captions, which every reader is charged for. The pipeline's real errors on the same pages are all ones Claude reads right: a drawn initial ("HAT"), a lost subtitle, four breaks in text wrapped around a drawing, a line join ("by-the-bye,every"), a split ellipsis, "B&B" torn. So reading whole pages can be near-perfect, at line joins, initials and wrapped text too, where the pipeline's errors cluster: the architecture to aim for once a local reader gets close; today's local ones don't (Qwen 76 wrong words).
- 2026-10-16: The page-number split's regression guard (text layer v8): `bench tuning` BETTER, 0.32 → 0.30 after review [−0.04, −0.02], paragraph breaks 0.19 → 0.19, no book worse (De eerlijke vinder 0.74 → 0.32); `bench validation` NO CHANGE (0.50 → 0.50). Both runs warm, 5 and 4 minutes. Stella built cold in 50 minutes (67 pages).
- 2026-10-16: Stella against Claude's whole-page reading of its 67 body pages (subagents, the user's permission for this probe only; `experiments/compare_stella_claude.py`, no models; readings and notes in `work/probes/claude-stella/`). 13 differences over 17,889 words, checked on the scan: 5 paragraph breaks at page turns are the comparison's (Claude reads a page alone; the next page's first line is not indented), 2 are one dash the comparison folds (the print sets "irriteert–een" with hairline gaps, the book's measured thin spacing), and 4 are the build's: "féts" (íéts) and "is" (ís), both asked by the review, and "grofwerk", "trofik", unasked, words joined across the tight space after an f that every reader shares (the OCR check fixed a third, "trof ik mezelf rokend", p. 65). The review asks 6 questions. So Stella should come out of review with about 2 wrong words in 67 pages, quotes, dashes and italics not compared, plus any error Claude shares. The joined-after-f pattern is a candidate for the detector of errors every reading shares.
- 2026-10-16: The line readers' caches (glm-ocr's and Qwen's) are keyed on a line's page, text and box, no longer its position on the page (`ocrcheck.line_key`, reading cache v3; a v2 cache is converted on load). Under position keys a line inserted near a page's top had every line below it read again: the page-number split cost 64 minutes of near-cold re-reading on 73 pages, and De eerlijke vinder's cache held 1,058 lines read twice (2 of them differently). Offline rebuild of Dolittle with Ollama unreachable: no reading needed. `bench tuning` warm, 2 minutes: NO CHANGE (0.30 → 0.30, no book moved). The judges still see the line's position in their question (`"line": k`); taking it out changes their input, so it waits for a cold run of its own.
- 2026-10-16: "No page reader reads this line" as a line-role feature: NULL on the short test (`experiments/probe_unread_errors.py tuning`, no models). Of 25,555 lines on pages both page readers read, the build's treatment is wrong on 49; the trees already treat the 657 unread lines right but for 5 kept as text ("«", "t", "it.", a garbled line), the most the feature could fix. The rest are headings and Dolittle's captions, read by both. Not worth running the page readers on every book (about an hour of Qwen per 200 pages); the step is dropped.
- 2026-10-16: Words joined across the tight space after an f (Stella's two unasked errors): across the tuning books' 107 unasked places none is one (6 joins in all, at punctuation and "beacknowledged"; 13 splits, 6 of them Monterosso's "B & B"). Stella's typeface's own; no general fix.
- 2026-10-16: Line-role rules the trees still need, one switched off at a time for the trees' features, trees scored leaving one book out (`experiments/probe_retire_rules.py`, no models, 7 min; errors tuning/validation, baseline 200/57): section-number 230/60, subtitle 218/61, finishes-sentence 206/54, heading-style 183/61, heading-label 200/57 (never fires), numeral-slot 185/58, running-text 185/55; numeral-slot and running-text both off 180/55. Those two RETIRED (`roles.running_text`, `roles._numeral_slots`), the trees retrained (`train_sorter.py --rebuild --save`, 1 min): `bench tuning` NO CHANGE 0.30 → 0.29 [−0.01, +0.00] (Dolittle better 0.49 → 0.45), `bench validation` NO CHANGE 0.50 → 0.51 [−0.00, +0.01]; headings: Reis 9/10 → 8/10 ("De smalfilm" now an artifact at 0.53, its titles all near the trees' boundary), one spurious more on Crime and De kerk, one fewer on Dolittle. heading-style stays (worse on validation), heading-label stays (no evidence either way).
- 2026-10-16: Ex-minnaar built cold (283 min; epubcheck clean) and its questions sampled: 308 over 273 pages, 105 of them unpaired quotes, most false: Brusselmans' Flemish "’m" (hem) counted as a closing quote. `quotes.marks` now takes ’m, ’k and a year's ’73 for elisions, after ’ only: where the layer reads the elision as ‘ ("Ik zei ‘m dat…", three places) the glyph is its error and stays asked. Quote questions 105 → 58, all 261; no golden book changes (170 quote places before and after, none with these elisions), so the bench can't weigh it; the counterexample test is in `tests/test_quotes.py`.
- 2026-10-16: Ex-minnaar's questions sampled (261 after the elision fix; `experiments/sample_questions.py`, crops in `work/probes/questions/ex-minnaar/`). Sound: the chapter numbers set in a decorated box ("twee", p. 37) asked as pictures (5), small-capital section titles mid-page dropped and asked ("Computers kunnen de pot op…", p. 179; 4), stress accents ("Wíe", "Wát", "álle", "níet") the bulk of the OCR doubts, the judges split. A shared misread no reading fixes ("Hiy" for Hij) only typing catches. Not a question but a style choice: the author blanks place names with a short rule on the baseline ("het __plein", "de __straat", ~25 times); the layer and readers render it "_", "__" or "____", so the output is inconsistent. One setting for the book, not a question per place: the user's call.
- 2026-10-16: Ex-minnaar's printed blanks (a rule on the baseline before a withheld place name, "het __plein") are set as "..." (the user): the convention of Brusselmans' publisher in its own e-books ("in de ...straat", Heilige schrik; no other blank before a place word in the user's 37 Brusselmans EPUBs, no underscore anywhere). `book.toml` `blank` sets it; `typography.blanked` turns every run of underscores into it, after the ellipses. Ex-minnaar: 15 blanks set, no underscore left. The layer also reads the rule as "—", "—-", "_-" or drops it; a dash glued to a word can be this book's own (em dashes set without spaces), so those stay review questions (12 of 261), answered by picking the reading with "__".
- 2026-10-16: Stella reviewed (the user): 6 questions, 2 corrections ("íéts", "ís"), the rest kept as built; rebuilt, epubcheck clean. 53 experiment scripts named only in this log and run-times.md deleted (the user: their results are recorded, git keeps them); `sample_questions.py` kept as a tool. The A/A's spare caches (`stages.cold/`, 16 books, 74 MB) deleted.
- 2026-10-16: The review asked about Ex-minnaar's motto (p. 7, "‘It’s closing time’" over its credit line) as running text, flagged centred and without a stop, though the epigraph stage had already set it apart and the EPUB has it as an epigraph (the user, first question of the review). The build now keeps its epigraph lines (`Stages.epigraph_lines`) and `flags.find` asks nothing about what they are, only OCR doubts about their words; the two scripts that called `flags.find` by hand call `scoring.questions`, as the review does.
- 2026-10-16: "An unknown word that splits into two known ones" as a sign of a lost space (Stella's "grofwerk", "trofik"; `experiments/probe_glued_words.py`, no models, all tuning and validation books): 9 such words are errors the reference prints as two ("zeize", "ikweet", "allemogelijke", "Zemoest"), 4,417 are right (Dutch compounds, unknown to the word list). Useless alone; the signal is on the scan, the narrow gap at the split, which a detector of shared errors would have to measure as dashes and ellipses are. Small prize: ~9 errors over the golden books, 2 in Stella.
- 2026-10-16: The epigraph question change, tested (the user: it could hide errors). Every line the epigraph stage marks over the golden books: Stranger's Child p. 123 (an Edith Sitwell poem, a real epigraph) and De eerlijke vinder p. 58, three noise lines ("de", "De |", "ap") taken for a motto, an error in the EPUB from before; its question (a picture box) survives. Narrowed anyway: on epigraph lines only what every motto is goes unasked (centred, set apart, the quote check, `flags._EPIGRAPH_TRAITS`); a garbled line still is (test). `bench tuning` and `bench validation` warm: NO CHANGE, no book's questions moved.
- 2026-10-16: Elision spaces in Ex-minnaar traced (the user asked): no stage of ours removes a space; the text layer glues ’s and ’m to the word before ("maar’s", "kom’s", 14 places), glm-ocr and Qwen mostly read the space. But `ocrcheck._curled` turned glm's straight 's at a word's start into an opening ‘ ("nog ‘s"), a version the judges rightly refused, so the glued layer won. It now curls an elision as ’ (`quotes.ELISION`, with Flemish ’m and ’k). Ex-minnaar: glued elisions 9 → 3, apostrophe-only OCR doubts 40 → 25, questions 261 → 237. `bench tuning` and `bench validation`: NO CHANGE.
- 2026-10-16: The quote check's apostrophes, by the user's rule: a closing ’ is never followed by a letter, so a ’ before one is an apostrophe. As OCR reads it, the layer sometimes sets a printed opening ‘ as ’ (Afscheid "dat ’alles heel anders"), so the rule takes only the short word an elision leaves (one or two letters, a decade, "’tis", "’cause"…, `quotes._ELIDES`); a ’ before a whole word stays a question. Golden books: 8 false quote questions gone (Dolittle "’em", You're Never Weird's "the ’80s"), Afscheid's real one kept; Ex-minnaar unchanged (59). `bench tuning` NO CHANGE, `bench validation` BETTER (You're Never Weird questions 1.39 → 1.33 a page, after review 0.74 → 0.73), no book worse.
- 2026-10-16: OCR doubts asked per line (the user, reviewing Ex-minnaar: "you ask me what the line says … don't ask me twice"; and the text box started from the raw layer line, "Citroén", which no option showed). `ocrcheck.line_doubts`: one question per line with its whole-line options: the text layer as read, each reader and judge, the likeliest at each place, as built. The answer is the line (no span): choosing the layer's own line keeps it over the fixes. Earlier per-place answers count for their line (Stella's six all show answered). The page: "Something else" starts from the option chosen or the central one, ✎ on any option starts from it, typed text is never overwritten; walked in a browser on Stella. `bench tuning` BETTER 0.29 → 0.29 [−0.01, −0.00], `bench validation` BETTER 0.51 → 0.49 [−0.03, −0.01] (You're Never Weird 0.73 → 0.69, De stilte 0.88 → 0.84), questions 653 → 651 and 453 → 431, no book worse.
- 2026-10-16: Small capitals, probed. Telling Qwen that a book may set words in small capitals, on the frozen reader set (`experiments/probe_smallcaps_prompt.py`, 20 min): fixed 1, broke 6 (none about capitals; the prompt's wobble), so not for every book; on Ex-minnaar p. 15 it fixed 2 of 3 "xm". On the scan, Ex-minnaar's small capitals are cut at x-height ("XM" 4.0–4.3 pt against 4.17 pt for "en", "ze"): only letter shape tells them apart. And the layer and readers already read nearly all of them as capitals (BMW ×20, FVT ×10, BRTN ×6, XM ×2, CRX, ABS); left in lower case: "xm" three times on one page, perhaps "rvr". Not worth a detector; the review's typing takes them.
- 2026-10-16: An epigraph needs a word of at least four letters (`epigraphs.LONG_WORD`): De eerlijke vinder p. 58's specks ("de", "De |", "ap") are no longer set as a motto; the two real epigraphs over all books (Stranger's Child p. 123, Ex-minnaar p. 7) stay. Benches NO CHANGE; De eerlijke vinder paragraph F1 0.993 → 0.996. Ex-minnaar rebuilt with the day's changes: 234 questions (308 this morning), sampled: the quote questions left are real layer misreads (a printed “ read as ‘‘, "bermuda’ s", "’Groetjes"), the OCR doubts mostly stress accents.
- 2026-10-16: Two more cheap features for the errors every reading shares, both NULL. Tesseract's word confidence (`experiments/probe_tesseract_confidence.py`, the pages of the tuning books' unasked errors, tesseract only): below 90 it marks 11 of 45 error words and 519 of 7,727 others. Unknown words whose accented variant the word list knows (`experiments/probe_accent_variants.py`, all tuning and validation books): 3 errors ("naiviteit", "creeerden", "geinjecteerd") against 4 right as printed. With the glued-words probe, the shared errors left are mostly stress accents (híj, zíjn, wás) and one-offs no cheap feature finds; the lever is a stronger reader (the ceiling probe: Claude read them right), measured on `probe_page_reader.py` as new local vision models come.
