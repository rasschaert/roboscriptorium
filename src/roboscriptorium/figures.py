"""Pictures from the scan in the book: which ones, cut out upright, and where they go.

A picture is a figure the layout model found on a body page, sure enough of it,
unless a human answered its region as something else (dropped, a decorated
initial). Its caption is one a human gave on the same page, or else the reading
of a sideways plate's caption. A sideways plate is turned upright: by the turn a
human gave its caption, or else the quarter turn in which its caption reads. A
picture's box is trimmed where it overlaps a caption, and the picture goes after
the last block that starts above it, so it never splits a paragraph.
"""

import bisect
import io
from dataclasses import dataclass

import pymupdf
from PIL import Image

from roboscriptorium import ocr
from roboscriptorium.corrections import Correction, Corrections, _located
from roboscriptorium.ir import Block, Figure
from roboscriptorium.layout import Region
from roboscriptorium.pdf import PageText

FIGURE_CONFIDENCE = 0.5
DPI = 300
MAX_SIDE = 1600  # pixels on the long side of a picture in the book
JPEG_QUALITY = 85
PAD = 2  # points of page around a picture's box
# Points kept clear between a picture and a caption it was trimmed off, beyond PAD.
TRIM_GAP = PAD + 2
# An answer belongs to a region when their boxes differ by at most this many points.
SAME_BOX = 1.0
OCR_DPI = 300


@dataclass(frozen=True)
class Picture:
    page: int
    box: tuple[float, float, float, float]
    turn: int  # degrees clockwise that make it upright
    caption: str

    @property
    def name(self) -> str:
        x0, y0, _, _ = self.box
        return f"p{self.page:04}-{round(y0):04}-{round(x0):04}.jpg"


def _box(r: Region) -> tuple[float, float, float, float]:
    return (r.x0, r.y0, r.x1, r.y1)


def _same(a, b) -> bool:
    return all(abs(u - v) <= SAME_BOX for u, v in zip(a, b, strict=True))


def _answer(answers: list[Correction], box) -> Correction | None:
    return next((c for c in answers if c.box and _same(c.box, box)), None)


def select(
    doc: pymupdf.Document,
    pages: list[PageText],
    regions: dict[int, list[Region]],
    answers: Corrections,
    lang: str,
) -> list[Picture]:
    """The pictures on the body pages, each with its turn and caption."""
    pictures = []
    for page in pages:
        found = regions.get(page.number, [])
        on_page = [c for c in answers.by_key.values() if c.page == page.number]
        figures = [r for r in found if r.label == "figure" and r.confidence >= FIGURE_CONFIDENCE]
        captions = [_box(r) for r in found if r.label == "figure_caption" or r.turned]
        kept = []
        for r in figures:
            answer = _answer(on_page, _box(r))
            if answer is None or answer.action == "image":
                kept.append(_without(_box(r), captions))
        if not kept:
            continue
        turn, read = _sideways(doc, page.number, found, on_page, lang)
        given = _captions(on_page, kept, page)
        default = read if len(kept) == 1 else ""
        pictures += [Picture(page.number, b, turn, given.get(b, default)) for b in kept]
    return pictures


def _without(box, captions: list) -> tuple[float, float, float, float]:
    """A picture's box trimmed on the side where a caption overlaps it."""
    x0, y0, x1, y1 = box
    for c0, d0, c1, d1 in captions:
        if c0 >= x1 or c1 <= x0 or d0 >= y1 or d1 <= y0:
            continue
        cx, cy = (c0 + c1) / 2, (d0 + d1) / 2
        if c1 - c0 < d1 - d0:  # a tall caption beside the picture: trim left or right
            if cx > (x0 + x1) / 2:
                x1 = min(x1, c0 - TRIM_GAP)
            else:
                x0 = max(x0, c1 + TRIM_GAP)
        elif cy > (y0 + y1) / 2:
            y1 = min(y1, d0 - TRIM_GAP)
        else:
            y0 = max(y0, d1 + TRIM_GAP)
    return (x0, y0, x1, y1)


def _sideways(doc, number: int, found: list[Region], answers: list[Correction], lang: str):
    """A sideways plate's turn and its caption as read upright; (0, "") on an upright page."""
    sideways = [r for r in found if r.turned]
    if not sideways:
        return 0, ""
    zoom = pymupdf.Matrix(OCR_DPI / 72, OCR_DPI / 72)
    png = doc[number - 1].get_pixmap(matrix=zoom, clip=pymupdf.Rect(_box(sideways[0])))
    turn, read = ocr.read_sideways(png.tobytes("png"), lang)
    answer = _answer(answers, _box(sideways[0]))
    return (answer.turn if answer is not None and answer.turn else turn), read


def _caption_box(c: Correction, page: PageText) -> tuple[float, float, float, float] | None:
    """Where a caption answer sits: its region's box, or else around the lines it names."""
    if c.box:
        return c.box
    c = _located(page, c)
    if c is None or c.last < c.first:
        return None
    lines = page.lines[c.first : c.last + 1]
    return (
        min(ln.x0 for ln in lines),
        min(ln.y0 for ln in lines),
        max(ln.x1 for ln in lines),
        max(ln.y1 for ln in lines),
    )


def _captions(answers: list[Correction], boxes: list, page: PageText) -> dict:
    """Each caption a human gave on the page, with the picture whose centre is nearest."""
    out: dict = {}
    for c in answers:
        if c.action != "caption" or (box := _caption_box(c, page)) is None:
            continue
        text = " ".join((c.text if c.text is not None else c.original).split())
        if not text:
            continue
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        near = min(
            boxes, key=lambda b: ((b[0] + b[2]) / 2 - cx) ** 2 + ((b[1] + b[3]) / 2 - cy) ** 2
        )
        out[near] = f"{out[near]} {text}".strip() if near in out else text
    return out


def render(doc: pymupdf.Document, picture: Picture) -> bytes:
    """The picture as an upright JPEG."""
    x0, y0, x1, y1 = picture.box
    page = doc[picture.page - 1]
    clip = pymupdf.Rect(x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD) & page.rect
    zoom = pymupdf.Matrix(DPI / 72, DPI / 72)
    image = page.get_pixmap(matrix=zoom, clip=clip).pil_image().convert("RGB")
    if picture.turn:
        image = image.rotate(-picture.turn, expand=True)
    image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    image.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def place(blocks: list[Block], pictures: list[Picture], pages: list[PageText]) -> list[Block]:
    """The blocks with each picture after the last block that starts above it.

    `pages` is the text layer the blocks' line references point into.
    """
    by_number = {p.number: p for p in pages}

    def start(block: Block) -> tuple[int, float]:
        ref = block.sources[0]
        lines = by_number[ref.page].lines
        return (ref.page, lines[ref.line].y0 if ref.line < len(lines) else 0.0)

    starts = [start(b) for b in blocks]
    out = list(blocks)
    for picture in sorted(pictures, key=lambda p: (p.page, p.box[1]), reverse=True):
        at = bisect.bisect_right(starts, (picture.page, picture.box[1]))
        out.insert(at, Figure(picture.name, picture.page, picture.box, picture.caption))
    return out
