"""The OCR check's suspects on golden books, each version labelled from the aligned truth.

For every suspect: its versions (the text layer's first), what each model and
reading said about each, and which version makes the line read as printed
(`golden.align`). Cached per book in work/probes/ocr-trust/<book>.json
(`ROBO_TRUST_DATA` for another folder). Built by `experiments/ocr_trust_data.py`,
trained on by `experiments/train_ocr_trust.py` (`save`).
"""

import json
import os
from dataclasses import asdict, replace
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench, ocrcheck, pipeline, trust
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections, place
from roboscriptorium.disagreements import patch
from roboscriptorium.evaluate import normalise
from roboscriptorium.files import write_atomic
from roboscriptorium.golden import notes as golden_notes
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef
from roboscriptorium.reflow import _SPACE_BEFORE_PUNCTUATION

# The books and slices the trust data is built from, apart from the bench's sets: some
# slices are longer or whole, and validation books have data the trainer never trains
# on (`trainable`). A tuning book left out is in `bench.NO_TRUST_DATA`.
SPECS = {
    "goede-dochter--ia-scan": "9-99:1-6",
    "vals-alarm--ia-scan": "11-60:1-10",
    "the-nature-of-a-crime--doubleday-1924": "",
    "the-story-of-doctor-dolittle--stokes-1920": "",
    "reis-om-mijn-schedel--ia-scan": "11-99:1-10",
    "afscheid-van-verspilde-tijd--ia-scan": "9-70:1-11",
    "metro-2033--ia-scan": "7-92:1-8",
    "de-cipier--ia-scan": "9-33:1-2",
    "artemis--ia-scan": "13-34:1-1",
    "de-tuin-van-de-avondnevel--ia-scan": "11-29:1-1",
    "de-eerlijke-vinder--ia-scan": "",
    "youre-never-weird-on-the-internet--ia-scan": "13-26:1-2",
    "the-thief-takers-apprentice--ia-scan": "11-26:1-6",
    "het-heft-in-eigen-hand--ia-scan": "9-33:1-2",
    "doodskleed--ia-scan": "13-22:1-2",
    "het-ijzige-land--ia-scan": "11-21:1-1",
    "de-kerk-van-de-dode-meisjes--ia-scan": "11-27:1-3",
    "vuurspel--ia-scan": "9-29:1-2",
    "monterosso-mon-amour--ia-scan": "",
    # No golden reference: labelled by a human's answers in the review.
    "stella": "answers",
}
# ROBO_TRUST_DATA keeps an ablation's data apart (another reader set, say).
OUT = Path(os.environ.get("ROBO_TRUST_DATA", "work/probes/ocr-trust"))


def fold(text: str) -> str:
    """Text compared as the score compares it (`evaluate.normalise`: quote and dash
    glyphs, ellipses, spaced dots), with what reflow sets anyway folded too: a break
    hyphen, spaces before punctuation. A space beside a quote mark stays: no stage
    removes it, so the score counts it ("geweest. ‘" is not "geweest.’")."""
    return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", normalise(text.replace("¬", "-")))


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
                    out[(s.page, s.line, s.start)] = (
                        s.original[: s.start] + place(c) + s.original[s.end :]
                    )
            elif c.first == c.last == s.line and c.original == s.original:
                out[(s.page, s.line, s.start)] = c.text if c.text is not None else c.original
    return out


def build(name: str, spec: str) -> list[dict]:
    pages_arg, chapters = (spec.split(":") + ["", ""])[:2] if spec else ("", "")
    book = Book.load(Path("work") / name)
    # The fixed rule's choices are the baseline the trust model is scored against.
    settings = replace(Settings.from_env(), ocr_trust=False)
    pages = scoring.page_range(None if spec == "answers" else pages_arg or None)
    stages = pipeline.run(book, pages=pages, settings=settings)
    if spec == "answers":
        return rows_from(stages.suspects, answered(book, stages.suspects))
    golden = Golden.load(book.golden)
    reference = load_chapters(golden.text_dir)
    if span := scoring.page_range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = patch(reference, scoring.verdicts(book))
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
    write_atomic(path, json.dumps(rows, ensure_ascii=False))
    return rows


# Never trained on: the validation and test books.
HELD_OUT = {spec.split("--")[0] for spec in bench.SETS["validation"] + bench.SETS["test"]}


def judges(settings: Settings) -> set[str]:
    """The judges a build with these settings asks: votes of any other model in the data
    (an alarm tried and left off) would train the arbiter on a vote it never gets."""
    models = {settings.judge_model, settings.check_model, settings.alarm_model}
    return (models | {"word list"}) - {""}


def readings(settings: Settings) -> set[str]:
    """Every reading the OCR check makes with these settings; data built before one of
    them lacks its support."""
    return {"glm", "tess"} | ({"qwen"} if settings.read_model else set())


def rows_of(name: str, settings: Settings) -> list[dict]:
    """A book's settled rows, each with its suspect (`s`) as these settings' judges saw
    it, and its book."""
    keep = judges(settings)
    rows = [r for r in load(name) if r["settled"]]
    for r in rows:
        s = suspect(r)
        r["s"] = replace(
            s,
            votes={m: v for m, v in s.votes.items() if m in keep},
            judges=tuple(m for m in s.judges if m in keep),
            confidence={m: c for m, c in s.confidence.items() if m in keep},
        )
        r["book"] = name
    return rows


def usable(name: str, settings: Settings) -> str:
    """Why a book's data can't be used, or "" when it can."""
    if not (OUT / f"{name}.json").exists():
        return "no data yet"
    rows = load(name)
    if any(not readings(settings) <= set(r["suspect"]["support"]) for r in rows):
        return "built before the current readings"
    # Data without one of these settings' judges would train its slot on nothing.
    asked = judges(settings) - {"word list"}
    if any(not asked <= set(r["suspect"]["votes"]) for r in rows):
        return "built without one of the current judges"
    return ""


def trainable(name: str) -> bool:
    return name.split("--")[0] not in HELD_OUT


def models_to_save(books: dict[str, list[dict]], path: Path, score) -> list[tuple]:
    """The arbiter the pipeline uses, trained on every trainable book but Stella, and a
    copy without each tuning book, which `bench` scores that book with: (path, model,
    suspects trained on, book left out). Each one's sureness is calibrated on its
    training books, each scored by `score(names, rows)` trained on the others, as a new
    book is scored. All are trained before any is written, so an interrupted run leaves
    no mix of old and new."""
    tuning = [n for n in books if trainable(n) and n != "stella"]
    out = []
    for without in [None, *tuning]:
        names = [n for n in books if n != without and trainable(n)]
        every = [r for name in names for r in books[name]]
        model = trust.train(
            [r["s"] for r in every], [r["right"] for r in every], [r["book"] for r in every]
        )
        sure, hit = [], []
        for held in names:
            rows = books[held]
            for r, ps in zip(rows, score([n for n in names if n != held], rows), strict=True):
                sure.append(float(ps.max()))
                hit.append(bool(r["right"][int(ps.argmax())]))
        model.calibration = trust.calibrate(sure, hit)
        out.append((trust.without(path, without) if without else path, model, len(every), without))
    return out
