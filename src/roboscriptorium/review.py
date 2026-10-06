"""A local web page for reviewing disagreements next to the scan.

`roboscriptorium review <book>` serves it on 127.0.0.1. Each disagreement shows
a crop of the scan, the output and the reference in context, and takes a
verdict: the reference is right (a pipeline mistake), the scan prints the
output, something else, or unsure.
"""

import json
import re
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pymupdf

from roboscriptorium.disagreements import PIPELINE, SCAN, UNSURE, Disagreement, Verdicts
from roboscriptorium.pdf import PageText

# Crops show this many lines around the disagreement, at this zoom (PDF points → pixels).
CROP_CONTEXT_LINES = 1
CROP_ZOOM = 2.5
PAGE_ZOOM = 1.5


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


class Review:
    def __init__(
        self, pdf: Path, pages: list[PageText], items: list[Disagreement], verdicts: Verdicts
    ):
        self.pdf = pdf
        self.pages = {p.number: p for p in pages}
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

    def crop(self, page_number: int, first: int, last: int) -> bytes:
        page = self.pages[page_number]
        lo = max(0, first - CROP_CONTEXT_LINES)
        hi = min(len(page.lines) - 1, last + CROP_CONTEXT_LINES)
        x0 = min(ln.x0 for ln in page.lines) - 6
        x1 = max(ln.x1 for ln in page.lines) + 6
        target = pymupdf.Rect(x0, page.lines[first].y0 - 2, x1, page.lines[last].y1 + 2)
        clip = pymupdf.Rect(x0, page.lines[lo].y0 - 6, x1, page.lines[hi].y1 + 6)
        with pymupdf.open(self.pdf) as doc:
            pdf_page = doc[page_number - 1]
            pdf_page.draw_rect(target, color=(0.9, 0.6, 0), fill=(1, 0.85, 0.3), fill_opacity=0.25)
            pix = pdf_page.get_pixmap(matrix=pymupdf.Matrix(CROP_ZOOM, CROP_ZOOM), clip=clip)
            return pix.tobytes("png")

    def full_page(self, page_number: int) -> bytes:
        with pymupdf.open(self.pdf) as doc:
            return (
                doc[page_number - 1]
                .get_pixmap(matrix=pymupdf.Matrix(PAGE_ZOOM, PAGE_ZOOM))
                .tobytes("png")
            )

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


def serve(review: Review, port: int) -> None:
    page = (Path(__file__).parent / "review.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header(
                "Cache-Control", "no-store" if "json" in content_type else "max-age=3600"
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
                elif url.path == "/crop":
                    png = review.crop(int(q["page"]), int(q["first"]), int(q["last"]))
                    self._send(png, "image/png")
                elif url.path == "/page":
                    self._send(review.full_page(int(q["page"])), "image/png")
                else:
                    self._send(b"not found", "text/plain", 404)
            except (KeyError, ValueError, IndexError) as exc:
                self._send(str(exc).encode(), "text/plain", 400)

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/verdict":
                self._send(b"not found", "text/plain", 404)
                return
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            try:
                self._json(review.record(body))
            except KeyError as exc:
                self._json({"error": f"unknown {exc}"}, 400)

        def log_message(self, *args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
