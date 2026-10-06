"""Layout regions from page images, with DocLayout-YOLO (the `layout` dependency group).

Each page is rendered, and the model marks regions such as title, plain text,
figure, figure caption and page furniture ("abandon"). Regions are kept in PDF
points and cached per book in `stages/layout.json`; a page is analysed once.

A page with a picture and no text may be a landscape plate printed sideways.
The model is run on it turned a quarter both ways; text it finds then is the
caption, kept as one region marked `turned`. Which way it reads is left to OCR:
the model labels the strip under a figure a caption whichever side is up.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

REPO = "juliozhao/DocLayout-YOLO-DocStructBench"
WEIGHTS = "doclayout_yolo_docstructbench_imgsz1024.pt"
IMAGE_SIZE = 1024
MIN_CONFIDENCE = 0.25
# Bump when what is cached changes.
VERSION = 2
TEXT = {"figure_caption", "title", "plain text"}
# A page is tried turned when it holds a picture this sure and no text.
TURN_FIGURE_CONFIDENCE = 0.5


@dataclass(frozen=True)
class Region:
    label: str  # "title", "plain text", "figure", "figure_caption", "abandon", ...
    confidence: float
    x0: float
    y0: float
    x1: float
    y1: float
    turned: bool = False  # found on the page turned a quarter: text printed sideways


def available() -> bool:
    try:
        import doclayout_yolo  # noqa: F401
    except ImportError:
        return False
    return True


def detect(pdf: Path, numbers: list[int], cache: Path) -> dict[int, list[Region]]:
    done: dict[int, list[Region]] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("weights") == WEIGHTS and raw.get("version") == VERSION:
            done = {int(n): [Region(**r) for r in rs] for n, rs in raw["pages"].items()}
    todo = [n for n in numbers if n not in done]
    if todo:
        from doclayout_yolo import YOLOv10
        from huggingface_hub import hf_hub_download

        model = YOLOv10(hf_hub_download(REPO, WEIGHTS))
        with pymupdf.open(pdf) as doc:
            for n in todo:
                page = doc[n - 1]
                zoom = IMAGE_SIZE / max(page.rect.width, page.rect.height)
                image = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).pil_image()
                regions = [
                    Region(label, p, *(v / zoom for v in box))
                    for label, p, box in _predict(model, image, 0)
                ]
                if _maybe_sideways(regions):
                    regions += _sideways_caption(model, image, zoom)
                done[n] = regions
        blob = {
            "weights": WEIGHTS,
            "version": VERSION,
            "pages": {str(n): [asdict(r) for r in rs] for n, rs in sorted(done.items())},
        }
        cache.write_text(json.dumps(blob, indent=1))
    return {n: done[n] for n in numbers}


def _predict(model, image, turn: int) -> list[tuple[str, float, tuple[float, ...]]]:
    """Regions in the image turned `turn` degrees clockwise, boxed in the upright image."""
    turned = image.rotate(-turn, expand=True)
    result = model.predict(
        turned, imgsz=IMAGE_SIZE, conf=MIN_CONFIDENCE, device="mps", verbose=False
    )[0]
    return [
        (result.names[int(c)], round(float(p), 3), _unturn(box, turn, image.width, image.height))
        for box, c, p in zip(
            result.boxes.xyxy.tolist(), result.boxes.cls, result.boxes.conf, strict=True
        )
    ]


def _unturn(box: list[float], turn: int, width: int, height: int) -> tuple[float, ...]:
    """A box in the image turned `turn` degrees clockwise, in the upright image."""
    u0, v0, u1, v1 = box
    if turn == 90:
        return (v0, height - u1, v1, height - u0)
    if turn == 270:
        return (width - v1, u0, width - v0, u1)
    return (u0, v0, u1, v1)


def _maybe_sideways(regions: list[Region]) -> bool:
    return any(
        r.label == "figure" and r.confidence >= TURN_FIGURE_CONFIDENCE for r in regions
    ) and not any(r.label in TEXT for r in regions)


def _sideways_caption(model, image, zoom: float) -> list[Region]:
    """The text the model finds on the page turned a quarter, as one region."""
    found = {t: [r for r in _predict(model, image, t) if r[0] in TEXT] for t in (90, 270)}
    best = max(found.values(), key=lambda rs: sum(p for _, p, _ in rs))
    if not best:
        return []
    boxes = [box for _, _, box in best]
    return [
        Region(
            "figure_caption",
            max(p for _, p, _ in best),
            min(b[0] for b in boxes) / zoom,
            min(b[1] for b in boxes) / zoom,
            max(b[2] for b in boxes) / zoom,
            max(b[3] for b in boxes) / zoom,
            turned=True,
        )
    ]
