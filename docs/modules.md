# The code, module by module

What each module in `src/roboscriptorium/` does, as the code stands now; the one-line map
is in AGENTS.md, why each part is there in [design.md](design.md), the walk through a build
in [how-it-works.md](how-it-works.md). Keep this file true when a module changes.

- `cli.py`: typer app, the entry point.
- `config.py`: `Settings`, overridable via `ROBO_OLLAMA_URL`,
  `ROBO_ROLE_MODEL` and the others it lists (`ROBO_READ_MODEL`
  reads quote questions' lines, "" for none).
- `clients/decide.py`: decision models on Ollama's `/v1/systemone` (`for_model`).
- `clients/llama.py`: imajev, a vision decision model whose trained readout a GGUF
  lacks, on llama-server (`ROBO_LLAMA_URL`); as `ROBO_ALARM_MODEL` it is the OCR check's
  second vision judge, asked clef's question, a vote for the arbiter only.
- `clients/ollama.py`: a thin httpx client for Ollama's own API (`doctor` lists the
  models with it). Decision models answer through `clients/decide.py` (or
  `clients/llama.py`), hosted models through `clients/openrouter.py`; the line readers
  (`readers.read_line`, `readers.transcribe`) post to Ollama's `/api/generate`
  themselves.
- `clients/retry.py`: `patiently`, a local model call tried again after a timeout
  (three tries), so one slow answer from a queued Ollama doesn't end a long run.
- `files.py`: `write_atomic`, how every per-book cache is written (whole or not at all);
  `read_cache` and `write_cache`, a versioned JSON cache with the identity it was made
  with (model, prompt, language); the append-only logs; `check_source`, which refuses a source PDF other than the one a
  book's `stages/` were built from (`stages/source.json`).
- `clients/openrouter.py`: a hosted model, named `openrouter:<model>@<provider tag>`
  read by `readers.transcribe`; the key is `OPENROUTER_API_KEY`. As `ROBO_READ_MODEL`
  its readings cache under its own name; as `ROBO_READ_VIA`
  (`openrouter:qwen/qwen3.8-27b@deepinfra/bf16`) it reads in place of the local
  `read_model`, its readings cached under the local name and each listed under `via`
  in the cache, so a later local run reuses them and a reader can tell them apart. A
  decision model's hosted build answers through `decide.HostedClient` (`ROBO_JUDGE_VIA`
  for the judge), its answers cached under the local name with `via`. `experiments/probe_line_reader.py`
  compares it with the local readings of a book.
- `book.py`: a book directory (`work/<book>/`) and its `book.toml`.
- `pdf.py`: reads the PDF text layer as visual lines with boxes; renders pages. An
  image-only PDF, given the book's language, is read by tesseract instead
  (`first_reading`), its words grouped into lines as an OCR layer's are. A bare
  number far from the rest of its line becomes a line of its own (`_apart`).
- `page.py`: what a page's layout says without a model, shared by roles,
  flags and reflow: geometry, edge lines, text repeated across pages, sunk
  pages, printed page numbers, heading labels and numerals, garbled lines.
  "Centred" has two meanings, named apart: `centred_on_page` (loose, chooses
  what to ask the model) and `centred_in_text` (strict, for flagging).
- `roles.py`: line roles via a decision model. A gate picks the doubtful lines
  (page edges, short centred lines), features include cross-page repetition,
  and answers are cached in `stages/decisions.jsonl`. Rules in code then
  override the model where layout settles it; `LineRole.rule` names the rule
  that set a role ("" for the model's own answer).
- `sorter.py`: line roles from trees over layout, type, repetition and the role
  model's answer, in place of `roles.py`'s rules (`ROBO_SORTER=1`, on by default). Its
  copies without each tuning book are scored by `bench`.
- `sorterdata.py`: the trees' labelled lines (golden alignment on the bench's slices and
  a few training-only ones, cached in `work/probes/sorter/`) and the models to save;
  scored and saved by `experiments/train_sorter.py [--save]`.
