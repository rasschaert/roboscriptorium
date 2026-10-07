# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State at the end of 2026-10-07 (evening)

Everything is committed on `main`. Another Claude session works on the review
page (`regions.html`, `review.html`); stay out of those files and commit only
your own files by name.

What changed today, in the order it matters:

- **Learned trust decides the OCR check** (`trust.py`, default on;
  `ROBO_OCR_TRUST=0` for the old SURE/SURE_ALONE rule). Shallow trees over the
  judges' picks and confidence, which readings read each version, the word
  list, and the kind of difference; trained on the tuning books' suspects
  (labels from `golden.align`) plus Stella's review answers, never on held-out
  books. The least sure suspects are asked, up to `ROBO_OCR_QUESTIONS` per page
  (1.0). Held out: De tuin wrong words 5.38 → 3.07/page with half the
  questions. Retrain with `experiments/ocr_trust_data.py --rebuild` then
  `PYTHONPATH=experiments uv run python experiments/train_ocr_trust.py --save`.
- **OCR doubts are asked per place**, cropped to the words, answers change only
  their span, machine fixes elsewhere in the line still apply
  (`corrections.apply(..., fixes)`), and a break hyphen is asked across the
  break ("dankbaar" / "dank baar"). Earlier whole-line answers still count
  (`Corrections.for_flag`).
- **Dash style per book** (`typography.py`): measured on the scan or set in
  book.toml (`dash`, `dash_spacing`); every dash written that way; dash-only
  differences aren't doubts. Stella: en dashes, thin spacing. **Not yet set in
  Stella's book.toml**: the user decides.
- **Quote balance as questions** (`quotes.py`): 25/32 on an error on Reis.
- **Footnotes kept apart from scores** (`golden/notes.py`, `note_classes`).
  Reis, Stella's stand-in: CER 0.12%, 0.25 unasked wrong words/page.
- **Break hyphens by the book's own spelling** (`reflow.spellings`).
- **Word list** from tesseract's DAWG (`lexicon.py`): a recorded vote and a
  trust feature, not a decider.
- **Stella's review is finished** and proofread: the agent checked every crop
  and fixed 9 errors in the answers (typing slips, a lost ‘, "waarbijj");
  originals in `work/stella/review/regions.jsonl.before-proofread`.
- **Qwen3.8** (`qwen3.8:27b-nvfp4`, pulled by the user) is the proofreader:
  reading a tight crop and comparing in code caught 9/9 wrong answers with 3
  false alarms in 58 (`experiments/probe_proofread.py --read`); as a text
  judge with thinking on, read by winnow (`probe_proofread_judge.py --think`),
  10/12. Generative models are only ever read through first-token logprobs
  (thinking off) or through a decision model reading their free reply.
- **Line-role classifier** with layout-region features: 111 role errors against
  256 for `roles.py` over twelve books, but unstable on the English books
  (Lady into Fox up to 71 when another book is left out). Thief-Taker is now
  built with models; rebuild the line-role data with it and rerun
  `tune_line_roles.py --focus` before wiring it in.

## Next steps, in order

1. **Qwen as a third reading in the OCR check.** Bench result on Goede dochter
   in `work/probes/line-readings/goede-dochter-qwen.log` (see below). If it
   reads as well as the layer and its errors differ, add it to the readings
   (`readings["qwen"]`) and its support to the trust features, retrain, and
   score with `quality`, held-out books last.
2. **Quote questions with a proposed fix.** The user twice answered a quote
   question "as the layer reads it" where an opening ‘ was missing: the
   question offers no reading to choose. Offer Qwen's reading of the region as
   a reading.
3. **Proofread answers automatically**: after each answer, Qwen reads the crop;
   a difference becomes a follow-up question. Straight quotes in a curly book's
   answer are corrected without asking.
4. **Line-role classifier**: add Thief-Taker's data, check stability, wire in
   behind a switch, compare with `quality`, then delete the rules it covers.
5. **Paragraph language judge** (the user's point 3): Qwen with thinking reads
   the paragraph around a suspect; probe on ~50 labelled suspects first.
6. Settle verdicts on Reis and the CPNB books (`golden review`), so small gains
   there can be told from edition noise.

## From an outside review (Gemini, `review.md`, 2026-10-07)

Another model reviewed the repo. Checked against the code, four of its bugs were
real and are fixed, each with a test: `disagreements.patch` skipped a verdict
whose context overlapped one applied before it; `ocrcheck.apply` keyed fixes on
the line's text, so identical lines on a page took each other's fixes;
`corrections.apply` dropped `Line.source` on a retyped line; and a large initial
set inside a text-layer line made that line's box tall enough to swallow the
next printed line (Thief-Taker's chapter openings). Its ideas worth keeping:

- **A sequence model over pages for furniture and headings.** Page numbers
  count up by one, running heads alternate verso/recto, a chapter title follows
  its label, a chapter opening sits on a sunk page. A CRF/HMM (or a Viterbi pass
  over the line-role classifier's per-line probabilities) enforces that
  structure jointly, where the rules and the classifier now judge each line
  alone. Try it as a layer on top of the classifier once that's wired in (step
  4); the page-number sequence is the easiest first case.
- **Don't ask a vision model about a tiny mark.** Whether a crop shows `zijn’` or
  `zijn.’` is at the limit of what a patch-based encoder sees (clef missing the
  small period on Vals alarm agrees). Prefer constraints that need no eyes:
  quote pairing (`quotes.py`), sentence ends before a closing quote, the word
  list, and give these to the trust model as features.
- **Question ranking by kind ignores the kind of book.** `quality` ranks a
  question's kind by how often it caught an error in other books; a kind means
  different things in a picture book and in plain prose. Make the reason's hit
  rate a feature conditioned on simple book traits, or learn it with the trust
  model.
- Smaller: votes are keyed by model name, so the same model as judge and reader
  would collapse into one vote (key by role); a drop cap that is its own
  fragment (Thief-Taker p70 "P", the only real one in fourteen books) still
  joins the line below it; file reads and writes lean on the UTF-8 default.

Checked and rejected: releasing `PDF_LOCK` during a review rebuild (the lock is
what keeps PyMuPDF single-threaded while the pipeline runs; nothing inside
takes it again, so no deadlock), `Figure` blocks reaching `figures.place` (they
can't yet), making the page image the primary reading (the text layer is the
best single reading on modern Dutch), and portability to non-Mac machines.

## Working with the user

- Before every long run, say why, what it should show, how long it takes and
  what each outcome would mean. One book per long command.
- Held-out books are scored, never used to find errors.
- The user picks no models; ask before adding a runtime or a large download
  (slow connection), and let the user run `ollama pull` themselves.
- 1Password locks: if signing fails, stop and ask for it to be unlocked.
