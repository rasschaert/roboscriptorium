# Outlook: where the needle can still move

For an agent choosing what to work on. It says how close the build is to its goal,
which areas still have room, and which have been tried without effect, so effort goes
where it can move results. Numbers are from the bench of 2026-10-09 (commit `cd556e4`);
rerun `roboscriptorium bench tuning|validation` before relying on them, and update
this file when they move.

## How close we are

The goal (AGENTS.md, Purpose): an edition as careful as Standard Ebooks', in hours, with
a human answering only what the machine can't.

| Kind of book | Example | Wrong words a page after review | Questions a page |
| --- | --- | --- | --- |
| Clean scan, modern Dutch prose (Stella's kind) | Goede dochter, Reis, De cipier | 0.25–0.40 | 1.2–1.3 |
| Clean scan, modern English prose | Metro, Thief-Taker, Crime | 0.40–0.42 | 1.2–1.5 |
| Born-digital PDF | Villa Toscane | 0.12 | 0.13 |
| Old typography, plates | Dolittle | 0.77 | 1.6 |
| Busy layout, pictures | 11/22/63, You're Never Weird | 0.83–0.84 | 2.2 |
| Washed-out scan | Afscheid | 0.24 (a typed page counts as one question) | 0.5 |

Bench totals: tuning 0.48, validation 0.79 wrong words a page after review, with about
half the questions of before (tuning was 0.96 until an error over a page break counted
on the page holding most of it; questions halved by not asking what the arbiter is
≥ 0.8 sure of, a figure to revisit with any new arbiter, judge or reader).

**Assessment (2026-10-09):**
- Stella coming out as a clean, valid EPUB is likely (~80–90%) and near: its kind of
  book is at one wrong word in three or four pages.
- Standard Ebooks' fidelity on any scan, in hours, with few questions, is about even
  odds with today's models. The build plugs in better models quickly
  (`experiments/tryout.py`), so it improves as they do.

## Where there is room, by expected gain

1. **Structure the word counts can't see.** Until 2026-10-09 the bench counted only
   words, and a book could lose every heading unseen (Villa Toscane 0/12 in every run).
   `bench` now prints headings and paragraph F1 per book. Still lost:
   - De eerlijke vinder 0/4 (plus a spurious "de"): part numerals I–IV, the first drawn.
   - You're Never Weird 4/16: "- 1 -" numbers, bracketed sections, subtitles.
   - Paragraph F1: Afscheid 0.709, You're Never Weird 0.901, Dolittle 0.905, Reis 0.922.
   - Thief-Taker 9/22 and Metro 5/10 are a scoring convention: the reference has label
     and title as two headings, the build one heading of two parts.
   - Not handled at all yet: footnotes in the body, verse, tables, scene breaks beyond
     "* * *".
2. **The errors no question asks about** ("unasked", by kind, in each bench record):
   - Vals alarm: 33 unasked letter errors, its lost full stops (checklist 5): only its
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
   data and its ABBYY reading gives a confidence per letter (checklist 6f). Only the
   public-domain books have them: Crime and Dolittle so far.

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

## What would make "done" checkable

Not yet agreed with the user; a proposal to settle before the end:

- Stella under 0.3 wrong words a page after review, under 1 question a page.
- Headings and paragraphs right (heading recall 1.0, paragraph F1 ≥ 0.98).
- epubcheck clean.
- The test set (Het geluid van bananen) scored once, at the end, within reach of the
  validation books.
