# Checklist

The plan: what is left, in the order it runs, with who does it and how long it takes.
Every step is the machine's unless it says **user**. A time is an estimate until the run
is timed through `experiments/timed.sh` ([run-times.md](run-times.md)); then the measured
time replaces it. A step done moves to [Done](#done), one line with its date and the
number that settled it; the numbers behind it are in [decisions.md](decisions.md). A
dropped step stays there, struck through, with why. Updated in the same change that
plans, ticks or drops a step. Cite a step by its words: the section numbers are
positions and get renumbered.

Where the build stands and where results can still move: [outlook.md](outlook.md).
What runs right now and what waits on the user: `HANDOVER.md`.

**The plan now:** the codebase review's steps first (the user, 2026-10-13: bug fixes
first, no urgency in building books), then accuracy from what the bench data shows,
new suspects where the readings agree first, then **Stella end to end with the user's
review**, the target book, then the user's four books. After them, the open
areas below in order, and the test set scored once at the end.

## Assumptions to test (quick probes, minutes to an hour each)

The pipeline reads lines and joins them by hand-built geometry because that was what
models could do. Each probe below asks whether that's still true, on a few golden pages
(tuning books), before any building. Record each result, null ones too.

- [x] Whole-page reading (`probe_page_reader.py`, 2026-10-13): Qwen 76 wrong words and
      32 breaks over 19 pages against the pipeline's 27 and 7 (letters doubled at page
      resolution, dialogue paragraphs merged); glm-ocr near-exact on plain text pages at a
      third of the size, but invents text on near-empty and picture pages
- [x] glm-ocr whole pages at full resolution (2026-10-13): 103 wrong words over 18 text
      pages against the pipeline's 27, but right on 5 of the pipeline's 9 error places,
      nearly all line joins; it invents text on near-empty pages
- [x] glm-ocr's page reading as a reader (2026-10-13): right on 226 of 473 pipeline error
      places, but wrong on 910 where the pipeline is right: alone, four false questions a
      catch
- [x] Two page readers agreeing against the pipeline (2026-10-14): outside paragraph
      breaks, right 152 times to 65 (70%), about 0.7 places a page; breaks not trustworthy
- [x] The two readers' agreement on the errors left after review (2026-10-14): 60 errors
      no question catches (+21 unmatched), 71 asked already, 68 false: about a quarter of
      what's left after review, for ~0.3 questions a page
- [x] Build it (the user chose this way, 2026-10-14): `pagereader.py`, two more readers
      for the OCR check behind `ROBO_PAGE_READERS`, the arbiter keeping which readings
      it was trained on
- [x] Read the pages and train with them (2026-10-15, a night): `bench tuning` no change
      0.32 → 0.32, validation 0.50 → 0.43 after review but worse before it on two
      books; the page readers stay off as line readers
- [x] ~~A line no page reader has words for as a feature of the line-role trees~~
      (2026-10-16, dropped): the trees get the unread lines right but for 5 of 657; the
      line-role mistakes left (49 of 25,555) are on lines both readers read
- [x] ~~Both page readers' spelling of a line-end compound as evidence for a learned
      hyphen decision~~ (2026-10-15, dropped): with the judge's answers, as the build runs,
      the build is wrong on 19 of 3,184 line-end hyphens; the readers agreeing fix 9 and
      break about 6, under the bench's noise
- [x] Whole-page reading by the bigger build (2026-10-14): `qwen3.8:27b-mxfp8` 65 wrong
      words over 19 pages against the nvfp4's 76, mostly one page; 60% slower; not taken
- [ ] Whole-page reading with the page before as context, for paragraphs that cross a page
- [ ] The whole-page reading as one more reader: where it and the line readers differ,
      a suspect for the arbiter; how many of the undoubted errors it would have raised
- [ ] Paragraph breaks by a model: the page image plus the pipeline's lines, "which lines
      start a paragraph?", against `reflow.indented`. A learned text table (quote after quote at
      the margin: 87 of 88 starts) did nothing, the tuning books having no unindented
      book (2026-10-16, `work/probes/parastarts.patch`); Vuurspel's unindented layout is
      rare (the user, 2026-10-17), so no pair is sought for it
- [ ] Grow the seven short tuning slices (`work/runs/queue-20261017.sh`, branch
      `longer-slices`), then trust data and the role trees on them, and bench (a night)
