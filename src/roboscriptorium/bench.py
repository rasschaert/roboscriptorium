"""A fixed benchmark: the same golden slices every time, recorded whole, compared paired.

Each run scores every book of a set (`SETS`) with `evaluate.score` and `quality`, the
question ranking learned from the other books of the same set, and writes one JSON
under `work/bench/` with the commit, the settings, the OCR check's decider, the model
versions and, per book, the per-page counts. Two runs are compared page by page: a
change counts only when the 95% bootstrap interval of the paired difference in mean
per-page counts excludes zero. Rerunning with warm caches repeats itself; pages are
the noise worth measuring.
"""

import json
import os
import random
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from roboscriptorium import disagreements, errorlog, evaluate, italics, quality, sorter, trust
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring, signals

OUT = Path("work/bench")
BOOTSTRAP_SAMPLES = 2000

# Golden scans and the pages:chapters scored. Tuning books are tuned on, and scored
# with models trained without them (`unseen`); validation books have been consulted
# for choices before, so they validate, not test. Long books are sliced at a chapter
# boundary (a run costs about 0.9 min per cold page), about 120 to 270 pages: the
# bootstrap's power comes from the pages in all, so more books of fewer pages decide as
# surely and vary more. Monterosso runs its chapters on without a page break, so no slice
# short of the whole book ends on one. Dolittle's slice holds its plates and drawn
# initials. A new pair waits in "first-look" for one untouched score (`bench first-look
# --first-look`): nothing is chosen on it and no model trains on it before, and the CLI
# refuses to score it without `--first-look`; then it joins tuning or validation.
# Verminkt's reference has no chapters, so its look is the whole book.
SETS = {
    "tuning": [
        "goede-dochter--ia-scan:9-278:1-13",
        "vals-alarm--ia-scan:11-188:1-31",
        "reis-om-mijn-schedel--ia-scan:11-182:1-19",
        "the-story-of-doctor-dolittle--stokes-1920:23-146:1-14",
        "the-thief-takers-apprentice--ia-scan:11-165:1-48",
        "afscheid-van-verspilde-tijd--ia-scan:9-122:1-22",
        "metro-2033--ia-scan:7-263:1-22",
        "de-cipier--ia-scan:9-252:1-8",
        "artemis--ia-scan:13-251:1-13",
        "de-tuin-van-de-avondnevel--ia-scan:11-254:1-16",
        "het-heft-in-eigen-hand--ia-scan:9-253:1-11",
        "doodskleed--ia-scan:13-264:1-41",
        "het-ijzige-land--ia-scan:11-266:1-30",
        "de-eerlijke-vinder--ia-scan",
        "monterosso-mon-amour--ia-scan",
        "het-geluid-van-bananen--ia-scan:9-264:1-31",
        "het-schaduwhuis--ia-scan:9-254:1-68",
        "au-pair--ia-scan:7-230:1-44",
        "de-vergelding--ia-scan:9-253:1-10",
        "glazuur--ia-scan:11-177:1-16",
    ],
    "validation": [
        "de-kerk-van-de-dode-meisjes--ia-scan:11-107:1-13",
        "vuurspel--ia-scan:9-111:1-6",
        "youre-never-weird-on-the-internet--ia-scan:13-94:1-16",
        "de-stilte-van-de-hel--ia-scan:11-101:1-15",
        "het-laatste-bevel--ia-scan:9-100:1-5",
        "the-strangers-child--ia-scan:121-208:15-23",
        "normal-people--ia-scan:146-232:23-31",
        "verminkt--ia-scan:7-100",
        "de-geruchten--ia-scan:9-97:2-22",
        "vanille-en-andere-smaken--dbnl-scan:9-79:1-16",
    ],
    "first-look": [],
    # The quick tier, for a change's short test: a chapter or two of each tuning book
    # (a later one where the first are front matter or a single short one), ending where
    # the next opens a page; Monterosso's chapters run on, so it has no such end.
    "quick": [
        "goede-dochter--ia-scan:51-64:4-4",
        "vals-alarm--ia-scan:11-25:1-4",
        "reis-om-mijn-schedel--ia-scan:11-29:1-3",
        "the-story-of-doctor-dolittle--stokes-1920:23-40:1-2",
        "the-thief-takers-apprentice--ia-scan:11-26:1-6",
        "afscheid-van-verspilde-tijd--ia-scan:9-20:1-2",
        "metro-2033--ia-scan:7-29:1-2",
        "de-cipier--ia-scan:9-33:1-2",
        "artemis--ia-scan:13-34:1-1",
        "de-tuin-van-de-avondnevel--ia-scan:11-29:1-1",
        "het-heft-in-eigen-hand--ia-scan:9-33:1-2",
        "doodskleed--ia-scan:13-22:1-2",
        "het-ijzige-land--ia-scan:11-21:1-1",
        "de-eerlijke-vinder--ia-scan:59-76:3-3",
        "het-geluid-van-bananen--ia-scan:22-34:7-7",
        "het-schaduwhuis--ia-scan:11-19:2-3",
    ],
}
# Pairs held back: guarded like the first-look set, so nothing scores or trains on them by
# accident, and in no run. Na die nacht is a sibling of two tuning books, so its first look
# would be flattered; it is kept as a training candidate.
RESERVE = [
    "na-die-nacht--ia-scan",
]
FIRST_LOOK = frozenset(spec.split(":")[0] for spec in SETS["first-look"] + RESERVE)
# Tuning books with no trust data (`trustdata.SPECS` lacks them, a test checks):
# the trust model never trains on them, so they are scored with the full model.
NO_TRUST_DATA: frozenset[str] = frozenset(
    {"au-pair--ia-scan", "de-vergelding--ia-scan", "glazuur--ia-scan"}
)
TRAINED_ON = frozenset(spec.split(":")[0] for spec in SETS["tuning"]) - NO_TRUST_DATA
# The line-role model trains on every tuning book (`experiments/train_sorter.py`).
SORTER_TRAINED_ON = frozenset(spec.split(":")[0] for spec in SETS["tuning"])

