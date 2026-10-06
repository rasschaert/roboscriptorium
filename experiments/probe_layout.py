"""Probe DocLayout-YOLO: what layout regions does it find on tricky pages?

uv run --group layout python experiments/probe_layout.py

Renders each sample page, runs the model, prints the regions and writes an
annotated image per page to work/layout-probe/.
"""

import time
from pathlib import Path

import pymupdf
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download

SAMPLE = {
    "the-story-of-doctor-dolittle--stokes-1920": [23, 29, 36, 51, 58, 70, 97, 200],
    "de-aanslag--calibre-pdf": [6, 70, 152],
    "sense-and-sensibility--tauchnitz-1864": [7, 60],
    "the-nature-of-a-crime--doubleday-1924": [25, 52],
    "boze-tongen--prometheus-2002": [11, 12, 300],
    "lady-into-fox--chatto-1922": [13, 40],
}
OUT = Path("work/layout-probe")
LONG_SIDE = 1024


def render(pdf: Path, number: int, dest: Path) -> Path:
    with pymupdf.open(pdf) as doc:
        page = doc[number - 1]
        zoom = LONG_SIDE / max(page.rect.width, page.rect.height)
        page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(dest)
    return dest


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    weights = hf_hub_download(
        "juliozhao/DocLayout-YOLO-DocStructBench", "doclayout_yolo_docstructbench_imgsz1024.pt"
    )
    model = YOLOv10(weights)
    for book, pages in SAMPLE.items():
        pdf = Path("work") / book / "source.pdf"
        for n in pages:
            image = render(pdf, n, OUT / f"{book}-p{n}.png")
            t0 = time.time()
            result = model.predict(str(image), imgsz=LONG_SIDE, conf=0.25, device="mps", verbose=False)[0]
            took = time.time() - t0
            result.save(filename=str(OUT / f"{book}-p{n}-layout.png"))
            names = result.names
            regions = sorted(
                (
                    (float(b[1]), names[int(c)], float(p))
                    for b, c, p in zip(
                        result.boxes.xyxy.tolist(), result.boxes.cls, result.boxes.conf, strict=True
                    )
                ),
                key=lambda r: r[0],
            )
            found = ", ".join(f"{name} {conf:.2f} @y{y:.0f}" for y, name, conf in regions)
            print(f"{book} p{n} ({took:.2f}s): {found}")


if __name__ == "__main__":
    main()
