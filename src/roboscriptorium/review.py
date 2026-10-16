"""The local review page for a book next to its scan, served on 127.0.0.1
(`roboscriptorium review <book>`).

It asks about what the pipeline flagged as not plain running text. Each question shows
a crop of the scan and takes an answer: running text, heading, drop, image, initial or
caption, optionally with the text as printed. A region with a box can be turned and
read again. Answers apply on the next build, which the page can start. A golden book's
places where our text and the publisher's e-book differ are more questions in the same
list, each a doubt between the two; their answers are verdicts on the reference.
"""

import difflib
import itertools
import json
import math
import re
import threading
import unicodedata
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pymupdf

from roboscriptorium import corrections, errata, ocr
from roboscriptorium import flags as F
from roboscriptorium.corrections import ACTIONS, Correction, Corrections
from roboscriptorium.disagreements import UNSURE, Disagreement, Verdicts
from roboscriptorium.evaluate import normalise
from roboscriptorium.files import append_jsonl
from roboscriptorium.pdf import PDF_LOCK, PageText

# Crops show this many lines around the disagreement, at this zoom (PDF points → pixels).
CROP_CONTEXT_LINES = 1
# Each zoom-out step widens a crop by this much on every side, in PDF points.
ZOOM_OUT_STEP = 80
CROP_ZOOM = 2.5
PAGE_ZOOM = 1.5
OCR_DPI = 300


# The verdict category when the page prints the output: the reference differs from its print.
SCAN_EDITION = "edition"


def guess_category(d: Disagreement) -> str:
    """The likeliest pipeline mistake, recorded with a verdict for the reference."""
    if d.auto:
        return d.auto
    letters = lambda s: re.sub(r"[^\w]", "", s).lower()  # noqa: E731
    if not d.want:
        return "artefact"
    if not d.got:
        return "lost"
    if d.got.replace("-", "").replace(" ", "") == d.want.replace("-", "").replace(" ", ""):
        return "hyphen"
    if letters(d.got) == letters(d.want):
        return "punctuation"
    return "ocr"


# Highlights are drawn beside or beneath the print, never over it, so a mark the reviewer
# is asked about (a quote, a dash) is never covered: a faint tint behind the lines in
# question, a soft outline around a region, an underline beneath a doubt's place.
TINT = (1, 0.93, 0.55)
TINT_OPACITY = 0.18
OUTLINE = (0.85, 0.65, 0.2)
# How far below a line's box (which ends at the baseline) its descenders reach, as a share
# of the box's height.
DESCENT = 0.4
# Where a lost line's draft is read from: the crop's top, as shares of the line above's
# height below its baseline.
GAP_STEPS = (0.0, 0.1, 0.2, 0.3, 0.4)
UNDERLINE = (0.25, 0.45, 0.95)


def _tint(pdf_page: pymupdf.Page, rect: pymupdf.Rect) -> None:
    pdf_page.draw_rect(rect, color=None, fill=TINT, fill_opacity=TINT_OPACITY)


def _widened(clip: pymupdf.Rect, out: int, page: pymupdf.Rect) -> pymupdf.Rect:
    pad = out * ZOOM_OUT_STEP
    return pymupdf.Rect(clip.x0 - pad, clip.y0 - pad, clip.x1 + pad, clip.y1 + pad) & page