# Per-page counts compared between runs: (name, index into a page's counts). "After
# review" is the unasked plus, per question, the reviewer's expected slips and the cost
# of the reviewer's time (`quality.QUESTION_COST`), at the mean slip rate and at either
# end of its interval. A comparison computes it from the unasked and the questions, not
# from the figure a run saved, so runs saved under another cost or slip rate compare.
PAIRED = (
    ("wrong words", 0),
    ("unasked", 1),
    ("questions", 2),
    ("after review", 3),
    ("after review, few slips", 4),
    ("after review, many slips", 5),
    ("paragraph breaks", 6),
    ("typography", 7),
)
# The one test that decides a change: "after review" over the set, each book weighing
# the same, at each slip rate.
PRIMARY = ("after review", "after review, few slips", "after review, many slips")
# A book vetoes a change when its "after review", or its paragraph breaks set wrong, get
# worse by at least VETO_MIN per page on the mean and its 99% interval of the difference
# lies above zero. Eleven tuning books at 95% would veto about one change in four that
# leaves them all as they were; at 99%, about one in nineteen.
VETO_LEVEL = 0.99
VETO_MIN = 0.05


@dataclass(frozen=True)
class Change:
    book: str
    measure: str
    before: float  # mean per page
    after: float
    low: float  # 95% bootstrap interval of the paired difference
    high: float

    @property
    def real(self) -> bool:
        return self.low > 0 or self.high < 0


