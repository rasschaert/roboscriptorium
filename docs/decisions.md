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
- 2026-10-08: A reader of the finished text planned (checklist 3c), on the user's point
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
  question a page from 23 to 11 over nine books, leave-one-out (checklist 6b).
- 2026-10-08: Trust gets a prior for the exact substitution a version makes (`trust.pair`,
  model version 3, 23 features; the priors saved with the model). On the labelled
  suspects each scan's errors are three to five signatures, nearly deterministic across
  books (a lost `’` the print 223/234, `|`→`I` 59/59, `é`→`ë` 28/28; glm-ocr dropping a
  `’` wrong 232/235), which the kind features can't tell apart. Leave one book out over
  nine books: silent errors at 0/.25/.5/1 questions a page 153/87/44/23 → 117/50/31/11.
  A pair counts when seen in ≥ 2 training books (Opus's caution: one book's reference
  conventions must not teach the rest) and a training suspect is scored without its own
  label (with it in, 76/48/28 at .25/.5/1: worse than no prior). Its bench step waits for
  the retrain (checklist 6b). The saved model stays version 1 until `--save`.
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
  xfail test naming checklist 6b, not an assertion of the wrong output.
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
