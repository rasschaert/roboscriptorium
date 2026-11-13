# Checklist

The plan: what is left, in the order it runs, with who does it and how long it takes.
Every step is the machine's unless it says **user**. A time is an estimate until the run
is timed through `experiments/timed.sh` ([run-times.md](run-times.md)); then the measured
time replaces it. A step done moves to [Done](#done), one line with its date and the
number that settled it; the numbers behind it are in [decisions.md](decisions.md). A
dropped step goes there too, struck through, with why. An open step says only what is
left of it. Updated in the same change that plans, ticks or drops a step. Cite a step by
its words: positions change.

Where the build stands and where results can still move: [outlook.md](outlook.md).
What runs right now and what waits on the user: `HANDOVER.md`.

**The plan now** (2026-11-11). Stella, the target book, is done: reviewed, rebuilt and
read through by the user without an error (2026-10-31). The order from here:

1. what is in flight: production's switch to the steadier arbiter (the user's word);
2. one path for every doubt (the user, 2026-11-10: first), and with it the questions
   that made the user stop Nervous System's review;
3. small capitals, what is left of them;
4. the user's books, each reviewed only once the machine has done all it can;
5. then the open areas below, by what [outlook.md](outlook.md) says they can gain.

Standing, not steps: each new golden pair is scored once, at its first look, before it
joins a set; the sets are reviewed at least weekly (AGENTS.md, "Reviewing the sets";
last on 2026-11-06, so next by 2026-11-13).

## In flight

In this order; `HANDOVER.md` has the paths and the commands.

- [ ] After batch five, the two nulls that waited for it: autotrust-jev 9B as a second
      text judge (branch `text-seat`; not taken 2026-11-09, validation's unasked places
      170 → 178) and the book's own vocabulary as an arbiter feature (null 2026-11-08)
- [ ] Trust data for the tuning books that have none (`bench.NO_TRUST_DATA`: Au pair, De
      vergelding, Glazuur); batch five's rebuild left all three out

## One path for every doubt (the user, 2026-11-10, first)

The user, reviewing Nervous System: "when you ask me for review, it's to settle who is right.
i should be offered everyone's opinion and they should already have 'duked it out'. only when
their differences can't be settled, it goes to me. that's the whole point, no?" The OCR check
works so; the quote check, garbled lines, headings and washed-out pages raise questions on
side paths that skip the judges and the arbiter, and their cards show one or two readings.

- [ ] The quote check as a reader in the OCR check (`ROBO_QUOTE_READER=1`, off;
      design.md, Quote questions). Benched twice on tuning, not taken: the arbiter was
      never trained on its two readings, so asked places go unasked (decisions.md,
      2026-11-11). Left: the trust data rebuilt with the two quote readers, the arbiter
      retrained to weigh them, then `bench tuning` and `validation`; on by default if
      neither says worse. Then whether `quotes.closed_at_end` is still needed (it added
      a ’ the print lacks, The Loudest Sound and Nothing, PDF 235), the mark opening a
      word ("’bout", 40 lines in that book) the quote check still asks itself, and
      nested quotes by the book's own habit, not assumed as the outer mark's opposite
      (De tuin sets “ alone 147 times)