def unseen(settings: Settings, book: str) -> Settings:
    """The settings to score `book` with: each learned model's copy trained without it,
    so a tuning book isn't scored by a model that saw its labels.

    The trust model trains on the tuning books with trust data (`TRAINED_ON`,
    `train_ocr_trust.py --save`), so one of them without its copy is refused; any other
    book is scored with the full model."""
    if settings.sorter:
        copy = sorter.without(Path(settings.sorter_model), book)
        if copy.exists():
            settings = replace(settings, sorter_model=str(copy))
        elif book in SORTER_TRAINED_ON:
            raise FileNotFoundError(
                f"{copy} is missing: {book} is a tuning book, which the line-role model "
                "trains on (experiments/train_sorter.py --save writes it)"
            )
    if settings.italic_trees:
        copy = italics.without(Path(settings.italic_model), book)
        if copy.exists():
            settings = replace(settings, italic_model=str(copy))
        elif book in SORTER_TRAINED_ON:
            raise FileNotFoundError(
                f"{copy} is missing: {book} is a tuning book, which the italic model "
                "trains on (experiments/italic_words.py --save writes it)"
            )
    if not settings.ocr_trust:
        return settings
    path = trust.without(Path(settings.ocr_trust_model), book)
    if path.exists():
        return replace(settings, ocr_trust_model=str(path))
    if book in TRAINED_ON:
        raise FileNotFoundError(
            f"{path} is missing: {book} is a tuning book, which the trust model trains on "
            "(experiments/train_ocr_trust.py --save writes it)"
        )
    return settings


def run(
    set_name: str,
    settings: Settings,
    commit: str,
    model_versions: dict[str, str],
    on_book: Callable[[str], None] = lambda spec: None,
) -> dict:
    """Build and score every slice of a set, each with the learned models trained
    without it (`unseen`): the record `save` writes and `verdict` compares. A book's
    questions are ranked by how often each kind caught an error in the set's other
    books."""
    specs = SETS[set_name]
    done: dict[str, tuple[str, scoring.Scored, Settings]] = {}
    if (n := min(workers(), len(specs))) <= 1:
        for spec in specs:
            on_book(spec)
            done[spec] = _build_one(spec, settings)
    else:
        # Each book in its own process: the books are independent until their questions
        # are ranked below, and PyMuPDF can't be shared between threads.
        with ProcessPoolExecutor(n) as pool:
            futures = {pool.submit(_build_one, spec, settings): spec for spec in specs}
            for future in as_completed(futures):
                on_book(futures[future])
                done[futures[future]] = future.result()
    built = [done[spec] for spec in specs]
    books = {}
    for spec, run, own in built:
        rates: dict[str, tuple[int, int]] = {}
        for _, other, _ in built:
            if other.name != run.name:
                for r, (h, n) in quality.hit_rates(other.found, other.errors).items():
                    h0, n0 = rates.get(r, (0, 0))
                    rates[r] = (h0 + h, n0 + n)
        books[run.name] = _book_record(spec, run, own, rates)
    return {
        "set": set_name,
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit,
        "settings": {k: v for k, v in asdict(settings).items() if not k.endswith("_url")},
        "model_versions": model_versions,
        "books": books,
    }


def workers() -> int:
    """How many books `run` scores at once: `ROBO_BENCH_WORKERS`, else one fewer than the
    machine's cores. Not a setting of the build, so not in `Settings` or a run's record."""
    if value := os.environ.get("ROBO_BENCH_WORKERS"):
        return max(1, int(value))
    return max(1, (os.cpu_count() or 2) - 1)


def _build_one(spec: str, settings: Settings) -> tuple[str, scoring.Scored, Settings]:
    """One slice built and scored with the learned models trained without it."""
    own = unseen(settings, spec.split(":")[0])
    return spec, scoring.build(f"work/{spec}", own), own


