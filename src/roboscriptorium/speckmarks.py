"""A speck on the paper read as punctuation: a doubt raised where a mark is unlike the
book's own.

Dirt beside a word reads as a comma, a dot over a comma as ";", over a full stop as ":",
and every reader reads it alike, so no difference raises it: most of the tuning bench's
52 silent punctuation swaps, in two speckled scans (docs/decisions.md, 2026-11-16). Each
comma, semicolon and colon a token of the book ends on is measured (`survey`): its own
ink, the letter before it left out (`picture`; a mark touching its letter is passed
over), against the book's usual picture of that mark (`unlike`) and against its every
other one (`odd_pictures`). Where it is `CUT` apart from both, the token is offered
without the speck's part (`lesser`) as another version (`doubts`), which the judges and
the arbiter settle like any suspect. It decides nothing itself, and needs no typeface:
the book's own marks are the measure.

A fleck between two words reads as an apostrophe ("je'vader", "had'him"). There the
words say it (`parted`): two words of the word list joined by a mark into no word, in a
form the book doesn't repeat, are offered as two words; 134 such tokens in the tuning
books, nearly all specks by their look.

A speck before a line's first word reads as a hyphen ("- I followed"), and one after a
full stop as a second ("system.. He added"). Neither is a rule: a few prints set a spaced
dash there, or two dots (decisions.md, 2026-11-17 and 2026-11-20), so the line without the
mark is offered (`leading_dash`, `double_stop`) and the judges see the scan; a book with
two stops on `REPEATS` words or more prints them so (Goede dochter's "vermoord..’") and
gets no such offer.

The offers are kept per book (`stages/speck-marks.json`).
"""

import re
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

from roboscriptorium import rendercheck
from roboscriptorium.files import code_stamp, read_cache, write_cache
from roboscriptorium.pdf import PageText, line_words, page_words

VERSION = 2
# How unlike the book's usual picture of its mark (`unlike`) a token's is for the lesser
# version to be offered: the printed marks' median is 0.03 to 0.05; the 15 speck marks
# the tuning bench names in Doodskleed and The Thief-Taker's Apprentice score 0.15 to
# 0.9 (`experiments/probe_speck_marks.py`, 2026-11-16).
CUT = 0.15
# The widest a mark's own ink runs, in heights of its strip: a comma is about 0.2.
MARK = 0.35
# The rows of a word's strip (`rendercheck.place_ink`, the line and 0.3 of its height
# either side) a comma, semicolon or colon lies in: from under the ascenders down.
ROWS = (0.28, 0.9)
# How many of the book's other pictures of a mark may be like an odd one for it still
# to be offered: specks that happen to look alike.
ALIKE = 3
# Marks of a kind a book must show for its usual one to be known.
FEWEST = 10
# A joined form the book has this often is its spelling ("ma'am", "sp'ers"), not a speck.
REPEATS = 3
_JOINED = re.compile(r"^(\W*)([^\W\d_]{2,})['’‘`·_]([^\W\d_]{2,})(\W*)$")
CLOSERS = "'\"’”"
_TOKEN = re.compile(r"\S+")
_SIZE = (18, 40)


def lesser(token: str) -> tuple[str, str] | None:
    """The mark a token ends on that a speck could have made (closing quote marks after
    it aside), and the token without the speck's part: "," lost, ";" a comma, ":" a
    stop. None for another token, or a mark standing alone."""
    core = token.rstrip(CLOSERS)
    tail = token[len(core) :]
    if len(core) < 2 or not core[-2].isalnum():
        return None
    if core[-1] == ",":
        return ",", core[:-1] + tail
    if core[-1] == ";":
        return ";", core[:-1] + "," + tail
    if core[-1] == ":":
        return ":", core[:-1] + "." + tail
    return None


def leading_dash(text: str) -> tuple[str, str] | None:
    """A line opening on a hyphen standing alone before a word: the line's start up to
    that word's end, and the word without it ("- I" and "I"); None for another line."""
    m = re.match(r"(-\s+)(\S+)", text)
    if not m or not any(c.isalnum() for c in m.group(2)):
        return None
    return m.group(0), m.group(2)


