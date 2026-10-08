"""Try PP-DocLayoutV3 as the spotter, scored by what reads its regions.

Writes its regions in `layout.py`'s cache format into a copy of the book at
work/probes/spotter/ppv3/<book>/ (same directory name, so `eval` finds the verdicts;
the other caches are cloned, so only what depends on the regions runs again). Score
the copy and the original with the same settings and compare.

    uv run --with transformers --with accelerate python experiments/probe_spotter.py \\
        work/<book> <first> <last>
"""

import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

import pymupdf
import torch
from transformers import AutoImageProcessor, AutoModelForObjectDetection

from roboscriptorium import layout
from roboscriptorium.files import write_atomic
from roboscriptorium.layout import Region

REPO = "PaddlePaddle/PP-DocLayoutV3_safetensors"
LONG_SIDE = 1600
# PP-DocLayoutV3's classes as the labels the pipeline reads (figure, figure_caption,
# title, plain text, abandon for page furniture).
LABELS = {
    "image": "figure",
    "chart": "figure",
    "seal": "figure",
    "figure_title": "figure_caption",
    "vision_footnote": "figure_caption",
    "doc_title": "title",
    "paragraph_title": "title",
    "header": "abandon",
    "footer": "abandon",
    "number": "abandon",
    "table": "table",
}
OUT = Path("work/probes/spotter/ppv3")

book_dir, first, last = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
processor = AutoImageProcessor.from_pretrained(REPO)
model = AutoModelForObjectDetection.from_pretrained(REPO).eval()


def predict(_model, image, turn: int) -> list[tuple[str, float, tuple[float, ...]]]:
    """`layout._predict` for PP-DocLayoutV3: regions in the image turned `turn` degrees
    clockwise, boxed in the upright image."""
    turned = image.rotate(-turn, expand=True).convert("RGB")
    with torch.no_grad():
        raw = model(**processor(images=turned, return_tensors="pt"))
    found = processor.post_process_object_detection(
        raw, threshold=layout.MIN_CONFIDENCE, target_sizes=[(turned.height, turned.width)]
    )[0]
    out = []
    for score, label, box in zip(found["scores"], found["labels"], found["boxes"], strict=True):
        name = model.config.id2label[int(label)]
        out.append(
            (
                LABELS.get(name, "plain text"),
                round(float(score), 3),
                layout._unturn(box.tolist(), turn, image.width, image.height),
            )
        )
    return out


layout._predict = predict  # the sideways-caption pass uses it too
copy = OUT / book_dir.name
if not copy.exists():
    (copy / "stages").mkdir(parents=True)
    (copy / "source.pdf").symlink_to((book_dir / "source.pdf").resolve())
    shutil.copy(book_dir / "book.toml", copy / "book.toml")
    for f in (book_dir / "stages").iterdir():
        if f.name != "layout.json" and f.is_file():
            subprocess.run(["cp", "-c", str(f), str(copy / "stages" / f.name)], check=True)

pages: dict[int, list[Region]] = {}
start = time.time()
with pymupdf.open(book_dir / "source.pdf") as doc:
    for n in range(first, last + 1):
        page = doc[n - 1]
        zoom = LONG_SIDE / max(page.rect.width, page.rect.height)
        image = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).pil_image()
        regions = [
            Region(label, p, *(v / zoom for v in box)) for label, p, box in predict(model, image, 0)
        ]
        if layout._maybe_sideways(regions):
            regions += layout._sideways_caption(model, image, zoom)
        pages[n] = regions
print(f"{len(pages)} pages in {time.time() - start:.0f} s")

ours = json.loads((book_dir / "stages" / "layout.json").read_text())["pages"]
for name in ("figure", "figure_caption", "title", "abandon"):
    a = sum(r["label"] == name for n in pages for r in ours.get(str(n), []))
    b = sum(r.label == name for rs in pages.values() for r in rs)
    print(f"{name:15} DocLayout-YOLO {a:4}   PP-DocLayoutV3 {b:4}")
blob = {
    "weights": layout.WEIGHTS,  # so `layout.detect` takes this cache as its own
    "version": layout.VERSION,
    "spotter": REPO,
    "pages": {str(n): [asdict(r) for r in rs] for n, rs in sorted(pages.items())},
}
write_atomic(copy / "stages" / "layout.json", json.dumps(blob, indent=1))
print(f"regions in {copy / 'stages' / 'layout.json'}")