class Scan:
    """Page images and highlighted crops of a book's source PDF."""

    def __init__(self, pdf: Path, pages: list[PageText]):
        self.pdf = pdf
        self.pages = {p.number: p for p in pages}
        self._turns: dict[tuple, int] = {}

    def crop(
        self, page_number: int, first: int, last: int, out: int = 0, mark: bool = True
    ) -> bytes:
        page = self.pages[page_number]
        lo = max(0, first - CROP_CONTEXT_LINES)
        hi = min(len(page.lines) - 1, last + CROP_CONTEXT_LINES)
        x0 = min(ln.x0 for ln in page.lines) - 6
        x1 = max(ln.x1 for ln in page.lines) + 6
        target = pymupdf.Rect(x0, page.lines[first].y0 - 2, x1, page.lines[last].y1 + 2)
        clip = pymupdf.Rect(x0, page.lines[lo].y0 - 6, x1, page.lines[hi].y1 + 6)
        with PDF_LOCK, pymupdf.open(self.pdf) as doc:
            pdf_page = doc[page_number - 1]
            clip = _widened(clip, out, pdf_page.rect)
            if mark:
                _tint(pdf_page, target)
            pix = pdf_page.get_pixmap(matrix=pymupdf.Matrix(CROP_ZOOM, CROP_ZOOM), clip=clip)
            return pix.tobytes("png")

    def crop_box(
        self,
        page_number: int,
        box: tuple[float, float, float, float],
        turn: int = 0,
        out: int = 0,
        line: int | None = None,
        mark: bool = True,
        gap: bool = False,
    ) -> bytes:
        """A region with some of the page around it.

        `turn` (degrees clockwise) shows sideways text upright, cropped to the region;
        `out` zoom-out steps show more of the page around it. With `line`, the box is a
        place in that line (an OCR doubt): the line is tinted and the place underlined.
        `mark` False draws nothing. With `gap`, the box is white space where text may be
        missing: it is drawn inside the space, clear of the lines around it.
        """
        x0, y0, x1, y1 = box
        target = pymupdf.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
        with PDF_LOCK, pymupdf.open(self.pdf) as doc:
            pdf_page = doc[page_number - 1]
            if turn in (90, 270):
                clip = pymupdf.Rect(x0 - 40, y0, x1 + 40, y1) & pdf_page.rect
            else:
                clip = pymupdf.Rect(0, y0 - 40, pdf_page.rect.width, y1 + 40) & pdf_page.rect
            clip = _widened(clip, out, pdf_page.rect)
            if mark and line is not None:
                ln = self.pages[page_number].lines[line]
                _tint(pdf_page, pymupdf.Rect(ln.x0 - 2, ln.y0 - 1, ln.x1 + 2, ln.y1 + 1))
                bottom = max(y1, ln.y1) + 1.5
                pdf_page.draw_rect(
                    pymupdf.Rect(x0 - 1, bottom, x1 + 1, bottom + 1.2), color=None, fill=UNDERLINE
                )
            elif mark and gap:
                pdf_page.draw_rect(self._gap(page_number, box), color=OUTLINE, width=0.8)
            elif mark:
                pdf_page.draw_rect(target + (-1, -1, 1, 1), color=OUTLINE, width=0.8)
            pix = pdf_page.get_pixmap(matrix=pymupdf.Matrix(CROP_ZOOM, CROP_ZOOM), clip=clip)
            return ocr.turned(pix.tobytes("png"), turn)

    def _gap(self, page_number: int, box: tuple[float, float, float, float]) -> pymupdf.Rect:
        """A box of white space between lines, kept clear of them: a text layer's line box
        ends at the baseline, so the line above's descenders hang below it."""
        x0, y0, x1, y1 = box
        lines = self.pages[page_number].lines
        above = [ln for ln in lines if ln.y1 <= y0 + 1]
        below = [ln for ln in lines if ln.y0 >= y1 - 1]
        if above:
            last = max(above, key=lambda ln: ln.y1)
            y0 = max(y0, last.y1 + DESCENT * (last.y1 - last.y0))
        if below:
            y1 = min(y1, min(ln.y0 for ln in below)) - 1
        return pymupdf.Rect(x0 - 2, y0, x1 + 2, max(y1, y0 + 2))

    def turn(self, page_number: int, box: tuple[float, float, float, float], lang: str) -> int:
        """Degrees clockwise that make sideways text upright: the quarter turn that reads."""
        key = (page_number, box)
        if key not in self._turns:
            self._turns[key], _ = ocr.read_sideways(self._ocr_png(page_number, box), lang)
        return self._turns[key]

    def read_box(
        self,
        page_number: int,
        box: tuple[float, float, float, float],
        lang: str,
        single_char: bool = False,
        turn: int = 0,
    ) -> str:
        """Tesseract's reading of a region, as a draft for the human."""
        return ocr.tesseract(ocr.turned(self._ocr_png(page_number, box), turn), lang, single_char)

    def read_gap(self, page_number: int, box: tuple[float, float, float, float], lang: str) -> str:
        """Tesseract's reading of a line that may be lost in white space between lines.

        The gap starts at the line above's baseline, so its descenders hang into it, and
        a lost line's ascenders may reach up among them: the crop's top is tried a few
        steps down from the baseline, and the line read with the most words is kept.
        """
        x0, y0, x1, y1 = box
        above = [ln for ln in self.pages[page_number].lines if ln.y1 <= y0 + 1]
        last = max(above, key=lambda ln: ln.y1, default=None)
        height = last.y1 - last.y0 if last else 0
        readings = [
            self.read_box(page_number, (x0, y0 + step * height, x1, y1), lang)
            for step in GAP_STEPS
            if y0 + step * height < y1 - 2
        ]
        # One line is lost at most: a scrap of a neighbour read beside it is left out.
        lines = [max(r.splitlines() or [""], key=ocr.words) for r in readings]
        return max(lines, key=ocr.words, default="")

    def _ocr_png(self, page_number: int, box: tuple[float, float, float, float]) -> bytes:
        with PDF_LOCK, pymupdf.open(self.pdf) as doc:
            zoom = OCR_DPI / 72
            pix = doc[page_number - 1].get_pixmap(
                matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box)
            )
            return pix.tobytes("png")

    def full_page(self, page_number: int) -> bytes:
        with PDF_LOCK, pymupdf.open(self.pdf) as doc:
            return (
                doc[page_number - 1]
                .get_pixmap(matrix=pymupdf.Matrix(PAGE_ZOOM, PAGE_ZOOM))
                .tobytes("png")
            )


