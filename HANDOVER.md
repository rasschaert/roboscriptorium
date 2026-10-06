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
| Sense, Tauchnitz, full | clef roles | 4.75% | 3.15% | 0.682 | **50/50** |
| Sense, Tauchnitz, ch. 1–9 | clef roles | 3.85% | 3.02% | 0.723 | 9/9 |
| Crime | clef roles | 0.72% | 0.53% | 0.965 | 5/8 |
| Dolittle | heuristics | 21% | 18% | 0.43 | 0/21 |

### OCR candidates, Teirlinck, 12 pages

| Reader | CER | Modernised |
| --- | --- | --- |
| tesseract (`nld`, tessdata_best) | 0.90% | 1 |
| `gemma4:latest`, transcribe prompt | 0.70% | 41 |
| `gemma4:latest`, old-spelling prompt | 0.63% | 27 |
| merge gemma4 + tesseract | **0.54%** | flags 89, 56 of them real errors, ~no silent wrong words |
| `translategemma:4b` | 4.9% (1 page) | paraphrases; unfit |
| `translategemma:12b`, old-spelling prompt | ~1.4% on 11 pages; loops on p5 | 12; unfit |

Pending when downloaded: `translategemma:27b`, Nemotron 3 Nano Omni
(33B), `llava:34b`. Run them with
`uv run python experiments/probe_ocr.py run <model> oldspelling`, then
`merge <model>@oldspelling tesseract@plain`.

## Next steps, in order

1. When the user has given Crime verdicts: rerun `eval` on Crime and look at
   the mistakes by category; they decide what to fix first. Expected: `;`/`:`
   confusion, line-end hyphens in compounds (`To-morrow`), lost accents.
2. Probe the pending OCR models (above).
3. An OCR stage in the pipeline: render page images (or take them as given),
   run tesseract + a vision LLM, merge as in the probe, carry the flags into
   the IR so the review page can show them. Page images as a book source
   (no PDF) for Teirlinck.
4. Dolittle: the text layer splits widely justified lines into fragments and
   drop caps break paragraph detection (`pdf.py` visual lines, `reflow.py`).
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
