"""Probe: does telling the OCR check's judges more make them pick right more often?

The judges (clef:27b on the crop, winnow on the line's text) are re-asked about a
book's settled, labelled suspects (`ocr_trust_data.py`) in prompt variants:

- `base`: the pipeline's questions as they are.
- `delim`: versions set off by ⟨ ⟩ rather than “ ”, which look like the quote marks
  the versions differ in.
- `style`: `delim` plus the book's typesetting (`quotes.style_note`).

Per variant and judge: picks that are right, over all suspects and over those that
differ only in typography; and right among sure picks (≥ 0.8). Answers to the new
variants are cached in work/probes/judge-prompts/<book>.jsonl.

    uv run python experiments/probe_judge_prompts.py <book> [limit]
"""

import random
import sys
from collections import Counter
from pathlib import Path

import pymupdf
from ocr_trust_data import load, suspect

from roboscriptorium import ocrcheck, quotes
from roboscriptorium.book import Book
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.roles import DecisionCache

name = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 200
book = Book.load(Path("work") / name)
settings = Settings.from_env()
rows = [r for r in load(name) if r["settled"]]
random.Random(0).shuffle(rows)
rows = rows[:limit]
for r in rows:
    r["s"] = suspect(r)

layer = cached_text_layer(book.source, book.stages / "textlayer.json")
text = " ".join(ln.text for p in layer for ln in p.lines)
single = text.count("‘") > 2 * text.count("“")
note = quotes.style_note(book.language, single, quotes.ellipsis(text), book.dash or "–")
print(f"{len(rows)} suspects; {note}")

vision = decide.for_model(settings.judge_model, settings.ollama_url)
reader = decide.for_model(settings.check_model, settings.ollama_url)
out = Path("work/probes/judge-prompts")
out.mkdir(parents=True, exist_ok=True)
probe_cache = DecisionCache(out / f"{name}.jsonl")
# The pipeline's own answers, for the questions as they are.
built = DecisionCache(book.stages / "decisions.jsonl")
lang = {"nl": "Dutch", "en": "English"}.get(book.language, "")
by_number = {p.number: p for p in layer}


def wrap(v: str, variant: str) -> str:
    return f"⟨{v}⟩" if variant != "base" else f"“{v}”"


def ask(pdf, r, variant):
    s = r["s"]
    versions = [s.ours, *s.others]
    letters = "abcdefg"[: len(versions)]
    style = f" {note}" if variant == "style" else ""
    cache = built if variant == "base" else probe_cache
    seen = ocrcheck._ask(
        vision, cache,
        {"page": s.page, "line": s.line, "readings": versions, "box": [round(v, 1) for v in s.box]},
        {"reading": decide.choice(
            "The image is cut from a scanned printed book. Which text does it show, "
            f"letter for letter, including quote marks, dashes and punctuation?{style}",
            {**{c: f"exactly {wrap(v, variant)}" for c, v in zip(letters, versions, strict=True)},
             "neither": "something else"},
        )},
        image=lambda: ocrcheck._crop(pdf[s.page - 1], s.box),
    )  # fmt: skip
    page = by_number[s.page]
    around = (
        page.lines[s.line - 1].text if s.line > 0 else "",
        page.lines[s.line + 1].text if s.line + 1 < len(page.lines) else "",
    )
    lines = [s.original[: s.start] + ocrcheck.across(v, s.joined) + s.original[s.end :] for v in versions]
    intro = "Two OCR readings" if len(lines) == 2 else "Several OCR readings"
    read = ocrcheck._ask(
        reader, cache,
        {"line before": around[0], **dict(zip(letters, lines, strict=True)), "line after": around[1]},
        {"reading": decide.choice(
            f"{intro} of the same line of a printed {lang} book differ. Which is the correct "
            f"transcription, as printed, read between the line before and the line after?{style}",
            {c: wrap(line, variant) for c, line in zip(letters, lines, strict=True)},
        )},
    )  # fmt: skip
    return [(a["value"], a["confidence"]) for a in (seen, read)], letters


tally: Counter = Counter()
with pymupdf.open(book.source) as pdf:
    for i, r in enumerate(rows):
        typo = ocrcheck._typographic([r["s"].ours, *r["s"].others])
        for variant in ("base", "delim", "style"):
            answers, letters = ask(pdf, r, variant)
            for judge, (value, conf) in zip(("clef", "winnow"), answers, strict=True):
                ok = value in letters and r["right"][letters.index(value)]
                tally[variant, judge, "right"] += ok
                tally[variant, judge, "typo"] += typo
                tally[variant, judge, "typo right"] += typo and ok
                if conf >= 0.8:
                    tally[variant, judge, "sure"] += 1
                    tally[variant, judge, "sure right"] += ok
        if (i + 1) % 25 == 0:
            print(f"  {i + 1} suspects asked", flush=True)

for judge in ("clef", "winnow"):
    for variant in ("base", "delim", "style"):
        t = lambda k: tally[variant, judge, k]  # noqa: E731
        print(
            f"{judge:6} {variant:5}  right {t('right')}/{len(rows)}  "
            f"typography {t('typo right')}/{t('typo')}  sure right {t('sure right')}/{t('sure')}"
        )