def _book_record(
    spec: str, run: scoring.Scored, own: Settings, rates: dict[str, tuple[int, int]]
) -> dict:
    book, stages, reference, errors, found = (
        run.book,
        run.stages,
        run.reference,
        run.errors,
        run.found,
    )
    numbers = [p.number for p in stages.pages if p.lines]
    body = (
        None
        if stages.model_roles is None
        else {r for r, role in stages.model_roles.items() if role.role == "body"}
    )
    scored = scoring.scored(book, stages)
    score = evaluate.score(scored, reference)
    kinds = disagreements.glyph_kinds(reference)
    return {
        "spec": spec,
        "pair": asdict(signals.measure(stages.pages, reference, body)),
        "ocr_decider": stages.ocr_decider,
        "ocr_trust_model": own.ocr_trust_model,
        "ocr_suspects": dict(Counter(s.choice for s in stages.suspects)),
        "read_via": scoring.read_via(book, {p.number for p in stages.pages}),
        "italics_scored": not scoring.italics_unlike(book),
        "breaks_scored": not scoring.breaks_unlike(book),
        "verdicts_applied": run.applied,
        "score": {k: v for k, v in asdict(score).items() if k != "confusions"},
        "quality": {k: asdict(v) for k, v in quality.report(numbers, errors, found, rates).items()},
        "unasked_by_kind": quality.unasked_by_category(errors, found),
        "typography_kinds": sorted(kinds),
        # Written beside the record by `save`, not into it: the rows quote the book.
        "_errors": (rows := errorlog.rows(run.name, errors, found, stages.pages, stages.suspects)),
        # Wrong words by cause (`errorlog.cause`), for trends over runs.
        "causes": dict(Counter(r["cause"] for r in rows for _ in range(r["size"]))),
        "pages": page_counts(
            numbers,
            errors,
            found,
            breaks=()
            if scoring.breaks_unlike(book)
            else disagreements.break_errors(scored, reference, stages.pages),
            glyphs=disagreements.glyph_errors(scored, reference, stages.pages, kinds),
        ),
    }


def page_counts(
    pages: list[int],
    errors,
    found,
    slips: tuple[float, float, float] | None = None,
    breaks: list[int] = (),
    glyphs: list[int] = (),
) -> dict[int, list[float]]:
    """Per page: wrong words, wrong words no question catches, questions, wrong words
    after the reviewer answers every question (`after_review`) at the mean slip rate, the
    low end and the high end (`quality.slip_rates`), paragraph breaks set wrong
    (`disagreements.break_errors`, no question asks about them), and words whose quote
    marks, dashes or ellipsis are set wrong (`disagreements.glyph_errors`)."""
    rates = slips or quality.slip_rates()
    counts = quality.per_page(pages, errors, found)
    wrong, glyph = Counter(breaks), Counter(glyphs)
    return {
        p: [
            w,
            u,
            q,
            *(after_review(u, q, rate) for rate in (rates[1], rates[0], rates[2])),
            wrong[p],
            glyph[p],
        ]
        for p, (w, u, q) in counts.items()
    }


def after_review(unasked: float, questions: float, slip: float) -> float:
    """Wrong words a page once every question is answered: the unasked, the answers
    expected wrong, and the reviewer's time, each question at `quality.QUESTION_COST`."""
    return unasked + (slip + quality.QUESTION_COST) * questions


def paired(
    pairs: list[tuple[float, float]], seed: int = 0, level: float = 0.95
) -> tuple[float, float, float, float]:
    """Mean per page before and after, and the bootstrap interval of the mean
    difference, from each page's (before, after)."""
    return pooled([pairs], seed, level)


def pooled(
    books: list[list[tuple[float, float]]], seed: int = 0, level: float = 0.95
) -> tuple[float, float, float, float]:
    """Per-page means before and after, averaged over books so each weighs the same,
    and the bootstrap interval of that difference (pages resampled within each book)."""
    books = [b for b in books if b]
    if not books:
        return 0.0, 0.0, 0.0, 0.0
    rng = random.Random(seed)
    diffs = [[a - b for b, a in pairs] for pairs in books]
    means = sorted(
        sum(sum(rng.choices(d, k=len(d))) / len(d) for d in diffs) / len(diffs)
        for _ in range(BOOTSTRAP_SAMPLES)
    )
    tail = (1 - level) / 2
    return (
        sum(sum(b for b, _ in pairs) / len(pairs) for pairs in books) / len(books),
        sum(sum(a for _, a in pairs) / len(pairs) for pairs in books) / len(books),
        means[int(tail * BOOTSTRAP_SAMPLES)],
        means[int((1 - tail) * BOOTSTRAP_SAMPLES) - 1],
    )


