"""What a reviewer is left with: errors the review doesn't ask about, per question asked.

An error is a stretch where the book's words differ from the golden reference
(`disagreements.find`, after verdicts are patched in). A question is a review
flag; it catches an error when it covers one of the error's lines, or, as a region
without lines, sits where the error's missing words go. Paragraph
breaks and headings aren't counted here, only words.

At a question budget (questions per page), the flags most likely to catch an
error are asked first: each flag is scored by how often flags with its first
reason caught errors in *other* books, so no book ranks its own questions.
Per-page figures come with a bootstrap interval over pages.
"""

import random
import re
from dataclasses import dataclass

from roboscriptorium.disagreements import Disagreement
from roboscriptorium.flags import Flag

BUDGETS = (0.25, 0.5, 1.0)
BOOTSTRAP_SAMPLES = 1000
# Answers a reviewer got wrong, of answers checked: Stella, by proofreading.
SLIPS, ANSWERS = 8, 68


def slip_rates(slips: int = SLIPS, answers: int = ANSWERS) -> tuple[float, float, float]:
    """The reviewer's chance of a wrong answer per question: the 2.5% point, mean and
    97.5% point of its Beta posterior from a uniform prior."""
    from scipy.stats import beta

    a, b = 1 + slips, 1 + answers - slips
    return float(beta.ppf(0.025, a, b)), a / (a + b), float(beta.ppf(0.975, a, b))


@dataclass(frozen=True)
class Estimate:
    mean: float
    low: float  # 95% bootstrap interval over pages
    high: float

    def __str__(self) -> str:
        return f"{self.mean:.2f} [{self.low:.2f}–{self.high:.2f}]"


QUOTES = "'\"‘’“”‚„«»`´"
DASHES = "-‐‑‒–—―"


def category(error: Disagreement) -> str:
    """The kind of error: what is left when the two sides are compared without it."""
    got, want = error.got, error.want
    if not got or not want:
        return "missing words" if not got else "extra words"
    if got.replace(" ", "") == want.replace(" ", ""):
        return "word breaks"
    strip = str.maketrans("", "", QUOTES)
    if got.translate(strip) == want.translate(strip):
        return "quotes"
    strip = str.maketrans("", "", QUOTES + DASHES + ".,;:!?…()[]*")
    if got.translate(strip).replace(" ", "") == want.translate(strip).replace(" ", ""):
        return "punctuation"
    if len(got.split()) == len(want.split()):
        return "letters"
    return "words"


def size(error: Disagreement) -> int:
    """Wrong words: the longer side of the differing stretch."""
    return max(len(error.got.split()), len(error.want.split()), 1)


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _place(flag: Flag) -> set[str]:
    """The words a question about one place in a line asks about: the place in the
    layer's line, and the words its readings differ in."""
    line = flag.text.split("\n")[0]
    out = _words(line[flag.span[0] : flag.span[1]])
    base = _words(flag.readings[0]["text"]) if flag.readings else set()
    for r in flag.readings[1:]:
        out |= _words(r["text"]) ^ base
    return out


def catches(flag: Flag, error: Disagreement) -> bool:
    """Whether answering the question would put the error in front of the reviewer: it
    covers the error's lines, and a question about one place in a line only catches an
    error that shares a word with that place (an error without words, a lost dash, any
    on its line)."""
    if flag.page != error.page:
        return False
    if error.lines is None:
        return False
    if flag.span is not None:
        words = _words(error.got) | _words(error.want)
        if words and not words & _place(flag):
            return False
    if flag.last < flag.first:
        # A region with no lines asks for text the layer lacks, between lines first - 1
        # and first; the missing words sit between the words either side of them, whose
        # lines may both be the one above it.
        return not error.got and error.lines[0] < flag.first <= error.lines[1] + 1
    return flag.first <= error.lines[1] and error.lines[0] <= flag.last


def reason(flag: Flag) -> str:
    return flag.reasons[0] if flag.reasons else ""


def hit_rates(flags: list[Flag], errors: list[Disagreement]) -> dict[str, tuple[int, int]]:
    """Per first reason: (flags that caught an error, flags)."""
    out: dict[str, tuple[int, int]] = {}
    for f in flags:
        hit = any(catches(f, e) for e in errors)
        h, n = out.get(reason(f), (0, 0))
        out[reason(f)] = (h + hit, n + 1)
    return out


def ranked(flags: list[Flag], rates: dict[str, tuple[int, int]]) -> list[Flag]:
    """Flags, those whose reason caught errors most often elsewhere first."""

    def score(f: Flag) -> float:
        h, n = rates.get(reason(f), (0, 0))
        return (h + 1) / (n + 2)  # Laplace: an unseen reason scores 0.5

    return sorted(flags, key=score, reverse=True)


def weight(flag: Flag) -> int:
    """How many questions a flag is to the reviewer: a washed-out page is typed whole, a
    question per line, each line as likely to slip as an answer."""
    return flag.last - flag.first + 1 if "washed-out" in flag.reasons else 1


def per_page(
    pages: list[int], errors: list[Disagreement], asked: list[Flag]
) -> dict[int, tuple[int, int, int]]:
    """Per page: (wrong words, wrong words no asked question catches, questions)."""
    out = {p: [0, 0, 0] for p in pages}
    for e in errors:
        if e.page in out:
            out[e.page][0] += size(e)
            if not any(catches(f, e) for f in asked):
                out[e.page][1] += size(e)
    for f in asked:
        if f.page in out:
            out[f.page][2] += weight(f)
    return {p: tuple(v) for p, v in out.items()}


def unasked_by_category(errors: list[Disagreement], asked: list[Flag]) -> dict[str, int]:
    """Wrong words no asked question catches, per category, largest first."""
    out: dict[str, int] = {}
    for e in errors:
        if not any(catches(f, e) for f in asked):
            out[category(e)] = out.get(category(e), 0) + size(e)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def bootstrap(values: list[float], seed: int = 0) -> Estimate:
    if not values:
        return Estimate(0.0, 0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(BOOTSTRAP_SAMPLES))
    return Estimate(
        sum(values) / n,
        means[int(0.025 * BOOTSTRAP_SAMPLES)],
        means[int(0.975 * BOOTSTRAP_SAMPLES) - 1],
    )


def report(
    pages: list[int],
    errors: list[Disagreement],
    flags: list[Flag],
    rates: dict[str, tuple[int, int]],
) -> dict[str, Estimate]:
    """Wrong words per page, before review and left unasked with all questions and at
    each budget, plus questions per page."""
    order = ranked(flags, rates)
    out = {}
    full = per_page(pages, errors, flags)
    out["wrong words"] = bootstrap([v[0] for v in full.values()])
    out["questions"] = bootstrap([v[2] for v in full.values()])
    out["unasked, all questions"] = bootstrap([v[1] for v in full.values()])
    for budget in BUDGETS:
        asked = order[: round(budget * len(pages))]
        counts = per_page(pages, errors, asked)
        out[f"unasked at {budget:g}/page"] = bootstrap([v[1] for v in counts.values()])
    return out
