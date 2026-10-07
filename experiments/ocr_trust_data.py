"""The OCR check's suspects on golden books, each version labelled from the aligned truth.

For every suspect: its versions (the text layer's first), what each model and
reading said about each, and which version makes the line read as printed
(`golden.align`). Cached per book in work/probes/ocr-trust/<book>.json.

    uv run python experiments/ocr_trust_data.py [--rebuild] [book …]
"""

import json
import re
import sys
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium import ocr, ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.config import Settings
from roboscriptorium.disagreements import patch
from roboscriptorium.golden import notes as golden_notes
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef
from roboscriptorium.lexicon import Lexicon

SPECS = {
    "goede-dochter--ia-scan": "9-64:1-4",
    "vals-alarm--ia-scan": "11-60:1-10",
    "the-nature-of-a-crime--doubleday-1924": "",
    "the-story-of-doctor-dolittle--stokes-1920": "",
    "reis-om-mijn-schedel--ia-scan": "",
    "lady-into-fox--chatto-1922": "",
    "de-tuin-van-de-avondnevel--ia-scan": "11-52:1-3",
    "grand-hotel-europa--ia-scan": "15-44:1-16",
}
OUT = Path("work/probes/ocr-trust")
_FOLD = str.maketrans("‘’“”¬–", "''\"\"-—")


def fold(text: str) -> str:
    """Text compared as typography aside: quote style, dashes, ellipses, spaced quotes."""
    text = re.sub(r"\s+", " ", text.translate(_FOLD).replace("…", "...")).strip()
    return re.sub(r"(^|\s)(['\"]+) ", r"\1\2", re.sub(r" (['\"]+)(\s|$)", r"\1\2", text))


def build(name: str, spec: str) -> list[dict]:
    pages_arg, chapters = (spec.split(":") + ["", ""])[:2] if spec else ("", "")
    book = Book.load(Path("work") / name)
    stages = pipeline.run(book, pages=_range(pages_arg or None))
    golden = Golden.load(book.golden)
    reference = load_chapters(golden.text_dir)
    if span := _range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = patch(reference, _verdicts(book))
    truth = align(stages.pages, reference)
    in_notes = golden_notes.note_lines(stages.pages, golden_notes.load(golden.notes_path))

    settings = Settings.from_env()
    lang = ocr.language(book.language)
    checked = {SourceRef(s.page, s.line) for s in stages.suspects}
    glm = ocrcheck.line_readings(
        book.source, stages.pages, checked, settings.ocr_model, settings.ollama_url,
        book.stages / "second-reading.json",
    )  # fmt: skip
    tess = ocrcheck.tesseract_readings(
        book.source, stages.pages, checked, lang, book.stages / "tesseract.json"
    )
    words = Lexicon.load(lang)

    rows = []
    for s in stages.suspects:
        ref = SourceRef(s.page, s.line)
        t = truth.get(ref)
        if t is None or t.role != "body" or ref in in_notes:
            continue
        versions = [s.ours, *s.others]
        lines = [s.original[: s.start] + v + s.original[s.end :] for v in versions]
        distance = [Levenshtein.distance(fold(line), fold(t.truth)) for line in lines]
        best = min(distance)
        right = [d == best for d in distance]
        supports = {}
        for label, reading in (("glm", glm.get(ref, "")), ("tess", tess.get(ref, ""))):
            found = ocrcheck.merged_differences(s.original, [reading]) if reading else []
            mine = [v for a0, a1, vs in found if a0 < s.end and s.start < a1 for v in vs]
            supports[label] = [v in mine or (k == 0 and reading and not mine)
                               for k, v in enumerate(versions)]  # fmt: skip
        rows.append(
            {
                "page": s.page,
                "line": s.line,
                "original": s.original,
                "truth": t.truth,
                "versions": versions,
                "right": right,
                "settled": right.count(True) == 1 and best <= max(2, len(s.ours) // 3),
                "choice": s.choice,
                "chosen": s.chosen,
                "votes": s.votes,
                "confidence": s.confidence,
                "glm": supports["glm"],
                "tess": supports["tess"],
                "known": [words._judge(v, False) for v in versions],
                "typographic": ocrcheck._typographic(versions),
            }
        )
    return rows


def load(name: str, rebuild: bool = False) -> list[dict]:
    path = OUT / f"{name}.json"
    if path.exists() and not rebuild:
        return json.loads(path.read_text())
    rows = build(name, SPECS[name])
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False))
    return rows


if __name__ == "__main__":
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(SPECS)
    for name in names:
        rows = load(name, "--rebuild" in sys.argv)
        settled = [r for r in rows if r["settled"]]
        wrong = sum(not r["right"][0] for r in settled)
        print(f"{name[:34]:34} {len(rows):4} suspects, {len(settled):4} settled, "
              f"layer wrong on {wrong}", flush=True)  # fmt: skip