- [ ] After the slice growth, merge branch `heading-pairs` (one found heading for a
      reference's number and title set as two: Metro 3/8 → 8/8, Normal People 4/9 → 8/9),
      and retrain the trees on the long slices with branch `number-lookalikes` (a line of
      digits or their look-alikes, "Io" for 10, as a feature: Monterosso's chapter numbers
      in old-style figures, 14/22 found; and a repeat counted only at the line's height,
      so a chapter title recurring as the running head isn't dropped as one: You're
      Never Weird's "Introduction", "Jail Bait"), then merge it and bench (agent, ~1 h;
      the role model is asked again about the ~15 lines whose count changes)
- [ ] Line roles by Qwen from the page image (text, heading, running head, page number,
      caption, picture), against the rules and the trees
- [ ] The text layer as a second reader only: the page built from the whole-page reading,
      the layer and the line readers judging where they differ
- [ ] Page kinds for `init` (cover, front matter, body, back matter) by Qwen from the page
      image, on `tryouts/page-kinds-v1.json`

## Before the user reviews another book (2026-10-16)

What Ex-minnaar's first review questions showed. The user reviews only after these
(AGENTS.md, "The user's review comes last"); Ex-minnaar's review is paused.

- [x] Elision spaces (2026-10-16): our curling made glm's "nog 's" an opening ‘; now ’.
      Ex-minnaar glued elisions 9 → 3, apostrophe-only doubts 40 → 25; benches no change
- [x] ~~Small capitals read in lower case~~ (2026-10-16, dropped): cut at x-height in
      Ex-minnaar, and already read as capitals but for three "xm"; a reader hint for every
      book breaks more than it fixes
- [x] One OCR question per line (2026-10-16): whole-line options from every source,
      "Something else" from any option; benches better, questions fewer
- [x] Ex-minnaar's questions sampled again (2026-10-16): 234, sound; its review is the
      user's (restart the review server)
- [x] Misprints (2026-10-16): the review's `m` writes the book's errata; answers stay as
      printed, so the readers that read the misprint aren't marked wrong

## From the codebase review (2026-10-13, first)

The user, 2026-10-13: the review's bug fixes come first, then its bench and structure
steps; building Ex-minnaar and Stella has no urgency. The findings are in decisions.md.

- [x] One cold A/A rerun of `bench tuning` (2026-10-15): 0.32 → 0.33 after review
      [+0.00, +0.01], no book apart; rebuilding the caches moves the score 0.01 at most
- [x] Book-wide statistics on the whole body (2026-10-16): tried and reverted; a
      raw repeat count over 564 pages took a dialogue tag for a running head
- [x] The line-role trainer's data and saving into `src/` (`sorterdata.py`, 2026-10-16)
- [x] One cache helper (`files.read_cache`, `write_cache`) for the nine copies
      (2026-10-16): formats unchanged on disk, benches identical and warm
- [x] The judges' crop settings and the second vision judge's readout in their cache
      keys (2026-10-16): older answers stand for the crop they were made at, so nothing
      ran cold; benches identical
- [x] `ocrcheck.py` split into `readers.py` and `ocrdoubts.py`; one `roles.is_body`
      (2026-10-16, benches identical)
- [x] `reflow.py` split: joins and hyphens into `hyphens.py`, quote mending into
      `quotes.py` (2026-10-16, benches identical)
- [x] `typography.py` split: scan measurements into `scanstyle.py`, one `ink.threshold`
      (2026-10-16, benches identical)
- [ ] Prune `experiments/`: 53 scripts named only in the logs deleted (2026-10-16, the
      user: results recorded, git keeps them); left: `probe_orientation.py` broken;
      AGENTS.md cut to rules and the map (manifest keys to golden-notes.md, environment
      detail to models.md, the review page to how-it-works.md); decisions.md a heading a
      day (agent, ~2 h)
- [x] Line roles learned (2026-10-13): the trees are on by default after warm benches no
      worse on both sets (decisions.md); running-text and numeral-slot retired (2026-10-16,
      `probe_retire_rules.py`, bench no change); the other rules still earn their place.
      Next: a book with text wrapped around pictures for Dolittle's case
- [ ] Trust data for the 20 books on qwen3.8:27b-nvfp4, then the arbiter and `bench
      tuning` (`experiments/rebuild-trust.sh`): all read 2026-10-12, first bench 0.31
      after review over 16 books; Monterosso read again whole (its 9-page slice cut a
      chapter), then retrain and bench (running, ~21:15)
- [ ] FKA USA, what its first bench showed (no models, from cache): note marks come out
      as LaTeX (`illegal, $ ^{1} $` for `illegal,1`), so a reader's superscript markup
      reaches the text; a chapter's epigraph and its credit line are dropped (p. 19,
      and `—Reed King`); the part heading "Part I / CRUNCHTOWN 407…" is missing; single
      words lost at a page top ("up", "almost every", "border"). Its 30% unplaced lines
      are its footnotes (the reference keeps notes apart), so the bench's suspect-pair
      warning is a false alarm on a footnote book: count note lines apart. Fix, then
      its trust data (SPECS gets `fka-usa--ia-scan: 11-22:1-5`, out of
      `bench.NO_TRUST_DATA`), retrain, bench (~30 min)
- [ ] No fixed test set or reserve (proposed, the user agreed to do it later, 2026-10-12):
      every new pair gets one untouched first-look score before anything is chosen or
      trained on it, then joins tuning or validation. Het geluid van bananen gets its
      first look (~5 h of models) and joins; De aanslag joins validation; Verminkt joins
      validation whole. Update design.md's test-set reason, `bench.SETS` and the CLI's
      `--score-test` guard (agent, ~1 h plus the run)
- [ ] A lighter feedback loop (agreed 2026-10-13; its two rules are in AGENTS.md): build a quick
      bench tier of each tuning book's first chapter or two (~10–20 pages, ending on a
      chapter), and check once overnight that it ranks changes as the full bench does
      (agent, ~1 h plus the run)
- [ ] `golden derive` keeps text before a book's first heading (an epigraph), so Normal
      People's reference and scan can start on p. 9; after the chain (agent, ~30 min)
- [x] A sampled review of Ex-minnaar (2026-10-16): false quote questions on Flemish
      ’m fixed (308 → 261 questions); its blanked place names ("het __plein") need one
      setting for the book (the user)
- [ ] Ex-minnaar's review by the user, then the fixes it teaches
- [ ] Stella rebuilt with those fixes and diffed against its dated copies in
      `work/stella/epubs/` (the user, 2026-10-12: not before the Ex-minnaar review)