- [ ] The other doubts as suspects on the same path: a garbled line (its readings judged
      as any other), a heading (asked only where the role evidence is split), a speck
      read as a mark (the three below). The arbiter learns the new kinds from labels:
      the user's answers of 2026-11-10 and the golden books' places of each kind. For
      specks the golden pairs give labels by the thousand: a reader's character absent
      from the reference, aligned to an ink blob, is a speck, and a mark the reference
      confirms is ink (~1 day; three pages were too few, 2026-10-21)
      - [ ] A speck read as a hyphen before a line's first word (Nervous System PDF 118
            line 2, "- I followed"; Going into a Dark House PDF 7, "- For"). A hyphen
            alone before a line's first word is never print in a book whose dashes are
            long and spaced and whose lines never open on a dash elsewhere; a book that
            opens dialogue with a dash (Dutch) keeps it. Counterexamples first: dialogue
            dashes in the tuning books
      - [ ] A speck read as a second full stop (Nervous System PDF 119 line 25,
            "system.. He added"; the layer, glm-ocr, tesseract, clef and d3 all read
            ".."). The book sets one stop or its measured ellipsis, never two dots.
            Counterexamples first: an ellipsis read short, an abbreviation's stop ending
            a sentence
      - [ ] A speck read as a quote mark after a word (Nervous System PDF 138 lines
            8–10, "disaster’"; the second scan's layer reads "disaster"). It unbalanced
            the paragraph's quotes, so the quote card asked. The evidence: an extra
            closing mark where nothing opens, and the witness
- [ ] Every card shows every reader's reading and every judge's vote, as the OCR check's
      do. A quote card shows only the OCR check's line and the read model's marks (the
      user, Nervous System PDF 120: "where are the other model's readings?"), though
      glm-ocr's and tesseract's readings of the same lines are cached; the same card
      kept a speck read as " ." after the closing quote ("notice.” ."). With the
      redesign, for the **user**'s say: same-page reference crops beside a punctuation,
      accent or small-capital question (this printer's comma and full stop, a plain i
      and an accented vowel), and an answer propagated to the word's other occurrences
- [ ] The arbiter asks where every judge and the layer agree (Nervous System PDF 92: the
      layer, tesseract and all four judges on "“Okay.”", only glm-ocr and Qwen without
      the stop): read its sureness on that book's 22 asked suspects, and whether English
      books have too little trust data. After the arbiter switch
- [ ] Line boxes off their ink (the user, same card: "the yellow box is drawn wrong").
      The layer puts "“Okay.”" at y 179–190 where the scan prints it at ~186–195, so the
      review's box and the crops the readers and judges see cut through the line.
      Measure how often by fitting each box to the ink band nearest it (a first count
      with a shifted-box test found none, so that test is wrong), then fit boxes to the
      ink before cropping; upstream of every reader, so through the frozen tryout sets
      and a bench
- [ ] Measure, and show the user before they review again: the questions a book like
      Nervous System leaves, by what raised them, each kind the machine could settle
      fixed at its source, and the silent errors on the benches before and after. Its 70
      questions held 21 on headings in a book whose headings are all right, 22 OCR
      doubts, and the arbiter's pick bringing a straight quote into a curly book for the
      quote check then to ask (PDF 37, 120, 201, 235)

## Small capitals (the user, 2026-11-09: "we need to nail this")

On by default since 2026-11-11: an all-capitals version of a mixed-case word, and doubts
on lower-case pieces no reading disputes (design.md, "Small capitals get an all-capitals
version"). Left, beside a lone small capital no judge tells from lower case (outlook.md,
"Tried"):

- [ ] The arbiter fixing where the judges agree on capitals, instead of asking: a
      retrained one does. It waits for the steadier arbiter (In flight) and comes with
      batch five's retraining

## The user's books

Books the user wants as EPUBs, none with a reference EPUB, each an IA Scribe scan with
its own hidden layer (Stella's format), in `work/<name>/` with a `book.toml`.

| Book | Directory | Pages (body) | Scan | Watch for | State |
| --- | --- | --- | --- | --- | --- |
| Marlen Haushofer, *Wij doden Stella* | `stella` | 76 (5–71) | 360 ppi | one continuous text, a sunk opening | done: read through by the user, no errors (2026-10-31) |
| Mirko Bonné, *Hoe wij verdwijnen* (Querido 2011, tr. Elly Schippers) | `hoe-wij-verdwijnen` | 300 (9–295, by `init`) | IA Scribe | dedication (p. 9) and a Camus motto (p. 11) before the text | reviewed (2026-11-02); waits on the user's spot-check and read-through |
| Louis Paul Boon, *Pieter Daens* (Singel Pockets 1997) | `pieter-daens` | 804 (7–787) | IA Scribe, Leeds library copy | six parts ("Boek een" … "Boek zes") and chapters headed by years; mottos (p. 7); a table of contents (pp. 11–12) left out; show-through read as text on pp. 8, 14; verse (p. 354); a sources list at the end | built; waits on the user's review (292 questions) |
| Jan Lars Jensen, *Nervous System* (Icon Books UK 2007), the first English one | `nervous-system` | 296 (11–290, by `init`) | IA Scribe, 360 ppi, Milton Keynes library copy | a library label on the dedication page (p. 11); four part pages; small capitals (RCMP, TV, CBC); "A Note to Readers of the UK Edition" (pp. 285–288); a second scan of the same setting (US Carroll & Graf 2005, ABBYY layer) in `work/nervous-system--scan2/`, four PDF pages earlier, a few words localised | review paused by the user after 10 of 70 |
| Jane Gardam, *Going into a Dark House* (Abacus 1997 printing) | `going-into-a-dark-house` (scan in `work/candidates/incoming/`) | 196 | IA Scribe 5.2 | short stories: story titles as headings and as running heads, a contents page | built, 165 questions; not yet for review |
| Clare Wigfall, *The Loudest Sound and Nothing* (Faber 2007) | `loudest-sound-and-nothing` (scans in `work/candidates/incoming/loudest-{1,2}/`) | 244 | built from scan 2 (IA Scribe 4.4, first printing); scan 1 (ABBYY layer, paperback 2008) the same setting at the same PDF pages, a witness | short stories; Blackpool's library label (PDF 7) | built, 136 questions; not yet for review |
| Herman Brusselmans, *Ex-minnaar* (Ooievaar 1998, 6th printing) | `ex-minnaar` | 284 (7–279) | 360 ppi | motto on p. 7 (Leonard Cohen), set as an epigraph; drop cap; a poem on p. 50; blanked place names ("het __plein", `blank` in `book.toml`); an OmniPage OCR of the same scan beside it (`omnipage.pdf`, worse) | built 2026-10-16, questions sampled then; its review paused |
| Herman Brusselmans, *De kus in de nacht* (Prometheus 2002) | `de-kus-in-de-nacht` | 620 (7–616) | 300 ppi, large pages | parts ("Deel een", "Proloog" on p. 7), small-capital openings | not built (~10 h cold) |
| Emmanuel Carrère, *Andere levens dan het mijne* (De Arbeiderspers, tr. Floor Borsboom) | `andere-levens` | 248 (9–244) | 360 ppi | library copy; French names and accents | built; seven candidate misprints wait on the user |
| Emmanuel Carrère, *Een Russische roman* (De Arbeiderspers, tr. Marianne Kaas) | `een-russische-roman` | 276 (7–271) | 360 ppi | library copy; seven parts, each a small number atop its own page, with pencil marks the layer reads as noise; lines lost inside text blocks (pp. 133, 175); p. 272 show-through only | on hold (the user, 2026-10-19) until pages 46, 47 and 259 are photographed from a library copy |

For each book in turn: check its front and back matter and `body_pages`, build (cold
about a minute a page), sample the questions (`experiments/sample_questions.py`), the
**user** reviews, rebuild, epubcheck, a spot-check (5 random pages drawn by
`experiments/spot_check.py`; the **user** marks every wrong word, break and italic against
the scan, ~15–20 min: the book's own error estimate with its interval), the **user** reads
the EPUB. A read book's rebuild that changes text goes to the user by eye, every
difference (`experiments/rebuild_diff.py`). No full read-throughs soon beyond Stella's
(the user, 2026-10-20).

- [ ] Nervous System's review, paused by the user after 10 of 70 (2026-11-10: "this is
      wasting my precious time with something i expect roboscriptorium to handle deftly
      and confidently"). Resumed only after "One path for every doubt" has cut its
      questions and the count per kind, with why each is still asked, has been shown to
      the user. The same before Going into a Dark House and The Loudest Sound and
      Nothing are reviewed
- [ ] Short-story collections: a running head per story (Going into a Dark House: each
      story's title atop its odd pages, the book's on the even ones). The line-role
      trees, trained on novels only, call the story heads body at 0.5–0.75 ("Blue
      Poppies", "Bevis" kept, some glued to a story's first words) and took the book's
      title for a story heading on PDF 128; the layout model calls every story head a
      title (64 questions). Needs labels: a golden pair that is a short-story collection
      (**user**, the gaps to hunt for), then the trees retrained
- [ ] A story's first line set in capitals taken into its heading (The Loudest Sound and
      Nothing, PDF 57, "Caro at the Pool / SHE FOUND HER AT THE SWIMMING POOL."). No
      rule does it: the trees call the line a heading at 0.68, and the same type on PDF
      111 body at 0.89. Theirs to learn, with the short-story labels of the step above
- [ ] Bulleted lists (the user, Nervous System PDF 117: "should i use a ■ here?"). The
      book sets lists with small square bullets (PDF 117, 259); the layer reads each as
      "e", "¢" or "*", one line is asked and the rest go into the text silently. Detect a
      list from the scan (a small mark left of an indented run of lines), build it as an
      EPUB list, drop the misread markers
- [ ] Going into a Dark House, before its review: PDF 90's show-through stands as a
      garbled motto, unasked (the page-kind model calls show-through a motto)
- [ ] The Loudest Sound and Nothing, before its review: its wrong headings are all asked
      (Blackpool's label "00430050" as a heading on PDF 7, the half-title on PDF 11,
      "The Numbers / NUMBERS", show-through on PDF 182); the machine should settle them
- [ ] **user**: Pieter Daens' review, 292 questions (`uv run roboscriptorium review
      work/pieter-daens`)
- [ ] **user**: Hoe wij verdwijnen's spot-check, PDF pages 41, 77, 87, 144, 292
      (`work/probes/spot-check/hoe-wij-verdwijnen/index.html`); the counts are of the
      build before the "op"/"een" italic fix
- [ ] **user**: Andere levens' seven candidate misprints, saved as printed
      (`work/probes/carrere-editions/andere-levens-checked.md`): which, if any, are
      misprints
- [ ] Ex-minnaar: rebuilt with everything since 2026-10-16 and its questions sampled
      again, then the **user**'s review and the fixes it teaches. Its poem on p. 50
      (title taken for a chapter heading, lines joined) waits on verse
- [ ] De kus in de nacht built, once the review's questions are worth the user's time
- [ ] The structure check's findings walked in the review page (every kind, its crop)
      before the next review (`flags.structural`)
- [ ] A washed-out page says which it is (the user, 2026-10-19, on a PDF's embedded
      images: "have a good think"): "lost in this PDF" (Een Russische roman's and
      Afscheid's pages, where the mask holds speckle and the background smudge) against
      "faint in print", and what the review offers for each. Contrast can't tell mottled
      paper from faint print. The rest is answered: the mask shows no more than the
      render the readers get (2026-10-23), and a lent item's full-resolution originals
      can't be had (2026-10-11)
- [ ] Een Russische roman, when it comes off hold: check that its lines lost inside
      text blocks (pp. 133, 175) are now read (`missing._fills`, 2026-11-06), and count
      the footnotes lost or made over the golden books with notes (its p. 270 note's
      misread mark was mended 2026-10-19)

## Headings and line roles

- [ ] Heading errors left on tuning, about twenty (low; `experiments/heading_misses.py`
      lists them by book). Each is one book's case, so they are mended only where one
      cause covers several or the trees can learn it, not by a rule a book: drawn part
      numerals read as digits (De eerlijke vinder's I–IV, 0 of 4, on pages the page-kind
      model calls blank), numbers on openings sunk less than `page.SUNK_PAGE_DROP`
      (Afscheid's chapters 1 and 2), headings found but not set as printed (Dolittle 7,
      Thief-Taker 6), a number misread or lost beside its title (Metro's "CHAPTER 6" and
      7, Het geluid van bananen's "8°"), Het ijzige land's chapters 1, 3, 7, 8,
      Dolittle's title page and drawn initial, De cipier's lost scene break
- [ ] Line-role trees that keep the grown slices' gains without keeping stray lines
      (decisions.md, 2026-11-05): retrained on the grown slices they find Monterosso's
      mid-page chapter numbers (7 → 15 of 22) and Reis' (16 → 19), but keep Dolittle's
      and Afscheid's running heads as text. Check each attempt with
      `experiments/sorter_keep.py` (stray lines kept at 0.25: 214) before a bench.
      Ideas: the running head's recurrence counted over its chapter, not the book; the
      stray lines weighed by the words they add, as the bench counts them. Also theirs:
      Het heft's datelines under its headings ("Februari 1829") joined to them
- [ ] Scene breaks the build misses: 23 of 295 (Reis 14, De eerlijke vinder 7). Reis's
      are page tops after a full page whose last line ends a sentence at the margin, the
      next opening flush: the same geometry as a paragraph running on, so only the text
      can tell (a sorter question, "a new scene?"). Het heft (`P_plat`), Villa
      (`Tekst_6-Na-witregel`) and Artemis (`noindent_topspace1`) undeclared, unsure on
      the scan

## Paragraphs, verse and lists

- [ ] Paragraph starts in books set flush, learned: edge classification on a graph of
      lines (Wang et al., WACV 2022), or a model told the book's indent regime. Every
      break error left in the flush books is a start after a full line, which only a
      learned model finds; the short last line is the mark, as in indented books, so
      synthetic flush pages from the tuning books miss nothing (2026-10-24). Blocked on
      a flush-set tuning book (**user**: a scan and the publisher's EPUB, not A.W.
      Bruna's); then the synthetic pages and the model (~2 days)
- [ ] Verse, lists and block quotes: most of the paragraph errors left on tuning
      (Dolittle's poem, Thief-Taker's song, Glazuur's numbered list); also Pieter Daens
      p. 354 and Ex-minnaar p. 50. In scope later (AGENTS.md, content order); golden
      pages that have them first

## Errors no question asks about

About 85% of the wrong words left after review were never suspects: every reading agreed
on them. On tuning, 2026-11-06: stress accents 105 (half the reference's), compound
hyphens 86 (line-end breaks), letters 76, punctuation 59. What was tried on them
without effect, and what each would need to be tried again, is in
[outlook.md](outlook.md) ("Tried, and why it didn't help").

- [ ] Past nulls the judge panel may turn (2026-11-08; the ones whose stated bottleneck
      was the judges or the arbiter), in this order: the hints about kinds of OCR error
      (`tryout.py --prompt kinds|targeted`) on autotrust-jev, d3 and pplx-decider
      (~15–30 min each, judge set v2); d3 and autotrust-jev as the line-end hyphen judge
      on the 542 undecided Dutch breaks and the English ones (offline probe); line roles
      by the small decision models; then the whole-page readers as line readers (null
      2026-10-14/15: the arbiter trusted their versions wrongly on unseen books; their
      readings are cached, so the cost is the panel's judges on the new suspects, a
      trust-data rebuild with `ROBO_PAGE_READERS=1` in its own folder, the arbiter
      retrained and both benches)
- [ ] De vergelding's own arbiter: it has the most unsure suspects and was never trained
      on; comes with its trust data (In flight)
- [ ] Spacing the build sets against the print, read off the crops of 223 unasked
      places (2026-11-12, decisions.md; `work/probes/unasked/spacing-20261112/`), each a
      repair with its counterexamples tested:
      - a dash before a closing quote set closed ("Dud—’") or spaced on both sides
        ("Granny – ’") where the book's other dashes take a space on one side (16, The
        Stranger's Child): the scan tells them apart, the layer doesn't (decisions.md,
        2026-11-12); needs each dash's place on the scan in the styling, and a tuning
        book that prints so to choose the line on
      - single slips with no rule in common, the readers' and the arbiter's to catch: a
        line-end hyphen kept inside a word (5: "brab-bel", "sexy-er", "zig-zag-ging"),
        a speck read as a hyphen (4: "was-time", "doordat-hij"), a space the print sets
        before a mark lost (4: "Paulina :"), Het laatste bevel's tight lines glued (4;
        splitting long unknown words by the word list doesn't find them, decisions.md)

## Assumptions to test (quick probes, minutes to an hour each)

The pipeline reads lines and joins them by hand-built geometry because that was what
models could do. Each probe asks whether that still holds, on a few golden pages
(tuning books), before any building; worked through between fixes (AGENTS.md, "Test
the architecture"). Record each result, null ones too. The probes already answered
are under Done, "Architecture probes".

- [ ] **Render and compare** (the user's idea, 2026-11-11; decisions.md of that day has
      the idea whole): a judge that knows no language. Each version of a suspect is
      drawn as the book would print it and laid over the scan's ink; the better fit gets
      the vote, and the arbiter learns its trust from the golden books. Aimed at specks,
      small capitals, ligatures, accents. First test, Stella: the print on 9 of 9
      labelled places, each judge 5 or 6; De tuin and De cipier 94% and 93% of 4,162,
      with nineteen in twenty of the judges' misses right (`probe_render_compare.py`,
      decisions.md 2026-11-12). In order:
      - [x] The golden books' typefaces matched and the test on their labelled places:
            the print on 87% of 26,309 over 23 books; as one more vote the arbiter's
            silent errors fall at every budget (26 → 19 at the rule's questions,
            189 → 153 at a question every four pages; decisions.md 2026-11-12)
      - [x] The font pick mended (a Medium weight is a text cut: four books 81 → 85%)
            and the fit built in as a judge, off by default (`rendercheck.py`,
            `ROBO_ALARM_MODEL=…,render`; decisions.md 2026-11-12)
      - [ ] Its vote and margin in the trust data, the arbiter retrained, `bench
            tuning` and `validation` (in flight, `work/runs/render-judge.sh`); then
            **on by default** (the user, 2026-11-12): `render` in `alarm_model`, the
            arbiter trained with its vote in production's place, the diagram,
            how-it-works and the judge's row in AGENTS.md
      - [x] The typeface chosen among near-ties: the best five text cuts ranked again
            by the judge's own fit on 150 plain words (90.0 → 91.1% of labelled places
            over 23 books, Metro 2033 67 → 87%; the best of the five 91.7%). Null: the
            best few faces voting together (decisions.md 2026-11-12)
      - [x] **The typeface as part of `init`** (the user, 2026-11-12): `init` runs the
            match and drafts book.toml's `typeface` with the faces it chose among; the
            build reads the key before matching
      - [x] An ordinal's ending drawn as a superscript and digits in the font's
            old-style figures (20 of 478 labelled places with a digit fixed, 4 made)
      - [ ] The second round: trust data and arbiter with the new typefaces and
            drawings, benched against the first round's control (in flight,
            `work/runs/render-judge2.sh`)
      - [x] The judge's confidence as the probability its pick is the print, from how
            well the pick fits and its margin (AUC 0.80 against the margin's 0.73): a
            typeface that suits a book poorly lowers its votes' weight
      - [ ] **More tactics** (the user, 2026-11-12: future sessions explore them; each
            is a probe on the labelled places first): punctuation, its weakest kind
            (91% against the model judges' 96%): the two versions compared only where
            their drawings differ (probed 2026-11-13: 92.6 → 93.3% of places as the
            pick, uneven by book; next as features for the arbiter); font features in the drawing
            (libraqm or HarfBuzz: real ligatures, small capitals and old-style figures
            for every font, not only those with code points for them); the ink spread
            and blur fitted to each scan more finely; a word's cut chosen per place
            (italic, bold, small capitals); the kerning and spacing ways learnt from
            the book's uncontested words instead of fixed lists
      - [ ] **Matched-font rendering** (the user's): the typeface found from the scan,
            for the shapes the book can't supply. The family is found for eight of the
            user's ten books (the user's library, in `work/fonts/`: Quadraat, Janson Text
            four times, Trump Mediaeval, Minion, Sabon); Ex-minnaar and Going into a
            Dark House undecided. Left: the weight, the italic and small-capital cuts
            (which word is set in which), and the two undecided books
      - [ ] **Own-type templates**: letters, ligatures and marks cut from the book's own
            uncontested words, same scan and ink: to fit the matched font to the book's
            ink (accent margins are thin: 0.02–0.06), and for a book whose typeface the
            library lacks
      - [ ] **Leftover ink**: the agreed reading drawn and taken from the scan; ink left
            over raises a suspect where every reading agrees (a missed stress accent, a
            speck). Tried first on the six known stress accents and the quiet set
- [ ] Qwen's page roles as an input to the trees (`pageroles.py`, `ROBO_PAGE_ROLES`,
      off; not taken twice, 2026-10-24 and 25). A strong signal on plain pages (headings
      126 of 126 against the pipeline's 110), but the trees trained with page features
      go wrong on picture pages, mottos and an epigraph's attribution. Before another
      bench: the trees retrained with picture pages and mottos labelled

## Starting from a PDF alone

- [ ] `init`'s confirmation on the review page (agreed 2026-10-11; the user,
      2026-10-21): the first and last page of the text proper shown with their crops,
      each named by both numbers ("PDF page 9 (the page prints 7)", or that it prints
      none), with whatever else the draft `book.toml` marks to confirm

## Golden books and the bench

- [ ] **user**: golden pairs for the gaps (golden-notes.md, "Gaps to hunt for"): first a
      book set flush for tuning and a short-story collection; then section headings
      without numbers, text wrapped around pictures. From before: De Arbeiderspers,
      Prometheus/Ooievaar or Vrijdag; a Kosmos book for later, beyond prose
- [ ] **user**: 58 unasked errors that look like the reference's, to confirm
      (~15 min, one `review --only` command a book in HANDOVER.md, "Waiting on the
      user"). Of the 223 unasked places that
      differ from the reference only in spaces or hyphens (fresh baselines, 2026-11-12),
      each read on its crop by the agent: in 58 the print is as ours has it (a space
      before a mark the print doesn't set, words the e-book runs together or splits, a
      hyphen the print sets inside the line); 75 are the build's (Errors no question
      asks about); 70 are hyphens at the print's line end, which no crop settles; 20 are
      the spacing beside an ellipsis. The readings:
      `work/probes/unasked/spacing-20261112/readings.json`
      (`experiments/unasked_spacing_sheets.py`)
- [ ] `golden check <pdf> <epub>` writing a draft manifest, once a batch of candidates
      comes

## Housekeeping

- [ ] Worktrees and branches: `../roboscriptorium-caps` holds `italics-by-place` and
      `../robo-grow6` `grow6` until they are merged; `../robo-text` (`text-seat`) stays
      for the retest; `../roboscriptorium-py315` has two untracked scratch files. The 24
      branches merged into main can be deleted; `cutoff-dash`, `qwen-second-look` and
      `trial-merge` are unmerged experiments, not taken (the merged worktrees
      `../robo-quote` and `../robo-phased` were removed 2026-11-11)
- [ ] **user**: disk. `work/models/mlx-env` (809 MB), `~/models/roboscriptorium/lighton-env`
      (767 MB) and `work/models/ocr-trust-grown*.pkl` stay until the user says they can go
- [ ] Python 3.15 once PyTorch publishes cp315 wheels (pytorch/pytorch#184352): with
      nightly torch every test passed (2026-10-11); bump `.python-version`, `uv lock`,
      bench once

## Later

- [ ] French, the user's idea (2026-10-09); not yet (2026-10-10: no French books to
      make). It brings its own typography (« », a thin space before `; : ! ?`, dialogue
      dashes) that `quotes.py`, `typography.py` and the arbiter's training data would
      all need. If it comes: one French Wikisource book proofread page by page against
      its scan, a first look like any new pair

# Done

By area, newest first within each; one step each, with its date and the number that
settled it. The numbers behind them are in [decisions.md](decisions.md) on the day.

## The user's books

- [x] 2026-10-19 Other editions as an error finder (the user, 2026-10-18;
      `experiments/probe_translation_check.py`, hosted): an instrument for a book with
      no reference. Stella: one reading error ("trofik") in 46 flags, and 29 of 31
      planted word errors caught, none of 6 lost accents; Andere levens: one silent
      error ("LC1" for "LCI"); Een Russische roman: the hyphenated chains, the diaeresis
      and the footnote mark, all mended since. For another book: the user's permission
      for the hosted run first
- [x] Nervous System built cold (2026-11-09, judging finished on the new judge order;
      epubcheck clean): 520 OCR suspects, 285 fixed, 23 asked. The second scan as a
      witness found two of our errors in 756 disagreements (decisions.md): not a stage
- [x] Hoe wij verdwijnen reviewed by the user (2026-11-02, 53 answers in two rounds; the
      review smartened between them); rebuilt with them, epubcheck clean
- [x] **user** read the EPUB through (2026-10-31, `epubs/stella-2026-10-19-0014.epub`):
      no errors. Two sentences queried as odd (p. 41 "Ik weet dat aan…", *wijten*; p. 50
      "met welgevallen") match the scan
- [x] 2026-10-24 Stella rebuilt with every fix since its review: text and paragraphs
      unchanged
- [x] Stella's errors estimated against Claude's reading (2026-10-16): 4 wrong words in
      67 pages before review, 2 asked; 6 questions. Unasked: two words joined after a
      tight f ("grofwerk", "trofik")
- [x] Stella's review (2026-10-16): 6 questions answered, two accents corrected ("íéts",
      "ís"); rebuilt, epubcheck clean (`epubs/stella-2026-10-16-0859.epub`)

## Structure and line roles

- [x] ~~Structure findings repaired where the book's own evidence settles them, beyond
      the chapter numbers~~ (dropped 2026-11-11): no case behind it; a finding that
      shows one becomes its own step
- [x] ~~De geruchten's narrator names as section headings (0 of 21) and You're Never
      Weird's bracketed sections (5 of 16)~~ (moved 2026-11-11): validation books, so
      not chosen on; a tuning book with such headings is on the gaps to hunt for
      (golden-notes.md)
- [x] ~~De laatste roker as line-role training~~ (dropped 2026-11-11): another novel,
      where the trees lack short stories and picture pages
- [x] ~~A heading suspect whose versions differ only in case settled by the book's other
      headings~~ (2026-11-09, `chapters.heading_case`): Het ijzige land's six asked
      headings, nothing else in any book's cached suspects; benched with production's
      tuning run
- [x] ~~A scan that repeats or skips pages~~ (2026-11-07, `scanpages.py`): Goede
      dochter's repeated PDF 218–219 left out, its missing printed 286–287 named by
      `build` and taken out of its reference by a verdict; its wrong words 3.22 → 0.48 a
      page
- [x] ~~A chapter number with a speck after it~~ (2026-11-06, `chapters.value` leaves
      out punctuation after the number): Thief-Taker's "20 ;", tuning heading errors 24
      → 23
- [x] ~~Specks read as a number off the run~~ (2026-11-06, `chapters.off_run`):
      Doodskleed's "7" and "3", tuning heading errors 26 → 24, no word changed
- [x] ~~A part page's title under its "Boek n"~~ (2026-11-06, `title_lines`,
      "part-page"): Het geluid van bananen 32 → 35 of 36, tuning heading errors 29 → 26,
      no word changed
- [x] ~~Misread chapter numbers where the run has a gap~~ (2026-11-06,
      `chapters.run_gaps` reads them again with glm-ocr): Monterosso 19 → 22 of 22,
      tuning heading errors 32 → 29, no word changed on either set
- [x] ~~Chapter labels recurring under headings~~ (2026-11-04): Het schaduwhuis'
      headings 32 → 67 of 68, no extra headings in another book
- [x] ~~Chapter numbers the layer and the spotter both miss~~ (2026-11-04,
      `missing.openings`): six lost numbers in three books read; Vuurspel's headings 5 →
      6 of 6 on validation
- [x] Het schaduwhuis' reference had no italics (its e-book sets them by class):
      `italic_classes` declared, derived again (2026-11-03)
- [x] Pieter Daens rebuilt warm with [7, 787] and today's code (2026-11-02, 3 min): the
      table of contents left out, the ads gone, its page of four mottos set apart (asked
      as a page before the first heading). Boek twee to vier's subtitles, dropped by the
      trees, headings again (`chapters.title_lines`). Boek vijf's "Onze doden", absent
      from the layer, read since (2026-11-02): all six part titles whole
- [x] A motto's wrapped lines joined into its paragraphs (2026-11-02,
      `reflow._wrapped`): Pieter Daens' three prose mottos one paragraph each, its song
      and the Camus motto line by line
- [x] Chapter numbers (2026-11-01, `chapters.py`): all 52 of Hoe wij verdwijnen right on
      its warm rebuild; the five dropped ones read right by the readers once kept
- [x] Front matter (2026-11-01, `pagekinds.set_apart`): the page-kind model asked about
      short pages of the text proper; Hoe wij verdwijnen's dedication and motto each one
      block. Their italics too (`italics.uniform`, one type per motto or dedication):
      "Voor" italic, "Zwart" upright, nothing else in the book moved
- [x] A structure check at the end of every build (2026-11-01, `structure.py`): numbers
      out of their run, a title among numbers, sections under 20 words; `build` prints
      the count. On the 44 books built so far: 18 places in 6 books, all errors by eye
- [x] Each structure finding a review question (2026-11-01, `flags.structural`): at its
      first line, or a reason on the question already there. To walk in the review page
      before the next review (every kind, its crop)
- [x] A footnote whose mark the layer misreads (done 2026-10-19, merged: decisions.md;
      its notes lost or made are still to count on the golden books with notes; found by
      the edition check): Een Russische roman p. 270's translator's note "*Erik Orsenna
      (1947)…" stays in the running text, spliced mid-sentence into the paragraph that
      runs on, because the layer reads its "*" as "“" and `footnotes._MARK` decides on
      the layer's text; the OCR check corrects the mark to "*" afterwards. Decide on the
      checked text, or take a quote glyph at a small-type foot line's start for a
      misread mark; then count notes missed over the golden books with notes
- [x] `heading-pairs` and `number-lookalikes` merged (2026-10-17), the trees retrained
      on the long slices: Metro's headings 3/8 → 8/8; extra text 1.08 → 0.63 a page on
      tuning
- [x] ~~Verdict page: a place where one side has something the print lacks says so in
      words~~: merged 2026-10-17 (`review.py`: "the publisher's e-book has “>” here, our
      text nothing")
- [x] 2026-10-17 Paragraph starts: a line beginning in lower case after one not ending a
      sentence carries on (no model); the vision judge (`parabreaks.py`) off, as it
      broke more than it fixed; breaks tuning 0.19 → 0.15, validation 0.21 → 0.13 a page
- [x] Metro's lost closing quote after a spaced ellipsis (2026-10-16): the layer drops
      it, the readers write `. . . '`, curled as opening or not at all; now closed at a
      line's end and curled by the book's style, Metro 0.42 → 0.33 wrong words a page
- [x] Monterosso's capital T read as an opening quote (2026-10-16): one case left in the
      build ("‘Lieve ‘Tiziana,’ zegt"), asked at the paragraph's end ("open at end"),
      not where the ‘ stands, since quotes nest in their own mark; not worth a rule for
      one
- [x] 2026-10-11 Footnotes out of the running text, linked to their marks
      (`footnotes.py`): Reis 7 of 8 found and linked (the eighth's mark read "ie"), no
      false ones on the benches after a stroke-weight limit; Reis paragraph breaks 0.07
      → 0.06, BETTER
- [x] 2026-10-11 Paragraph breaks in unindented books (Bruna's): justification judged on
      lines that stop mid-sentence, a page's short last sentence carried over;
      validation breaks 1.97 → 0.21 a page (Vuurspel 7.91 → 0.44), tuning 0.26 → 0.22,
      no book worse
- [x] 2026-10-11 A dropped line that reads as running text kept and flagged
      (`roles.running_text`): tuning **better** 0.43 → 0.37, validation **better** 0.82
      → 0.76. The trees on top of it: no change (0.37 → 0.40, 0.76 → 0.72), Thief-Taker
      and Vuurspel clearly worse; ~~trees on by default~~ dropped, they stay off
- [x] 2026-10-09 Line roles by trees (`sorter.py`, `ROBO_SORTER=1`, off): role errors
      406 → 152 tuning, 77 → 29 validation leaving one book out; bench no change, three
      books clearly better, Crime one lost line
- [x] 2026-10-09 Paragraph starts from a page margin fitted on full lines: breaks set
      wrong −28% tuning, −34% validation, the second review's one clear win
- [x] 2026-10-09 Headings: 11/22/63's numbered sections 5 → 23 of 24; Villa Toscane 0 →
      12; De cipier 3 → 4; Afscheid's misread numerals 8 → 11 (`numeral-slot`);
      Artemis's circled numbers 0 → 3 (`missing.py` reads five lines above a sunk page)
- [x] 2026-10-08 Line-end hyphens by evidence in order (the book's spelling, the word
      list, a capital, the parts beside an inner hyphen): wrong 29 → 15 of 1,574
- [x] 2026-10-08 Italics measured against Metro's print: the print sets every station
      name in italics, the eBook two; marked unscored (`italics_unlike_print`)
- [x] 2026-10-08 PP-DocLayoutV3 as the spotter: worse downstream (Dolittle CER 1.22% →
      1.71%), not adopted. ~~A crop reader on tesseract's boxes~~ dropped: an image-only
      scan's layer is tesseract's already
- [x] 2026-10-08 tesseract's first reading of an image-only PDF (`pdf.first_reading`):
      Goede dochter without its layer 0.35% CER against 0.20%

## Words, quotes and typography

- [x] 2026-11-12 Four repairs to spacing the build set wrong, read off the crops of the
      unasked places: a chain broken beside a short word keeps its hyphen
      ("second-to-last"), a line ending on a dash its box leaves out doesn't start a
      paragraph (Dolittle, 9), an ellipsis after a closing quote keeps the layer's
      space, a dash before a word opening on an apostrophe keeps its space. Tuning
      BETTER (38 fixed, 1 made), validation no change (7 fixed, none made)
- [x] ~~An accent told from an i-dot or a speck by its shape; the per-book alphabet~~
      (the user, 2026-10-21; parked 2026-11-11): at line level the shape gives AUC
      0.66–0.76; emphasis accents and the dotless ı need each mark tied to its letter,
      so a reader that gives letter positions (outlook.md, "Tried")
- [x] ~~The errors the build makes where the layer was right~~ (51 unasked on tuning,
      2026-11-06; closed 2026-11-11): accents (18) are accent-shaped specks with no
      cheap signal, commas added are wrong 13 of 14 with no rule, quote glyphs (6)
      aren't told by the book's quote style; the specks go to "One path for every doubt"
- [x] ~~Line-end compound hyphens learned from the compounds the books print unbroken~~
      (dropped 2026-11-11): 14 real hyphens in 542 undecided Dutch breaks, and qwen,
      clef and the cheap cues tell none apart; the judge panel's hyphen probe is the
      last try
- [x] ~~The line-end join's book spellings counted from the text after the OCR check~~
      (2026-11-08): already so (`pipeline._book_spellings`: the pages being built after
      the check and the answers; only a bench slice's other pages as the layer reads
      them, which no build checks). The join asks the book first ("Númen-" / "or" joins
      where the book prints "Númenor" inside a line)
- [x] ~~(Low) Line-end compounds by definition~~ (2026-11-08, branch `hyphen-rules`,
      merged once `src/` is free): an all-capitals part before a lower-case one keeps
      the hyphen ("NSB-leden"), a stem left open before "en" where the word after is a
      compound whose end joins the stem ("voor- en achterbank"); tuning 8 fixed,
      validation no change
- [x] ~~A paragraph the layer lost whole~~ (2026-11-06, `missing.blocks`): Dolittle's
      PDF 97, tuning 105 wrong words fixed (81 unasked), 1 made; its title kept with it
- [x] ~~Lines of dots both layer and spotter lose~~ (2026-11-06, `missing.slots`,
      `quoted`, `slot_lines`): tuning 4 fixed (Het geluid van bananen), validation 5
      (Verminkt), none made; Het geluid van bananen's p. 25 and 76 and Vanille's leaders
      stay lost
- [x] ~~A quote mark misread from a speck no version~~ (2026-11-06, `quote_misread`):
      "keek’en" fixed; "de’schaft" (two letters before) stays
- [x] ~~Whole lines of text lost inside a block, found in the same inked slots~~
      (2026-11-06, `missing._fills`): nine lines read right by glm-ocr, tuning 103 wrong
      words fixed (12 unasked), validation 9 (all unasked), none made; Dolittle's short
      last line of a paragraph stays a question
- [x] ~~A Dutch line-end break between clashing vowels keeps its hyphen~~ (2026-11-06,
      `hyphens.vowel_clash`, a word of four letters or more after the break, no glide
      before it): tuning 3 fixed, validation 1 ("mini-jurk"), none made
- [x] 2026-11-06 Lines lost inside a text block read before they are asked
      (`missing._fills`; found by the edition check on Een Russische roman, 2026-10-19):
      the same step as the whole lines found in inked slots, below
- [x] ~~A stop added mid-line right before a lower-case word no version~~ (2026-11-05,
      `line_end_stop`, the next word undisputed): tuning 2 fixed, validation 5, none
      made
- [x] ~~An "ij" read as u, ui, y, ii or i no version~~ (2026-11-05, `ij_misread`): De
      vergelding's names, tuning 3 fixed, none made
- [x] ~~Learned italics on by default~~ (2026-11-04): `italic_trees = True`; tuning
      italic errors 2,445 → 1,088, validation 328 → 203, BETTER on both, no veto
- [x] ~~Stops added after a word before lower case~~ (2026-11-04, `line_end_stop`
      widened): 4 of the 7 fixed on tuning; "the. ground" (Artemis) is no suspect, from
      another stage
- [x] A short word leaning a little among upright ones no italic (the user's spot-check,
      2026-11-03: "op", "een" in Hoe wij verdwijnen): a lone word measured on fewer than
      three stems needs 12°, slants count from the page's upright, a run keeps its word
      at a line end (`italics._italic`). Tuning false italics 433 → 331, validation 245
      → 162
- [x] ~~A lone word with a diagonal letter or acute accent held to 12°~~ (2026-11-03,
      not taken): tuning italic errors 2,445 → 2,588; a capital Z or W leans the word
      ~26°
- [x] Quote questions: a possessive after an s-sound ("Maurice’ moeder") no longer a
      closing quote (2026-11-02): Hoe wij verdwijnen's quote questions 37 → 16
- [x] Pieter Daens' quote questions sorted (2026-11-02): of 159 unpaired places, 101
      open at a paragraph's end, by the scan real losses (p. 50 prints "zingen.’", we
      read "zingen."): a closing mark after the stop that the readers drop. Fair
      questions
- [x] The closing mark lost after a paragraph's last stop as a fix where the reading
      adds only that mark (2026-11-02, `quotes.closed_at_end`): 39 of 39 the print on
      tuning; Pieter Daens 38 closed, its questions 338 → 309
- [x] ~~One question per letter quoted over paragraphs~~ (dropped 2026-11-02): where a
      paragraph is left open and the next opens with the same mark, the print closes the
      first 20 times in 45 on tuning: asking once would leave those 20 unasked
- [x] ~~A comma at a line's end turned into a stop by the check~~: done 2026-10-24 as a
      rule true by definition (`ocrcheck.line_end_stop`, widened 2026-11-04 to a stop
      added after the last word; tuning 0.290 → 0.286, 6 fixed, none made)
- [x] ~~Line-end hyphens as questions where the judge is unsure~~ (dropped 2026-10-24):
      Dutch real hyphens are 14 of 542 undecided breaks, so no band of the judge's
      sureness pays; English 6 wrong of 30, near the price
- [x] Line-end hyphens inside hyphenated chains (done 2026-10-19, merged; 55 of 60 right
      on the chain probe, warm bench no change: decisions.md; found by the edition
      check): Een Russische roman prints a chant,
      "geen-verandering-in-de-toestand-van-de- patiënt", broken at its own hyphens
      ("in-de-" / "toestand", "van-" / "de"), and the build joins both as break hyphens
      ("in-detoestand-vande"), silently; the next line prints the chant whole. The
      latest benches hold five more, all unasked: "neem-jehuisdier",
      "doe-hetzelfbouwdozen", "muzieken-lichtshows", "topaasen-amberkleurige",
      "glas-inloodramen". A hyphen at a line end in a word that has another hyphen is
      mostly the word's own, but not always ("Noord-Hol-" / "landse"): give the joiner
      the chain as evidence (and the book's spellings of chain pieces), its
      counterexamples tested first
- [x] A Dutch word broken at its diaeresis gets it back when joined (done 2026-10-19,
      merged: decisions.md; low; found by the edition check, 2026-10-19): Dutch drops
      the diaeresis where it breaks a word ("democratieën" as "democratie-" / "en"), so
      the join must try the ë or ï form against the word list. Een Russische roman's
      became "democratie- en", taken for a word left open before "en"
      (`hyphens._suspended`, "voor- en nadelen"). True by definition, so code; no other
      case in the latest benches
- [x] ~~A closing dash keeps the layer's spacing on its open side~~ (2026-10-18, not
      taken, branch `cutoff-dash`): tuning fixed 5 and made 10, all Goede dochter. Its
      print spaces a sentence broken off after a word ("ik –’") and closes up a word cut
      off ("directeursk–’"), and the layer reads both closed. Only each gap measured on
      the scan could tell them apart: ~10 places in 1,900 pages, left
- [x] 2026-10-17 Lines the text layer lacks at a text block's top or bottom: a strip of
      a text region above its first layer line or below its last is a candidate
      (`missing.edges`); Vuurspel p. 19's two lines read right. With Bruna's references
      re-derived without markup spaces: validation BETTER 0.49 → 0.38 after review
- [x] 2026-10-17 The Stranger's Child's nested-quote spacing: the print sets a thin gap
      between nested marks, some e-books write it as a space; folded in the score
      (`evaluate._NESTED_GAP`), validation BETTER 0.38 → 0.36. Its "think—’" against our
      "think –’" is the print's after all: a dash breaking speech off sits close to its
      word there (scan crops, 2026-10-18), where its other dashes are spaced
- [x] De eerlijke vinder's unasked errors (2026-10-15): 28 of 38 were page numbers the
      layer joins to a body line; split off (`pdf._apart`), wrong words 0.88 → 0.42 a
      page on the short test; `bench tuning` 0.32 → 0.30 after review, no book worse

## Trust data, the judges and the arbiter

- [x] 2026-11-12 Production's arbiter is twenty trainings averaged with a smooth
      calibration, trained on batch five's trust data, asking below 0.93 (the user's
      choice; the old one kept in `work/models/ocr-trust-backup-20261112/`)
- [x] ~~A lone small capital with the lower case's shape ("v-hals", "u-bocht")~~ (parked
      2026-11-11): no judge tells it, on a tight crop or a wide one; retest with each
      new vision judge (outlook.md, "Tried")
- [x] ~~A detector for errors every reading shares~~ (the user, 2026-10-12; parked
      2026-11-11): its features were null (the word list for lost spaces, tesseract's
      confidence, accent variants; 2026-10-16); the lever is a stronger reader
      (outlook.md, "The errors every reading shares")
- [x] 2026-11-11 The arbiter's variance brought down: retraining is exact, and one
      retraining differed from the next by some fifteen unasked errors for 72 changed
      suspects; twenty trainings averaged and a smooth calibration steady it
      (`trust.Trees`, `trust.Curve`; design.md). The switch is under In flight
- [x] 2026-11-11 Small capitals: the capitals version of a mixed-case word merged
      (tuning unasked 524 → 521), and the doubts on lower-case pieces on by default, the
      user's call (`ROBO_LOWER_CAPITALS`: tuning unasked 524 → 512, none made unasked,
      questions +1.7%)
- [x] ~~autotrust-jev 9B as a second text judge~~ (2026-11-09, pass 4): not taken.
      Tuning unasked 551 → 535, validation 170 → 178 (decisions.md); failed on the
      arbiter's 23 books, branch `text-seat` kept for a retest after batch five
- [x] ~~New vision decision models as judges~~ (2026-11-09): autotrust-jev 35B and d3 9B
      taken beside clef, asking below 0.9 (decisions.md); pplx-decider on the wide crop
      not taken (pass 3); the rest screened and set aside on the panel test (models.md).
      Still open from it: the hints for the new judges and line roles for the small
      ones, under "Past nulls the judge panel may turn"
- [x] ~~The book's own vocabulary as an arbiter feature~~ (the user's idea, 2026-11-08):
      null on today's arbiter (decisions.md, 2026-11-08). Its signal is real on readers'
      real-word swaps ("wegkwijnen" over "wegwijken"), but the trees pay for any extra
      columns about as much; retest when the arbiter's training data grows or it changes
      kind