def _pairs(
    old: dict, new: dict, i: int, books: list[str], slips: tuple[float, float, float] | None = None
) -> list[tuple[float, float]]:
    """Each page's (before, after) of the measure at `i` in `PAIRED`; the after-review
    measures computed from the unasked and the questions."""
    rates = slips or quality.slip_rates()
    after = {3: rates[1], 4: rates[0], 5: rates[2]}

    def value(row: list[float]) -> float:
        return after_review(row[1], row[2], after[i]) if i in after else row[i]

    out = []
    for name in books:
        before, later = old["books"][name]["pages"], new["books"][name]["pages"]
        # A run saved before a measure existed has no count for it.
        out += [
            (value(before[p]), value(later[p]))
            for p in sorted(set(before) & set(later))
            if len(before[p]) > i and len(later[p]) > i
        ]
    return out


def compare(old: dict, new: dict) -> list[Change]:
    """Every book and measure the two runs share, each on its own: diagnostics, not
    tests (24 intervals star about one by chance)."""
    shared = [n for n in new["books"] if n in old["books"]]
    return [
        Change(name, measure, *paired(_pairs(old, new, i, [name])))
        for name in shared
        for measure, i in PAIRED
    ]


@dataclass(frozen=True)
class Verdict:
    outcome: str  # "better", "worse", "no change" or "vetoed"
    pooled: list[Change]  # the primary measure over the shared books, per slip rate
    vetoes: list[str]  # books whose own "after review" got worse
    breaks: Change | None = None  # paragraph breaks over the shared books
    # Heading errors over the shared books, before and after (`heading_errors`).
    headings: tuple[int, int] | None = None
    # Italic words set wrong over the shared books, before and after (`italic_errors`).
    italics: tuple[int, int] | None = None


# A book whose italic words set wrong rise by this many, and by this share, is worse on
# its own: a cut can mend one book's lone words and cost a few in another.
ITALIC_VETO_MIN = 10
ITALIC_VETO_SHARE = 0.1


def heading_errors(a: dict, b: dict) -> tuple[int, int]:
    """A book's heading errors in scores `a` and `b`: reference headings missing, extra
    headings, and, where both scores count them, headings not set letter for letter. A
    warm build sets the same headings each time, so the counts need no interval."""

    def errors(s: dict, exact: bool, extra: bool) -> int:
        found = s["headings_exact"] if exact else s["headings_found"]
        return (
            s["headings_expected"]
            - found
            + (s["headings_extra"] if extra else s["headings_spurious"])
        )

    exact = "headings_exact" in a and "headings_exact" in b
    extra = "headings_extra" in a and "headings_extra" in b
    return errors(a, exact, extra), errors(b, exact, extra)


def italic_errors(score: dict) -> int:
    """A book's italic words set wrong: italic where the reference is upright, and upright
    where it is italic. Warm builds measure the same slants, so the count needs no interval."""
    output, expected = score["italic_output"], score["italic_expected"]
    right = round(score["italic_precision"] * output)
    return (output - right) + (expected - right)


