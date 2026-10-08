"""Local web pages for reviewing a book next to its scan, served on 127.0.0.1.

- Regions (`roboscriptorium review <book>`): what the pipeline flagged as not
  plain running text. Each shows a crop of the scan and takes an answer: running
  text, heading, drop, image, initial or caption, optionally with the text as
  printed. A region with a box can be turned and read again. Answers apply on
  the next build, which the page can start.
- Disagreements (`roboscriptorium golden review <book>`): where a golden book's
  output and reference differ. Each takes a verdict: the reference is right (a
  pipeline mistake), the scan prints the output, something else, or unsure.
"""

import io
import json
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

from roboscriptorium import corrections, ocr
from roboscriptorium import flags as F
from roboscriptorium.corrections import ACTIONS, Corrections
from roboscriptorium.disagreements import PIPELINE, SCAN, UNSURE, Disagreement, Verdicts
from roboscriptorium.pdf import PDF_LOCK, PageText

# Crops show this many lines around the disagreement, at this zoom (PDF points → pixels).
CROP_CONTEXT_LINES = 1
# Each zoom-out step widens a crop by this much on every side, in PDF points.
ZOOM_OUT_STEP = 80
CROP_ZOOM = 2.5
PAGE_ZOOM = 1.5
OCR_DPI = 300


def guess_category(d: Disagreement) -> str:
    """The likeliest pipeline mistake, preselected in the page."""
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


def _turned(pix: pymupdf.Pixmap, turn: int) -> bytes:
    """PNG bytes of a pixmap turned `turn` degrees clockwise."""
    if not turn:
        return pix.tobytes("png")
    buf = io.BytesIO()
    pix.pil_image().rotate(-turn, expand=True).save(buf, "PNG")
    return buf.getvalue()