- [x] ~~The judges told the kinds of OCR error~~ (2026-11-07, judge set v2): not taken.
      clef:27b weighted 91.3% → 89.9% (91 hard picks fixed, 16 right ones broken, all at
      low confidence); Winnow-12B worse on both halves, stopped at 525 of 995
- [x] ~~One more reader?~~ Answered 2026-10-24 by the quiet set (`quiet_set.py`): the
      layer and both readers are wrong together on 23 lines of the tuning slices, so a
      new reader can add a handful; LightOnOCR-3 found 1
- [x] ~~Winnow subtracted?~~ Done 2026-10-24: WORSE without it (tuning 0.282 → 0.316, 79
      fixed, 164 made; decisions.md); Winnow stays
- [x] ~~Small capitals as a version for the judges~~ (null on its short test,
      2026-10-20: decisions.md; branch `small-caps` unmerged; found by the edition
      check, 2026-10-19): Andere levens' one silent error is "LC1" for "LCI" set in
      small capitals, where no reading had the capitals; in the latest benches 18 errors
      are capitals read in mixed case ("vTM", "voc", "ocMw", "xTc", "cr" for CT), 7
      unasked. The judges' prompt already knows the pattern but can only pick among the
      readings: add a reading's all-capitals form (letters only, 1 → I, 0 → O) as one
      more version where it mixes case inside a word, and let them choose. Upstream of
      the OCR check's caches: short test on the pages it touches, then a cold bench
