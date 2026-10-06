"""Layout regions from page images, with DocLayout-YOLO (the `layout` dependency group).

Each page is rendered, and the model marks regions such as title, plain text,
figure, figure caption and page furniture ("abandon"). Regions are kept in PDF
points and cached per book in `stages/layout.json`; a page is analysed once.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

REPO = "juliozhao/DocLayout-YOLO-DocStructBench"
WEIGHTS = "doclayout_yolo_docstructbench_imgsz1024.pt"
IMAGE_SIZE = 1024
MIN_CONFIDENCE = 0.25


@dataclass(frozen=True)
class Region:
    label: str  # "title", "plain text", "figure", "figure_caption", "abandon", ...
    confidence: float
    x0: float
    y0: float
    x1: float
    y1: float


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
        if raw.get("weights") == WEIGHTS:
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
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
                image = pix.pil_image()
                result = model.predict(
                    image, imgsz=IMAGE_SIZE, conf=MIN_CONFIDENCE, device="mps", verbose=False
                )[0]
                done[n] = [
                    Region(result.names[int(c)], round(float(p), 3), *(v / zoom for v in box))
                    for box, c, p in zip(
                        result.boxes.xyxy.tolist(), result.boxes.cls, result.boxes.conf, strict=True
                    )
                ]
        blob = {
            "weights": WEIGHTS,
            "pages": {str(n): [asdict(r) for r in rs] for n, rs in sorted(done.items())},
        }
        cache.write_text(json.dumps(blob, indent=1))
    return {n: done[n] for n in numbers}
