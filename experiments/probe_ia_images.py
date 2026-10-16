"""Readers on Internet Archive's own page images: reader set v1's lines of a public book,
cut from the JP2 the PDF was compressed from instead of the PDF, read by the readers in
use, scored like `tryout.py run reader` (the set's truth, `fold`).

The n-th leaf with addToAccessFormats is PDF page n; its crop box gives the scale, and
the PDF page is found in the leaf by template matching (rotation and crop make the box
alone unreliable). Crops are saved in work/probes/ia-images/ to look at.

    PYTHONPATH=experiments uv run python experiments/probe_ia_images.py [book]
"""

import io
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image
from rapidfuzz.distance import Levenshtein
from tryout import fold, load_set

from roboscriptorium.config import Settings
from roboscriptorium import readers

book_name = sys.argv[1] if len(sys.argv) > 1 else "the-nature-of-a-crime--doubleday-1924"
OUT = Path("work/probes/ia-images")
OUT.mkdir(parents=True, exist_ok=True)
books, items = load_set()
items = [i for i in items if i["book"] == book_name]
root = Path("work") / book_name
scandata = ET.parse(next((root / "ia").glob("*_scandata.xml")))
leaves = [p for p in scandata.iter("page") if p.findtext("addToAccessFormats") == "true"]
archive = zipfile.ZipFile(next((root / "ia").glob("*_jp2.zip")))
names = {int(re.search(r"_(\d+)\.jp2$", n).group(1)): n for n in archive.namelist() if n.endswith(".jp2")}
doc = pymupdf.open(root / "source.pdf")
settings = Settings.from_env()
placed: dict[int, tuple[np.ndarray, float, int, int, float]] = {}


def place(number: int):
    """The leaf image of PDF page `number`, pixels per point, the page's offset in it, and
    the match score."""
    if number in placed:
        return placed[number]
    leaf = leaves[number - 1]
    image = np.array(Image.open(io.BytesIO(archive.read(names[int(leaf.get("leafNum"))]))).convert("L"))
    page = doc[number - 1]
    scale = float(leaf.find("cropBox/w").text) / page.rect.width
    small = 0.25
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale * small, scale * small), colorspace=pymupdf.csGRAY)
    template = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    haystack = cv2.resize(image, None, fx=small, fy=small, interpolation=cv2.INTER_AREA)
    res = cv2.matchTemplate(haystack, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, (x, y) = cv2.minMaxLoc(res)
    placed[number] = (image, scale, int(x / small), int(y / small), score)
    return placed[number]


reads = {"pdf": {}, "jp2": {}}
cache = OUT / f"{book_name}.json"
done = json.loads(cache.read_text()) if cache.exists() else {}
for n, it in enumerate(items, 1):
    parts = it["cache_key"].split(":")
    page_no = parts[0]
    x0, y0, x1, y1 = map(float, parts[3].split(","))
    if len(parts) > 4:
        top, bottom = map(float, parts[4].split("-"))
    else:
        top, bottom = y0 - readers.LINE_PAD, y1 + readers.LINE_PAD
    em = y1 - y0
    image, scale, ox, oy, score = place(int(page_no))
    clip = [int(ox + (x0 - em) * scale), int(oy + top * scale), int(ox + (x1 + em) * scale), int(oy + bottom * scale)]
    crop = Image.fromarray(image[max(0, clip[1]) : clip[3], max(0, clip[0]) : clip[2]])
    buf = io.BytesIO()
    crop.save(buf, "PNG")
    jp2 = buf.getvalue()
    (OUT / f"{it['id'].replace(':', '_')}.png").write_bytes(jp2)
    (OUT / f"{it['id'].replace(':', '_')}-pdf.png").write_bytes(it["png"])
    for kind, png in (("pdf", it["png"]), ("jp2", jp2)):
        for model in ("glm-ocr", "qwen"):
            key = f"{it['id']}|{kind}|{model}"
            if key not in done:
                if model == "glm-ocr":
                    done[key] = readers.read_line(png, settings.ocr_model, settings.ollama_url)
                else:
                    done[key] = readers.transcribe(png, settings.read_model, settings.ollama_url, books[book_name]["prompt"])
                cache.write_text(json.dumps(done, ensure_ascii=False))
    if n % 10 == 0:
        print(f"  {n}/{len(items)} lines; page {page_no} match {score:.2f}", flush=True)

print(f"{book_name}: {len(items)} lines; page matches {min(s for *_, s in placed.values()):.2f}–{max(s for *_, s in placed.values()):.2f}")
for model in ("glm-ocr", "qwen"):
    for stratum in ("hard", "control"):
        group = [i for i in items if i["stratum"] == stratum]
        row = []
        for kind in ("pdf", "jp2"):
            right = sum(fold(done[f"{i['id']}|{kind}|{model}"]) == fold(i["truth"]) for i in group)
            edits = sum(Levenshtein.distance(fold(done[f"{i['id']}|{kind}|{model}"]), fold(i["truth"])) for i in group)
            chars = sum(len(fold(i["truth"])) for i in group)
            row.append(f"{kind} {right}/{len(group)} right, CER {edits / max(1, chars):.2%}")
        print(f"  {model:8} {stratum:8} " + "   ".join(row))