def verdict(old: dict, new: dict) -> Verdict:
    """Whether the new run is better. Worse when "after review", each book weighing the
    same, is clearly worse at any slip rate, the paragraph breaks set wrong clearly rise,
    or the heading errors over all books rise; better when it improves at every slip
    rate, or the breaks clearly fall, or the heading or italic errors fall, and none is
    worse (the italic errors rising is worse too); vetoed when better but a book clearly
    gets worse in words or in breaks (`VETO_LEVEL`, `VETO_MIN` on the mean), gains heading
    errors, or gains italic errors (`ITALIC_VETO_MIN`, `ITALIC_VETO_SHARE`)."""
    shared = [n for n in new["books"] if n in old["books"]]
    index = dict(PAIRED)
    primary = [
        Change("all", m, *pooled([_pairs(old, new, index[m], [n]) for n in shared]))
        for m in PRIMARY
    ]
    vetoes = []
    for n in shared:
        for m in (PRIMARY[0], "paragraph breaks"):
            pairs = _pairs(old, new, index[m], [n])
            if not pairs:
                continue
            before, after, low, _ = paired(pairs, level=VETO_LEVEL)
            if low > 0 and after - before >= VETO_MIN:
                vetoes.append(n)
                break
    # Headings are counted over a book's whole slice, so only a slice both runs score
    # alike compares: a grown one holds more chapters, and more headings to miss.
    counts = {
        n: heading_errors(old["books"][n]["score"], new["books"][n]["score"])
        for n in shared
        if "headings_found" in old["books"][n].get("score", {})
        and "headings_found" in new["books"][n].get("score", {})
        and old["books"][n].get("spec") == new["books"][n].get("spec")
    }
    vetoes += [n for n, (a, b) in counts.items() if b > a and n not in vetoes]
    headings = (sum(a for a, _ in counts.values()), sum(b for _, b in counts.values()))
    # Italics only where the reference sets them as the print does (`italics_scored`).
    slanted = {
        n: (italic_errors(old["books"][n]["score"]), italic_errors(new["books"][n]["score"]))
        for n in shared
        if old["books"][n].get("italics_scored")
        and new["books"][n].get("italics_scored")
        and "italic_output" in old["books"][n].get("score", {})
        and "italic_output" in new["books"][n].get("score", {})
        and old["books"][n].get("spec") == new["books"][n].get("spec")
    }
    vetoes += [
        n
        for n, (a, b) in slanted.items()
        if b - a >= max(ITALIC_VETO_MIN, ITALIC_VETO_SHARE * a) and n not in vetoes
    ]
    italics = (sum(a for a, _ in slanted.values()), sum(b for _, b in slanted.values()))
    pairs = [_pairs(old, new, index["paragraph breaks"], [n]) for n in shared]
    breaks = Change("all", "paragraph breaks", *pooled(pairs)) if any(pairs) else None
    words_better = all(c.high < 0 for c in primary)
    words_worse = any(c.low > 0 for c in primary)
    breaks_better = breaks is not None and breaks.high < 0
    breaks_worse = breaks is not None and breaks.low > 0
    headings_worse, headings_better = headings[1] > headings[0], headings[1] < headings[0]
    italics_worse, italics_better = italics[1] > italics[0], italics[1] < italics[0]
    if words_worse or breaks_worse or headings_worse or italics_worse:
        outcome = "worse"
    elif words_better or breaks_better or headings_better or italics_better:
        outcome = "vetoed" if vetoes else "better"
    else:
        outcome = "no change"
    return Verdict(
        outcome,
        primary,
        vetoes,
        breaks,
        headings if counts else None,
        italics if slanted else None,
    )


# A book whose unasked errors at least double, and rise by this many a page, is named
# for a look: one place broken, as Reis om mijn schedel's lost page (0.08 → 0.30, inside
# a veto's interval). Over 95 past tuning comparisons it fired 8 times (2026-11-02).
DOUBLED_RISE = 0.1


def doubled(old: dict, new: dict) -> list[tuple[str, float, float]]:
    """The books whose unasked errors a page at least doubled, by `DOUBLED_RISE` or more,
    on the pages both runs scored: a warning beside the verdict, not part of it."""
    out = []
    for name, book in new["books"].items():
        if name not in old["books"]:
            continue
        a, b = old["books"][name]["pages"], book["pages"]
        shared = [p for p in b if p in a]
        if not shared:
            continue
        before = sum(a[p][1] for p in shared) / len(shared)
        after = sum(b[p][1] for p in shared) / len(shared)
        if after >= 2 * before and after - before >= DOUBLED_RISE:
            out.append((name, before, after))
    return out


def _f1(score: dict) -> float:
    p, r = score["paragraph_precision"], score["paragraph_recall"]
    return 2 * p * r / (p + r) if p + r else 0.0


def scenes(score: dict) -> str:
    """Scene breaks found of those expected, and how many more the output sets (a score
    saved before they were counted reads 0/0)."""
    found = score.get("scene_breaks_found", 0)
    extra = score.get("scene_breaks_output", 0) - found
    return f"{found}/{score.get('scene_breaks_expected', 0)} (+{extra})"


