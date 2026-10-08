"""The OCR check's suspects on golden books, each version labelled from the aligned truth.

For every suspect: its versions (the text layer's first), what each model and
reading said about each, and which version makes the line read as printed
(`golden.align`). Cached per book in work/probes/ocr-trust/<book>.json.

    uv run python experiments/ocr_trust_data.py [--rebuild] [book …]
"""

import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium import ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.corrections import Corrections, place
from roboscriptorium.disagreements import patch
from roboscriptorium.golden import notes as golden_notes
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef

SPECS = {
    "goede-dochter--ia-scan": "9-64:1-4",
    "vals-alarm--ia-scan": "11-60:1-10",
    "the-nature-of-a-crime--doubleday-1924": "",
    "the-story-of-doctor-dolittle--stokes-1920": "",
    "reis-om-mijn-schedel--ia-scan": "11-110:1-11",
    "afscheid-van-verspilde-tijd--ia-scan": "9-70:1-11",
    "metro-2033--ia-scan": "7-111:1-10",
    "de-cipier--ia-scan": "9-92:1-4",
    "artemis--ia-scan": "13-80:1-3",
    "de-tuin-van-de-avondnevel--ia-scan": "11-52:1-3",
    "grand-hotel-europa--ia-scan": "15-44:1-16",
    # No golden reference: labelled by a human's answers in the review.
    "stella": "answers",
}
OUT = Path("work/probes/ocr-trust")
_FOLD = str.maketrans("‘’“”¬–", "''\"\"-—")


def fold(text: str) -> str:
    """Text compared as typography aside: quote style, dashes, ellipses, spaced quotes."""
    text = re.sub(r"\s+", " ", text.translate(_FOLD).replace("…", "...")).strip()
    return re.sub(r"(^|\s)(['\"]+) ", r"\1\2", re.sub(r" (['\"]+)(\s|$)", r"\1\2", text))


def answered(book: Book, suspects: list) -> dict[tuple, str]:
    """Per suspect (page, line, start), the line as a human answered it: a whole line
    retyped or chosen labels every place in it; an answer about one place, only that
    place."""
    out = {}
    answers = Corrections(book.corrections_path)
    for s in suspects:
        for c in answers.by_key.values():
            if c.page != s.page or c.action != "text":
                continue
            if c.span is not None:
                if c.original == s.original and c.span == (s.start, s.end) and place(c) is not None:
                    out[(s.page, s.line, s.start)] = s.original[: s.start] + place(c) + s.original[s.end :]
            elif c.first == c.last == s.line and c.original == s.original:
                out[(s.page, s.line, s.start)] = c.text if c.text is not None else c.original
    return out


def build(name: str, spec: str) -> list[dict]:
    pages_arg, chapters = (spec.split(":") + ["", ""])[:2] if spec else ("", "")
    book = Book.load(Path("work") / name)
    # The fixed rule's choices are the baseline the trust model is scored against.
    os.environ["ROBO_OCR_TRUST"] = "0"
    stages = pipeline.run(book, pages=_range(None if spec == "answers" else pages_arg or None))
    if spec == "answers":
        return rows_from(stages.suspects, answered(book, stages.suspects))
    golden = Golden.load(book.golden)
    reference = load_chapters(golden.text_dir)
    if span := _range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = patch(reference, _verdicts(book))
    truth = align(stages.pages, reference)
    in_notes = golden_notes.note_lines(stages.pages, golden_notes.load(golden.notes_path))
    lines = {
        (s.page, s.line, s.start): t.truth
        for s in stages.suspects
        if (t := truth.get(SourceRef(s.page, s.line))) is not None
        and t.role == "body"
        and SourceRef(s.page, s.line) not in in_notes
    }
    return rows_from(stages.suspects, lines)


def rows_from(suspects: list, truths: dict[tuple, str]) -> list[dict]:
    """Each suspect with a true line, its versions labelled by which comes closest to it."""
    rows = []
    for s in suspects:
        if (truth := truths.get((s.page, s.line, s.start))) is None:
            continue
        versions = [s.ours, *s.others]
        lines = [s.original[: s.start] + v + s.original[s.end :] for v in versions]
        distance = [Levenshtein.distance(fold(line), fold(truth)) for line in lines]
        best = min(distance)
        right = [d == best for d in distance]
        rows.append(
            {
                "suspect": asdict(s),
                "truth": truth,
                "right": right,
                "settled": right.count(True) == 1 and best <= max(2, len(s.ours) // 3),
            }
        )
    return rows


def suspect(row: dict) -> ocrcheck.Suspect:
    d = dict(row["suspect"])
    d["others"], d["box"], d["known"] = tuple(d["others"]), tuple(d["box"]), tuple(d["known"])
    d["support"] = {k: tuple(v) for k, v in d["support"].items()}
    return ocrcheck.Suspect(**d)


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
        wrong = sum(not r["right"][0] for r in settled)  # the text layer's version
        print(f"{name[:34]:34} {len(rows):4} suspects, {len(settled):4} settled, "
              f"layer wrong on {wrong}", flush=True)  # fmt: skip
