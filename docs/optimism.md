# Optimism

How likely the goal looks, asked often by the user and answered here, dated, so the
trend shows. The goal: feed in a PDF of a scanned physical book, get out a high-quality
EPUB with only an acceptable level of subtle mistakes.

What counts as acceptable, in the bench's terms: wrong words a page after review (or
unasked, with no review). One wrong word in 1,000 (~0.3 a page) is about a decent
commercial e-book; a careful edition like Standard Ebooks is nearer one in 10,000.

Each entry is a judgment, not a measurement: the numbers it rests on are in
[outlook.md](outlook.md) and [decisions.md](decisions.md). Newest first.

## 2026-11-13, morning: 7/10 (held; a new kind of judge under it)

Render and compare, the user's idea of 2026-11-11, is in use: a judge that knows no
language, drawing each reading in the book's typeface over the scan. On tuning it takes
one question in eight away and a twentieth of the unasked wrong words (after review
0.24 → 0.22 a page); validation doesn't move in words. It doesn't move the chances by
itself: the errors no reading doubts are still the wall. What it changes is the kind of
evidence the arbiter has: the first judge that fails for other reasons than the models
do (best of all on accents, worst on punctuation), built from the scan and a font
folder, with no model to wait for. The chances stand as on 2026-11-09.

## 2026-11-09, night: 7/10 (held; the numbers under it firmer)

| Goal | Chance |
| --- | --- |
| Modern prose, clean IA scan, commercial-e-book quality with a light review | ~85% |
| The same books with no human at all, ≤ 1 wrong word in 1,000 | ~40% |
| Universal, unattended, on today's local models | ~20% |
| The same by 2030 | ~65–70% (was ~60–70%) |

**Where it stands** (production since tonight: autotrust-jev 35B and d3 9B judging beside
clef, the arbiter asking below 0.9; a page is about 300 words):

| | Tuning, 5,274 pages | Validation, 889 pages |
| --- | --- | --- |
| Wrong words a page before review | 0.738 → 0.770 | 0.755 → 0.706 |
| Questions a page | 0.645 → 0.759 | 0.487 → 0.584 |
| Wrong words no question asks about, a page | 0.169 → 0.147 (1 in ~2,000 words) | 0.374 → 0.326 (1 in ~900) |
| Wrong words a page after review, with the reviewer's slips | 0.271 → 0.267 (~0.9 in 1,000) | 0.451 → 0.418 (~1.4 in 1,000) |

(Before the arrow, the arbiter of the 7th at 0.8; set means over books.) Tuning's before
review rises at 0.9 because the surer threshold leaves more of the arbiter's picks for the
reviewer, who then settles them: the after-review line is the one that counts.

**Up:** the first new signal the arbiter took since October, and it held on the books
nothing was chosen on: a seventh fewer silent errors on tuning, an eighth fewer on
validation, validation after review down 7%. It came from models that go wrong in
different places, which says a panel can keep growing as models come out; most of the
year's gain should come from there. Line-end hyphens that are the word's own
("SA-mannen", "voor- en achterbank") now come out right where the print sets them.

