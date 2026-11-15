"""Accents every reader drops: a doubt raised where the scan shows one.

A Dutch book sets stress with an acute ("zíjn", "één", "wílde"), and the text layer and
the readers often read the word plain alike, so no difference raises it: 105 of the tuning
bench's 604 silent errors were a dropped mark, 36 of them where no reading differed
(docs/decisions.md, 2026-11-15). For each word of a line no reading disputes, the word is
drawn with the acute an emphasis would set on each of its vowel groups, and the scan is
scored on that mark alone (`rendercheck.mark_fit`). Where it clears `CUT`, the marked
word is offered as another version (`doubts`), which the judges and the arbiter then
settle like any suspect. It decides nothing itself: an i's dot sits where an acute would,
and about one plain word in 400 clears the cut.

The fits are kept per book (`stages/accent-marks.json`), by the typeface they were drawn in.
"""

import re
import unicodedata
from pathlib import Path

import pymupdf

from roboscriptorium.files import read_cache, write_cache
from roboscriptorium.rendercheck import Judge

VERSION = 1
# The mark's fit from which the marked word is offered: 30 of 37 printed marks the build
# dropped score this or more, and 0.24% of 10,000 plain words (`probe_missed_accents.py`).
CUT = 0.79
ACUTE = "́"
LANGUAGES = ("nl",)
_GROUP = re.compile(r"ij|[aeiou]+", re.I)
_WORD = re.compile(r"[^\W\d_]+")


def _plain(text: str) -> bool:
    return unicodedata.normalize("NFD", text) == text


def stressed(word: str) -> list[str]:
    """The word as an emphasis on each of its vowel groups would mark it: an acute on the
    group's first two vowels ("één", "normáál"), on the i of "ij" ("zíjn"). None for a
    word that carries a mark already."""
    if not _plain(word):
        return []
    out = []
    for m in _GROUP.finditer(word):
        hit = m.group()
        marked = hit[0] + ACUTE + hit[1:] if hit.lower() == "ij" else "".join(
            c + ACUTE if i < 2 else c for i, c in enumerate(hit)
        )  # fmt: skip
        out.append(unicodedata.normalize("NFC", word[: m.start()] + marked + word[m.end() :]))
    return out


class Marks:
    """The marks a book's scan shows over words read plain, by the render judge's typeface."""

    def __init__(self, judge: Judge, cache: Path):
        self._judge, self._cache = judge, cache
        kept = read_cache(cache, VERSION, typeface=judge.fingerprint)
        self._fits: dict[str, list] = kept["fits"] if kept else {}
        self._new = 0

    def best(
        self, page: pymupdf.Page, number: int, k: int, at: int, word: str, box
    ) -> tuple[str, float] | None:
        """The marked form of a word that fits the scan best and its fit, or None where
        the word has no vowel to mark or no ink at its box."""
        key = f"{number}|{k}|{at}|{word}"
        if key not in self._fits:
            scored = [
                (fit, marked)
                for marked in stressed(word)
                if (fit := self._judge.mark(page, number, box, marked, word)) is not None
            ]
            self._fits[key] = list(max(scored)) if scored else []
            self._new += 1
        got = self._fits[key]
        return (got[1], got[0]) if got else None

    def doubts(
        self, page: pymupdf.Page, number: int, k: int, ours: str, taken, box_of
    ) -> list[tuple[int, int, list[str]]]:
        """Spans of a line no reading disputes (outside `taken`) whose word the scan shows
        marked, each with the marked word as its one other version. `box_of` gives a
        span's box on the page."""
        out = []
        for m in _WORD.finditer(ours):
            a0, a1 = m.start(), m.end()
            if any(t0 < a1 and a0 < t1 for t0, t1 in taken):
                continue
            found = self.best(page, number, k, a0, m.group(), box_of(a0, a1))
            if found and found[1] >= CUT:
                out.append((a0, a1, [found[0]]))
        return out

    def save(self) -> None:
        if self._new:
            write_cache(
                self._cache, VERSION, {"fits": self._fits}, typeface=self._judge.fingerprint
            )
            self._new = 0