def double_stop(token: str) -> str | None:
    """A word ending on two full stops, not three (closing quote marks after them
    aside), with one; None for another token."""
    core = token.rstrip(CLOSERS)
    if len(core) < 3 or not core.endswith("..") or not core[-3].isalnum():
        return None
    return core[:-1] + token[len(core) :]


def parted(token: str, knows) -> str | None:
    """A token that is two known words joined by an apostrophe or a like mark into no
    known word ("je'vader"), as the two words; None for any other. `knows` says whether
    a word is in the word list."""
    m = _JOINED.match(token)
    if not m or not (knows(m.group(2)) and knows(m.group(3))):
        return None
    if knows(f"{m.group(2)}'{m.group(3)}"):
        return None
    return f"{m.group(1)}{m.group(2)} {m.group(3)}{m.group(4)}"


def picture(ink: np.ndarray) -> np.ndarray | None:
    """The mark a word's strip ends on, at one size for a book: its last run of inked
    columns, set at the right of a frame 0.45 of the strip's height wide, so the letter
    before the mark is left out. None where the run is wider than a mark (`MARK` of the
    strip's height: one touching its letter, an f's hook over a comma), or the strip is
    blank."""
    # The strip reaches into the lines above and below: their letters' ends are no mark.
    top, bottom = round(ink.shape[0] * ROWS[0]), round(ink.shape[0] * ROWS[1])
    ink = ink[top:bottom]
    cols = (ink > 0.5).any(0)
    inked = np.where(cols)[0]
    if len(inked) == 0:
        return None
    wide = max(4, round(ink.shape[0] * 0.45))
    end = inked[-1] + 1
    start = end
    while start > 0 and cols[start - 1]:
        start -= 1
    if end - start > ink.shape[0] * MARK:
        return None
    frame = np.zeros((ink.shape[0], wide), np.float32)
    frame[:, wide - (end - start) :] = ink[:, start:end]
    return np.asarray(Image.fromarray(frame).resize(_SIZE, Image.BILINEAR))


def unlike(patch: np.ndarray, usual: np.ndarray) -> float:
    """1 less a mark's best correlation with the book's usual picture of it, over small
    shifts up and down: the layer's boxes sit a little differently line by line."""
    best = -1.0
    b = usual[4:-4].ravel() - usual[4:-4].mean()
    for dy in range(-4, 5):
        a = np.roll(patch, dy, 0)[4:-4].ravel()
        a = a - a.mean()
        best = max(best, float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6)))
    return 1 - best


def _rows(patches: list[np.ndarray], shift: int = 0) -> np.ndarray:
    """Pictures as rows to correlate: shifted, their edge rows cut, centred, unit length."""
    flat = np.stack([np.roll(p, shift, 0)[4:-4].ravel() for p in patches]).astype(np.float32)
    flat -= flat.mean(1, keepdims=True)
    return flat / (np.linalg.norm(flat, axis=1, keepdims=True) + 1e-6)