class GoldenQuestions:
    """Where a golden book's output and reference differ, as questions in the region
    review: the words around the place, read once with the output's words and once with
    the reference's, and what the page prints is the verdict. The kind of mistake follows
    from the answer: the output's likeliest slip when the reference is chosen or
    something else typed, an edition difference when the output is chosen."""

    REASON = "our text and the publisher's e-book differ here"
    OURS = "our text"
    THEIRS = "the publisher's e-book"
    # What a place is when it isn't running text, as the region review asks it, and the
    # verdict category it records; the kind and any words typed go in the verdict's note.
    KINDS = {
        "heading": "heading",
        "caption": "caption",
        "drop": "artefact",
        "image": "artefact",
        "initial": "other",
    }

    def __init__(self, items: list[Disagreement], verdicts: Verdicts):
        # A disagreement with no place on a page has no crop to answer from.
        self.items = {d.key: d for d in items if d.page is not None and d.lines is not None}
        self.verdicts = verdicts

    @staticmethod
    def _shown(d: Disagreement) -> tuple[str, str, str, str]:
        """Our words, the reference's, and the reference's words before and after the
        place, as each side writes them."""
        return d.written or (d.got, d.want, d.before, d.after)

    def _parts(self, d: Disagreement) -> tuple[str, str]:
        """The words before and after the place, each with the space that joins it."""
        _, _, before, after = self._shown(d)
        return (before + " " if before else ""), (" " + after if after else "")

    def _line(self, d: Disagreement, words: str) -> str:
        before, after = self._parts(d)
        return before + words + after if words else (before + after.lstrip()).rstrip()

    def _readings(self, d: Disagreement) -> tuple[str, str]:
        """The line with our words at the place, and with the reference's."""
        got, want, _, _ = self._shown(d)
        return self._line(d, got), self._line(d, want)

    def state(self) -> list[dict]:
        """Each place in the shape of a flagged region (`RegionReview.state`), with `got`,
        our words at the place, which a heading or caption answer starts from."""
        items = []
        for d in self.items.values():
            before, after = self._parts(d)
            ours, theirs = self._readings(d)
            v = self.verdicts.by_key.get(d.key)
            answer = None
            kind, _, typed = (v.note if v else "").partition(": ")
            if v is not None and kind in self.KINDS:
                answer = {"action": kind, "text": typed or None}
            elif v is not None and v.category != UNSURE:
                truth = normalise(v.truth or "")
                text = ours if truth == d.got else theirs if truth == d.want else None
                answer = {"action": "text", "text": text or self._line(d, v.truth or "")}
            items.append(
                {
                    "key": d.key,
                    "page": d.page,
                    "first": d.lines[0],
                    "last": d.lines[1],
                    "across": (
                        {"page": d.across[0], "first": d.across[1], "last": d.across[1]}
                        if d.across
                        else None
                    ),
                    "box": None,
                    "treatment": "text",
                    "reasons": [self.REASON],
                    "text": ours,
                    "got": self._shown(d)[0],
                    "span": [len(before), len(ours) - len(after)] if d.got else None,
                    "readings": [
                        {"text": ours, "votes": [self.OURS]},
                        {"text": theirs, "votes": [self.THEIRS]},
                    ],
                    "joined": "",
                    "elsewhere": [],
                    "before": "",
                    "after": "",
                    "answer": answer,
                    "draft": None,
                    "turn": 0,
                }
            )
        return items

    def lines(self, key: str) -> tuple[str, list[dict]]:
        """A place's line as our text has it and its two readings, for `doubtful`."""
        ours, theirs = self._readings(self.items[key])
        return ours, [{"text": ours}, {"text": theirs}]

    def record(self, body: dict) -> dict:
        d = self.items[body["key"]]
        kind = body.get("action", "text")
        if kind in self.KINDS:
            # Not running text: the reference, which holds running text only, is right.
            # A caption's or heading's words as printed go with the kind in the note.
            typed = (body.get("text") or "").strip()
            note = f"{kind}: {typed}" if typed else kind
            self.verdicts.record(d, d.want, self.KINDS[kind], note)
            return {"action": kind, "text": typed or None}
        text = body.get("text") or ""
        got, want, _, _ = self._shown(d)
        ours, theirs = self._readings(d)
        if text == ours:
            truth, category = got, SCAN_EDITION
        elif text == theirs:
            truth, category = want, guess_category(d)
        elif (inner := self._typed(d, text)) is not None:
            truth, category = inner, guess_category(d)
        else:
            raise ValueError(self.CONTEXT_CHANGED)
        self.verdicts.record(d, truth, category)
        return {"action": "text", "text": text}

    CONTEXT_CHANGED = (
        "Change only the marked words: a word around them that differs is a place of its own."
    )

    def _typed(self, d: Disagreement, text: str) -> str | None:
        """The words a typed line sets at the place, or None when it changes the words
        around it too: the verdict replaces the place's words only, so a changed context
        would be written into the reference beside the original."""
        line = " ".join(text.split())
        before, after = (" ".join(s.split()) for s in self._shown(d)[2:])
        if not (line.startswith(before) and line.endswith(after)):
            return None
        inner = line[len(before) : len(line) - len(after)]
        if len(line) < len(before) + len(after):
            return None
        # The context is whole words: a letter typed onto its edge word changes it.
        if (before and inner[:1] not in ("", " ")) or (after and inner[-1:] not in ("", " ")):
            return None
        return inner.strip()

    def refused(self, key: str, action: str, text: str | None) -> str:
        """Why an answer can't be saved at all, or "" when it can."""
        d = self.items[key]
        if action != "text" or text is None or text in self._readings(d):
            return ""
        return "" if self._typed(d, text) is not None else self.CONTEXT_CHANGED


