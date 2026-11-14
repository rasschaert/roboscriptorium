"""The OCR check's suspects on golden books, each version labelled from the aligned truth.

For every suspect: its versions (the text layer's first), what each model and
reading said about each, and which version makes the line read as printed
(`golden.align`). Cached per book in work/probes/ocr-trust/<book>.json
(`ROBO_TRUST_DATA` for another folder). Built by `experiments/ocr_trust_data.py`,
trained on by `experiments/train_ocr_trust.py` (`save`).
"""

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

from roboscriptorium import bench, corrections, errata, ocrcheck, pipeline, trust
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections
from roboscriptorium.disagreements import patch
from roboscriptorium.files import write_atomic
from roboscriptorium.golden import notes as golden_notes
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import Chapter, load_chapters
from roboscriptorium.ir import SourceRef
from roboscriptorium.trust import fold, rows_from  # noqa: F401 - read by the experiments

# The books and slices the trust data is built from, apart from the bench's sets: some
# slices are longer or whole, and validation books have data the trainer never trains
# on (`trainable`). A tuning book left out is in `bench.NO_TRUST_DATA`.
SPECS = {
    "goede-dochter--ia-scan": "",
    "vals-alarm--ia-scan": "",
    # Trained on, never scored: without it the arbiter left more errors unasked.
    "the-nature-of-a-crime--doubleday-1924": "",
    "the-story-of-doctor-dolittle--stokes-1920": "",
    "reis-om-mijn-schedel--ia-scan": "",
    "afscheid-van-verspilde-tijd--ia-scan": "",
    "metro-2033--ia-scan": "",
    "de-cipier--ia-scan": "",
    "artemis--ia-scan": "",
    "de-tuin-van-de-avondnevel--ia-scan": "",
    "de-eerlijke-vinder--ia-scan": "",
    "youre-never-weird-on-the-internet--ia-scan": "13-26:1-2",
    "the-thief-takers-apprentice--ia-scan": "",
    "het-heft-in-eigen-hand--ia-scan": "",
    "doodskleed--ia-scan": "",
    "het-ijzige-land--ia-scan": "",
    "de-kerk-van-de-dode-meisjes--ia-scan": "11-27:1-3",
    "vuurspel--ia-scan": "9-29:1-2",
    "monterosso-mon-amour--ia-scan": "",
    "het-geluid-van-bananen--ia-scan": "",
    "het-schaduwhuis--ia-scan": "9-328:1-91",
    # No golden reference: labelled by a human's answers in the review.
    "stella": "answers",
    "ex-minnaar": "answers",
}
# ROBO_TRUST_DATA keeps an ablation's data apart (another reader set, say).
OUT = Path(os.environ.get("ROBO_TRUST_DATA", "work/probes/ocr-trust"))


def answered(book: Book, suspects: list) -> dict[tuple, str]:
    """Per suspect (page, line, start), the line as the book's reviewer answered it."""
    return corrections.answered(Corrections(book.corrections_path), suspects)


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
    truth = align(stages.pages, as_printed(reference, errata.load(book.root)))
    in_notes = golden_notes.note_lines(stages.pages, golden_notes.load(golden.notes_path))
    lines = {
        (s.page, s.line, s.start): t.truth
        for s in stages.suspects
        if (t := truth.get(SourceRef(s.page, s.line))) is not None
        and t.role == "body"
        and SourceRef(s.page, s.line) not in in_notes
    }
    return rows_from(stages.suspects, lines)


def as_printed(reference: list[Chapter], found: list[errata.Erratum]) -> list[Chapter]:
    """The reference with each erratum's corrected words set back as printed: the readers
    are labelled on what the page prints, the build's text on what the edition reads.
    An erratum whose corrected words the reference holds other than once is left out."""
    chapters = [replace(c, paragraphs=list(c.paragraphs), italic=list(c.italic)) for c in reference]
    for e in found:
        reads = e.reads.translate(errata.FOLD)
        at = [
            (c, p, k)
            for c, ch in enumerate(chapters)
            for p, para in enumerate(ch.paragraphs)
            for k in _starts(para.translate(errata.FOLD), reads)
        ]
        if len(at) != 1:
            continue
        c, p, k = at[0]
        para, ch = chapters[c].paragraphs[p], chapters[c]
        changed = para[:k] + e.printed + para[k + len(reads) :]
        ch.paragraphs[p] = changed
        if p < len(ch.italic) and (shift := len(changed.split()) - len(para.split())):
            word = len(para[:k].split())
            ch.italic[p] = frozenset(i + shift if i > word else i for i in ch.italic[p])
    return chapters


