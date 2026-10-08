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
import random
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from roboscriptorium import quality, trust
from roboscriptorium.config import Settings

OUT = Path("work/bench")
BOOTSTRAP_SAMPLES = 2000

# Golden scans and the pages:chapters scored. Tuning books are tuned on, and scored
# with models trained without them (`unseen`); validation books have been consulted
# for choices before, so they validate, not test. Long books are sliced at a chapter
# boundary (a run costs about 1.1 min per cold page): Dolittle's slice holds its
# plates and drawn initials, Reis's the Voorwoord and ten chapters. The test set is scored once, at
# the end: nothing is chosen on it, no model trains on it, and the CLI refuses to
# score it without `--score-test`.
SETS = {
    "tuning": [
        "goede-dochter--ia-scan:9-64:1-4",
        "vals-alarm--ia-scan:11-60:1-10",
        "reis-om-mijn-schedel--ia-scan:11-110:1-11",
        "the-nature-of-a-crime--doubleday-1924",
        "the-story-of-doctor-dolittle--stokes-1920:23-88:1-7",
        "the-thief-takers-apprentice--ia-scan:11-84:1-22",
        "afscheid-van-verspilde-tijd--ia-scan:9-70:1-11",
        "metro-2033--ia-scan:7-111:1-10",
        "de-cipier--ia-scan:9-92:1-4",
        "artemis--ia-scan:13-80:1-3",
        "11-22-63--ia-scan:15-94:1-24",
    ],
    "validation": [
        "de-tuin-van-de-avondnevel--ia-scan:11-52:1-3",
        "de-eerlijke-vinder--ia-scan",
        "youre-never-weird-on-the-internet--ia-scan:13-94:1-16",
        "villa-toscane--calibre-pdf::1-12",
    ],
    "test": [
        "het-geluid-van-bananen--ia-scan:9-101:1-14",
    ],
}
TEST_BOOKS = frozenset(spec.split(":")[0] for spec in SETS["test"])

# Per-page counts compared between runs: (name, index into a page's counts). "After
# review" is the unasked plus the reviewer's expected slips per question, at the mean
# slip rate and at either end of its interval.
PAIRED = (
    ("wrong words", 0),
    ("unasked", 1),
    ("questions", 2),
    ("after review", 3),
    ("after review, few slips", 4),
    ("after review, many slips", 5),
)
# The one test that decides a change: "after review" over the set, each book weighing
# the same, at each slip rate.
PRIMARY = ("after review", "after review, few slips", "after review, many slips")
# A book vetoes a change only when it gets worse by at least this much per page with
# 99% confidence: six books at 95% would veto about one change in seven that helps all.
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
    where there is one, so a tuning book isn't scored by a model that saw its labels."""
    path = trust.without(Path(settings.ocr_trust_model), book)
    return replace(settings, ocr_trust_model=str(path)) if path.exists() else settings


def page_counts(
    pages: list[int], errors, found, slips: tuple[float, float, float] | None = None
) -> dict[int, list[float]]:
    """Per page: wrong words, wrong words no question catches, questions, and wrong words
    after the reviewer answers every question (the unasked plus expected slips) at the
    mean slip rate, the low end and the high end (`quality.slip_rates`)."""
    low, mean, high = slips or quality.slip_rates()
    counts = quality.per_page(pages, errors, found)
    return {
        p: [w, u, q, u + mean * q, u + low * q, u + high * q] for p, (w, u, q) in counts.items()
    }


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


def _pairs(old: dict, new: dict, i: int, books: list[str]) -> list[tuple[float, float]]:
    out = []
    for name in books:
        before, after = old["books"][name]["pages"], new["books"][name]["pages"]
        out += [(before[p][i], after[p][i]) for p in sorted(set(before) & set(after))]
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


def verdict(old: dict, new: dict) -> Verdict:
    """Whether the new run is better: "after review", each book weighing the same, must
    improve at every slip rate, and no book may clearly get worse (`VETO_LEVEL`,
    `VETO_MIN`)."""
    shared = [n for n in new["books"] if n in old["books"]]
    index = dict(PAIRED)
    primary = [
        Change("all", m, *pooled([_pairs(old, new, index[m], [n]) for n in shared]))
        for m in PRIMARY
    ]
    vetoes = []
    for n in shared:
        before, after, low, _ = paired(_pairs(old, new, index[PRIMARY[0]], [n]), level=VETO_LEVEL)
        if low > 0 and after - before >= VETO_MIN:
            vetoes.append(n)
    if all(c.high < 0 for c in primary):
        outcome = "vetoed" if vetoes else "better"
    elif all(c.low > 0 for c in primary):
        outcome = "worse"
    else:
        outcome = "no change"
    return Verdict(outcome, primary, vetoes)


def save(record: dict, out: Path = OUT) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = out / f"{record['set']}-{stamp}-{record['commit']}.json"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False))
    return path


def previous(set_name: str, before: Path, out: Path = OUT) -> Path | None:
    """The last run of the set saved before `before`."""
    runs = sorted(p for p in out.glob(f"{set_name}-*.json") if p.name < before.name)
    return runs[-1] if runs else None