- `reflow.py`: lines → blocks (headings, paragraphs; indents, punctuation spacing),
  lines joined by `hyphens.join`, a single-quoted book's misread openings and an old
  layer's closings mended by `quotes`. Without roles it falls back to a footer heuristic.
- `scanstyle.py`: the book's dash and ellipsis as measured on the scan (`guess`,
  `measure_ellipses`, cached); `typography.py` sets the text in the style found.
- `ink.py`: `threshold`, the grey level between ink and paper (Otsu), for the italics,
  type and scan measurements.
- `hyphens.py`: lines joined across their ends (`join`). A line-end hyphen stays or goes
  by evidence in order: the book's own spelling (`spellings`), the word list, a capital
  after the break, the parts beside an inner hyphen, then `Compounds`, the judge
  (`judge_model`) asked whether an English hyphen nothing else decides is the word's
  own, its answers cached by the hyphenated word in `stages/compounds.json` (only
  English books ask it, `asked`; docs/design.md).
- `ir.py`: the IR (`Document`; `Paragraph` and `Heading` with `SourceRef`s back
  to page lines, a paragraph marking a scene break before it; `Figure` with its image file, page box and caption).
- `figures.py`: the pictures in the book. The layout model's figures on body
  pages (≥ 0.5) unless a human answered them as something else; trimmed
  where a caption overlaps; sideways plates turned upright (the human's turn,
  else the quarter turn in which the caption reads); captions from the
  human, else a sideways caption's reading. Each goes after the last block
  that starts above it; JPEG at 300 dpi, at most 1600 px.
