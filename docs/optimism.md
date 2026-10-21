# Optimism

How likely the goal looks, asked often by the user and answered here, dated, so the
trend shows. The goal: feed in a PDF of a scanned physical book, get out a high-quality
EPUB with only an acceptable level of subtle mistakes.

What counts as acceptable, in the bench's terms: wrong words a page after review (or
unasked, with no review). One wrong word in 1,000 (~0.3 a page) is about a decent
commercial e-book; a careful edition like Standard Ebooks is nearer one in 10,000.

Each entry is a judgment, not a measurement: the numbers it rests on are in
[outlook.md](outlook.md) and [decisions.md](decisions.md). Newest first.

## 2026-10-21, early morning: 6.5/10 (unchanged)

| Goal | Chance |
| --- | --- |
| Modern prose, clean IA scan, commercial-e-book quality with a light review | ~80% |
| The same books with no human at all, ≤ 1 wrong word in 1,000 | ~45% |
| Universal, unattended, on today's local models | ~20% |
| The same by 2030 | ~60–70% |

**Where it stands:** tuning 0.29 wrong words a page after review (0.30 on the 18th),
validation 0.51 (0.37 on the 18th, but the set has grown with harder books: not
comparable). The arbiter that settles the OCR check's suspects takes 9 wrong ones
silently in 9,300; almost everything left is a place no reader doubts.

**What the last two days taught:** the line reader is the lever, and it moves fast.
Qwen3.8-27B is two months old and reads 463 of 510 hard lines right; Qwen2.5-VL-72B,
state of the art in open vision models in January 2025, reads 382. Five models were
tried as readers, witnesses or detectors (PaddleOCR-VL, olmOCR-2-7B, Qwen2.5-VL-72B,
H2O-Lightning-Omni-4B, fonles-decision-1) and none beat the current one; olmOCR helped
a plain vote (801 → 809) but not the arbiter. That is a snapshot of what could be
pulled this week, not a verdict on swapping models: something will dethrone it within a
year in the memory a laptop holds, and the build is set up to take it (frozen sets, one
command to screen a reader, the arbiter retrained on its readings). Two arbiter
features for a line-end comma failed. What paid besides: reading the errors place by
place. About half of the biggest unasked class (stress accents) is the reference's
slips, not ours (our text matches the print), so the measured error rate overstates the
build by a fifth or so, and a book's hyphens should be weighed by the whole book, not
the slice (compound hyphens 0.023 → 0.020).

**The doubts:** the real half of what is left is reader blindness to rare marks (an
emphasis accent on an i, the dotless ı of a Turkish name): no prompt, no model and no
higher resolution but a narrow one (450 DPI keeps 2 of 6) sees them. Lost lines (about
half are decorated chapter openings no whole-page reader reads) and every new kind of
book still need their own work. Local models are still the ceiling.

**The horizon:** unchanged, and the last two days support it (the user's point): the
reader that fits a laptop has changed more in the months since January 2025 than any
tuning of ours did, and what is hard now (accents and rare marks no reader sees) is what
the next vision models are likely to fix. The work that carries over is the gate a new
model must pass: the reader set, the vote simulation, and the unasked-error set.

**Would move it up:** a reader that keeps emphasis accents and rare glyphs; an
opening-line reader for lost lines; `init` finding the body range alone.
**Would move it down:** first looks far worse than tuning; a measure found to flatter
the build (the reference's slips cut the other way today).

## 2026-10-18, late morning: 6.5/10

| Goal | Chance |
| --- | --- |
| Modern prose, clean IA scan, commercial-e-book quality with a light review | ~80% |
| The same books with no human at all, ≤ 1 wrong word in 1,000 | ~45% |
| Universal, unattended, on today's local models | ~20% |
| The same by 2030 | ~60–70% |

**Up:** the first look, the first scores on books nothing was ever chosen on. Het
schaduwhuis 0.17 wrong words a page after review, Het geluid van bananen 0.47, Verminkt
whole (417 pages) 0.49, against 0.28 and 0.37 on the books the machine was tuned and
checked on. The machine carries over to new books of the kind it was built for; the
golden books weren't simply fitted.

**Not down, but noted:** the two that scored far off were mostly their references
(De geruchten's e-book changed the print's quote marks; Steve Jobs's is a revised
text), which says the pairs need the same scrutiny as the machine. What is the
machine's in them is structure: De geruchten's section headings (a narrator's name in
capitals mid-page) found 0 of 21, and Verminkt's quote marks and dashes. Each new kind
of book still brings a structural surprise.

## 2026-10-18, past midnight: 6/10

| Goal | Chance |
| --- | --- |
| Modern prose, clean IA scan (Stella's kind), commercial-e-book quality with a light review (≤ 0.2 questions a page) | ~75% |
| The same books with no human at all, ≤ 1 wrong word in 1,000 | ~45% |
| Universal: any physical-book scan (old typography, footnotes, verse, busy layouts, washed-out pages) in, high-quality EPUB out, unattended | ~20% on today's local models |
| The same by 2030, with the same bones and the models and memory of then | ~60–70% |

**Where it stands:** tuning 0.30 and validation 0.37 wrong words a page after review,
with 0.3–0.6 questions a page; about one wrong word in 1,000.

**Up since the morning:** structural experiments still pay. The context judge would
settle two thirds of the questions at 8–12% wrong; Winnow-12B is right on 78% against
winnow's 67%; every error now has a cause and the remaining ones are a handful of
nameable kinds (extra text, glued words, quotes, accents).

**The doubts:** about two thirds of what is left was never doubted by any reader, and
nothing yet catches it but a better reader. Each new kind of book has needed its own
work. `init` drafts a book's setup from the PDF (2026-10-21) but can't settle the text's
two ends unattended: first end right on 22 of 27 labelled books, last on 21, off by a page or
two (an advert for an afterword), so a person confirms both from a contact sheet. Local
models are the ceiling.

**The horizon** (the user: models get better and consumer hardware gets more memory;
the project keeps its bones with better models in them). What is hard now (a reader
seeing what no reader doubts, sorting a busy layout) is what better vision models fix.
Code won't be the limit either: a future agent rewrites any of it (the user: "it will
have no problem solving any coding task"). What carries over is the evidence: the
human labels, the golden pairs, the measurements and the record of what was tried and
why. The 2030 chance rests on how much of that we gather now.

**Would move it up:** a reader that catches what none doubts today; `init` finding the
body range alone; first-look scores within reach of the tuned books.
**Would move it down:** first looks far worse than tuning (the golden books fitted, not
the machine built); the context judge or Winnow-12B failing on the bench.