- [x] ~~A context judge~~: stays off (the user, 2026-10-19, shown it passing both sets
      with fewer questions but more unasked errors: "then i'm against it"; decisions.md)
- [x] 2026-10-18 Winnow-12B the text judge, asked through token probabilities: right
      alone 81% (winnow-ollama:e4b 67%), its arbiter tuning 0.30 → 0.28 after review,
      better; validation 0.37 → 0.39, no change; the Ollama pin's reason gone
- [x] 2026-10-18 `experiments/rebuild-trust.sh` builds every book's trust data, the two
      labelled by review answers (Stella, Ex-minnaar) at their body pages too, and
      trains without `--partial`
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
- [x] 2026-10-11 Ask threshold 0.7 / 0.8 / 0.9 on tuning: 0.74 / 0.92 / 1.11 questions a
      page for 0.351 / 0.344 / 0.343 after review; stays at 0.8 (yield falls off past
      it)
- [x] 2026-10-11 ~~De tuin's four questions no longer asked~~ dropped: it no longer
      loses (0.64 → 0.59 with `bughunt`)
- [x] 2026-10-11 Branch `bughunt` merged: the hunt's 22 fixes and its seven open
      findings, trust data rebuilt warm (MODEL_VERSION 6), arbiter retrained; tuning
      **better** 0.50 → 0.48, six books clearly better, none worse; validation no change
