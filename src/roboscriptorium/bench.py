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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from roboscriptorium import quality

OUT = Path("work/bench")
BOOTSTRAP_SAMPLES = 2000

# Golden scans and the pages:chapters scored. Tuning books are tuned on; validation
# books have been consulted for choices before, so they validate, not test.
SETS = {
    "tuning": [
        "goede-dochter--ia-scan:9-64:1-4",
        "vals-alarm--ia-scan:11-60:1-10",
        "reis-om-mijn-schedel--ia-scan",
        "the-nature-of-a-crime--doubleday-1924",
        "the-story-of-doctor-dolittle--stokes-1920",
        "the-thief-takers-apprentice--ia-scan",
    ],
    "validation": [
        "de-tuin-van-de-avondnevel--ia-scan:11-52:1-3",
        "grand-hotel-europa--ia-scan:15-44:1-16",
        "lady-into-fox--chatto-1922",
        "villa-toscane--calibre-pdf::1-12",
    ],
}

# Per-page counts compared between runs: (name, index into a page's counts).
PAIRED = (("wrong words", 0), ("unasked", 1), ("questions", 2), ("after review", 3))


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


def page_counts(
    pages: list[int], errors, found, slip_rate: float = quality.HUMAN_SLIPS
) -> dict[int, list[float]]:
    """Per page: wrong words, wrong words no question catches, questions, and wrong words
    after the reviewer answers every question (the unasked plus expected slips)."""
    counts = quality.per_page(pages, errors, found)
    return {p: [w, u, q, u + slip_rate * q] for p, (w, u, q) in counts.items()}


def paired(before: dict[str, list[float]], after: dict[str, list[float]], i: int, seed: int = 0):
    """Mean per page before and after, and the 95% interval of the mean difference, over
    the pages both runs scored."""
    shared = sorted(set(before) & set(after))
    if not shared:
        return 0.0, 0.0, 0.0, 0.0
    diffs = [after[p][i] - before[p][i] for p in shared]
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(rng.choices(diffs, k=n)) / n for _ in range(BOOTSTRAP_SAMPLES))
    return (
        sum(before[p][i] for p in shared) / n,
        sum(after[p][i] for p in shared) / n,
        means[int(0.025 * BOOTSTRAP_SAMPLES)],
        means[int(0.975 * BOOTSTRAP_SAMPLES) - 1],
    )


def compare(old: dict, new: dict) -> list[Change]:
    """Every book and measure the two runs share."""
    out = []
    for name, book in new["books"].items():
        if name not in old["books"]:
            continue
        before, after = old["books"][name]["pages"], book["pages"]
        for measure, i in PAIRED:
            out.append(Change(name, measure, *paired(before, after, i)))
    return out


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
