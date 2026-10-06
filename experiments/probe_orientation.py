"""Probe: which quarter turn makes a page upright, by running the layout model on each turn.

Prints, per page and turn, the text-like regions DocLayout-YOLO finds (caption,
title, plain text) with their summed confidence.

    uv run python experiments/probe_orientation.py work/the-story-of-doctor-dolittle--stokes-1920 \
        6:90 25:90 57:90 83:90 87:90 90:90 107:90 198:0 200:90 36:0
"""

import sys
from pathlib import Path

import pymupdf
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download

from roboscriptorium import ocr
from roboscriptorium.layout import IMAGE_SIZE, REPO, WEIGHTS
from roboscriptorium.review import OCR_DPI, _turned, _words

TEXTY = {"figure_caption", "title", "plain text"}


def main() -> None:
    book = Path(sys.argv[1])
    model = YOLOv10(hf_hub_download(REPO, WEIGHTS))
    with pymupdf.open(book / "source.pdf") as doc:
        for arg in sys.argv[2:]:
            n, _, truth = arg.partition(":")
            page = doc[int(n) - 1]
            zoom = IMAGE_SIZE / max(page.rect.width, page.rect.height)
            image = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).pil_image()
            scores, boxes = {}, {}
            for turn in (0, 90, 180, 270):
                result = model.predict(
                    image.rotate(-turn, expand=True),
                    imgsz=IMAGE_SIZE,
                    conf=0.25,
                    device="mps",
                    verbose=False,
                )[0]
                found = [
                    (result.names[int(c)], round(float(p), 2), box)
                    for c, p, box in zip(
                        result.boxes.cls, result.boxes.conf, result.boxes.xyxy.tolist(), strict=True
                    )
                ]
                boxes[turn] = [b for label, _, b in found if label in TEXTY]
                scores[turn] = sum(p for label, p, _ in found if label in TEXTY)
                print(f"p{n} turn {turn:3}: {scores[turn]:.2f} {[f[:2] for f in found]}")
            best = max(scores, key=scores.get)
            if best in (90, 270):
                # The layout model can't tell 90 from 270: read its text boxes both ways.
                h = image.height if best == 90 else image.width
                words = {90: 0, 270: 0}
                for u0, v0, u1, v1 in boxes[best]:
                    if best == 90:  # rotated (u, v) -> page (v, h - u)
                        rect = pymupdf.Rect(v0, h - u1, v1, h - u0) / zoom
                    else:  # rotated (u, v) -> page (w - v, u)
                        rect = pymupdf.Rect(image.width - v1, u0, image.width - v0, u1) / zoom
                    pix = page.get_pixmap(
                        matrix=pymupdf.Matrix(OCR_DPI / 72, OCR_DPI / 72), clip=rect
                    )
                    for t in words:
                        text = ocr.tesseract(_turned(pix, t), "eng", False)
                        words[t] += _words(text)
                        print(f"   read {t}: {text.strip()[:70]!r}")
                best = max(words, key=words.get)
            print(f"p{n} best {best} truth {truth or '?'}\n")


if __name__ == "__main__":
    main()