- [x] 2026-10-11 Trust data for Thief-Taker and the five new books (567 pages, 525 min),
      arbiter (~10,400 suspects) and trees retrained: **the new baseline**, tuning 0.50,
      validation 0.74 wrong words a page after review; trees 0.48 / 0.67, no change
- [x] 2026-10-09 imajev-4b as a third judge: trust data with its votes, retrained, no
      change (tuning 1.02 → 1.01, validation 0.81 → 0.80); off. Page types 19/23 like
      clef-flash, body ends 227 against 231: `body_pages` stays in book.toml. Which way
      a plate is up: 10/10, the candidate for plates without a caption
- [x] 2026-10-09 Qwen's third reading stays: without it tuning 1.00 → 1.33, validation
      0.81 → 1.01. Short lines stay. Qwen's second look at 450 dpi as a trust feature:
      no change, branch `qwen-second-look`. Washed-out pages left out of the check
      (`faint.py`), the arbiter's ≥ 0.8 suspects not asked (`ROBO_OCR_ASK_BELOW`):
      questions halved
- [x] 2026-10-08 winnow-ollama:e4b as the second judge (right alone 285/208/265 on three
      books against Ollaya's 174 each); Ollaya stripped; trust data re-asked for 14
      books, retrained, bench no change (1.00 → 1.02)
- [x] 2026-10-08 The substitution-pair prior (`trust.pair`, model version 3): silent
      errors at 0/.25/.5/1 questions a page [153, 87, 44, 23] → [110, 48, 25, 10], leave
      one book out; the trainer uses only data that exists and has every reading, never
      trains on validation books
- [x] 2026-10-08 The retrained arbiter against the fixed rule: after review 1.37 → 1.00,
      eight books better, none worse. Metro's veto before it was its spaced ellipses,
      fixed book-wide by `typography.py` (4.63 → 0.43)
- [x] 2026-10-08 The crop bug: a line's crop reached into its neighbour's box on up to
      97% of lines (Metro); `crop_span` stops at the neighbour. glm-ocr on Metro's
      changed crops CER 1.87% → 0.29%; every book re-read and rebuilt, Metro the clear
      gain, the rest neutral. ~~An ink-fitted crop~~ tried, not adopted: the readers
      read no better from it. ~~A reading far off its line's length counting as none~~
      dropped: readers stray on 1 line in 958 since
- [x] 2026-10-08 Faster readers screened: gemma4 8B (quote marks wrong), qwen3.6 MoE
      (wraps narration in quotes), gemma4:26b MoE (reads whole other lines on Metro):
      all out; the failed MoE models deleted. On Goede dochter and Metro only 1 line in
      ~1,000 has no current reading right: the errors left come from choosing, not from
      missing readings. Local and hosted Qwen interchangeable (same reading on 97.6%).
      ~~winnow:12b~~ dropped with Ollaya

## The reviewer

- [x] ~~Identical questions batched into one card~~ (dropped 2026-11-11 as a step of its
      own): 30 of 456 OCR cards on tuning, 7%; with the cards' redesign under "One path
      for every doubt"
- [x] ~~A reader of the finished text (the proofreader)~~ (parked 2026-11-11): probed
      twice, about one catch per 100 paragraphs against as many false questions; rerun
      `experiments/probe_text_reader.py` when a stronger text model comes (outlook.md,
      "Tried")
- [x] Washed-out cards (the user, 2026-11-10, reviewing Nervous System: "what a mess"):
      the read model reads only lines holding ink, and a reading repeating a sentence is
      never offered (decisions.md); whether `faint.pages` should tell mottled paper from
      faint print is left open: contrast can't (both under 17 grey levels)
- [x] ~~What the review shows of a contested place~~ (2026-11-07): already the whole
      line and one line either side (`review.CROP_CONTEXT_LINES`); only the judges see
      the suspect alone, which the panel's wide-crop judge tests
- [x] A build's comparison with the last shows italic changes (2026-11-03, `*word*`)
- [x] Questions with no readings (headings, missing lines) get Qwen's reading as an
      option, and a typed answer is checked against it (2026-10-17): Ex-minnaar 170 of
      199 questions; benches identical
- [x] Elision spaces (2026-10-16): our curling made glm's "nog 's" an opening ‘; now ’.
      Ex-minnaar glued elisions 9 → 3, apostrophe-only doubts 40 → 25; benches no change
- [x] ~~Small capitals read in lower case~~ (2026-10-16, dropped): cut at x-height in
      Ex-minnaar, and already read as capitals but for three "xm"; a reader hint for
      every book breaks more than it fixes
- [x] One OCR question per line (2026-10-16): whole-line options from every source,
      "Something else" from any option; benches better, questions fewer
- [x] Ex-minnaar's questions sampled again (2026-10-16): 234, sound; its review is the
      user's (restart the review server)
- [x] Misprints (2026-10-16): the review's `m` writes the book's errata; answers stay as
      printed, so the readers that read the misprint aren't marked wrong
- [x] The book teaches itself, first half (2026-10-16): a book's answers join its
      arbiter's substitution table (`trust.with_answers`); Ex-minnaar's review showed
      the signature (wc, stress accents, ’s)
- [x] The book teaches itself, second half (2026-10-16): one question per pattern,
      replayed on Ex-minnaar's answers (`probe_patterns.py`), saves 12–17 of ~140
      questions and settles one skipped line in eight to twelve wrong; not built
- [x] 2026-10-13 One review for a golden book: its places that differ from the e-book
      are questions in `roboscriptorium review`, answers stored as verdicts; `golden
      review` and the page's verdict mode are gone. Each side's words shown as written.
      Walked on Dolittle (89 questions, 15 of them places): choose, type (warned once),
      caption from our words, page-break crops
- [x] 2026-10-11 Stella built with today's build (every stage cached, under a minute,
      epubcheck clean): 7 questions, 3 answered before, 80 of 83 old answers applied
      (the other 3 lie inside a line another answer retyped whole)