- [x] The epigraph stage took noise for a motto (2026-10-16): a word of four letters is
      now required; benches no change

## 1. Accuracy before Stella (~half a day)

About 85% of the wrong words left after review were never suspects: every reading agreed
on them, so no judge and no question saw them. The rules have taken the groups with one
cause; what is left needs new suspects where the readings agree, which today's models
don't yet give at a price worth the reviewer's time.

- [ ] A detector for errors every reading shares (the user, 2026-10-12): a small model
      over every word, trained leave-one-out on the golden books' silent errors (word
      list, letter confidence of tesseract and IA's ABBYY, a smudge on the crop, the
      book's other spellings), raising suspects where the readings agree. Guarded
      against regressions: its suspects are only asked at first, never fixed
      unasked; it ships only when `bench tuning` improves with no book's veto and
      `bench validation` doesn't worsen, and the questions it adds are counted
      against the errors they catch. Labels first, from tonight's trust data (agent,
      ~half a day). Lost spaces: the word list alone is useless (9 errors to 4,417 right
      compounds, 2026-10-16); the gap at the split, measured on the scan, is the feature.
      Tesseract's confidence and accent variants: null too (2026-10-16); wait for a
      stronger reader (the ceiling probe) before building it
- [ ] A reader of the finished text (the proofreader), for errors every reading shares:
      probed twice, about one catch per 100 paragraphs against as many false questions
      (2026-10-11, qwen3.8 proposing, clef filtering): rerun the probe
      (`experiments/probe_text_reader.py`, ~25 min) whenever a stronger text model comes,
      build it only if the catches outnumber the false questions