def headings(score: dict) -> str:
    """Headings found of those expected, how many of them letter for letter ("4I" for 41
    is found, not exact), and how many
    more the output sets (a score saved before exact ones were counted reads them as found)."""
    exact = score.get("headings_exact", score["headings_found"])
    extra = score.get("headings_extra", score["headings_spurious"])
    return f"{score['headings_found']}/{score['headings_expected']} ({exact} exact, +{extra})"


def heading_totals(run: dict) -> dict:
    """The run's heading counts summed over its books."""
    keys = ("headings_found", "headings_expected", "headings_spurious")
    total = {k: sum(b["score"][k] for b in run["books"].values()) for k in keys}
    total["headings_extra"] = sum(
        b["score"].get("headings_extra", b["score"]["headings_spurious"])
        for b in run["books"].values()
    )
    total["headings_exact"] = sum(
        b["score"].get("headings_exact", b["score"]["headings_found"])
        for b in run["books"].values()
    )
    return total


def structure(old: dict, new: dict) -> list[str]:
    """Per book, the headings and scene breaks found and spurious and the paragraph F1
    where they changed, after the headings over all books where they did: the primary measure counts
    words, so a change to a book's structure shows only here."""
    before, after = headings(heading_totals(old)), headings(heading_totals(new))
    out = [f"{'all books':40} headings {before} → {after}"] if before != after else []
    for name, book in new["books"].items():
        if name not in old["books"]:
            continue
        a, b = old["books"][name]["score"], book["score"]
        if headings(a) != headings(b):
            out.append(f"{name[:40]:40} headings {headings(a)} → {headings(b)}")
        if scenes(a) != scenes(b):
            out.append(f"{name[:40]:40} scene breaks {scenes(a)} → {scenes(b)}")
        if round(_f1(a), 3) != round(_f1(b), 3):
            out.append(f"{name[:40]:40} paragraph F1 {_f1(a):.3f} → {_f1(b):.3f}")
    return out


def by_cause(
    old: dict, new: dict, old_rows: list[dict], new_rows: list[dict]
) -> list[tuple[str, float, float, float, float]]:
    """Per cause, wrong words a page before and after over the pages both runs scored,
    each book weighing the same, with the interval of the difference (`pooled`); the
    causes either run has, largest first."""

    def per_page(rows: list[dict]) -> dict[tuple[str, int, str], int]:
        out: Counter = Counter()
        for r in rows:
            out[(r["book"], r["page"], errorlog.cause_of(r))] += r["size"]
        return out

    a, b = per_page(old_rows), per_page(new_rows)
    shared = old["books"].keys() & new["books"].keys()
    pages = {
        book: sorted(set(old["books"][book]["pages"]) & set(new["books"][book]["pages"]))
        for book in shared
    }
    causes = {k[2] for k in a} | {k[2] for k in b}
    out = []
    for c in causes:
        books = [
            [(a[(book, int(p), c)], b[(book, int(p), c)]) for p in pages[book]] for book in shared
        ]
        out.append((c, *pooled(books)))
    return sorted(out, key=lambda t: -max(t[1], t[2]))


def save(record: dict, out: Path = OUT) -> Path:
    """The record as JSON, and its books' error rows beside it (`errorlog`)."""
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = out / f"{record['set']}-{stamp}-{record['commit']}.json"
    books = {n: {k: v for k, v in b.items() if k != "_errors"} for n, b in record["books"].items()}
    path.write_text(json.dumps({**record, "books": books}, indent=1, ensure_ascii=False))
    errorlog.save(path, [r for b in record["books"].values() for r in b.get("_errors", [])])
    return path


def settings_changed(old: dict, new: dict) -> list[str]:
    """Each setting the two runs were made with that differs, as "name: old → new". A
    paired comparison measures every one of them, not only the change in hand."""
    a, b = old.get("settings", {}), new.get("settings", {})
    return [
        f"{k}: {a.get(k)} → {b.get(k)}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)
    ]


def previous(set_name: str, before: Path, out: Path = OUT) -> Path | None:
    """The last run of the set saved before `before`."""
    runs = sorted(p for p in out.glob(f"{set_name}-*.json") if p.name < before.name)
    return runs[-1] if runs else None