- [x] 2026-10-11 Stella's 4 new questions reviewed (p. 19 "íéts", the other three as the
      text had them), rebuilt, epubcheck clean
- [x] 2026-10-11 English line-end hyphens nothing else decides settled by the judge, not
      a question: tuning **better** 0.36 → 0.34 (Dolittle 0.52 → 0.44, Metro 0.26 →
      0.22)
- [x] 2026-10-11 A quote left open at a paragraph's end asked whatever follows: tuning
      0.37 → 0.36, De tuin's unasked 0.24 → 0.16, no book worse
- [x] 2026-10-11 No paragraph starts on a line that continues a word broken with a
      hyphen: tuning **better** 0.32 → 0.31, validation **better** 0.74 → 0.70
- [x] 2026-10-11 A quote mark left open right after a word asked where it stands, not at
      the paragraph's end: tuning **better** 0.33 → 0.32, no more questions
- [x] 2026-10-11 A section opening on a word in capitals flagged as a lost drawn initial
      too: Dolittle 0.44 → 0.40, pooled no change
- [x] 2026-10-11 A section opening in lower case below a heading flagged as a lost drawn
      initial: Het ijzige land 0.25 → 0.20, pooled no change, no book worse
- [x] 2026-10-11 Speech closed on a letter at a paragraph's end asked as a quote
      question (De tuin kerns the stop under the mark): tuning **better**, De tuin 0.46
      → 0.41
- [x] 2026-10-09 Quote questions offer the OCR-checked line, Qwen's marks on it (quote
      marks only, no dashes) and the nested-quote combination: 3 of 4 now offer the
      right line, where none did
- [x] 2026-10-09 A lost line as a question (`lost-line`), scene breaks in the EPUB
      (`break_before`, unscored), budget diagnostics in shuffled order
- [x] 2026-10-08 Answers checked before they are saved (`review.doubtful`): a typed line
      matching no reading, or a straight quote in a curly-quoted book, is queried once;
      warnings logged. The review page tints the line and underlines the place, nothing
      drawn over the letters
- [x] 2026-10-08 A reader of the finished text, probed: gemma4 flags 56 on 200
      paragraphs, ~4 real; clef as the filter keeps both clear catches and drops 31 of
      37 urges. The proposer is the weak part (open step above)

## Starting from a PDF alone

- [x] ~~An image-only scan's ellipsis measured on the image for typography alone~~
      (dropped 2026-11-11): none of the books to make is image-only
- [x] ~~The contents page read for the book's structure and its chapters' names~~
      (dropped 2026-11-11): the chapters come from their run (`chapters.py`); no book
      has needed it
- [x] ~~`init`: Thief-Taker's "about the author" page (PDF 295) called a back cover~~
      (dropped 2026-11-11): one page, a page too many is mild
- [x] 2026-11-09 `init` carries the text on over a page under the book's running head
      (`pagekinds.run_on`): Nervous System's last end right (PDF 290), the 27 labelled
      books unchanged (23 first, 22 last); the neighbours' kinds told to the model were
      null
- [x] 2026-11-09 `init` starts the text proper after the front's title or copyright page
      (`pagekinds.after_title`): first ends right 23 → 26 of 27, Going into a Dark
      House's author blurb before its title page left out
- [x] `init`: the model walks inward from each edge until three pages in a row go into
      the EPUB (2026-11-02): Pieter Daens now ends at PDF 787; on the 27 labelled books
      starts right 22 → 23, ends 21 → 21 (22 against Het laatste bevel's corrected
      label, where the old setup's 20), no new cut. Left: Thief-Taker's "about the
      author" page (PDF 295) called a back cover, an old miss
- [x] ~~The dash style of an image-only scan, measured on the image~~: done 2026-10-24
      (the first reading's words, the stroke cropped on its line's height; Goede dochter
      without its layer 23 of 26 dashes against 5, Vanille's typography 0.56 → 0.00).
      The ellipsis the same way was vetoed by validation (the readers told ". . ." read
      Vanille worse; decisions.md): measuring it for typography alone, not the readers'
      prompt, is left
- [x] ~~An image-only scan through the whole pipeline~~: done 2026-10-23
      (`work/goede-dochter--nolayer`, decisions.md): 0.84 wrong words a page against the
      layered 0.33, the gap tesseract's reading; italics from the first reading's word
      boxes since (323 of 364). Dashes wait on the item above
- [x] 2026-10-23 `build` and `review` run `init` first when given a PDF or a folder
      without a book.toml (`cli._book_dir`)
- [x] **`init`, first version** (2026-10-21; `bookinit.py`, `pagekinds.py`): language,
      page kinds (signals in the middle, clef-flash on the 8 pages at either edge), the
      two ends of the text proper, the cover and the title page's lines, written as
      `book.toml` (or a draft beside it), `init/report.md` and a contact sheet
      `init/ends.png`, every page named by both numbers. Ends right on 22 and 21 of 27
      books; a rewording of the question changed nothing. Title, author and translator
      are drafted from the title and copyright pages (2026-10-22: title 26, author 25
      right of 27). `build` and `review` run it when book.toml is missing, given a PDF
      or a folder holding one (2026-10-23). Still open below: the confirmation on the
      review page.

## Architecture probes

- [x] ~~Per-book settings: a pre-pass that picks each book's reader resolution~~ (the
      user, 2026-10-22; NOT TAKEN 2026-11-11, `probe_setting_agreement.py`, no models):
      the resolution at which the read model agrees most with glm-ocr does follow its
      score (r = +0.72 over 32 book-settings), but there is nothing to win: every book
      at 450 dpi reads 758 of 800 lines right, each at the setting agreeing most 759,
      each at its best 765, a setting drawn at random 748–760. Contrast, crop and prompt
      variants were not read: as witnesses they can add a handful (the quiet set)
- [x] ~~Surya as a second spotter, heading tags from Granite-Docling, per-book image
      tuning for pale scans, Het Kindeken Jezus as a golden book~~ (dropped 2026-11-11):
      each waited on a result that didn't come (image tuning null on normal pages)
- [x] ~~Glyph-level checks (pairwise classifiers for confusable letters, glyph
      clusters)~~ (dropped 2026-11-11): they waited on the accent-shape probes, which
      were too weak (outlook.md, "Tried")
- [x] ~~Two-line crops at each line break as a decision for clef~~ (dropped 2026-11-11):
      of 236 unasked errors on tuning 2 span a join; the compound hyphens sit at line
      ends, where the scan can't show whose the hyphen is
- [x] ~~New OCR models as witnesses, as a step~~ (dropped 2026-11-11): every reader is
      wrong together on 23 lines of the tuning slices, so a line witness can add a
      handful; a new model goes through the gate in HANDOVER.md ("When a new vision
      model appears") and AGENTS.md's two questions. Not screened: dots.mocr, Chandra
      OCR 2, HunyuanOCR, PaddleOCR-VL-1.6
- [x] ~~LightOnOCR-3's grounding mode as an input to line roles~~ (dropped 2026-11-11):
      Qwen's page roles, the stronger version of the idea, cost more words than they
      saved, and its weights are deleted
- [x] ~~Whole-page reading with the page before as context~~ (dropped 2026-11-11): 14 of
      the 78 paragraph-break errors on tuning sit on a page's first line, and a
      whole-page reading starts from more errors than the pipeline
- [x] ~~The text layer as a second reader only~~: closed 2026-10-24 on the evidence
      above: a whole-page reading starts from more errors than the pipeline (Qwen 76
      wrong words over 19 pages against 27, glm-ocr 103) while the layer reads 0.21% CER
      on modern Dutch, so the page would start from the worse reading. Reopen when a
      page reader beats the layer
- [x] ~~Page kinds for `init` by Qwen from the page image~~: done 2026-10-24, no better
      than clef-flash (ends right 20 and 23 of 27 against 22 and 21, 3 ends cut against
      2); not taken
- [x] ~~Token probabilities of a reading as a per-line confidence~~: done 2026-10-24
      (`probe_image_gain.py`): AUC 0.78 over all lines, 0.57 where glm-ocr agrees, so it
      marks only what the readers' disagreement already flags; not taken
- [x] Paragraph breaks by a model (2026-10-23, NOT TAKEN; `probe_page_breaks.py`): on 47
      tuning pages with a break error it fixes 53 of 78 wrong starts, but it sets 7
      wrong on 47 clean pages (0.15 a page, against the reflow's 0.06 over all pages).
      The page image plus the pipeline's lines, "which lines start a paragraph?",
      against `reflow.indented`. A learned text table (quote after quote at the margin:
      87 of 88 starts) did nothing, the tuning books having no unindented book
      (2026-10-16, `work/probes/parastarts.patch`); Vuurspel's unindented layout is rare
      (the user, 2026-10-17), so no pair is sought for it; the vision judge on line
      crops (±1 and ±4 lines) gains nothing over the lower-case check (2026-10-17): a
      page-level reading is what's left
- [x] ~~The 450 dpi qwen reading as an extra arbiter reader~~ (dropped 2026-10-23):
      right alone on 0 of 57 quiet lines where it differs, and the 2026-10-09 bench of
      the same second look found no gain.
- [x] ~~A line no page reader has words for as a feature of the line-role trees~~
      (2026-10-16, dropped): the trees get the unread lines right but for 5 of 657; the
      line-role mistakes left (49 of 25,555) are on lines both readers read
- [x] Read the pages and train with them (2026-10-15, a night): `bench tuning` no change
      0.32 → 0.32, validation 0.50 → 0.43 after review but worse before it on two books;
      the page readers stay off as line readers
- [x] ~~Both page readers' spelling of a line-end compound as evidence for a learned
      hyphen decision~~ (2026-10-15, dropped): with the judge's answers, as the build
      runs, the build is wrong on 19 of 3,184 line-end hyphens; the readers agreeing fix
      9 and break about 6, under the bench's noise
- [x] Two page readers agreeing against the pipeline (2026-10-14): outside paragraph
      breaks, right 152 times to 65 (70%), about 0.7 places a page; breaks not
      trustworthy
- [x] The two readers' agreement on the errors left after review (2026-10-14): 60 errors
      no question catches (+21 unmatched), 71 asked already, 68 false: about a quarter
      of what's left after review, for ~0.3 questions a page
- [x] Build it (the user chose this way, 2026-10-14): `pagereader.py`, two more readers
      for the OCR check behind `ROBO_PAGE_READERS`, the arbiter keeping which readings
      it was trained on
- [x] Whole-page reading by the bigger build (2026-10-14): `qwen3.8:27b-mxfp8` 65 wrong
      words over 19 pages against the nvfp4's 76, mostly one page; 60% slower; not taken
- [x] ~~The whole-page reading as one more reader~~: answered 2026-10-14/15
      (decisions.md): the page readers point at about 60 errors no question asks, mostly
      at line joins a line reading can't carry; added as readers for the arbiter, tuning
      no change (outlook.md, "Tried")
- [x] Whole-page reading (`probe_page_reader.py`, 2026-10-13): Qwen 76 wrong words and
      32 breaks over 19 pages against the pipeline's 27 and 7 (letters doubled at page
      resolution, dialogue paragraphs merged); glm-ocr near-exact on plain text pages at
      a third of the size, but invents text on near-empty and picture pages
- [x] glm-ocr whole pages at full resolution (2026-10-13): 103 wrong words over 18 text
      pages against the pipeline's 27, but right on 5 of the pipeline's 9 error places,
      nearly all line joins; it invents text on near-empty pages
- [x] glm-ocr's page reading as a reader (2026-10-13): right on 226 of 473 pipeline
      error places, but wrong on 910 where the pipeline is right: alone, four false
      questions a catch

## Ideas from the deep-research reports (2026-10-23)

- [x] ~~The arbiter's own silent errors, a feature for them~~ (NOT TAKEN 2026-10-26,
      `probe_accent_mark*.py`, `probe_ask_threshold.py`): of the 97 bench places where a
      version had it right, 39 are accents, specks taken for accents and emphasis
      dropped; the mark's shape adds nothing to the trees, and the rest are suspects the
      arbiter was 0.8 sure of; three questions a page caught 8 on De vergelding, tuning
      no change
- [x] ~~A per-book character recogniser with no language model, as a witness that fails
      differently~~ (Fable's first idea, Argon's fourth; DeepSeek advised against; NOT
      TAKEN 2026-10-24, `kraken_lines.py`, `kraken_eval.py`): Kraken 7 trained from
      scratch on 22k golden line crops (the reader set's other half of books held out),
      99.73% characters right on its validation lines after 8 epochs. On its 400 frozen
      lines it reads 169 of 240 hard lines right (qwen 216) and 142 of 160 control (qwen
      160); of the 6 lines where the layer, qwen and glm-ocr agree on the same wrong
      reading it reads 1 right (a stray full stop left out), and it shares the others'
      errors ("some one", a colon for a full stop); right alone on 3, breaking 74 qwen
      reads right. The other fold not trained: half the set settles it. The per-book
      fine-tune and the ensemble were not tried
- [x] ~~Image-gain as a silent-error signal~~ (Fable; Argon's runner-up margin; NOT
      TAKEN 2026-10-24, `probe_image_gain.py`): on the 800 frozen lines, qwen wrong on
      45, the weakest token's log-probability marks them with AUC 0.78 and the runner-up
      margin 0.77, image-gain 0.47 (no better than chance). Where glm-ocr reads as qwen
      does (676 lines, qwen wrong on 12, the errors no disagreement flags) the three are
      0.57, 0.57 and 0.44: qwen is as sure of its silent errors as of its right lines
- [x] ~~A threshold per kind of question~~ (Argon's value of information; DeepSeek 8 as
      ranking; NOT TAKEN 2026-10-24, `probe_kind_threshold.py`): on the trust data, with
      each tuning book scored by the arbiter saved without it, thresholds chosen on the
      other books (accent 0.9, space 0.95, quote 0.7, letters 0.85, in every fold) left
      65 → 58 silent errors for 330 → 318 questions; the warm bench didn't carry it
      (after review 0.290 → 0.290, questions 0.732 → 0.721 a page, unasked 0.174 →
      0.176: 9 unasked fixed, 10 made). The reviewer-mistake test (does the arbiter's
      margin predict a wrong answer) was not run: 8 mistakes on Stella are too few to
      choose by
- [x] Is the scan's text mask lossy? (Fable's review; 2026-10-23, no): Internet
      Archive's Scribe scans (Stella, Goede dochter, Het schaduwhuis) code their mask as
      JBIG2 generic regions, an exact bitmap with no symbol dictionary, so no letter can
      be substituted; Dolittle's older scan uses symbol dictionaries. At a known
      emphatic accent ("vríénden", Het schaduwhuis PDF page 56) the accent shows plainly
      in both the mask and the composited render the readers get: the loss is the
      readers', not the scan's, and the mask shows an accent no better than the render
- [x] ~~Crops padded to the vision encoder's grid instead of resized~~ (Argon; NOT TAKEN
      2026-10-23, `probe_grid_pad.py`): Qwen3.8 takes 16-px patches merged 2×2, so its
      processor scales the frozen crops' heights by 0.8–1.2 to a multiple of 32. Padded
      with paper colour instead, qwen read 427 of 480 hard lines right against 436 and
      311 of 320 control lines against 319 (9 fixed, 26 broken; the 68 most squashed
      lines 64 → 65); re-reading the crops as they are changed none, so it is the
      padding. It invents marks: "nògal", "dië", "én", "Ârtyôm"