- [ ] Smaller groups, by size, only where one cause covers several: quotes (~35 words;
      nested quotes need the book's own habit, learned from the book rather than assumed
      as the outer mark's opposite; De tuin sets “ alone 147 times), word breaks
      (~70, scattered), small capitals read in lower case (7, visual)

## 2. Stella, the target book

- [x] Stella's errors estimated against Claude's reading (2026-10-16): 4 wrong words in
      67 pages before review, 2 asked; 6 questions. Unasked: two words joined after a
      tight f ("grofwerk", "trofik")

- [x] Stella's review (2026-10-16): 6 questions answered, two accents corrected
      ("íéts", "ís"); rebuilt, epubcheck clean (`epubs/stella-2026-10-16-0859.epub`)
- [ ] **user** reads the EPUB through, noting each error with a few words around it; no spot-check (the read covers every page). Each noted error is fixed as an answer and checked against the build's suspects: was it asked, settled wrongly, or never a suspect ("Errors no question asks about"): what the bench can't see
      (layout, italics, front matter)

## 3. The user's books after Stella

Four Dutch books the user wants as EPUBs, none with a reference EPUB, each an IA Scribe
scan with its own hidden layer (Stella's format), in `work/<name>/` with a `book.toml`.
In this order:

| Book | Directory | Pages (body) | Scan | Watch for |
| --- | --- | --- | --- | --- |
| Herman Brusselmans, *Ex-minnaar* (Ooievaar 1998, 6th printing) | `ex-minnaar` | 284 (7–279) | 360 ppi | motto on p. 7 ("It's closing time", Leonard Cohen), set as an epigraph; drop cap; an OmniPage OCR of the same scan beside it (`omnipage.pdf`, worse: the motto's "It's" reads "h's") |
| Herman Brusselmans, *De kus in de nacht* (Prometheus 2002) | `de-kus-in-de-nacht` | 620 (7–616) | 300 ppi, large pages | parts ("Deel een", "Proloog" on p. 7), small-capital openings |
| Emmanuel Carrère, *Andere levens dan het mijne* (De Arbeiderspers, tr. Floor Borsboom) | `andere-levens` | 248 (9–244) | 360 ppi | library copy; French names and accents |
| Emmanuel Carrère, *Een Russische roman* (De Arbeiderspers, tr. Marianne Kaas) | `een-russische-roman` | 276 (7–271) | 360 ppi | library copy; seven parts, each a small number atop its own page (pp. 7, 47, 131, 169, 233, 259, …) with pencil marks the layer reads as noise (pre-check, no OCR check: part "1" read "I" and dropped as a page number; the marks kept as running text, "Fyarvin er pan ee Ka": see what the full build asks, then decide on a rule); p. 272 show-through only |

- [ ] Each book in turn: check its front and back matter and `body_pages`, build (cold
      ~1 min a page: Ex-minnaar ~4 h, De kus ~10 h), sample the questions, **user**
      reviews, rebuild, epubcheck, a **spot-check** (5 random pages drawn by a script,
      the **user** marks every wrong word, break and italic against the scan, ~15–20
      min: the book's own error estimate with its interval), **user** reads the EPUB
- [ ] Ex-minnaar: whether OmniPage earns a place as another reading (it fails
      differently from the layer); only if the questions show the readers stuck together

## 4. The reviewer's time

- [x] The book teaches itself, first half (2026-10-16): a book's answers join its
      arbiter's substitution table (`trust.with_answers`); Ex-minnaar's review showed the
      signature (wc, stress accents, ’s)
- [x] The book teaches itself, second half (2026-10-16): one question per pattern,
      replayed on Ex-minnaar's answers (`probe_patterns.py`), saves 12–17 of ~140
      questions and settles one skipped line in eight to twelve wrong; not built
- [x] Questions with no readings (headings, missing lines) get Qwen's reading as an
      option, and a typed answer is checked against it (2026-10-17): Ex-minnaar 170 of
      199 questions; benches identical

## 5. Errors no question asks about

- [x] 2026-10-17 Lines the text layer lacks at a text block's top or bottom: a strip of a
      text region above its first layer line or below its last is a candidate
      (`missing.edges`); Vuurspel p. 19's two lines read right. With Bruna's references
      re-derived without markup spaces: validation BETTER 0.49 → 0.38 after review
- [x] 2026-10-17 The Stranger's Child's nested-quote spacing: the print sets a thin gap
      between nested marks, some e-books write it as a space; folded in the score
      (`evaluate._NESTED_GAP`), validation BETTER 0.38 → 0.36. Its "think—’" against our
      "think –’" is the e-book's: the scan has the spaced en dash (5 places, left as is)
- [x] De eerlijke vinder's unasked errors (2026-10-15): 28 of 38 were page numbers the
      layer joins to a body line; split off (`pdf._apart`), wrong words 0.88 → 0.42 a page
      on the short test; `bench tuning` 0.32 → 0.30 after review, no book worse

## 6. Structure

- [x] Metro's lost closing quote after a spaced ellipsis (2026-10-16): the layer drops
      it, the readers write `. . . '`, curled as opening or not at all; now closed at a
      line's end and curled by the book's style, Metro 0.42 → 0.33 wrong words a page
- [ ] Verdict page: a place where one side has something the print lacks (Metro p. 61's
      stray `>` in the e-book) says so in words (agent, ~30 min)
- [x] Monterosso's capital T read as an opening quote (2026-10-16): one case left in the
      build ("‘Lieve ‘Tiziana,’ zegt"), asked at the paragraph's end ("open at end"), not
      where the ‘ stands, since quotes nest in their own mark; not worth a rule for one
- [ ] Scene breaks the build still misses: 23 of 295 (Reis 14, De eerlijke vinder 7).
      Reis's are page tops after a full page whose last line ends a sentence at the
      margin, the next opening flush: the same geometry as a paragraph running on, so
      only the text can tell (a sorter question, "a new scene?", for later). Het heft
      (`P_plat`), Villa (`Tekst_6-Na-witregel`), Artemis (`noindent_topspace1`)
      undeclared, unsure on the scan
- [ ] De eerlijke vinder's part numerals I–IV (0/4): read from the drawing
- [ ] You're Never Weird's headings (5/16: bracketed sections, "- 1 -" numbers) and p. 47's
      picture text read into the body
- [ ] Dolittle's captions scored: derive them into the reference, or leave caption lines
      out of the score as footnotes are

## 7. Better pixels: Internet Archive's own files

Public on public-domain items only (Crime, Dolittle); private on lending-library items.
Sharper pixels lower the readers' errors at the source, the other way at the errors every
reading shares: many are specks and faint marks.

- [ ] JP2s as the image source for public-domain books (a borrowed item offers no
      downloads, so not for Stella or the user's books): on Crime's 50 reader-set lines
      both readers err about a fifth less (glm-ocr hard CER 1.57% → 1.26%, Qwen 1.78% →
      1.36%; `experiments/probe_ia_images.py`, 2026-10-11). Later, with public-domain books
- [ ] ABBYY's letter confidence as an arbiter feature: first check the PDF's layer is
      ABBYY's reading, then does a low one separate the real errors? ~1 h, no models

## 8. Beyond the golden books' kind

- [ ] **`roboscriptorium init <pdf>`** (agreed 2026-10-11): drafts book.toml and asks the
      user only what it can't settle, on the review page; `build` and `review` run it first
      when book.toml is missing. Steps: (1) each page's **kind** (cover, blank, scan noise
      or library stamp, half title, title page, colophon, contents, dedication, motto,
      foreword or introduction, dramatis personae, text, epilogue or afterword, notes,
      appendix, bibliography, index, acknowledgements, about the author, also by / ads,
      back cover) and a fixed rule from kind to *in the EPUB*, *metadata* or *left out*
      (the list in decisions.md, 2026-10-11, What goes into the EPUB: everything but
      what it leaves out); the contents page read for the book's structure and its
      chapters' names. (2) Labels: every golden scan's pages by kind (the old
      body ranges follow the references, which leave forewords and afterwords out, so
      they aren't labels for this). (3) Signals without models first (words on the page,
      page number, short centred lines, ©/ISBN, headings like "Woord vooraf", "Proloog",
      "Inhoud"), clef-flash's page-kind question on the doubtful pages. (4) Title,
      author, translator, language from the title page and colophon. The earlier screen
      put 227–231 of 252 edge pages on the right side, missing forewords and afterwords
      that the ranges of then left out (design.md, Where the body starts and ends).
- [ ] An image-only scan through the whole pipeline (Goede dochter with its layer removed:
      tesseract 0.35% CER against the layer's 0.20%): does the OCR check close the gap?
      ~1 h cold. Then italics from tesseract's word boxes

## 9. Golden books and housekeeping

- [ ] **user** More golden pairs when convenient: Koning Wilders (Atlas Contact) and Het
      laatste bevel (Manteau) came in 2026-10-11; De Arbeiderspers, Prometheus/Ooievaar or
      Vrijdag next; a Kosmos book for later, beyond prose
- [ ] **user** Settle verdicts on the tuning books (`review` on each), the disagreements
      the arbiter's labels sit on first: hours, spread out, whenever convenient
- [ ] Remove the `baseline` and `qwen2` worktrees when convenient

## 10. At the end

- [ ] Rederive the test set's reference with the derive of the day (it was left out of the
      2026-10-11 rederive: ornament paragraphs and blockquotes now read differently), then
      score it once: `bench test --score-test`

## Later

- [ ] Python 3.15 once PyTorch publishes cp315 wheels (pytorch/pytorch#184352): with
      nightly torch every test passes and the spotter's regions match 3.13 exactly
      (2026-10-11); bump `.python-version`, `uv lock`, bench once
- [ ] Qwen on fewer lines (quote marks, disagreements), for speed: only if cold runs
      become the bottleneck (a new book's ~100 pages take ~2 h)
- [ ] MiniCPM-V 4.6 as a faster reader: the readers already cover nearly every line, so
      it pays only by speed
- [ ] Surya's layout model as a second spotter: screen it on the drawn numerals
      DocLayout-YOLO misses and the figure pages
- [ ] Block quotes and verse: find golden pages that have them first (epigraphs on a
      page of their own done 2026-10-11; De eerlijke vinder's mottos at its part
      openings, beside a drawn numeral, are not caught)
      Ex-minnaar p. 50 (2026-10-16): a poem, "Gemis", short indented lines; its title
      taken for a chapter heading and its lines joined into one paragraph
- [ ] Per-book image tuning for pale or tinted scans: null on normal pages so far
- [ ] Het Kindeken Jezus as a golden book, only if the image probe looks
      language-dependent
- [ ] `golden check <pdf> <epub>` writing a draft manifest, once a batch of candidates comes
- [ ] French, the user's idea (2026-10-09); **not yet** (2026-10-10: no French books to
      make yet). It brings its own typography
      (« », a thin space before `; : ! ?`, dialogue dashes) that `quotes.py`,
      `typography.py` and the arbiter's training data would all need, and Gallica is
      mostly older print. If it comes: one French Wikisource book proofread page by page
      against its scan, held out like the test set. Proposed first instead: count the
      accent errors Dutch already leaves unasked (`knieén`, `hé` for `hè`, lost stress
      accents, Stella's `scenes`), by book

# Done

By area, newest first within each; one line a step. Dates and numbers are as recorded in
[decisions.md](decisions.md) on the day.

## Measurement

- [x] 2026-10-13 What a perfect reader could still gain (`probe_reader_ceiling.py`): 53
      of 186 wrong words left after review (29%) are undoubted reading errors, under the
      half agreed as the bar; fine-tuning a reader dropped for now
- [x] 2026-10-13 `bench validation` finished with the ellipsis measured on the scan: BETTER
      1.10 → 0.59 after review (The Stranger's Child 4.59 → 0.53); tuning BETTER 0.52 → 0.50
- [x] ~~2026-10-11 `_scandata.xml` page types as labels for page classification~~:
      dropped, they mark the cover and title page (Dolittle also contents and
      copyright) and call every other page Normal, colophon, motto and ads included
- [x] 2026-10-11 Scene breaks scored: derive reads them (thought breaks, ornaments,
      break, opening and closing classes, each checked on the scan) in 10 references;
      the build finds 255 of 295 and sets 20 more where they are recorded
- [x] 2026-10-11 A page opening flush left after a finished paragraph is a scene break
      where paragraphs indent: found 255 → 272 of 295, 2 more set; words unchanged
- [x] 2026-10-10 Longer tuning slices, each ending on a chapter (Goede dochter 9–162, Reis
      whole, De cipier 9–174, Metro 7–162, De tuin 11–122): 446 new pages in 7.5 h, arbiter
      and trees retrained; tuning 0.53 → 0.53, validation 0.77 → 0.76, no change. The
      pooled slip rate lowered "after review" a little everywhere (a measure, not a build
      change); the quote questions' new readings changed nothing the bench counts
- [x] 2026-10-10 The bench books read again by the local Qwen (30,572 lines, ~9 h), trust
      data and arbiter rebuilt: tuning 0.56 → 0.56, validation 0.77 → 0.79, no change; the
      bench now measures the build Stella gets
- [x] 2026-10-09 The slip rate measured again on today's questions: 30 of 32 right (picks
      17/18, typed 6/7, roles 7/7); the bench uses the two reviews pooled, 10 of 100 (the
      user's choice), applied after the chains as the new baseline
- [x] 2026-10-09 The bench counts paragraph breaks set wrong, catches an error only at the
      question's place, counts a typed page as a question per line: tuning 0.48 → 0.56 on
      the same build, honest; prints headings and reports heading and paragraph-F1 changes
      beside its test (`bench.structure`); records the hosted share of each book's readings
- [x] 2026-10-09 The arbiter's sureness calibrated (isotonic), so 0.8 means 80% right
      whatever the retrain: no change by the bench, kept for the threshold's meaning
- [x] 2026-10-09 An error over a page break counts on the page holding most of it
      (Afscheid 5.03 → 0.24 after review)
- [x] 2026-10-09 clef's cached answers stand for fresh ones: judge set v1 re-asked, 2 flips
      of 518, both at confidence ≤ 0.1
- [x] 2026-10-09 Retirement signals per book in the bench (`golden/signals.py`: layer CER,
      unplaced body lines, a suspect named)
- [x] 2026-10-08 Judge set v1 frozen (518 settled suspects, 25 wrong and 25 right a book);
      reader set v1 (550 lines, 30 the layer reads wrong and 20 right a book);
      `experiments/tryout.py` screens a candidate for a role against the incumbent
- [x] 2026-10-07 `roboscriptorium bench`: pinned slices, one JSON per run, paired page by
      page; one primary test with books weighing the same and a per-book veto; the
      reviewer's slips counted; leave-one-out trust models for tuning books; a missing
      or stale trust model stops the build; `eval` records decider, settings and model
      digests; long runs timed into run-times.md; design.md and decisions.md started

## Golden books

- [x] 2026-10-11 Validation from 5 books to 7 (Monterosso and De stilte van de hel, cold):
      **0.76** wrong words a page after review by the rules
- [x] 2026-10-10 Sets changed (the user's go): De kerk van de dode meisjes and Vuurspel
      validate; De tuin, Het heft in eigen hand, Doodskleed and Het ijzige land tune.
      Derive learns `capital_classes` and a spaced `--` as the print's dash. Rejected:
      Cavendon Hall, Alsof het niets is, Het spel van de engel (EPUBs made through Word or
      OCR); De stilte van de hel kept unused as Vuurspel's sibling
- [x] 2026-10-10 ~~The five tuning books whole~~ dropped (the user): more pages of books
      already trained on add the same errors again
- [x] 2026-10-09 Internet Archive's own files fetched by manifest (`[scans.ia]`): Crime and
      Dolittle. Five public-domain Dutch Scribe items pair with Gutenberg (Het Kindeken
      Jezus, David Malan, …) but all in pre-1934 spelling: none taken
- [x] 2026-10-08 Grand Hotel Europa and Lady into Fox retired to reserve (another printing;
      a reference unlike its print in typography); De eerlijke vinder and You're Never
      Weird into validation; Metro, De cipier, Artemis, 11/22/63, Afscheid and Reis into
      tuning; Het geluid van bananen frozen as the test set
- [x] 2026-10-08 `experiments/probe_candidate.py`: a no-model check of a scan and EPUB
      pair; known deviations tracked in the manifest, the fold or a verdict, nowhere else
- [x] 2026-10-08 Hosted clef as the judge, measured against criteria fixed first: fails all
      three (PrimeIntellect hardly reads the image; Cloudflare 96.2% the same pick, fewer
      right), so clef stays local

## Trust data and the arbiter

- [x] 2026-10-11 Training code for the shipped models in the package: `trust.train`,
      `trust.training_matrix` and `sorter.train` were there already, with feature-count
      tests for trust; the sorter's feature names now tested with regions and styles
- [x] 2026-10-11 The pair prior's own ablation (an empty table, retrained): without it
      tuning 0.31 → 0.34, validation 0.70 → 0.73, both worse; it stays
- [x] ~~2026-10-11 Bad pages by the readers' disagreement~~: the 5% densest pages hold
      32 of 319 unasked words; dropped
- [x] 2026-10-11 Whether a borrowed item's JP2s can be had: no, its download options are
      empty while on loan (the user, on Stella)
- [x] ~~2026-10-11 The book's own consistency as new suspects~~: 13 catches against 17
      false alarms, 10 of them in one bad scan; dropped
- [x] 2026-10-11 Ask threshold 0.7 / 0.8 / 0.9 on tuning: 0.74 / 0.92 / 1.11 questions
      a page for 0.351 / 0.344 / 0.343 after review; stays at 0.8 (yield falls off past it)
- [x] 2026-10-11 ~~De tuin's four questions no longer asked~~ dropped: it no longer loses
      (0.64 → 0.59 with `bughunt`)
- [x] 2026-10-11 Branch `bughunt` merged: the hunt's 22 fixes and its seven open
      findings, trust data rebuilt warm (MODEL_VERSION 6), arbiter retrained; tuning
      **better** 0.50 → 0.48, six books clearly better, none worse; validation no change

- [x] 2026-10-11 Trust data for Thief-Taker and the five new books (567 pages, 525 min),
      arbiter (~10,400 suspects) and trees retrained: **the new baseline**, tuning 0.50,
      validation 0.74 wrong words a page after review; trees 0.48 / 0.67, no change

One book per run, `experiments/ocr_trust_data.py --rebuild <book>`; about 1.1 min a page
cold, Qwen's reading 70–75% of it. Per book: suspects, settled (a clear label), and how
many the layer had wrong.

| Book | Pages | Suspects | Settled | Layer wrong | Note |
| --- | --- | --- | --- | --- | --- |
| Goede dochter | 9–64 | 419 | 377 | — | Qwen readings cached by the line bench |
| Vals alarm | 11–60 | — | — | — | its lost full stop is in no other book |
| Crime | 94 pages | 262 | 231 | — | relabelled with the score's fold |
| Dolittle | 23–88 | 684 | 570 | 396 | |
| De tuin | 42 pages | 473 | 455 | 350 | |
| Grand Hotel Europa | 30 pages | 173 | — | 99 | retired since |
| Stella | 5–71 | 66 | — | 34 | labelled by the user's answers only |
| Metro 2033 | 7–111 | 835 | 745 | 222 | the crop fix's clear gain |
| Artemis | 13–80 | 317 | 273 | 207 | its `\|` for I |
| 11/22/63 | 15–94 | 357 | 319 | 188 | three runs: Ollama stalls |
| De cipier | 9–92 | 429 | 327 | 97 | |
| Afscheid | 9–70 | 266 | 240 | 88 | |
| Reis om mijn schedel | 11–110 | 480 | 363 | 94 | |
| De eerlijke vinder | 12–95 | 895 | 829 | 85 | validation |
| You're Never Weird | 13–94 | 317 | 283 | 87 | validation; clef right on 268 |

- [x] 2026-10-09 imajev-4b as a third judge: trust data with its votes, retrained, no
      change (tuning 1.02 → 1.01, validation 0.81 → 0.80); off. Page types 19/23 like
      clef-flash, body ends 227 against 231: `body_pages` stays in book.toml. Which way a
      plate is up: 10/10, the candidate for plates without a caption
- [x] 2026-10-09 Qwen's third reading stays: without it tuning 1.00 → 1.33, validation
      0.81 → 1.01. Short lines stay. Qwen's second look at 450 dpi as a trust feature: no
      change, branch `qwen-second-look`. Washed-out pages left out of the check (`faint.py`),
      the arbiter's ≥ 0.8 suspects not asked (`ROBO_OCR_ASK_BELOW`): questions halved
- [x] 2026-10-08 winnow-ollama:e4b as the second judge (right alone 285/208/265 on three
      books against Ollaya's 174 each); Ollaya stripped; trust data re-asked for 14 books,
      retrained, bench no change (1.00 → 1.02)
- [x] 2026-10-08 The substitution-pair prior (`trust.pair`, model version 3): silent errors
      at 0/.25/.5/1 questions a page [153, 87, 44, 23] → [110, 48, 25, 10], leave one book
      out; the trainer uses only data that exists and has every reading, never trains on
      validation books
- [x] 2026-10-08 The retrained arbiter against the fixed rule: after review 1.37 → 1.00,
      eight books better, none worse. Metro's veto before it was its spaced ellipses,
      fixed book-wide by `typography.py` (4.63 → 0.43)
- [x] 2026-10-08 The crop bug: a line's crop reached into its neighbour's box on up to 97%
      of lines (Metro); `crop_span` stops at the neighbour. glm-ocr on Metro's changed
      crops CER 1.87% → 0.29%; every book re-read and rebuilt, Metro the clear gain, the
      rest neutral. ~~An ink-fitted crop~~ tried, not adopted: the readers read no better
      from it. ~~A reading far off its line's length counting as none~~ dropped: readers
      stray on 1 line in 958 since
- [x] 2026-10-08 Faster readers screened: gemma4 8B (quote marks wrong), qwen3.6 MoE (wraps
      narration in quotes), gemma4:26b MoE (reads whole other lines on Metro): all out; the
      failed MoE models deleted. On Goede dochter and Metro only 1 line in ~1,000 has no
      current reading right: the errors left come from choosing, not from missing readings.
      Local and hosted Qwen interchangeable (same reading on 97.6%). ~~winnow:12b~~ dropped
      with Ollaya

## The reviewer

- [x] 2026-10-13 One review for a golden book: its places that differ from the e-book
      are questions in `roboscriptorium review`, answers stored as verdicts; `golden
      review` and the page's verdict mode are gone. Each side's words shown as written.
      Walked on Dolittle (89 questions, 15 of them places): choose, type (warned once),
      caption from our words, page-break crops
- [x] 2026-10-11 Stella built with today's build (every stage cached, under a minute,
      epubcheck clean): 7 questions, 3 answered before, 80 of 83 old answers applied (the
      other 3 lie inside a line another answer retyped whole)
- [x] 2026-10-11 Stella's 4 new questions reviewed (p. 19 "íéts", the other three as
      the text had them), rebuilt, epubcheck clean
- [x] 2026-10-11 English line-end hyphens nothing else decides settled by the judge, not a
      question: tuning **better** 0.36 → 0.34 (Dolittle 0.52 → 0.44, Metro 0.26 → 0.22)
- [x] 2026-10-11 A quote left open at a paragraph's end asked whatever follows: tuning
      0.37 → 0.36, De tuin's unasked 0.24 → 0.16, no book worse
- [x] 2026-10-11 No paragraph starts on a line that continues a word broken with a hyphen:
      tuning **better** 0.32 → 0.31, validation **better** 0.74 → 0.70
- [x] 2026-10-11 A quote mark left open right after a word asked where it stands, not at
      the paragraph's end: tuning **better** 0.33 → 0.32, no more questions
- [x] 2026-10-11 A section opening on a word in capitals flagged as a lost drawn initial
      too: Dolittle 0.44 → 0.40, pooled no change
- [x] 2026-10-11 A section opening in lower case below a heading flagged as a lost drawn
      initial: Het ijzige land 0.25 → 0.20, pooled no change, no book worse
- [x] 2026-10-11 Speech closed on a letter at a paragraph's end asked as a quote question
      (De tuin kerns the stop under the mark): tuning **better**, De tuin 0.46 → 0.41
- [x] 2026-10-09 Quote questions offer the OCR-checked line, Qwen's marks on it (quote
      marks only, no dashes) and the nested-quote combination: 3 of 4 now offer the right
      line, where none did
- [x] 2026-10-09 A lost line as a question (`lost-line`), scene breaks in the EPUB
      (`break_before`, unscored), budget diagnostics in shuffled order
- [x] 2026-10-08 Answers checked before they are saved (`review.doubtful`): a typed line
      matching no reading, or a straight quote in a curly-quoted book, is queried once;
      warnings logged. The review page tints the line and underlines the place, nothing
      drawn over the letters
- [x] 2026-10-08 A reader of the finished text, probed: gemma4 flags 56 on 200 paragraphs,
      ~4 real; clef as the filter keeps both clear catches and drops 31 of 37 urges. The
      proposer is the weak part (open step above)

## Structure and line roles

- [x] 2026-10-17 Paragraph starts: a line beginning in lower case after one not ending a
      sentence carries on (no model); the vision judge (`parabreaks.py`) off, as it broke
      more than it fixed; breaks tuning 0.19 → 0.15, validation 0.21 → 0.13 a page
- [x] 2026-10-11 Footnotes out of the running text, linked to their marks (`footnotes.py`):
      Reis 7 of 8 found and linked (the eighth's mark read "ie"), no false ones on the
      benches after a stroke-weight limit; Reis paragraph breaks 0.07 → 0.06, BETTER
- [x] 2026-10-11 Paragraph breaks in unindented books (Bruna's): justification judged on
      lines that stop mid-sentence, a page's short last sentence carried over; validation
      breaks 1.97 → 0.21 a page (Vuurspel 7.91 → 0.44), tuning 0.26 → 0.22, no book worse
- [x] 2026-10-11 A dropped line that reads as running text kept and flagged
      (`roles.running_text`): tuning **better** 0.43 → 0.37, validation **better** 0.82 →
      0.76. The trees on top of it: no change (0.37 → 0.40, 0.76 → 0.72), Thief-Taker and
      Vuurspel clearly worse; ~~trees on by default~~ dropped, they stay off
- [x] 2026-10-09 Line roles by trees (`sorter.py`, `ROBO_SORTER=1`, off): role errors
      406 → 152 tuning, 77 → 29 validation leaving one book out; bench no change, three
      books clearly better, Crime one lost line
- [x] 2026-10-09 Paragraph starts from a page margin fitted on full lines: breaks set wrong
      −28% tuning, −34% validation, the second review's one clear win
- [x] 2026-10-09 Headings: 11/22/63's numbered sections 5 → 23 of 24; Villa Toscane 0 → 12;
      De cipier 3 → 4; Afscheid's misread numerals 8 → 11 (`numeral-slot`); Artemis's
      circled numbers 0 → 3 (`missing.py` reads five lines above a sunk page)
- [x] 2026-10-08 Line-end hyphens by evidence in order (the book's spelling, the word
      list, a capital, the parts beside an inner hyphen): wrong 29 → 15 of 1,574
- [x] 2026-10-08 Italics measured against Metro's print: the print sets every station
      name in italics, the eBook two; marked unscored (`italics_unlike_print`)
- [x] 2026-10-08 PP-DocLayoutV3 as the spotter: worse downstream (Dolittle CER 1.22% →
      1.71%), not adopted. ~~A crop reader on tesseract's boxes~~ dropped: an image-only
      scan's layer is tesseract's already
- [x] 2026-10-08 tesseract's first reading of an image-only PDF (`pdf.first_reading`):
      Goede dochter without its layer 0.35% CER against 0.20%

## Reviews of the build

- [x] 2026-10-13 Third review of the codebase, four reviewers: eight bugs fixed with tests
      (a typed verdict could write its context into the reference twice, a word left
      open before "en" lost its hyphen, a typed line took the identity of the one below
      it, notes scored on the wrong version of the pages, answers saved at once could cut
      each other, no cache knew its source PDF, the arbiter read its judges by the order
      of their votes, the docs put copyrighted books' verdicts in git); the rest planned
      above
- [x] 2026-10-13 Three suspect pairs retired (the user): 11/22/63, FKA USA, Koning
      Wilders; the arbiter retrained without 11/22/63
- [x] 2026-10-13 The bench prices the reviewer's time (20 questions = one wrong word, the
      user) and its verdict is worse when any slip rate is, a veto on breaks too: this
      morning's tuning run stays better, 0.57 → 0.55
- [x] 2026-10-13 The bench counts typography where the words agree, a measure of its own:
      0.0–2.0 words a page, Dolittle 8.7, nearly all straight quotes kept from the layer
- [x] 2026-10-13 The trust data and the arbiter's saving into `src/roboscriptorium/trustdata.py`,
      tested; its book list kept in step with `bench.NO_TRUST_DATA` by a test; retrained
      from the cached data with the old code and the new: the same models
- [x] 2026-10-13 The measurement code out of `cli.py`: `golden.scoring` (a golden slice
      built and scored) and `bench.run`; 25 experiments and the tests use them, not the
      CLI's private helpers
- [x] 2026-10-13 Straight quotes and apostrophes left from the layer curled
      (`quotes.curl`): typography 0.00–0.09 a page on every tuning book, the verdict
      unchanged

- [x] 2026-10-09 Fable's second review: what the bench couldn't see and leaks in the OCR
      check, each change benched alone; the ledger of probe against verdict is in
      outlook.md
- [x] 2026-10-09 Strict review of the codebase: six reviewers, every finding checked,
      fixes with tests in seven commits; trust data rebuilt, tuning 1.00 → 0.96,
      validation no change. Qwen's read prompt (five variants) and crop (dpi, upscale,
      contrast, sharpen, margin) can't be improved: each fixes as many lines as it breaks
