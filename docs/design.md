# Why it is built this way

Each component, what job it does, and the evidence that it earns that job. When
the evidence changes, this file changes with it (AGENTS.md's standing rules). The
dated history behind each line is in [decisions.md](decisions.md).

Numbers marked *trust data* come from the OCR check's labelled suspects
(`experiments/ocr_trust_data.py`, each version labelled from the aligned golden
text, settled ones only): 2,663 over nine books on 2026-10-07.

## The text layer is one reading, not the truth

A scan's OCR layer is good (Goede dochter: 0.20% CER on body lines) but drops
quote marks, misreads accents and splits contractions. Every other reading exists
to catch what it gets wrong; none replaces it, because each has errors of its own
(bench: `experiments/bench_line_readings.py`, Goede dochter pp. 9–64).

## OCR check

**Several readings that fail differently.** A reading only helps where it is
right and the layer is wrong, so readings are chosen for different errors, not
for the best score alone:

| Reading | Why it is there | Its own failure |
| --- | --- | --- |
| glm-ocr, line crop | letters and words (right where the layer is wrong on 114 of Goede dochter's lines) | drops quotes, diaereses; a word now and then |
| tesseract, whole page | its own line segmentation, so it sees marks the layer's boxes cut off; dashes | punctuation, opening quotes |
| qwen3.8, line crop, told the book's style | quote marks (keeps them where glm-ocr loses 31, tesseract 80) | plausible real words (`doodgaan→doorgaan`) |

glm-ocr and qwen3.8 read crops cut from the layer's boxes, so they share its
segmentation errors; only tesseract doesn't.

**Two judges where the readings differ.**

- *clef:27b looks at the crop.* It is the judge that is usually right: 2,290 of
  2,663 alone (86%, trust data). Told the book's typesetting and given options in
  ⟨ ⟩ rather than “ ”, it picks right more often on typography (Goede dochter 92 →
  98 of 102).
- *winnow:e4b reads the sentence, not the image.* It is a poor judge alone (1,728
  of 2,663, 65%) and is kept as **an alarm on clef**: where winnow agrees with
  clef, clef is wrong on 59 of 1,536 (4%); where it disagrees, on 314 of 1,127
  (28%). The alarm works on every book but the cleanest: on Goede dochter clef is
  wrong 13/170 against 12/191, no lift. On Lady into Fox winnow even beats clef
  (132 against 54 of 149), but that book's labels differ from its print in
  typography, so the number measures the reference more than the judges. Told the
  book's style winnow got worse on Goede dochter (91 → 84 of 200), so it isn't.
- *The word list is a vote, not a judge.* Where it knows only one version's words
  it is nearly always right, but acting on it added unasked errors on two
  validation books (lost compounds, stress accents). It is shown to the reviewer
  and is a trust feature.

**Learned trust decides, not a fixed rule.** The judges' confidences aren't
probabilities of being right, and how much each signal is worth differs by kind of
error and book (the winnow numbers above). Shallow trees over the judges' picks
and confidence, the readings' support, the word list and the kind of difference
learn that from labels: leaving one book out, silent errors at the rule's own
number of questions fell 57 → 15 over seven books. The fixed rule (both judges
agree, clef ≥ 0.3) asks about 35% of suspects because it needs winnow's
agreement; it is only an explicit fallback (`ROBO_OCR_TRUST=0`). A missing or
mismatched model stops the build, because a silent fallback once ran unnoticed.

**The question budget is book-wide.** Questions go where the model is least sure,
which may be several on one bad page; a per-page cap would spend questions on
clean pages.

**Doubts are asked per place, not per line.** Two wrong places in one line, each
fixed by a different reading, left no right option, and the reviewer then typed
the line and added an error.

## Book-wide style

Dash kind and spacing, and the quote style, are a property of the book, not of a
line: asked line by line they came out mixed. Dashes are measured on the scan;
quote style comes from the layer's own marks. Models that read or judge
typography are told the style; this halved Qwen's wrong quote proposals on Reis.

## Quote questions

A paragraph whose quotes don't pair up is flagged where the mark is missing, and
the question offers Qwen's reading of the line, keeping only its quote marks and
the punctuation beside them on the OCR-checked letters: its letters slip too often
to take (`krimpachtig`, a Cyrillic word), its quote marks rarely do (Reis right on
51 lines where the line is wrong, wrong on none where it is right).

## Line roles

clef-flash:9b answers the doubtful lines, and rules in `roles.py` override it
where layout settles the question. The rules don't carry over to unseen books
(Villa Toscane headings 0/12); a tree classifier over layout, type and clef's
answer makes 111 role errors to the rules' 256 over twelve books, but is unstable
on the English books with three to train on. It replaces the rules once more
English data makes it stable and the bench says so.

## Measuring

- **`bench`, not single runs.** Warm caches replay themselves, so reruns agree;
  the noise is which pages a book happens to have. Runs are compared page by
  page, with one primary test ("after review" pooled over the set's pages, at the
  low, mean and high slip rate) and a veto when any book alone gets worse: 24
  separate intervals would star about one by chance each run.
- **"After review" counts the reviewer's slips.** 8 of 68 checked answers on
  Stella were wrong (Beta posterior 0.06–0.21), so a question isn't free.
- **Validation books are not a test.** Earlier choices were made on their scores.
- **Tuning books are scored by models trained without them**
  (`*-without-<book>.pkl`).
- **The reference isn't the truth either.** 563 of 3,232 suspects (17%) can't be
  labelled: no single version is close enough to the aligned reference (edition
  differences, transcriber changes, or no reading right). They are left out of
  the trust data, so trust isn't trained on them, but in a build they are
  questions with no right option, where the reviewer types and slips more.
  Verdicts (`golden review`) settle the reference's side.