- [x] ~~Small capitals from the descender band~~ (Argon; dropped on reading the errors,
      2026-10-23): of the 27 unasked case errors on tuning, 15 are Au pair's reference
      writing small capitals in lower case (verdicts, golden-notes), and the other 12
      are short acronyms in small capitals ("ss", "wa", "voc", "usb", "cv", "v-hals",
      "u-boten") with no letter that descends: the test reaches none. What is left needs
      a shape classifier (the glyph-level checks below), and a small-capital S is nearly
      a lower-case s
- [x] ~~Book-wide consistency for diaereses and letters outside ASCII only~~ (Argon's
      narrowing; 2026-10-23, `probe_book_consistency.py --marks`): one flag over every
      tuning slice, and a right one ("geinteresseerd" for "geïnteresseerd"), but 1 of
      184 unasked one-word errors: most such words occur once in a book, so the book
      can't vouch for them
- [x] ~~Real-word confusion pairs mined from the golden pages~~ (Fable; NOT TAKEN
      2026-10-23, `probe_book_consistency.py --pairs`): pairs from the other tuning
      books' errors flag 216 word types whose partner occurs in the book, mostly common
      words with an emphatic twin ("mijn"/"míjn", "ik"/"ík"), thousands of occurrences,
      for 2 unasked catches
- [x] ~~Book-wide consistency as a suspect~~ (DeepSeek 5; NOT TAKEN 2026-10-23,
      `probe_book_consistency.py`): a word spelled one way once and a close variant
      three times or more flags 4,802 words over the tuning slices (3 a page), 34 of
      them errors; it catches 17 of 184 unasked one-word errors, about 6 of them real,
      the rest emphasis accents the print has and the reference drops, which it would
      remove
- [x] ~~PaddleOCR-VL-1.5 as one more reader~~ (DeepSeek 2): screened 2026-10-20, unfit
- [x] ~~Gated language-model scoring of words with a visual twin~~ (Argon's PLLR with
      RobBERT; Fable and DeepSeek against): parked behind the glyph and image-gain
      probes, which ask the scan rather than the language
- [x] ~~Constrained LLM post-correction~~ (all three call it low value at this error
      rate)
- [x] ~~The JBIG2 text mask as the readers' image~~ (DeepSeek 6): the accent is as plain
      in the composited render as in the mask (the lossiness check above); the mask
      stays a geometry channel for the descender band and specks
- [x] ~~Character-level ROVER with a diacritic-restoration vote~~ (DeepSeek 1, not taken
      on reading): suspects are already made at character level where any reader
      differs; the silent errors are where every reader gives the same characters, which
      a vote can't open, and a dictionary-driven accent restoration would invent Dutch
      emphasis accents, which are optional
- [x] ~~LLM post-correction under a learned edit budget~~ (DeepSeek 4, parked): only on
      the places the consistency test flags, if that probe earns it

## Measurement

- [x] ~~Qwen faster on the same output; MiniCPM-V 4.6 as a faster reader~~ (dropped
      2026-11-11): a line is 52% prefill and 23% decode, batching was ruled out, and
      speed is not the bottleneck (outlook.md, Inference speed)
- [x] ~~JP2s as the image source for public-domain books~~ (dropped 2026-11-11): both
      readers err about a fifth less on Crime's 50 lines (2026-10-11), but a lent item
      offers no downloads, so no book to make can use them
- [x] ~~Dolittle's captions scored or left out of the score~~ (dropped 2026-11-11): 19
      words on tuning, all asked
