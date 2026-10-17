# Optimism

How likely the goal looks, asked often by the user and answered here, dated, so the
trend shows. The goal: feed in a PDF of a scanned physical book, get out a high-quality
EPUB with only an acceptable level of subtle mistakes.

What counts as acceptable, in the bench's terms: wrong words a page after review (or
unasked, with no review). One wrong word in 1,000 (~0.3 a page) is about a decent
commercial e-book; a careful edition like Standard Ebooks is nearer one in 10,000.

Each entry is a judgment, not a measurement: the numbers it rests on are in
[outlook.md](outlook.md) and [decisions.md](decisions.md). Newest first.

## 2026-10-18, past midnight: 6/10

| Goal | Chance |
| --- | --- |
| Modern prose, clean IA scan (Stella's kind), commercial-e-book quality with a light review (≤ 0.2 questions a page) | ~75% |
| The same books with no human at all, ≤ 1 wrong word in 1,000 | ~45% |
| Universal: any physical-book scan (old typography, footnotes, verse, busy layouts, washed-out pages) in, high-quality EPUB out, unattended | ~20% in this project's horizon |

**Where it stands:** tuning 0.30 and validation 0.37 wrong words a page after review,
with 0.3–0.6 questions a page; about one wrong word in 1,000.

**Up since the morning:** structural experiments still pay. The context judge would
settle two thirds of the questions at 8–12% wrong; Winnow-12B is right on 78% against
winnow's 67%; every error now has a cause and the remaining ones are a handful of
nameable kinds (extra text, glued words, quotes, accents).

**The doubts:** about two thirds of what is left was never doubted by any reader, and
nothing yet catches it but a better reader. Each new kind of book has needed its own
work. `init` can't yet find a body range unattended (page kinds 86%, the text's start
right on 25 of 29 books). Local models are the ceiling.

**Would move it up:** a reader that catches what none doubts today; `init` finding the
body range alone; first-look scores within reach of the tuned books.
**Would move it down:** first looks far worse than tuning (the golden books fitted, not
the machine built); the context judge or Winnow-12B failing on the bench.