**Not up:** the price is questions (+18% a page on tuning, the user's choice of 0.9), and
validation is still about 1.4 wrong words in 1,000 after review, half again the
commercial line. The third vision judge (pplx-decider) and the book's own vocabulary
both carried real signal the arbiter couldn't use: at 23 books of training data its
trees pay for every new column about as much as the column earns. That is the
bottleneck now, more than the judges. The no-human row waits on the same thing, and on
errors no reader doubts, which no judge ever sees.

**Would move it up:** more training data for the arbiter (batch five of the slices, the
user's verdicts), then the signals that came back null tonight tried again on it;
autotrust-jev 9B as a text judge (pass 4, benched by morning) paying on the bench.
**Would move it down:** pass 4 adding questions without fewer silent errors, the way
pass 3 did; Stella's or Ex-minnaar's reading finding errors the bench can't see.

## 2026-11-07, midday: 7/10 (up from 6.5)

| Goal | Chance |
| --- | --- |
| Modern prose, clean IA scan, commercial-e-book quality with a light review | ~85% (was ~80%) |
| The same books with no human at all, ≤ 1 wrong word in 1,000 | ~40% |
| Universal, unattended, on today's local models | ~20% |
| The same by 2030 | ~60–70% |

**Where it stands:** tuning 0.27 wrong words a page after review over ~5,200 pages
(0.277 over ~3,100 on 2026-10-25), validation 0.45 (0.502); before review 0.74 a page,
unasked 0.17; tuning's heading errors 32 → 20 in two days.

**Up:** validation, which nothing is chosen on, moved a tenth (0.502 → 0.45), and tuning
held its level while growing by two thirds into harder pages (front matter, part pages,
picture pages). Each gain was a general repair the build now makes on every book, found
by reading its own errors: chapter numbers read by their run, lost text blocks read line
by line, specks and page numbers no longer headings, a scan's repeated pages left out.
None was fitted to one book, and none moved a heading of the user's own books.

**Not up:** much of today's drop in tuning's wrong words (0.876 → 0.740 before review)
is a fairer score, not better reading: Goede dochter's scan repeats two pages and lacks
two. The reading itself moves slowly: a new reader (Qwen3.8-Flash-Next) failed its screen,
and the errors no reader doubts are where they were. The second row waits on that, and
on the arbiter's new signal; the judges told the kinds of OCR error (in its A/B now) is
the first new signal tried since the 25th.

**Would move it up:** the judge prompt paying on the bench; Stella's read-through finding
few errors the bench can't see.
**Would move it down:** the judge prompt trading picks it fixes for picks it breaks (its
interim count: 58 of 320 hard suspects right, 10 of 305 right ones lost). Later that day it
did (decisions.md): no new signal for the arbiter from it, and the second row stays at ~40%.

## 2026-10-25, morning: 6.5/10 (unchanged; the reasons sharper)

| Goal | Chance |
| --- | --- |
| Modern prose, clean IA scan, commercial-e-book quality with a light review | ~80% |
| The same books with no human at all, ≤ 1 wrong word in 1,000 | ~40% (was ~45%) |
| Universal, unattended, on today's local models | ~20% |
| The same by 2030 | ~60–70% |

**Where it stands:** tuning 0.282 wrong words a page after review on the slices of the 24th
(0.290 that morning), 0.286 on the seven slices grown overnight to ~170 pages; validation
0.502; paragraph breaks set wrong 0.045 a page on tuning (0.057).

**The deep-research ideas** (2026-10-23): about twenty tested, none kept: image-gain and
runner-up margin, a threshold per kind of question, grid-padded crops, Kraken, book-wide
consistency, confusion pairs, character-level voting, qwen as hyphen judge, page roles
twice, page kinds, LightOnOCR-3, small capitals from shape, speculative decoding,
learned compound hyphens, accent shape. What paid came from reading our own errors: three
readings that are never the print (a stop before a lower-case line, a half-accented
doubled vowel, marks prose doesn't print), any short line in justified text ending a
paragraph, an image-only scan's dashes measured on the image.

**Why the first row holds:** the errors are located now. Every reader is wrong together on
only 23 lines of the tuning slices (the quiet set); most unasked errors sit where the
readers did disagree and the arbiter chose wrong, which questions catch.

**Why the second slips:** the arbiter twice failed to improve with more labelled suspects
(three more books on the 20th; 2,600 more suspects on the 25th: more unasked errors both
times). It has reached what its features can tell; going unattended needs a new signal
for it, and none of the reports found one.

**Would move it up:** a signal that tells the arbiter's wrong choices apart; a flush-set
tuning book (the flush books' break errors wait on it); a reader that keeps emphasis
accents and rare glyphs.
**Would move it down:** Stella's read-through or a first look finding errors the bench
can't see.

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