_CURLY = "‘’“”"
# The most options a line's question shows, its readings' combinations included, and the
# most combinations an answer is checked against before it is called a stranger.
OPTIONS = 6
COMBINATIONS_CHECKED = 256
_STRAIGHT = str.maketrans("‘’“”", "''\"\"")


def _fold(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).translate(_STRAIGHT).split())


def combinations(texts: list[str], limit: int) -> list[str]:
    """Every line the readings make between them, place by place: where they differ at
    separate places, one reading's version at one place and another's at the next
    ("‘Ga jij" from "“Ga jij" and "‘Gajij"). The first text is the base; the readings'
    own lines come first. Empty when there would be more than `limit`."""
    base = texts[0]
    edits = []  # per reading: (start, end, replacement) spans of the base
    for t in texts[1:]:
        ops = difflib.SequenceMatcher(None, base, t, autojunk=False).get_opcodes()
        edits.append([(i1, i2, t[j1:j2]) for tag, i1, i2, j1, j2 in ops if tag != "equal"])
    # Places: the spans any reading changes, merged where they overlap or where an
    # insertion meets another edit at its point.
    spans = sorted((a, b) for e in edits for a, b, _ in e)
    places: list[list[int]] = []
    for a, b in spans:
        if places and (a < places[-1][1] or a == places[-1][1] and (a == b or places[-1][0] == a)):
            places[-1][1] = max(places[-1][1], b)
        else:
            places.append([a, b])
    variants = []
    for a, b in places:
        seen = [base[a:b]]
        for e in edits:
            piece, at = "", a
            for i1, i2, rep in e:
                if a <= i1 and i2 <= b and not (i1 == i2 == b and a < b):
                    piece += base[at:i1] + rep
                    at = i2
            piece += base[at:b]
            if piece not in seen:
                seen.append(piece)
        variants.append(seen)
    if math.prod(len(v) for v in variants) > limit:
        return []
    out = list(dict.fromkeys(texts))
    for choice in itertools.product(*variants):
        line, at = "", 0
        for (a, b), piece in zip(places, choice, strict=True):
            line += base[at:a] + piece
            at = b
        line += base[at:]
        if line not in out:
            out.append(line)
    return out