- `epub.py`: IR → EPUB 3, hand-written with zipfile (no ebooklib). `keep_dated` keeps each
  build's EPUB in `work/<book>/epubs/` (`<book>-YYYY-MM-DD.epub`, the time added for a
  second that day) unless it holds the same book as the latest copy (`build` and the
  review's rebuild call it), so an earlier build stays to compare against.
- `pipeline.py`: runs the stages for one book and caches artefacts under `stages/`:
  the text layer in `textlayer.json`, the finished IR in `document.json`, and each
  stage's own cache named under its module.
- `docs/pipeline.d2`: the README's diagram of the stages and the model behind
  each; kept current under the standing rules.
- `experiments/`: probes for comparing models and settings, the trainers of the trust
  and line-role models (`train_ocr_trust.py`, `train_sorter.py`), the bench's tools
  (`golden_overview.py`, `chapter_pages.py`) and the run helpers (`detached.sh`,
  `timed.sh`). They use `golden.scoring`, never the CLI's private helpers.
- `experiments/tryout.py`: a candidate model tried for a role (reader, judge) on a frozen,
  versioned set (`tryouts/<role>-v<N>.json` in git, crops in `work/tryout/`), against
  the model playing the role; results in `tryouts/results.jsonl`. The screen before a
  trust-data rebuild and `bench`.
- `golden/`: golden books. `manifest.py` (scans, fetch with sha256 check),
  `gutenberg.py` (derives the reference text from a Project Gutenberg EPUB),
  `epub.py` (from a publisher's EPUB: headings by tag or class prefix),
  `se.py` (derives Standard Ebooks' text, kept for later style work),
  `reference.py` (reads the reference chapters, with their italic words),
  `signals.py` (whether a pair still measures the pipeline: layer CER and unplaced
  lines against the reference, printed by `bench`), `notes.py` (a reference's footnotes, `notes.txt` from the manifest's
  `note_classes`: the scan's footnote lines are left out of every score),
  `align.py` (labels a golden scan's text-layer lines with the reference words they
  hold, and their role: heading, body or furniture), `scoring.py` (a golden spec
  `work/<book>[:pages[:chapters]]` built and scored: `build` gives the build, the
  reference with verdicts applied, the remaining differences and the review's
  questions; `scored`, `verdicts`, `reference`, `questions`, `page_range`; what `eval`,
  `quality`, `review`, `bench` and the experiments share).
- `evaluate.py`: CER, WER, paragraph F1 and scene breaks (found where the reference has
  one, and set elsewhere) against a golden reference. Typography
  the EPUB may set differently (quote and dash glyphs, an ellipsis glyph or spaced
  dots, joiners) is folded on both sides and counted per side (`folded_*`, printed
  by `eval`), so a pair's convention gap is visible, not silent.
- `disagreements.py`: where output and reference differ, located on the scan;
  clearly garbled output and whitespace-only differences are auto-resolved; the pages
  of paragraph breaks set wrong (`break_errors`) and of words whose quote marks, dashes
  or ellipsis are set wrong (`glyph_errors`, the kinds a reference can speak for from
  `glyph_kinds`).
  Verdicts (what the scan prints, plus a mistake category) are stored per scan
  and patched into the reference by `eval`.
- `bench.py` (`roboscriptorium bench [tuning|validation|test]`): **the** measure for a
  change. Pinned golden slices per set, scored with `evaluate` and `quality`,
  saved whole to `work/bench/` (commit, settings, decider, model versions,
  per-page counts, paragraph breaks set wrong among them) and compared with the
  previous run page by page (or `--against` a named one), naming any setting the two
  were made with differently (`bench.settings_changed`): an experiment's run with
  other settings is the next run's default baseline. One test decides: "after review", each book of the set
  weighing the same, must improve at the low, mean and high slip rate, or the
  paragraph breaks set wrong must fall, with neither clearly worse at any slip rate,
  and no book may get worse by ≥ 0.05 wrong words or breaks per page on the mean with
  its 99% interval above zero (a veto); the per-book intervals are diagnostics, and so are the heading and paragraph-F1 changes it prints beside the test (`bench.structure`), which the word counts can't see. A tuning book is
  scored with the trust model trained without it
  (`ocr-trust-without-<book>.pkl`, written by `train_ocr_trust.py --save`). "After review"
  adds, per question asked, the reviewer's own slips (`quality.slip_rates`, a Beta
  posterior from 10 wrong of 100 checked answers, Stella's and Goede dochter's reviews
  pooled) and the reviewer's time (`quality.QUESTION_COST`, 1/20 of a wrong word),
  recomputed from the saved counts when two runs are compared (`bench.after_review`). Run it before and after a change; cite its
  starred lines, not single CER figures.
- `quality.py` (`roboscriptorium quality book[:pages[:chapters]] …`): what a
  reviewer is left with. Wrong words per page before review and left unasked,
  with every question and at budgets of 0.25, 0.5 and 1 question per page
  (questions ranked by how often their kind caught an error in the *other*
  books given), each with a 95% bootstrap interval over pages; the unasked
  errors by kind (punctuation, quotes, letters, word breaks, missing words…).
- `flags.py`: regions a human should check, i.e. what isn't plain running
  text: headings, lines dropped mid-page or without the model being sure,
  garbled text, centred or set-apart lines. Page furniture (repeated running
  heads, printed page numbers) isn't flagged. With layout regions it also
  flags pictures, captions, titles that aren't headings, and text the text
  layer lacks (one region per page, as an area rather than lines), and a line's height
  of white space inside a sentence, where the layer lost a line (`lost-line`).
- `faint.py`: body pages scanned too faint to read (Afscheid's and 11/22/63's
  washed-out pages): the grey levels between the paper and the ink inside the text
  layer's line boxes, at 60 dpi, cached in `stages/contrast.json`; a page with words and
  under 30 levels (printed pages measure 50 or more, washed-out ones under 10). On scans
  only (`Stages.faint_pages`); `flags.find` makes such a page one `washed-out` region,
  and the OCR check leaves it out (its readers invent fluent text on faint crops).
- `quotes.py`: in a single-quoted book (`single_quoted`) a “ no ” closes is a misread ‘
  (`open_single`); an old layer's `'` closing a `"` is mended (`close_quotes`). `curl`, the straight quotes and apostrophes left from the text layer
  curled by their place after the answers (feet, inches and marks spaced on both sides
  stay); places where a paragraph's curly quotes don't pair up (a lost
  opening ‘, a lost closing ’, also at a paragraph's end before one that opens with a
  quote), apostrophes, Dutch `’s`, plural possessives and nested quotes aside; and
  speech closed on a letter at a paragraph's end (a lost stop); a mark left open right
  after a word is placed where it stands, not at the end. Found on the
  text before a human's answers (`Stages.quote_lines`) and flagged as `quotes`.
  Each such line (short ones too) is read by `read_model` (qwen3.8) with the book's
  typesetting in the prompt (`style_prompt`: quote marks, ellipsis, dashes); its
  marks on the OCR-checked line's letters (`proposed`) become the question's second
  reading (`Stages.quote_readings`, `pipeline.proposals`). The readings are cached with
  the OCR check's third readings in `stages/third-reading.json`, under the same model
  and prompt.
- `layout.py`: DocLayout-YOLO regions per page from the page image, cached in
  `stages/layout.json`; run on every build when the `layout` group is installed
  (`layout.available`). Picture-only pages are also run turned a
  quarter, to find captions printed sideways.
- `typestyle.py`: each line's type relative to the body text, measured on the
  page image (no model): size (tallest letters to baseline), stroke width, ink
  width per letter, capitals; cached in `stages/type.json`. `groups` gathers
  display lines (larger or capitals) set alike in one place on their pages;
  `roles.py` lets such a group share the role most of it got.
- `italics.py`: italic words, from each text-layer word's stroke slant on
  the page image (no model; scans and born-digital PDFs alike), marked on paragraphs by aligning their
  words with their source lines'; cached in `stages/italics.json`. The EPUB
  sets them in `<i>`; `eval` scores italic words.
- `missing.py`: printed lines the OCR layer lacks (bare chapter numbers,
  page numbers, short lines of dialogue). A layout region about one line tall
  (up to five above a sunk page's text, where Artemis draws its chapter numbers in a
  circle) with no text-layer line in it is read by glm-ocr and added to a copy of the
  page in reading order, before the line roles; figures, captions and regions
  a human answered are left alone. Scans only; cached in
  `stages/missing-lines.json`. Review answers find their lines again by text
  when lines are added above them.
- `readers.py`: the readings of a page's lines besides the text layer: each line's crop
  (`line_boxes`, `crop_span`), read by glm-ocr (`read_line`), the read model told the
  book's style (`transcribe`) and tesseract (`tesseract_readings`), each cached per book
  keyed on a line's page, text and box (`line_key`); Cyrillic transliterated (`ocr.latin`).
- `ocrdoubts.py`: the OCR check's suspects as review questions, one place (`doubts`) or a
  whole line with every source's version (`line_doubts`).
- `ocrcheck.py`: checks a scan's OCR layer (born-digital PDFs are skipped)
  against glm-ocr's reading of each body line's crop (short lines too) (`ROBO_OCR_MODEL`),
  cached in `stages/second-reading.json`, tesseract's of the page, and
  `read_model`'s (qwen3.8) of the crop, told the book's typesetting
  (`stages/third-reading.json`; readings by another model or prompt are kept aside
  in `third-reading.<hash>.json` and come back when asked for). Where a line's readings differ, clef picks from
  the crop and winnow (`ROBO_CHECK_MODEL`) from the sentence. The learned trust
  (`trust.py`, on by default) then fixes, keeps or asks, its substitution table
  extended with the book's own answers (`corrections.answered`, `trust.with_answers`);
  an asked place whose kind of change its readers were reliably right about in those
  answers is decided (`trust.book_buckets`, `by_book`). The fixed rule
  (`ROBO_OCR_TRUST=0`, `_choose`) applies a version when both judges pick it with clef
  ≥ 0.3 (`SURE`), or clef alone picks it with ≥ 0.5 (`SURE_ALONE`) where the versions
  differ only in punctuation, dashes or spacing; anything else becomes an `ocr-doubt`
  review region. Fixes go into a copy of the pages before reflow. Tesseract's page
  readings are cached in `stages/tesseract.json`.
  The judge is `judge_model` (clef:27b, `ROBO_JUDGE_MODEL`), not the role
  model; it is told the book's typesetting (`quotes.style_note`) and sees the
  versions set off by ⟨ ⟩. Suspects are saved to
  `stages/ocr-check.json`; `eval --no-check-ocr` skips the stage.
- `pagereader.py`: glm-ocr (`ocr_model`) and Qwen (`read_model`) read each body page
  whole (`read_page`, glm-ocr streamed and cut where it starts over), cached per page in
  `stages/page-reading-<reader>.json` under the model, prompt and size. `split_lines`
  aligns a reading's words to the layer's page-wide and gives each line its words, a word
  broken over a line end cut where the layer cuts it. With `ROBO_PAGE_READERS=1` the
  OCR check gets them as the readings `glm-page` and `qwen-page`; the arbiter must be
  trained with them (`trust.Trust.readings`), or the build stops.
- `lexicon.py`: a language's word list, unpacked from tesseract's own model
  (`<lang>.traineddata`'s LSTM word DAWG: Dutch 478k words, English 338k) into
  `work/lexicon/`, and which one of several readings it knows all the words
  of. Word breaks, line-end fragments, stress accents and words without a
  vowel get no verdict. The OCR check records its pick as a vote ("word list",
  shown in the review) but doesn't act on it.
- `trustdata.py`: the arbiter's training data and saved models. `SPECS` are the golden
  books and slices it is built from (a tuning book left out is in `bench.NO_TRUST_DATA`,
  which a test keeps in step); `load` builds or reads a book's rows, each suspect's
  versions labelled by the aligned reference (Stella's by the user's answers);
  `usable`, `rows_of` and `trainable` pick what trains, the validation and test books
  never; `models_to_save` trains the model the pipeline uses and a copy without each
  tuning book. Run by `experiments/ocr_trust_data.py` and
  `experiments/train_ocr_trust.py`, which also scores the model leaving each book out.
- `trust.py`: learned trust for the OCR check. A model (shallow gradient-boosted
  trees) scores each version of a suspect from the judges' picks and confidence,
  which second readings read it, the word list, the kind of difference and a prior
  for its exact substitution (`pair`: how often `|`→`I` was the print in the training
  books, pairs seen in two books or more, saved with the model);
  the least sure suspects are asked up to `ROBO_OCR_QUESTIONS` per page, except
  one whose best version is right with a chance of `ROBO_OCR_ASK_BELOW` (0.8) or more
  (its sureness calibrated on books it wasn't trained on, `trust.sureness`); the rest take
  their best version. The budget is book-wide (questions per page ×
  pages), so a bad page can take more than one. On by default (`ROBO_OCR_TRUST=0`
  for the fixed rule); a missing model, or one saved for another version or
  feature width (`MODEL_VERSION`, `FEATURES`), stops the build. The model lives
  in `work/models/ocr-trust.pkl`, trained by `experiments/train_ocr_trust.py
  --save` on the tuning books' suspects, never the validation ones (it refuses while a
  tuning book's data is missing or built before the current readings)
  (`experiments/ocr_trust_data.py`). Training uses only the votes of the judges the
  settings name. An ablation (another reader set, say) keeps its data and models apart:
  `ROBO_TRUST_DATA` for the data folder, `ROBO_OCR_TRUST_MODEL` for the model, whose
  leave-one-out copies sit beside it.
- `typography.py`: the book's ellipsis style (`…`, `...` or `. . .`, with or without a
  space before): its gaps measured on a scan (`measure_ellipses`, cached in
  `stages/ellipsis.json`; the dots and the blanks before and between them against the
  line's word gaps), its glyph or dots read in the text layer (`guess_ellipsis`, alone
  when too few ellipses can be measured), combined by `scanned_style`; or set in
  `book.toml` (`ellipsis`, `ellipsis_space`). It is set on every three-dot ellipsis in the output (no-break
  spaces); four dots and an ellipsis opening a quote are left alone. And the
  book's dash style (en or em; no, thin or word spacing),
  from `book.toml` (`dash`, `dash_spacing`) or, on a scan, measured on the page
  image (the stroke's length against the line's letter width, its gaps against
  the gaps between words; cached in `stages/typography.json`, and printed so a
  human can settle it). Every dash between words in the output is then set that
  way (a no-break space before it, narrow when thin); number ranges and hyphens
  stay. The OCR check doesn't raise dash kind or spacing as a doubt. And a printed
  blank, a rule standing for a withheld word ("het __plein"): where `book.toml` sets
  `blank`, every run of underscores becomes it (`blanked`). A rule the layer reads as a
  dash, or leaves out, is a review question (a dash glued to a word can be the book's
  own).
- `ocr.py`: `latin`, a reading's Cyrillic letters transliterated (the line and page
  readers' output goes through it); tesseract on a page region, for drafts a human corrects (text the
  text layer lacks, or reads as scraps because it is printed sideways).
- `initials.py`: guesses the letter of a decorated initial: the letters that
  make the word beside it a word (book vocabulary plus the system word list),
  then the role model picks among them from the drawing.
- `corrections.py`: a human's answers about regions (text, heading, drop,
  image, initial, caption, optionally the text as printed and the turn that
  makes the region upright; typed text for a missing region is
  inserted where the region sits, blank lines separating paragraphs), stored in
  `work/<book>/review/regions.jsonl` and applied to the line roles on the
  next build.
  It also takes answers about one place in a line (`Flag.span`):
  an answer changes only that span, so several answers about one line, and the
  OCR check's own fixes elsewhere in it, combine (`apply(..., fixes)`). A break
  hyphen's place is asked across the break (`Flag.joined`: "dankbaar" or "dank
  baar") and answered back as the hyphen or none.
- `errata.py`: the edition's departures from its print, misprints the reviewer chose to
  correct, in `work/<book>/errata.toml`: each the page and the printed words, with the
  words as they should read. Applied to the reflowed running text and notes together
  (`apply`), where a printed word broken across lines is whole; quote glyphs match either
  way. An erratum whose words its page holds not exactly once stops the build
  (`Unmatched`). The review writes one from a line and its correction (`from_line`: the
  words that differ, grown by words of the line until unique on the page) and keeps one
  per printed words (`save`).
- `footnotes.py`: the footnotes at a page's foot (`lines`: below the text, in type under
  0.78 of the body's and lighter than 1.2 of its strokes, opening on a mark, mostly
  words), given a role reflow leaves out (`with_notes`, by `Line.source` on corrected
  pages), collected into `ir.Note`s from the checked and answered pages (`collect`), and
  linked to the paragraph carrying the mark on their page (`link`, `Paragraph.notes`).
  `epub.py` sets the mark as a noteref and the note as an `aside` after the paragraph.
- `epigraphs.py`: a motto on a page of its own (`lines`: at most six short lines set in
  at least 0.15 of a full line from the book's margin, read on full pages nearby, three
  words or more, none garbled, not all capitals, no heading on the page). Reflow makes
  each line a paragraph marked `epigraph`; `epub.py` sets a run of them as one
  `blockquote epub:type="epigraph"`. The words stay in the scored paragraphs.
- `review.py` + `regions.html`: the local review page (stdlib HTTP server on
  127.0.0.1), with scan crops: the flagged regions of any book and, for a golden book,
  its places where our text and the reference differ (`GoldenQuestions`), in the same
  list as a doubt between the two, answered as verdicts.