def odd_pictures(patches: list[np.ndarray]) -> list[int]:
    """Which of a book's pictures of one mark are `CUT` unlike its usual one (the median
    of the four in five most alike, so specks don't draw it) and as unlike all but
    `ALIKE` of the others: a book's second form of a mark (its italic, one set after a
    space) has its like, a speck has none. None in a book with fewer than `FEWEST`."""
    if len(patches) < FEWEST:
        return []
    usual = np.median(patches, 0)
    near = sorted(patches, key=lambda p: unlike(p, usual))[: len(patches) * 4 // 5]
    usual = np.median(near, 0)
    apart = [i for i, p in enumerate(patches) if unlike(p, usual) >= CUT]
    if not apart:
        return []
    still = _rows(patches)
    best = np.full((len(apart), len(patches)), -1.0, np.float32)
    for shift in range(-4, 5):
        best = np.maximum(best, _rows([patches[i] for i in apart], shift) @ still.T)
    best[np.arange(len(apart)), apart] = -1.0
    # The correlation with the most alike other picture but `ALIKE`.
    nearest = np.sort(best, axis=1)[:, -1 - ALIKE]
    return [i for i, c in zip(apart, nearest, strict=True) if 1 - c >= CUT]


class Specks:
    """The tokens of a book whose closing mark is unlike the book's own, each with the
    version a speck would have been read from."""

    def __init__(self, cache: Path, lexicon=None, line_marks: bool = False):
        self._cache, self._lexicon, self._line_marks = cache, lexicon, line_marks
        kept = read_cache(cache, VERSION, code=code_stamp(__name__), line_marks=line_marks)
        self._offers: dict[str, str] | None = kept["offers"] if kept else None
        self._new = False

    def survey(self, pdf: Path, pages: list[PageText]) -> None:
        """Measures every comma, semicolon and colon a token ends on, over the lines
        whose words the layer places one for one, and keeps the odd ones' offers; with a
        word list, those of two words a mark joins (`parted`) too."""
        if self._offers is not None:
            return
        joined: dict[str, list[tuple[str, str]]] = {}
        for page in pages if self._lexicon else ():
            for k, line in enumerate(page.lines):
                for m in _TOKEN.finditer(line.text):
                    if other := parted(m.group(), self._lexicon.knows):
                        key = f"{page.number}|{k}|{m.start()}|{m.group()}"
                        joined.setdefault(other.strip(CLOSERS + ".,;:!?‘“").lower(), []).append(
                            (key, other)
                        )
        marks: dict[str, list[tuple[str, str, np.ndarray]]] = {",": [], ";": [], ":": []}
        with pymupdf.open(pdf) as doc:
            for page in pages:
                words = None
                for k, line in enumerate(page.lines):
                    found = [(m, lesser(m.group())) for m in _TOKEN.finditer(line.text)]
                    # The picture ends on the word's last ink: the mark itself.
                    if not any(hit and m.group()[-1] == hit[0] for m, hit in found):
                        continue
                    if words is None:
                        words = line_words(page_words(doc[page.number - 1], page), page)
                    if [w[4] for w in words[k]] != [m.group() for m, _ in found]:
                        continue
                    for (m, hit), w in zip(found, words[k], strict=True):
                        if hit is None or m.group()[-1] != hit[0]:
                            continue
                        ink = rendercheck.place_ink(doc[page.number - 1], w[:4], page)
                        patch = None if ink is None else picture(ink)
                        if patch is not None:
                            key = f"{page.number}|{k}|{m.start()}|{m.group()}"
                            marks[hit[0]].append((key, hit[1], patch))
        self._offers = {
            rows[i][0]: rows[i][1]
            for rows in marks.values()
            for i in odd_pictures([r[2] for r in rows])
        }
        for places in joined.values():
            if len(places) < REPEATS:
                self._offers.update(places)
        stops: dict[str, str] = {}
        for page in pages if self._line_marks else ():
            for k, line in enumerate(page.lines):
                if hit := leading_dash(line.text):
                    self._offers[f"{page.number}|{k}|0|{hit[0]}"] = hit[1]
                for m in _TOKEN.finditer(line.text):
                    if (one := double_stop(m.group())) is not None:
                        stops[f"{page.number}|{k}|{m.start()}|{m.group()}"] = one
        # A book that ends words on two stops this often prints them so (trailing speech).
        if len(stops) < REPEATS:
            self._offers.update(stops)
        self._new = True

    def doubts(
        self, page: pymupdf.Page, number: int, k: int, ours: str, taken, box_of
    ) -> list[tuple[int, int, list[str]]]:
        """Tokens of a line no reading disputes (outside `taken`) that the survey found
        odd, each with its version without the speck's part as its one other version."""
        out = []
        if (
            (hit := leading_dash(ours))
            and (other := (self._offers or {}).get(f"{number}|{k}|0|{hit[0]}")) is not None
            and not any(t0 < len(hit[0]) for t0, _ in taken)
        ):
            out.append((0, len(hit[0]), [other]))
        for m in _TOKEN.finditer(ours):
            a0, a1 = m.start(), m.end()
            other = (self._offers or {}).get(f"{number}|{k}|{a0}|{m.group()}")
            if other is None or any(t0 < a1 and a0 < t1 for t0, t1 in taken):
                continue
            out.append((a0, a1, [other]))
        return out

    def save(self) -> None:
        if self._new:
            write_cache(
                self._cache,
                VERSION,
                {"offers": self._offers},
                code=code_stamp(__name__),
                line_marks=self._line_marks,
            )
            self._new = False