# Highlights are drawn beside or beneath the print, never over it, so a mark the reviewer
# is asked about (a quote, a dash) is never covered: a faint tint behind the lines in
# question, a soft outline around a region, an underline beneath a doubt's place.
TINT = (1, 0.93, 0.55)
TINT_OPACITY = 0.18
OUTLINE = (0.85, 0.65, 0.2)
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
    ) -> bytes:
        """A region with some of the page around it.

        `turn` (degrees clockwise) shows sideways text upright, cropped to the region;
        `out` zoom-out steps show more of the page around it. With `line`, the box is a
        place in that line (an OCR doubt): the line is tinted and the place underlined.
        `mark` False draws nothing.
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
            elif mark:
                pdf_page.draw_rect(target + (-1, -1, 1, 1), color=OUTLINE, width=0.8)
            pix = pdf_page.get_pixmap(matrix=pymupdf.Matrix(CROP_ZOOM, CROP_ZOOM), clip=clip)
            return _turned(pix, turn)

    def turn(self, page_number: int, box: tuple[float, float, float, float], lang: str) -> int:
        """Degrees clockwise that make sideways text upright: the quarter turn that reads."""
        key = (page_number, box)
        if key not in self._turns:
            readings = {t: self.read_box(page_number, box, lang, turn=t) for t in (90, 270)}
            self._turns[key] = max(readings, key=lambda t: ocr.words(readings[t]))
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
        with PDF_LOCK, pymupdf.open(self.pdf) as doc:
            zoom = OCR_DPI / 72
            pix = doc[page_number - 1].get_pixmap(
                matrix=pymupdf.Matrix(zoom, zoom), clip=pymupdf.Rect(*box)
            )
            return ocr.tesseract(_turned(pix, turn), lang, single_char)

    def full_page(self, page_number: int) -> bytes:
        with PDF_LOCK, pymupdf.open(self.pdf) as doc:
            return (
                doc[page_number - 1]
                .get_pixmap(matrix=pymupdf.Matrix(PAGE_ZOOM, PAGE_ZOOM))
                .tobytes("png")
            )


class Review:
    html = "review.html"

    def __init__(
        self, pdf: Path, pages: list[PageText], items: list[Disagreement], verdicts: Verdicts
    ):
        self.scan = Scan(pdf, pages)
        self.items = {d.key: d for d in items}
        self.order = [d.key for d in items]
        self.verdicts = verdicts

    def state(self) -> dict:
        items = []
        for key in self.order:
            d = self.items[key]
            v = self.verdicts.by_key.get(key)
            items.append(
                {**asdict(d), "guess": guess_category(d), "verdict": asdict(v) if v else None}
            )
        return {"items": items, "pipeline": PIPELINE, "scan": SCAN}

    def record(self, body: dict) -> dict:
        d = self.items[body["key"]]
        kind = body["kind"]
        if kind == "reference":
            truth, category = d.want, body["category"]
        elif kind == "output":
            truth, category = d.got, body["category"]
        elif kind == "other":
            truth, category = body["truth"], body["category"]
        else:
            truth, category = None, UNSURE
        return asdict(self.verdicts.record(d, truth, category, body.get("note", "")))


_CURLY = "‘’“”"
_STRAIGHT = str.maketrans("‘’“”", "''\"\"")


def _fold(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).translate(_STRAIGHT).split())


def doubtful(flag: F.Flag, action: str, text: str | None) -> str:
    """Why an answer deserves a second look before it is saved, or "" when it doesn't.

    A reviewer's typed answer is wrong about one time in eight (`quality.slip_rates`),
    so a line typed for a question with readings must match one of them, letter for
    letter but for quote glyphs and spacing; and an answer with a straight quote where
    the book's line or readings use curly ones is a typing slip no model is needed for.
    """
    if text is None or action not in ("text", "heading", "caption"):
        return ""
    lines = [flag.text, *(g["text"] for g in flag.readings)]
    if any(c in line for line in lines for c in _CURLY) and any(c in text for c in "'\""):
        return "That has a straight quote where the book sets curly ones."
    if len(flag.readings) > 1 and _fold(text) not in {_fold(g["text"]) for g in flag.readings}:
        return "That matches none of the readings of this line. Check the scan once more."
    return ""


class RegionReview:
    """Flagged regions of a book; `rebuild` reruns the pipeline and returns new flags."""

    html = "regions.html"

    def __init__(
        self,
        pdf: Path,
        pages: list[PageText],
        regions: list[F.Flag],
        corrections: Corrections,
        rebuild: Callable[[], tuple[list[PageText], list[F.Flag], int]],
        lang: str,
        guess_letter: Callable[[bytes, str], str] | None = None,
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

    def state(self) -> dict:
        items = []
        for f in self.regions:
            page = self.scan.pages[f.page]
            c = self.corrections.for_flag(f)
            # Around sideways text the neighbouring lines are scraps too.
            context = "rotated" not in f.reasons
            items.append(
                {
                    **asdict(f),
                    "reasons": [F.REASONS[r] for r in f.reasons],
                    "before": page.lines[f.first - 1].text
                    if context and 0 < f.first <= len(page.lines)
                    else "",
                    "after": page.lines[f.last + 1].text
                    if context and f.last + 1 < len(page.lines)
                    else "",
                    "answer": asdict(c) if c else None,
                    "draft": self._draft(f),
                    "turn": self._turn(f),
                }
            )
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
        if not {"missing-text", "rotated"} & set(f.reasons) or f.box is None:
            return None
        if f.key not in self._drafts:
            self._drafts[f.key] = self.scan.read_box(f.page, f.box, self.lang, turn=self._turn(f))
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
        before and after the check."""
        flag = next(f for f in self.regions if f.key == body["key"])
        turn = int(body.get("turn") or 0)
        text = body.get("text")
        if not body.get("confirm") and (why := doubtful(flag, body["action"], text)):
            path = self.corrections.path.with_name("warnings.jsonl")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a") as f:
                entry = {
                    "key": flag.key,
                    "page": flag.page,
                    "text": text,
                    "why": why,
                    "at": datetime.now(UTC).isoformat(timespec="seconds"),
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return {"warning": why}
        return asdict(self.corrections.record(flag, body["action"], text, turn))

    def rebuild(self) -> dict:
        with self._lock, PDF_LOCK:
            pages, self.regions, self.applied = self._rebuild()
            self.scan = Scan(self.scan.pdf, pages)
        return self.state()


def serve(review: Review | RegionReview, port: int) -> None:
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
                    png = review.scan.crop_box(int(q["page"]), box, turn, out, line, mark)
                    self._send(png, "image/png")
                elif url.path == "/crop":
                    out, mark = int(q.get("out", 0)), q.get("mark", "1") != "0"
                    first, last = int(q["first"]), int(q["last"])
                    png = review.scan.crop(int(q["page"]), first, last, out, mark)
                    self._send(png, "image/png")
                elif url.path == "/api/initial" and isinstance(review, RegionReview):
                    self._json({"letter": review.guess_initial(q["key"])})
                elif url.path == "/api/read" and isinstance(review, RegionReview):
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
            path = urlparse(self.path).path
            if path == "/api/rebuild" and isinstance(review, RegionReview):
                self._json(review.rebuild())
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