def doubtful(line: str, readings: list[dict], action: str, text: str | None) -> str:
    """Why an answer deserves a second look before it is saved, or "" when it doesn't.

    A reviewer's typed answer is wrong about one time in eight (`quality.slip_rates`),
    so a line typed for a question with readings must match one of them, or a line they
    make between them (`combinations`), letter for letter but for quote glyphs and
    spacing; and an answer with a straight quote where
    the book's line or readings use curly ones is a typing slip no model is needed for.
    """
    if text is None or action not in ("text", "heading", "caption"):
        return ""
    lines = [line, *(g["text"] for g in readings)]
    if any(c in line for line in lines for c in _CURLY) and any(c in text for c in "'\""):
        return "That has a straight quote where the book sets curly ones."
    texts = [g["text"] for g in readings]
    if len(texts) < 2:
        return ""
    made = combinations(texts, COMBINATIONS_CHECKED) or texts
    if _fold(text) not in {_fold(t) for t in made}:
        return "That matches none of the readings of this line. Check the scan once more."
    return ""


class RegionReview:
    """Flagged regions of a book and, for a golden book, its places that differ from the
    reference (`golden`); `rebuild` reruns the pipeline and returns new flags and places."""

    html = "regions.html"

    def __init__(
        self,
        pdf: Path,
        pages: list[PageText],
        regions: list[F.Flag],
        corrections: Corrections,
        rebuild: Callable[[], tuple[list[PageText], list[F.Flag], int, list[Disagreement]]],
        lang: str,
        guess_letter: Callable[[bytes, str], str] | None = None,
        golden: GoldenQuestions | None = None,
        book_root: Path | None = None,
    ):
        self.scan = Scan(pdf, pages)
        self.lang = lang
        self.guess_letter = guess_letter
        self._drafts: dict[str, str] = {}
        self.regions = regions
        self.corrections = corrections
        self._rebuild = rebuild
        self._lock = threading.Lock()
        self.applied = None
        self.golden = golden
        # Where the book's errata file lives (`errata.py`); None takes no misprints.
        self.book_root = book_root

    def state(self) -> dict:
        items = []
        noted = errata.load(self.book_root) if self.book_root else []
        for f in self.regions:
            page = self.scan.pages[f.page]
            c = self.corrections.for_flag(f)
            # Around sideways text the neighbouring lines are scraps too.
            context = "rotated" not in f.reasons
            item = asdict(f)
            item["readings"] = with_combinations(merged(item["readings"]))
            if item["readings"] and "text layer" not in item["readings"][0]["votes"]:
                first = item["readings"][0]
                item["readings"][0] = {**first, "votes": ["text layer", *first["votes"]]}
            items.append(
                {
                    **item,
                    "reasons": [F.REASONS[r] for r in f.reasons],
                    "white_space": "lost-line" in f.reasons,
                    "before": page.lines[f.first - 1].text
                    if context and 0 < f.first <= len(page.lines)
                    else "",
                    "after": page.lines[f.last + 1].text
                    if context and f.last + 1 < len(page.lines)
                    else "",
                    "answer": asdict(c) if c else None,
                    "errata": _errata_of(f, c, noted),
                    "draft": self._draft(f),
                    "turn": self._turn(f),
                }
            )
        if self.golden is not None:
            # Each place after the flags on its line, so a doubt there is asked first.
            both = [(0, i) for i in items] + [(1, i) for i in self.golden.state()]
            both.sort(key=lambda k_i: (k_i[1]["page"], k_i[1]["first"], k_i[0]))
            items = [i for _, i in both]
        return {"items": items, "actions": ACTIONS, "applied": self.applied}

    def _turn(self, f: F.Flag) -> int:
        c = self.corrections.for_flag(f)
        if c and c.turn:
            return c.turn
        return self.scan.turn(f.page, f.box, self.lang) if "rotated" in f.reasons else 0

    def read(self, key: str, turn: int) -> str:
        """Tesseract's reading of a region turned the way the human says is upright."""
        f = next(f for f in self.regions if f.key == key)
        return self.scan.read_box(f.page, f.box, self.lang, turn=turn)

    def _draft(self, f: F.Flag) -> str | None:
        """Tesseract's reading of text the text layer lacks or reads as scraps."""
        if not {"missing-text", "lost-line", "rotated"} & set(f.reasons) or f.box is None:
            return None
        if f.key not in self._drafts:
            if "lost-line" in f.reasons:
                self._drafts[f.key] = self.scan.read_gap(f.page, f.box, self.lang)
            else:
                turn = self._turn(f)
                self._drafts[f.key] = self.scan.read_box(f.page, f.box, self.lang, turn=turn)
        return self._drafts[f.key]

    def guess_initial(self, key: str) -> str:
        """A guess at the letter a drawn initial shows, from the word it begins."""
        f = next(f for f in self.regions if f.key == key)
        page = self.scan.pages[f.page]
        beside = corrections.lines_beside(page, f.box)
        if not beside or self.guess_letter is None:
            return ""
        with PDF_LOCK, pymupdf.open(self.scan.pdf) as doc:
            png = (
                doc[f.page - 1]
                .get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=pymupdf.Rect(*f.box))
                .tobytes("png")
            )
        return self.guess_letter(png, page.lines[beside[0]].text)

    def record(self, body: dict) -> dict:
        """The answer saved, or, the first time an answer looks like a slip (`doubtful`),
        a warning instead; the page sends it again with `confirm` to save it anyway.
        Warned answers are logged beside the answers, so the slip rate can be measured
        before and after the check. One answer is recorded at a time: the page's requests
        are served on threads, and two appends at once could cut each other's line."""
        with self._lock:
            return self._record(body)

    def _record(self, body: dict) -> dict:
        place = self.golden is not None and body["key"] in self.golden.items
        action = body.get("action", "text")
        if place:
            line, readings = self.golden.lines(body["key"])
            page = self.golden.items[body["key"]].page
            # The readings are of running text; a heading or caption there is typed.
            readings = readings if action == "text" else []
        else:
            flag = next(f for f in self.regions if f.key == body["key"])
            line, readings, page = flag.text, flag.readings, flag.page
        turn = int(body.get("turn") or 0)
        text = body.get("text")
        if place and (why := self.golden.refused(body["key"], action, text)):
            return {"warning": why, "refused": True}
        if not body.get("confirm") and (why := doubtful(line, readings, action, text)):
            entry = {
                "key": body["key"],
                "page": page,
                "text": text,
                "why": why,
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
            append_jsonl(self.corrections.path.with_name("warnings.jsonl"), entry)
            return {"warning": why}
        if place:
            return self.golden.record(body)
        if (fix := body.get("misprint")) is not None:
            found = self._misprints(flag, text if text is not None else flag.text, fix)
            if isinstance(found, str):
                return {"warning": found, "refused": True}
        else:
            found = []
        answer = self.corrections.record(flag, action, text, turn)
        for e in found:
            errata.save(self.book_root, e)
        noted = errata.load(self.book_root) if self.book_root else []
        return {**asdict(answer), "errata": _errata_of(flag, answer, noted)}

    def _misprints(self, flag: F.Flag, printed: str, fix: str) -> list[errata.Erratum] | str:
        """The errata that turn a region's lines as printed into `fix`, or why not."""
        if self.book_root is None:
            return "This review keeps no errata."
        old, new = printed.split("\n"), fix.split("\n")
        if len(old) != len(new):
            return "A misprint changes words within lines: keep the region's line breaks."
        lines = [ln.text for ln in self.scan.pages[flag.page].lines]
        # The region's lines as the answer says they are printed: the text layer may not.
        lines[flag.first : flag.first + len(old)] = old
        found = [
            errata.from_line(flag.page, o, n, lines, flag.first + k)
            for k, (o, n) in enumerate(zip(old, new, strict=True))
        ]
        found = [e for e in found if e is not None]
        return found or "The edition's line is the same as the printed one."

    def rebuild(self) -> dict:
        with self._lock, PDF_LOCK:
            pages, self.regions, self.applied, places = self._rebuild()
            self.scan = Scan(self.scan.pdf, pages)
            if self.golden is not None:
                self.golden = GoldenQuestions(places, self.golden.verdicts)
        return self.state()


# A double quote set as two single ones ("‘‘Een nachtwaker’’"); two closing marks before
# a letter are an apostrophe read twice ("’’m"), not a quote.
_DOUBLED = [(re.compile("‘‘"), "“"), (re.compile("’’(?![^\\W\\d_])"), "”")]


def _undoubled(text: str) -> str:
    for pattern, mark in _DOUBLED:
        text = pattern.sub(mark, text)
    return text


def with_combinations(readings: list[dict]) -> list[dict]:
    """The readings, and when there are few the lines they make between them place by
    place, each an option of its own ("combined")."""
    if len(readings) < 2:
        return readings
    texts = combinations([g["text"] for g in readings], OPTIONS)
    have = {g["text"] for g in readings}
    return readings + [{"text": t, "votes": ["combined"]} for t in texts if t not in have]


def merged(readings: list[dict]) -> list[dict]:
    """The readings with those that differ only in a double quote set as two single ones
    made one option, under the first one's text, with everyone's votes."""
    out: list[dict] = []
    seen: dict[str, dict] = {}
    for g in readings:
        key = _undoubled(g["text"])
        if key in seen:
            seen[key]["votes"] = [*seen[key]["votes"], *g["votes"]]
        else:
            seen[key] = {**g}
            out.append(seen[key])
    return out


def _errata_of(f: F.Flag, c: Correction | None, noted: list[errata.Erratum]) -> list[dict]:
    """The misprints recorded for a region's lines: those on its page whose printed words
    are in its text, or in its answer's."""
    texts = [t for t in (f.text, c and c.text) if t]
    return [asdict(e) for e in noted if e.page == f.page and any(e.printed in t for t in texts)]


def _trusted(headers, port: int) -> bool:
    """Whether a POST comes from this server's own pages: JSON, addressed to this server
    by a loopback name, and from a page of it when the browser says where from. A form or
    a page on another site can't send that, so it can't answer or rebuild in the user's name."""
    if headers.get_content_type() != "application/json":
        return False
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if headers.get("Host") not in hosts:
        return False
    origin = headers.get("Origin")
    return origin is None or origin in {f"http://{h}" for h in hosts}


def serve(review: RegionReview, port: int) -> None:
    page = (Path(__file__).parent / review.html).read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header(
                "Cache-Control", "max-age=3600" if content_type == "image/png" else "no-store"
            )
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, status: int = 200) -> None:
            self._send(json.dumps(data, ensure_ascii=False).encode(), "application/json", status)

        def do_GET(self) -> None:  # noqa: N802
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path == "/":
                    self._send(page, "text/html; charset=utf-8")
                elif url.path == "/api/state":
                    self._json(review.state())
                elif url.path == "/crop" and "box" in q:
                    box = tuple(float(v) for v in q["box"].split(","))
                    turn, out = int(q.get("turn", 0)), int(q.get("out", 0))
                    line = int(q["line"]) if "line" in q else None
                    mark = q.get("mark", "1") != "0"
                    gap = q.get("gap") == "1"
                    png = review.scan.crop_box(int(q["page"]), box, turn, out, line, mark, gap)
                    self._send(png, "image/png")
                elif url.path == "/crop":
                    out, mark = int(q.get("out", 0)), q.get("mark", "1") != "0"
                    first, last = int(q["first"]), int(q["last"])
                    png = review.scan.crop(int(q["page"]), first, last, out, mark)
                    self._send(png, "image/png")
                elif url.path == "/api/initial":
                    self._json({"letter": review.guess_initial(q["key"])})
                elif url.path == "/api/read":
                    self._json({"text": review.read(q["key"], int(q.get("turn", 0)))})
                elif url.path == "/favicon.ico":
                    self._send(b"", "image/x-icon", 204)
                elif url.path == "/page":
                    self._send(review.scan.full_page(int(q["page"])), "image/png")
                else:
                    self._send(b"not found", "text/plain", 404)
            except (KeyError, ValueError, IndexError, StopIteration) as exc:
                self._send(str(exc).encode(), "text/plain", 400)

        def do_POST(self) -> None:  # noqa: N802
            if not _trusted(self.headers, port):
                self._send(b"forbidden", "text/plain", 403)
                return
            path = urlparse(self.path).path
            if path == "/api/rebuild":
                try:
                    self._json(review.rebuild())
                except Exception as exc:  # noqa: BLE001 - the page says why, the server stays up
                    self._send(f"rebuild failed: {exc!r}".encode(), "text/plain", 500)
                return
            if path != "/api/verdict":
                self._send(b"not found", "text/plain", 404)
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self._json(review.record(body))
            except (KeyError, StopIteration) as exc:
                self._json({"error": f"unknown {exc}"}, 400)
            except (ValueError, TypeError) as exc:
                self._json({"error": f"bad request: {exc}"}, 400)

        def log_message(self, *args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