- [x] ~~Pages below the quality the build supports~~ (2026-11-08, `scanpages.poor`,
      branch `poor-pages`, merged after the panel's benches, which run against today's
      scoring): 1.5 or more OCR-check suspects a line on a page of ten lines or more; De
      vergelding's nine blurred pages (1.54–6.0), the next page anywhere 1.24
      (Verminkt's Polish). Named by `build`, out of the bench's score
- [x] 2026-11-06 Qwen3.8-Flash-Next UD-Q2_K_XL (Unsloth Studio, part on SSD) as a reader
      or witness: rejected, on the quiet set's 23 lines every reader gets wrong 0 of 5
      plain, 4 of 23 with the crop doubled (two real), 2 of 12 thinking, contradicts 3
      of 170 right lines plain, ~15 s a line (models.md)
- [x] Italic errors in the bench's verdict (2026-11-03, `bench.italic_errors`): the
      first try lost Het geluid van bananen's italic pages (10,000 words) and the
      verdict said "no change"
- [x] Heading errors in the bench's verdict (the user, 2026-11-02): more is worse, fewer
      better, a book gaining any vetoes (`bench.heading_errors`)
- [x] The bench counts headings set letter for letter beside those found, and prints the
      totals over all books when they move (2026-11-01, `bench.heading_totals`)
- [x] 2026-11-12 The bench's italic count by a word's place, whatever its letters, and
      batch five's slices, on main; fresh baselines made (HANDOVER.md has their files)
- [x] 2026-11-12 Batch five's retraining weighed: the arbiter of twenty seeds trained on
      the four rebuilt books is better on tuning (unasked 576 → 564, 26 questions
      fewer) and no change on validation; the first retraining on grown slices ahead
- [x] 2026-11-12 Batch five of the slice growth: Vals alarm, The Thief-Taker's
      Apprentice, Metro 2033, De tuin van de avondnevel, Au pair and De vergelding scored
      whole (915 pages, 13 h cold): no change, tuning now 6,180 pages; the room to grow
      that was listed is used up
- [x] 2026-10-25 to 2026-11-07 The tuning slices grown in four batches while the machine
      was idle (the user, 2026-10-25), from ~1,700 to ~5,200 pages: the bench's interval
      narrows with the square root of the pages (about ±0.010 at 2,271 pages); more
      pages did not make a better arbiter (decisions.md, 2026-10-25)
- [x] ~~ABBYY's letter confidence as an arbiter feature~~: dropped 2026-10-24 without a
      probe: only the public-domain items (Crime, Dolittle) have their `_abbyy.gz`; a
      lending-library scan (Stella, the user's books, every other pair) keeps it
      private, so the target books could never have the feature
- [x] Error categories tracked per run (2026-10-17): 16 causes read from an error's two
      sides alone (`errorlog.cause`), chosen from stage (a)'s 618 saved errors across 23
      books; each run's record keeps them by book, `bench` and `bench-diff` print each
      before → after with its interval. "Reference fault" isn't one: a verdict settles
      it
- [x] Grow the seven short tuning slices (2026-10-17): read 10:28–17:55; trust data,
      role trees and arbiter retrained on them; validation 0.41 → 0.37 after review,
      tuning 0.30 → 0.30
- [x] 2026-10-17 and 18 The weekend's order after the slice growth: `bench quick` as a
      tier, the merges, the role trees and the arbiter retrained on the long slices, the
      context-judge probe, the first-look reads
- [x] 2026-10-13 What a perfect reader could still gain (`probe_reader_ceiling.py`): 53
      of 186 wrong words left after review (29%) are undoubted reading errors, under the
      half agreed as the bar; fine-tuning a reader dropped for now
- [x] 2026-10-13 `bench validation` finished with the ellipsis measured on the scan:
      BETTER 1.10 → 0.59 after review (The Stranger's Child 4.59 → 0.53); tuning BETTER
      0.52 → 0.50
- [x] ~~2026-10-11 `_scandata.xml` page types as labels for page classification~~:
      dropped, they mark the cover and title page (Dolittle also contents and copyright)
      and call every other page Normal, colophon, motto and ads included
- [x] 2026-10-11 Scene breaks scored: derive reads them (thought breaks, ornaments,
      break, opening and closing classes, each checked on the scan) in 10 references;
      the build finds 255 of 295 and sets 20 more where they are recorded
- [x] 2026-10-11 A page opening flush left after a finished paragraph is a scene break
      where paragraphs indent: found 255 → 272 of 295, 2 more set; words unchanged
- [x] 2026-10-10 Longer tuning slices, each ending on a chapter (Goede dochter 9–162,
      Reis whole, De cipier 9–174, Metro 7–162, De tuin 11–122): 446 new pages in 7.5 h,
      arbiter and trees retrained; tuning 0.53 → 0.53, validation 0.77 → 0.76, no
      change. The pooled slip rate lowered "after review" a little everywhere (a
      measure, not a build change); the quote questions' new readings changed nothing
      the bench counts
- [x] 2026-10-10 The bench books read again by the local Qwen (30,572 lines, ~9 h),
      trust data and arbiter rebuilt: tuning 0.56 → 0.56, validation 0.77 → 0.79, no
      change; the bench now measures the build Stella gets
- [x] 2026-10-09 The slip rate measured again on today's questions: 30 of 32 right
      (picks 17/18, typed 6/7, roles 7/7); the bench uses the two reviews pooled, 10 of
      100 (the user's choice), applied after the chains as the new baseline
- [x] 2026-10-09 The bench counts paragraph breaks set wrong, catches an error only at
      the question's place, counts a typed page as a question per line: tuning 0.48 →
      0.56 on the same build, honest; prints headings and reports heading and
      paragraph-F1 changes beside its test (`bench.structure`); records the hosted share
      of each book's readings
- [x] 2026-10-09 The arbiter's sureness calibrated (isotonic), so 0.8 means 80% right
      whatever the retrain: no change by the bench, kept for the threshold's meaning
- [x] 2026-10-09 An error over a page break counts on the page holding most of it
      (Afscheid 5.03 → 0.24 after review)
- [x] 2026-10-09 clef's cached answers stand for fresh ones: judge set v1 re-asked, 2
      flips of 518, both at confidence ≤ 0.1
- [x] 2026-10-09 Retirement signals per book in the bench (`golden/signals.py`: layer
      CER, unplaced body lines, a suspect named)
- [x] 2026-10-08 Judge set v1 frozen (518 settled suspects, 25 wrong and 25 right a
      book); reader set v1 (550 lines, 30 the layer reads wrong and 20 right a book);
      `experiments/tryout.py` screens a candidate for a role against the incumbent
- [x] 2026-10-07 `roboscriptorium bench`: pinned slices, one JSON per run, paired page
      by page; one primary test with books weighing the same and a per-book veto; the
      reviewer's slips counted; leave-one-out trust models for tuning books; a missing
      or stale trust model stops the build; `eval` records decider, settings and model
      digests; long runs timed into run-times.md; design.md and decisions.md started

## Golden books

- [x] 2026-11-11 The gaps to hunt for (golden-notes.md) name a short-story collection,
      section headings without numbers, text wrapped around pictures and old-style
      chapter numbers over sunk openings
- [x] 2026-10-24 and 2026-11-06 Set reviews: no pair retired; Dolittle past the
      layer-CER line since scored whole, its errors the pipeline's, kept
- [x] 2026-10-23 The sets trimmed (the user, 2026-10-18: "trim the fat"): Afscheid's
      paragraph breaks unscored (`breaks_unlike_print`); The Nature of a Crime out of
      tuning and quick but kept in the arbiter's training (without it: unasked fixed 7,
      made 16); Dolittle's quick slice kept; Na die nacht held back, not retired;
      Verminkt sliced to 7–100
- [x] 2026-10-20 De vergelding's, Glazuur's and Vanille en andere smaken's first looks:
      the first two tuning, Vanille validation
- [x] 2026-10-19 Au pair's first look (0.37 after review): tuning, with no trust data
      yet
- [x] 2026-10-18 The first looks of Het geluid van bananen, Het schaduwhuis, Steve Jobs,
      De geruchten and Verminkt scored once (decisions.md): Bananen and Het schaduwhuis
      to tuning, De geruchten and Verminkt to validation; Steve Jobs scores no words
      (the user), its photo insert stays line-role training
- [x] 2026-10-17 No fixed test set: a first look for every new pair (the user).
      `bench.SETS["first-look"]` replaces "test", its guard (`--first-look`) refuses
      every eval, review, probe and trust data on such a book; Na die nacht held back in
      `bench.RESERVE` (a sibling of two tuning books); now a standing rule in AGENTS.md
- [x] 2026-10-11 Validation from 5 books to 7 (Monterosso and De stilte van de hel,
      cold): **0.76** wrong words a page after review by the rules
- [x] 2026-10-10 Sets changed (the user's go): De kerk van de dode meisjes and Vuurspel
      validate; De tuin, Het heft in eigen hand, Doodskleed and Het ijzige land tune.
      Derive learns `capital_classes` and a spaced `--` as the print's dash. Rejected:
      Cavendon Hall, Alsof het niets is, Het spel van de engel (EPUBs made through Word
      or OCR); De stilte van de hel kept unused as Vuurspel's sibling
- [x] 2026-10-10 ~~The five tuning books whole~~ dropped (the user): more pages of books
      already trained on add the same errors again
- [x] 2026-10-09 Internet Archive's own files fetched by manifest (`[scans.ia]`): Crime
      and Dolittle. Five public-domain Dutch Scribe items pair with Gutenberg (Het
      Kindeken Jezus, David Malan, …) but all in pre-1934 spelling: none taken
- [x] 2026-10-08 Grand Hotel Europa and Lady into Fox retired to reserve (another
      printing; a reference unlike its print in typography); De eerlijke vinder and
      You're Never Weird into validation; Metro, De cipier, Artemis, 11/22/63, Afscheid
      and Reis into tuning; Het geluid van bananen frozen as the test set
- [x] 2026-10-08 `experiments/probe_candidate.py`: a no-model check of a scan and EPUB
      pair; known deviations tracked in the manifest, the fold or a verdict, nowhere
      else
- [x] 2026-10-08 Hosted clef as the judge, measured against criteria fixed first: fails
      all three (PrimeIntellect hardly reads the image; Cloudflare 96.2% the same pick,
      fewer right), so clef stays local

## Reviews of the build

- [x] ~~A lighter feedback loop~~: checked 2026-10-24 (decisions.md): quick ranks a
      change that acts everywhere in the same direction with less power, and misses one
      acting on front matter or pictures (outside its slices); it stays the short test,
      tuning the verdict
- [x] ~~Remove the `baseline` and `qwen2` worktrees~~ (gone by 2026-10-24)
- [x] `golden derive` keeps text before a book's first heading (2026-10-17,
      `leading_text`): Normal People's reference and scan start on p. 9, its slice now
      chapters 23–31
- [x] Book-wide statistics on the whole body (2026-10-16): tried and reverted; a raw
      repeat count over 564 pages took a dialogue tag for a running head
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
- [x] Prune `experiments/` (2026-10-16/17): 53 scripts named only in the logs deleted
      (the user: results recorded, git keeps them), `probe_orientation.py` mended;
      AGENTS.md cut to rules and the map (manifest keys to golden-notes.md, model setup
      to models.md, the review page to how-it-works.md); decisions.md a heading a day
- [x] A sampled review of Ex-minnaar (2026-10-16): false quote questions on Flemish ’m
      fixed (308 → 261 questions); its blanked place names ("het __plein") need one
      setting for the book (the user)
- [x] The epigraph stage took noise for a motto (2026-10-16): a word of four letters is
      now required; benches no change
- [x] One cold A/A rerun of `bench tuning` (2026-10-15): 0.32 → 0.33 after review
      [+0.00, +0.01], no book apart; rebuilding the caches moves the score 0.01 at most
- [x] Line roles learned (2026-10-13): the trees are on by default after warm benches no
      worse on both sets (decisions.md); running-text and numeral-slot retired
      (2026-10-16, `probe_retire_rules.py`, bench no change); the other rules still earn
      their place. Next: a book with text wrapped around pictures for Dolittle's case
- [x] ~~FKA USA's fixes from its first bench (note marks as LaTeX, a dropped epigraph, a
      missing part heading)~~ (2026-10-13, dropped): the pair was retired as a suspect
      (30% of its body lines unplaced) and its files deleted
- [x] 2026-10-13 Third review of the codebase, four reviewers: eight bugs fixed with
      tests (a typed verdict could write its context into the reference twice, a word
      left open before "en" lost its hyphen, a typed line took the identity of the one
      below it, notes scored on the wrong version of the pages, answers saved at once
      could cut each other, no cache knew its source PDF, the arbiter read its judges by
      the order of their votes, the docs put copyrighted books' verdicts in git); the
      rest planned above
- [x] 2026-10-13 Three suspect pairs retired (the user): 11/22/63, FKA USA, Koning
      Wilders; the arbiter retrained without 11/22/63
- [x] 2026-10-13 The bench prices the reviewer's time (20 questions = one wrong word,
      the user) and its verdict is worse when any slip rate is, a veto on breaks too:
      this morning's tuning run stays better, 0.57 → 0.55
- [x] 2026-10-13 The bench counts typography where the words agree, a measure of its
      own: 0.0–2.0 words a page, Dolittle 8.7, nearly all straight quotes kept from the
      layer
- [x] 2026-10-13 The trust data and the arbiter's saving into
      `src/roboscriptorium/trustdata.py`, tested; its book list kept in step with
      `bench.NO_TRUST_DATA` by a test; retrained from the cached data with the old code
      and the new: the same models
- [x] 2026-10-13 The measurement code out of `cli.py`: `golden.scoring` (a golden slice
      built and scored) and `bench.run`; 25 experiments and the tests use them, not the
      CLI's private helpers
- [x] 2026-10-13 Straight quotes and apostrophes left from the layer curled
      (`quotes.curl`): typography 0.00–0.09 a page on every tuning book, the verdict
      unchanged
- [x] Trust data for the 20 books on qwen3.8:27b-nvfp4, then the arbiter and `bench
      tuning` (2026-10-12): 0.31 after review over 17 tuning books, Monterosso read
      whole
- [x] 2026-10-09 Fable's second review: what the bench couldn't see and leaks in the OCR
      check, each change benched alone; the ledger of probe against verdict is in
      outlook.md
- [x] 2026-10-09 Strict review of the codebase: six reviewers, every finding checked,
      fixes with tests in seven commits; trust data rebuilt, tuning 1.00 → 0.96,
      validation no change. Qwen's read prompt (five variants) and crop (dpi, upscale,
      contrast, sharpen, margin) can't be improved: each fixes as many lines as it
      breaks
