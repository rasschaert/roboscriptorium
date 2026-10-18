# Outlook: where the needle can still move

For an agent choosing what to work on. It says how close the build is to its goal,
which areas still have room, and which have been tried without effect, so effort goes
where it can move results. Numbers are from the benches of 2026-10-17 (commit `9c5efc0`);
rerun `roboscriptorium bench tuning|validation` before relying on them, and update
this file when they move.

## How close we are

Bench totals (2026-10-18, Winnow-12B as the text judge): tuning **0.28**, validation
**0.39** wrong words a page after review; paragraph breaks set wrong 0.17 and 0.14 a page.
Per book, wrong words a page before review, questions a page, wrong words after review,
breaks set wrong a page:

| Kind of book | Books (before · questions · after · breaks) |
| --- | --- |
| Clean scan, modern Dutch prose (Stella's kind) | Reis 0.20 · 0.30 · 0.07 · 0.08; Het ijzige land 0.37 · 0.32 · 0.18 · 0.01; De cipier 0.21 · 0.21 · 0.18 · 0.02; Doodskleed 0.64 · 1.44 · 0.38 · 0.04; Goede dochter 0.41 · 0.41 · 0.21 · 0.00; Vals alarm 0.38 · 0.42 · 0.13 · 0.02; De kerk 0.42 · 0.69 · 0.35 · 0.02; De eerlijke vinder 0.31 · 0.51 · 0.19 · 0.05 |
| The same, chosen for their trouble | Het heft 0.33 · 0.32 · 0.21 · 0.00 (its washed-out lines); Monterosso 0.42 · 0.48 · 0.43 · 0.01 (small capitals, old-style figures); De tuin 0.70 · 0.67 · 0.28 · 0.01; Het laatste bevel 0.65 · 0.39 · 0.50 · 0.00 (its EPUB glues words) |
| Unindented Dutch (Bruna) | Vuurspel 0.39 · 0.50 · 0.20 · 0.43; De stilte 0.80 · 0.43 · 0.34 · 0.29 |
| Clean scan, modern English prose | Metro 0.30 · 0.43 · 0.24 · 0.02; Thief-Taker 0.51 · 0.54 · 0.42 · 0.14; Crime 0.28 · 0.26 · 0.28 · 0.01 (Gutenberg's edition); The Stranger's Child 0.64 · 0.55 · 0.48 · 0.01; Normal People 0.17 · 0.13 · 0.16 · 0.07; Artemis 0.56 · 0.44 · 0.33 · 0.34 |
| Old typography, plates | Dolittle 1.03 · 1.39 · 0.40 · 0.18 |
| Busy layout, pictures | You're Never Weird 1.00 · 1.13 · 0.68 · 0.20 |
| Washed-out scan | Afscheid 9.35 · 3.47 · 0.61 · 1.73 (typed pages; its EPUB's paragraphing) |

Since 2026-10-11 (tuning 0.31, validation 0.70): the trees on by default, the arbiter
retrained with the reviewers' answers, Metro's closing quotes, the lower-case paragraph
check (the break judge off), lines at a text block's edge, and three corrections of the
measurement (Bruna's markup spaces, nested-quote gaps, number and title as two
headings). What is left after review is mostly errors no question asks about; read
place by place (decisions.md, 2026-10-17), much of it is the reference's, not ours.

Until 2026-10-10 every bench figure but Goede dochter's and De tuin's measured DeepInfra's hosted Qwen,
not the local build Stella gets; read again locally on 2026-10-10, no change by the bench.

**Assessment (2026-10-09):**
- Stella coming out as a clean, valid EPUB is likely (~80–90%) and near: its kind of
  book is at one wrong word in three to five pages, and its paragraphs nearly all right.
- Standard Ebooks' fidelity on any scan, in hours, with few questions, is about even
  odds with today's models. The build plugs in better models quickly
  (`experiments/tryout.py`), so it improves as they do.

## Where there is room, by expected gain

0. **The page readings where they can reach the gain (readings cached, not built).**
   glm-ocr and Qwen agreeing against the build point at 60 errors no question asks,
   about a quarter of what's left after review, mostly at line joins and page numbers.
   Fed in as two more line readers they reached few of them: `bench tuning` no change
   (0.32 → 0.32), validation 0.50 → 0.43 after review but worse before it on two books
   (2026-10-15). The line-role feature they suggested found little left to fix
   (2026-10-16: 5 of 657 unread lines wrong), and the hyphen votes were a null too.
1. **Structure.** The bench now counts paragraph breaks per page and prints headings.
   - Line roles: the trees (`sorter.py`) are on by default since 2026-10-13 (validation
     0.59 → 0.50, no book worse); Dolittle's text wrapped around drawings is what they
     still drop.
   - Breaks left: Afscheid's are its EPUB's; Vuurspel 0.46 and De stilte 0.30 (sentences
     ending at the margin in unindented text), Artemis 0.32 (its letters, set without
     spacing), Dolittle 0.18 (verse and lines beside drawn initials). The vision judge
     on line crops broke more than it fixed (2026-10-17); a page-level reading of
     breaks is the untried way.
   - Headings still lost: De eerlijke vinder 0/4 (drawn part numerals), You're Never
     Weird 3/16 (titles recurring as running heads, bracketed section heads read as
     specks), Monterosso 14/22 (old-style figures misread). Branches `heading-pairs`
     (scoring) and `number-lookalikes` (repeats counted at their place, look-alike
     numbers) wait for the slice growth (checklist).
   - Scene breaks, scored since 2026-10-11 in the ten references that record them: 272 of
     295 found, few extra; the rest are page turns geometry can't tell from a paragraph
     running on.
   - Footnotes are taken out of the text (2026-10-11; Reis 7 of 8). Not handled: verse,
     tables, block quotes, epigraphs.
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
   A better reader alone moves little: 29% of what's left after review is misreading no
   reader doubted (2026-10-13), so fine-tuning a reader is off for now.
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

**The errors every reading shares** (2026-10-16): three cheap features tried (the word
list on glued words, tesseract's confidence, accent variants), none separates them; they
are mostly stress accents and one-offs. The lever is a stronger reader, not a detector
over today's readings.

**Stella, estimated** (2026-10-16, against Claude's reading): 4 wrong words in 67 pages
before review, 2 of them asked, 6 questions; quotes, dashes and italics not compared.

**A ceiling for whole-page reading** (2026-10-15): Claude Opus 5.5 read 17 probe pages
with one real error, right at every place the pipeline still errs (line joins, drawn
initials, text around pictures). Whole-page reading is the architecture to aim for; the
gap is the local readers (Qwen 76 wrong words on the same pages). Rerun the probe on
each new local vision model.

## Tried, and why it didn't help

Don't repeat these without a new reason (details in docs/decisions.md):

- **The page readers as two more line readers for the arbiter** (2026-10-14/15, a night
  of compute): tuning no change, validation mixed. Split into lines, a page reading
  can't carry the join errors it catches; the arbiter takes its versions wrongly on
  unseen books. The readings stay cached for the uses above.
- **"No page reader reads it" as a line-role feature** (2026-10-16, a probe): the trees
  already get those lines right but for 5 of 657.
- **The page readers' spelling of a line-end compound** (2026-10-15, a probe): with the
  hyphen judge in, the build is wrong on 19 of 3,184 line-end hyphens; the readers
  agreeing fix 9 and break about 6. Too few to build on.

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
- **Speeding Qwen on the server** (concurrency, crop size, context, pooled decision
  calls): nothing; see the next section before measuring any of it again.
- **qwen3.8:27b-q8_0 as the reader** (the same model as a GGUF on Ollama's llama.cpp
  runner): no more accurate on reader set v2 (hard 458 against 463 of 510, control 333
  against 338 of 340), 2.2 s a line at any concurrency: the runner doesn't batch it.
- **Unsloth's UD-Q6_K_XL and UD-Q8_K_XL as the reader** (through Unsloth Studio): 457
  and 460 of 510 hard, 334 of 340 control each, ~1.7 s a line. With the q8_0 they make
  the same control-line errors word for word: the llama.cpp runtime, not precision,
  parts the GGUF builds from the nvfp4 on MLX.
- **Fine-tuning a reader** (not tried, ruled out by measurement, 2026-10-13): of the 186
  wrong words the tuning books keep after a perfect review, only 53 (29%) are reading
  errors no reader doubted, the only ones a better reader alone would fix, and 31 of
  those are punctuation. Below the half agreed with the user as the bar.

## Inference speed: what a cold page costs, and what's been tried

Measured 2026-10-11 on an idle machine (docs/decisions.md of that date; the probes
`experiments/probe_qwen_speed.py`, `probe_glm_parallel.py`, `probe_decide_parallel.py`,
their results under `work/probes/`). Rerun a probe only when the server, a runner or a
model changes.

**A cold page, about 48 s** (the run-times table's 0.8–1.1 min a page): Qwen ~36 s
(30 lines at 1.2 s), the judges ~5 s (clef 1.25 s a call), the sorter ~3 s (5.4 calls a
page at 0.55 s), glm-ocr ~3 s (0.09 s a line), tesseract and layout ~2 s. Qwen is three
quarters; a trust-data rebuild of the 20 books (2,188 pages) is ~28 h, Qwen ~22 h of it.

**Qwen's 1.2 s a line**, the nvfp4 build on Ollama's MLX runner: 0.8 s prefill (the
vision tower ~0.3 s, the ~135 instruction and template tokens ~0.5 s) and 0.35 s
writing the ~20 output tokens. The image is ~45 of the 182 prompt tokens at any
resolution. The runner caches whole prompts (a repeat prefills in 0.05 s, still after
five others), so a rerun of cached lines is free even without the pipeline's cache.

**Tried, no effect, don't repeat:**

- **Requests in parallel to Qwen.** 1, 2, 4, 8 and 16 at a time: 1.16–1.21 s a line
  alike, with and without `OLLAMA_NUM_PARALLEL=4`. The MLX runner takes one request at
  a time; the pipeline's four reader threads only queue on it. Readings identical.
- **Crop resolution for speed.** 300, 200 and 150 dpi: 182, 168 and 166 prompt tokens,
  the same prefill time.
- **Context length.** 128k against 8k: the same speed; 128k only held memory.
- **Parallel calls to the decision models.** clef-flash (llama.cpp, four slots) 0.55 s
  a call and clef:27b (nvfp4, the MLX runner) 1.25 s, one or four at a time alike;
  choices and confidences identical. Their calls stay one after another.

**Done, in place:** `OLLAMA_NUM_PARALLEL=4` (docs/models.md, Setup) halves glm-ocr's
time a line (0.19 → 0.09 at four at a time, readings identical); the pipeline's four
threads already send that many. The same four slots did nothing for a 27B GGUF
(qwen3.8:27b-q8_0, 2.2 s a line at 1 to 16 at a time), so batching is a property to
measure per model, not a promise of the runner.

**Would speed Qwen but changes what it reads**, so each is a reader change through the
tryout, never a setting: the instructions as the system turn ahead of the image (the
prefix is reused: 0.80 s a line, but 4 of 64 readings change, one wrong); a shorter
instruction (untested); another build of the same model (the q8_0 GGUF was tried and
rejected, and so were Unsloth's UD-Q6_K_XL and UD-Q8_K_XL, above: slower and no more
accurate; an MLX build at higher precision, mxfp8, is untested and not pulled); the "mtp" builds (nothing on Ollama's library
says the runner uses the MTP head, and it could speed only the 0.35 s of output).

**What a faster reader must pass.** `experiments/tryout.py run reader <model>` on reader
set v2 (`tryouts/reader-v2.json`: 850 body lines from the 17 tuning books' slices, 510
the text layer reads wrong and 340 it reads right; the incumbents' readings are cached
under `work/tryout/reader-v2/readings/`, so a run costs the candidate's own 850 lines,
and reports seconds a line). The reader in use, qwen3.8:27b-nvfp4, reads 463 of the 510
hard lines right (CER 0.74%) and 338 of the 340 control lines (0.01%), quote marks wrong
on 26 and 5, at 1.20 s a line; a candidate must match both strata, quote marks and
accents included, and be right alone on lines the others miss (docs/models.md has the
ones that didn't: the q8_0, UD-Q6_K_XL and UD-Q8_K_XL builds, gemma4, a ~1-bit Qwen3.8-Flash-Next, MoE readers).
Speed is its own pace one request at a time, since no runner tried batches a model this
size (Unsloth Studio queues requests ahead of its llama-server); it must also fit beside clef:27b and the small models in 64 GB, think nothing and
write one line. A winner then needs the trust data rebuilt and the arbiter retrained
before it reads for the arbiter: cheapest while a rebuild is due anyway.

**The lever that changes the machine** (for the bench, not a setting): Qwen reading
only where the layer, glm-ocr and tesseract disagree, several times fewer calls.
Measurable offline once the trust data is rebuilt: how often Qwen alone is right where
the other three agree.

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
- the first looks (each new pair scored once, before anything is chosen on it) within
  reach of the tuning and validation books.