def _starts(text: str, part: str) -> list[int]:
    found, k = [], text.find(part)
    while k >= 0:
        found.append(k)
        k = text.find(part, k + 1)
    return found


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


# Never trained on: the validation books and those awaiting their first look.
HELD_OUT = {spec.split("--")[0] for spec in [*bench.SETS["validation"], *bench.FIRST_LOOK]}


def judges(settings: Settings) -> set[str]:
    """The judges a build with these settings asks: votes of any other model in the data
    (an alarm tried and left off) would train the arbiter on a vote it never gets."""
    models = {settings.judge_model, settings.check_model, *settings.alarm_models}
    return (models | {"word list"}) - {""}


def seats(settings: Settings) -> int:
    """The judge seats an arbiter for these settings reads: the vision and text judges
    and each second vision judge, at least `trust.SEATS`."""
    return max(trust.SEATS, 2 + len(settings.alarm_models))


def readings(settings: Settings) -> set[str]:
    """Every reading the OCR check makes with these settings; data built before one of
    them lacks its support."""
    pages = set(trust.PAGE_READINGS) if settings.page_readers else set()
    return {"glm", "tess"} | ({"qwen"} if settings.read_model else set()) | pages


def weighed(settings: Settings) -> tuple[str, ...]:
    """The readings an arbiter trained with these settings weighs, in feature order."""
    return trust.READINGS + (trust.PAGE_READINGS if settings.page_readers else ())


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
    # Data without one of these settings' judges would train its slot on nothing. A judge
    # asked only where the vision judge was unsure (`alarm_below`) is among a suspect's
    # judges without a vote on the others.
    asked = judges(settings) - {"word list"}
    if any(
        not asked <= set(r["suspect"]["votes"]) | set(r["suspect"].get("judges", ())) for r in rows
    ):
        return "built without one of the current judges"
    return ""


def trainable(name: str) -> bool:
    return name.split("--")[0] not in HELD_OUT


def staging(path: Path) -> Path:
    """Where a training run keeps its finished models until all are done."""
    return path.with_name(f"{path.name}.training")


def models_to_save(
    books: dict[str, list[dict]],
    path: Path,
    score,
    readings: tuple[str, ...] = trust.READINGS,
    seats: int = trust.SEATS,
    key: str = "",
) -> list[tuple]:
    """The arbiter the pipeline uses, trained on every trainable book (the books labelled
    by a reviewer's answers too), and a copy without each tuning book, which `bench`
    scores that book with: (path, model, suspects trained on, book left out). Each one's
    sureness is calibrated on its training books, each scored by `score(names, rows)`
    trained on the others, as a new book is scored.

    None is written to its place here, so an interrupted run leaves no mix of old and
    new; each is kept as it finishes in `staging(path)`, and a run started again on
    the same data, readings, seats and `key` (whatever else decides the training: the
    caller's settings) takes those up instead of training them again."""
    tuning = [n for n in books if trainable(n) and SPECS.get(n) != "answers"]
    held = staging(path)
    made_of = hashlib.sha256(
        repr((trust.MODEL_VERSION, readings, seats, key, sorted(books.items()))).encode()
    ).hexdigest()
    note = held / "made-of.txt"
    if not (note.exists() and note.read_text() == made_of):
        # Another training's leftovers: models of other data are not these models.
        for old in held.glob("*.pkl") if held.is_dir() else ():
            old.unlink()
        held.mkdir(parents=True, exist_ok=True)
        write_atomic(note, made_of)
    out = []
    for without in [None, *tuning]:
        names = [n for n in books if n != without and trainable(n)]
        every = [r for name in names for r in books[name]]
        target = trust.without(path, without) if without else path
        kept = held / target.name
        model = trust.load(kept) if kept.exists() else None
        if model is None:
            model = trust.train(
                [r["s"] for r in every],
                [r["right"] for r in every],
                [r["book"] for r in every],
                readings,
                seats,
            )
            sure, hit = [], []
            for left in names:
                rows = books[left]
                scores = score([n for n in names if n != left], rows)
                for r, ps in zip(rows, scores, strict=True):
                    sure.append(float(ps.max()))
                    hit.append(bool(r["right"][int(ps.argmax())]))
            model.calibration = trust.calibrate(sure, hit)
            trust.save(model, kept)
        out.append((target, model, len(every), without))
    return out


def save_models(models: list[tuple], path: Path) -> None:
    """`models_to_save`'s models written to their places, then the staging emptied."""
    for target, model, _, _ in models:
        trust.save(model, target)
    held = staging(path)
    for done in [held / target.name for target, *_ in models] + [held / "made-of.txt"]:
        done.unlink(missing_ok=True)
    if held.is_dir() and not any(held.iterdir()):
        held.rmdir()
