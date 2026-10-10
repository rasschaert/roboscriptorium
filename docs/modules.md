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
  (`ocrcheck.read_line`, `ocrcheck.transcribe`) post to Ollama's `/api/generate`
  themselves.
- `clients/retry.py`: `patiently`, a local model call tried again after a timeout
  (three tries), so one slow answer from a queued Ollama doesn't end a long run.
- `files.py`: `write_atomic`, how every per-book cache is written (whole or not at all).
- `clients/openrouter.py`: a hosted model, named `openrouter:<model>@<provider tag>`
  read by `ocrcheck.transcribe`; the key is `OPENROUTER_API_KEY`. As `ROBO_READ_MODEL`
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
  (`first_reading`), its words grouped into lines as an OCR layer's are.
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
  model's answer, in place of `roles.py`'s rules (`ROBO_SORTER=1`, off until the bench
  says otherwise); trained by `experiments/train_sorter.py --save`, its copies without
  each tuning book scored by `bench`.
- `reflow.py`: lines → blocks (headings, paragraphs; indents, de-hyphenation,
  punctuation spacing). A line-end hyphen stays or goes by evidence in order: the
  book's own spelling, the word list, a capital after the break, the parts beside an
  inner hyphen (docs/design.md). Without roles it falls back to a footer heuristic.
- `ir.py`: the IR (`Document`; `Paragraph` and `Heading` with `SourceRef`s back
  to page lines, a paragraph marking a scene break before it; `Figure` with its image file, page box and caption).
- `figures.py`: the pictures in the book. The layout model's figures on body
  pages (≥ 0.5) unless a human answered them as something else; trimmed
  where a caption overlaps; sideways plates turned upright (the human's turn,
  else the quarter turn in which the caption reads); captions from the
  human, else a sideways caption's reading. Each goes after the last block
  that starts above it; JPEG at 300 dpi, at most 1600 px.
- `epub.py`: IR → EPUB 3, hand-written with zipfile (no ebooklib).
- `pipeline.py`: runs the stages for one book and caches artefacts under `stages/`:
  the text layer in `textlayer.json`, the finished IR in `document.json`, and each
  stage's own cache named under its module.
- `docs/pipeline.d2`: the README's diagram of the stages and the model behind
  each; kept current under the standing rules.
- `experiments/`: throwaway probes for comparing models (line roles, page types).
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
  hold, and their role: heading, body or furniture).
- `evaluate.py`: CER, WER and paragraph F1 against a golden reference. Typography
  the EPUB may set differently (quote and dash glyphs, an ellipsis glyph or spaced
  dots, joiners) is folded on both sides and counted per side (`folded_*`, printed
  by `eval`), so a pair's convention gap is visible, not silent.
- `disagreements.py`: where output and reference differ, located on the scan;
  clearly garbled output and whitespace-only differences are auto-resolved.
  Verdicts (what the scan prints, plus a mistake category) are stored per scan
  and patched into the reference by `eval`.
- `bench.py` (`roboscriptorium bench [tuning|validation|test]`): **the** measure for a
  change. Pinned golden slices per set, scored with `evaluate` and `quality`,
  saved whole to `work/bench/` (commit, settings, decider, model versions,
  per-page counts, paragraph breaks set wrong among them) and compared with the
  previous run page by page. One test decides: "after review", each book of the set
  weighing the same, must improve at the low, mean and high slip rate, or the
  paragraph breaks set wrong must fall, neither clearly rising, and no book may get
  worse by ≥ 0.05 wrong words per page on the mean with its 99% interval above zero
  (a veto); the per-book intervals are diagnostics, and so are the heading and paragraph-F1 changes it prints beside the test (`bench.structure`), which the word counts can't see. A tuning book is
  scored with the trust model trained without it
  (`ocr-trust-without-<book>.pkl`, written by `train_ocr_trust.py --save`). "After review"
  adds the reviewer's own slips per question asked (`quality.slip_rates`, a Beta
  posterior from 10 wrong of 100 checked answers, Stella's and Goede dochter's reviews pooled). Run it before and after a change; cite its
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
- `quotes.py`: places where a paragraph's curly quotes don't pair up (a lost
  opening ‘, a lost closing ’), apostrophes, Dutch `’s`, plural possessives,
  nested quotes and quotations running over paragraphs aside. Found on the
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
- `ocrcheck.py`: checks a scan's OCR layer (born-digital PDFs are skipped)
  against glm-ocr's reading of each body line's crop (short lines too) (`ROBO_OCR_MODEL`),
  cached in `stages/second-reading.json`, tesseract's of the page, and
  `read_model`'s (qwen3.8) of the crop, told the book's typesetting
  (`stages/third-reading.json`; readings by another model or prompt are kept aside
  in `third-reading.<hash>.json` and come back when asked for). Where a line's readings differ, clef picks from
  the crop and winnow (`ROBO_CHECK_MODEL`) from the sentence. The learned trust
  (`trust.py`, on by default) then fixes, keeps or asks. The fixed rule
  (`ROBO_OCR_TRUST=0`, `_choose`) applies a version when both judges pick it with clef
  ≥ 0.3 (`SURE`), or clef alone picks it with ≥ 0.5 (`SURE_ALONE`) where the versions
  differ only in punctuation, dashes or spacing; anything else becomes an `ocr-doubt`
  review region. Fixes go into a copy of the pages before reflow. Tesseract's page
  readings are cached in `stages/tesseract.json`.
  The judge is `judge_model` (clef:27b, `ROBO_JUDGE_MODEL`), not the role
  model; it is told the book's typesetting (`quotes.style_note`) and sees the
  versions set off by ⟨ ⟩. Suspects are saved to
  `stages/ocr-check.json`; `eval --no-check-ocr` skips the stage.
- `lexicon.py`: a language's word list, unpacked from tesseract's own model
  (`<lang>.traineddata`'s LSTM word DAWG: Dutch 478k words, English 338k) into
  `work/lexicon/`, and which one of several readings it knows all the words
  of. Word breaks, line-end fragments, stress accents and words without a
  vowel get no verdict. The OCR check records its pick as a vote ("word list",
  shown in the review) but doesn't act on it.
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
  space before), read in a scan's text layer or set in `book.toml` (`ellipsis`,
  `ellipsis_space`), and set on every three-dot ellipsis in the output (no-break
  spaces); four dots and an ellipsis opening a quote are left alone. And the
  book's dash style (en or em; no, thin or word spacing),
  from `book.toml` (`dash`, `dash_spacing`) or, on a scan, measured on the page
  image (the stroke's length against the line's letter width, its gaps against
  the gaps between words; cached in `stages/typography.json`, and printed so a
  human can settle it). Every dash between words in the output is then set that
  way (a no-break space before it, narrow when thin); number ranges and hyphens
  stay. The OCR check doesn't raise dash kind or spacing as a doubt.
- `ocr.py`: tesseract on a page region, for drafts a human corrects (text the
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
- `review.py` + `regions.html` / `review.html`: the local review pages (stdlib
  HTTP server on 127.0.0.1), with scan crops: regions for any book, and
  disagreements for golden books.
