# Outlook: where the needle can still move

For an agent choosing what to work on. It says how close the build is to its goal,
which areas still have room, and which have been tried without effect, so effort goes
where it can move results. Numbers are from the bench of 2026-10-09 (commit `dc3eb53`);
rerun `roboscriptorium bench tuning|validation` before relying on them, and update
this file when they move.

## How close we are

The bench was made stricter on 2026-10-09 (paragraph breaks counted, a question catching
only the error at its place, a typed page counting a question per line), so these
figures aren't comparable with earlier ones: on the same build tuning went 0.48 → 0.56.
With the rules' line roles (the default), commit `dc3eb53`:

| Kind of book | Example | Wrong words a page after review | Questions a page | Breaks set wrong a page |
| --- | --- | --- | --- | --- |
| Clean scan, modern Dutch prose (Stella's kind) | Goede dochter, Reis, De cipier | 0.23–0.35 | 0.4–0.6 | 0.01–0.22 |
| Clean scan, modern English prose | Metro, Thief-Taker, Crime | 0.37–0.43 | 0.4–0.9 | 0.01–0.36 |
| Born-digital PDF | Villa Toscane | 0.12 | 0.13 | 0.01 |
| Old typography, plates | Dolittle | 0.77 | 1.1 | 0.42 |
| Busy layout, pictures | 11/22/63, You're Never Weird | 1.00–1.04 | 1.4–3.1 | 0.13–0.54 |
| Washed-out scan | Afscheid | 0.63 (its typed pages now count) | 3.5 | 1.73 (its EPUB's paragraphing) |

Bench totals (2026-10-10: Qwen read locally, the longer slices, the pooled slip rate):
tuning 0.53, validation 0.76 wrong words a page after review; paragraph breaks set wrong
0.34 and 0.20 a page. With the line-role trees on (`ROBO_SORTER=1`): 0.52 and 0.68, tuning
better on breaks, but Thief-Taker 0.47 → 0.97. The sets change tonight (Kerk and Vuurspel
validate, De tuin and three new books tune): the next bench is a new baseline.

Until 2026-10-10 every bench figure but Goede dochter's and De tuin's measured DeepInfra's hosted Qwen,
not the local build Stella gets; read again locally on 2026-10-10, no change by the bench.

**Assessment (2026-10-09):**
- Stella coming out as a clean, valid EPUB is likely (~80–90%) and near: its kind of
  book is at one wrong word in three to five pages, and its paragraphs nearly all right.
- Standard Ebooks' fidelity on any scan, in hours, with few questions, is about even
  odds with today's models. The build plugs in better models quickly
  (`experiments/tryout.py`), so it improves as they do.

## Where there is room, by expected gain

1. **Structure.** The bench now counts paragraph breaks per page and prints headings.
   - Line roles: the trees (`sorter.py`) halve role errors and improve three books
     clearly; Crime loses a last line. Bench them on the local readings, then switch.
   - Breaks left: Afscheid's are its EPUB's; Artemis 0.74 (its letters, set without
     spacing), Dolittle 0.42, Thief-Taker 0.36, a section break at a page turn.
   - Headings still lost: De eerlijke vinder 0/4 (part numerals), You're Never Weird 4/16.
     Thief-Taker 9/22 and Metro 5/10 are a scoring convention (label and title as two).
   - Scene breaks are set but not scored: derive drops the references' blank lines.
   - Not handled: footnotes in the body, verse, tables, block quotes.
2. **The errors no question asks about** ("unasked", by kind, in each bench record):
   - Vals alarm: 33 unasked letter errors, its lost full stops (checklist 4, the book teaches itself): only its
     own answers can teach the arbiter.
   - De eerlijke vinder: unasked 1.02 a page, the most of any ordinary book (words 26,
     letters 21, extra words 18). Unexamined.
   - 11/22/63 and You're Never Weird: ~20 missing words each, likely text in pictures
     or lines the layer lacks.
   - Dolittle: 26 wrong words unasked, old typography.
3. **The reviewer's time.** 1.2–2.2 questions a page is 250–400 for a 200-page book, and
   the reviewer is wrong on about 1 answer in 8 (8 of 68 on Stella). Fewer, better
   questions improve "after review" as much as better readings do. Untried: grouping
   the same question across pages (one answer for every "|" read as "I"), and
   ranking questions by expected errors removed per second of the reviewer's time.
4. **New models.** The judges and arbiter are near what these models can do (below).
   A better vision reader or judge is the likeliest source of a step change. Screen
   each new model on the frozen sets (`tryout.py run reader|judge`) for every role
   (AGENTS.md: every new model gets two questions).
5. **The hard tail, by hand or rescan.** Washed-out pages (Afscheid's four in its slice)
   are flagged whole (`faint.py`); no model reads them, and the readers invent fluent
   text on them. A human types them, or the book is rescanned.
6. **Better pixels.** Every reader and judge sees crops of a heavily compressed PDF
   (Crime's is 3 MB for 138 pages). Internet Archive's page images are about 13× the
   data and its ABBYY reading gives a confidence per letter (checklist 7). Only the
   public-domain books have them: Crime and Dolittle so far.

## What the second review's ideas did (2026-10-09)

Each benched on its own; the probe that predicted it beside the bench's verdict, the
start of a ledger of when a probe is enough.

| Change | Probe predicted | Bench | Kept |
| --- | --- | --- | --- |
| Count breaks, catch at the place, typed pages per line | (measurement) | tuning 0.48 → 0.56: honest | yes |
| Ellipsis style folded, trust relabelled | Reis's questions down | set unchanged; Reis 0.32 → 0.22 and questions a third, Goede dochter 0.20 → 0.33 in its noise | yes |
| Unseen version never applied | Thief-Taker p. 46 fixed | Thief-Taker 0.82 → 0.55 | yes |
| Paragraph starts (page margin, white space) | breaks 428 → 313 | breaks −28% / −34%, **better** | yes |
| Arbiter calibrated | raw already near calibrated | no change | yes, for the threshold's meaning |
| Lost lines asked | 2 of 13 questions catch | −0.01 / −0.03, no change | yes |
| Scene breaks | — | unscored | yes |
| Line roles by trees | role errors 406 → 152 | −0.04 / −0.07, no change; on the longer slices tuning better on breaks, four books better, Thief-Taker 0.47 → 0.97 | off, pending Thief-Taker |

## Tried, and why it didn't help

Don't repeat these without a new reason (details in docs/decisions.md):

- **Qwen's read prompt.** Five variants (copy exactly, neighbouring lines, both, the
  layer's reading): each fixed as many lines as it broke. Its misreads are visual.
- **Qwen's crop.** 450 and 600 dpi, 2× upscale, contrast, sharpening, a margin: no
  better; sharpening worse.
- **Qwen's second look as a trust feature.** A strong signal (where it changes, Qwen is
  wrong 95%), but the arbiter gains nothing: the judges already catch the same cases.
  Branch `qwen-second-look`.
- **imajev-4b as a third judge**, as the vision judge, or for page types: no change.
- **Removing Qwen** (to save its 70–75% of a cold run): clearly worse.
- **Faster readers** (gemma4, MoE models): worse on quote marks.

## The goal

The user's words (2026-10-10): an EPUB **as if the publisher had put it out**, faithful
to the text and the typesetting, with minimal errors. Perfection is unattainable;
progress toward it is the aim, so there is no finish line to agree, only the bench
moving the right way. A build is made and then measured, never held back for a bar.
The measures that say how close a book is:

- wrong words a page after review (the bench; a target book's spot-check);
- questions a page: the user answers until tired, so fewer and better questions are
  worth as much as fewer errors;
- headings and paragraphs (heading recall, paragraph F1);
- epubcheck clean;
- the test set (Het geluid van bananen) scored once, at the end, within reach of the
  validation books.
