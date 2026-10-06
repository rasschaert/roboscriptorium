# Handover

Where work stopped, for the next session. AGENTS.md holds the standing rules and
decisions; this file only covers the state of play. Replace it at the end of
each session.

## State on 2026-10-06

M0–M2 done; M3 (better OCR and decisions) in progress; an early piece of M4
(the review page) exists.

- **References are Project Gutenberg transcriptions now**, not Standard Ebooks
  (see the decision log). Golden books: Sense (Tauchnitz scan, but Gutenberg is
  the 1811 edition), *The Nature of a Crime* (Gutenberg made from the same
  scan: the cleanest benchmark), *Doctor Dolittle* (same printing).
- **Line roles: `clef-flash:9b`** on Ollama's `/v1/systemone` is the default.
- **Review page**: `uv run roboscriptorium review <book>` → http://127.0.0.1:8765/.
  The user offered to give verdicts on Crime's 54 open disagreements; none
  recorded yet. Verdicts land in `golden/<name>/verdicts/<scan>.jsonl` and
  `eval` patches them into the reference.
- **OCR probe** on *Het ivoren aapje* (Dutch, 1909, Gutenberg page images;
  EU-copyrighted, so only in `work/`): `experiments/probe_ocr.py`. Vision LLMs
  modernise old spelling; tesseract doesn't; merging them with a
  spelling-reform rule plus flags is best so far.

### Scores (all against Gutenberg)

| Book | Setup | CER | WER | Paragraph F1 | Headings |
| --- | --- | --- | --- | --- | --- |
| Sense, Tauchnitz, full | clef roles | 2.99% | 1.36% | 0.811 | 49/50 (+0 spurious) |
| Crime | clef roles | 0.63% | 0.44% | 0.976 | 8/8 (+1: the book title) |
| Dolittle | clef roles | 4.77% | 2.20% | 0.859 | 21/21 (+1: the book title) |
| Lady into Fox (**held out**) | clef roles | 0.93% | 0.33% | 0.841 | 0/1 (the title is also the running head) |
| De aanslag (born-digital PDF) | clef roles | 0.15% | 0.17% | 0.951 | 26/26 (+0) |
| Boze tongen (Dutch scan) | clef roles | 1.36% | 1.15% | 0.749 | 13/18 (+2) |

The visual-line fix (word boxes grouped by vertical overlap) made most of the
Sense and Dolittle gains; see the decision log.

### OCR candidates, Teirlinck, 12 pages

| Reader | CER | Modernised |
| --- | --- | --- |
| tesseract (`nld`, tessdata_best) | 0.90% | 1 |
| `gemma4:latest`, transcribe prompt | 0.70% | 41 |
| `gemma4:latest`, old-spelling prompt | 0.63% | 27 |
| merge gemma4 + tesseract | **0.54%** | flags 89, 56 of them real errors, ~no silent wrong words |
| `translategemma:4b` | 4.9% (1 page) | paraphrases; unfit |
| `translategemma:12b`, old-spelling prompt | ~1.4% on 11 pages; loops on p5 | 12; unfit |
| `translategemma:27b`, old-spelling prompt | 0.99% (merge with tesseract also 0.99%, 11 silent wrong words) | 11; unfit |
| `llava:34b` | 406% (1 page): invents text and loops, 170 s/page | unfit |
| `nemotron3:33b`, thinking off | 14% (1 page): invents words, 7 s/page | 5; unfit |

All candidates tried; gemma4 + tesseract stays the OCR design.

## Next steps, in order

1. When the user has given Crime verdicts: rerun `eval` on Crime and look at
   the mistakes by category; they decide what to fix first. Expected: `;`/`:`
   confusion, line-end hyphens in compounds (`To-morrow`), lost accents.
2. Probe the pending OCR models (above).
3. An OCR stage in the pipeline: render page images (or take them as given),
   run tesseract + a vision LLM, merge as in the probe, carry the flags into
   the IR so the review page can show them. Page images as a book source
   (no PDF) for Teirlinck.
4. Dolittle: drop caps
   lose the initial letter ("NCE upon a time"); plate captions end up in the
   text (the reference leaves them out). Chapter 9's title is missing from
   the text layer (probably set in the illustration). Sense chapter XXV's
   heading ("» CHAPTER XXV.", mid-page) never reaches the model.
5. Paragraph precision on Sense is ~0.6: find where false paragraph starts
   come from.
6. Page classification stage (vision) to replace hand-entered `body_pages`.

## Working with the user

- Run small probes first (10–60 items), say how long a big run will take,
  run it in the background.
- Ask the user to install or pull things when the docs don't cover how.
- Commits are signed through 1Password. If signing fails because 1Password is
  locked, stop and ask the user to unlock it.
- Their internet connection is slow: avoid large downloads (the Dutch
  tesseract model was fetched alone instead of `tesseract-lang`).
