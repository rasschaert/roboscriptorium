"""Pages for a whole-page OCR probe: the pages of the latest tuning bench's errors in the
classes a reader that never invents or paraphrases could settle (missing text, extra text,
glued or split words, compound hyphens), rendered so the longest edge is 1288 px, what olmOCR expects.

    uv run python experiments/probe_page_ocr_pages.py [limit]

Writes work/probes/olmocr-pages/<book>_<page>.png and pages.json (the errors per page).
Read them with `mlx_read_pages.py`, score with `probe_page_ocr_score.py`.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import pymupdf


RUN = "tuning-20261020T182636-f38e636-dirty"
CAUSES = {"missing text", "extra text", "glued or split words", "compound hyphen"}
OUT = Path("work/probes/olmocr-pages")
LONGEST = 1288


def _render(page: pymupdf.Page) -> bytes:
    zoom = LONGEST / max(page.rect.width, page.rect.height)
    return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    rows = [json.loads(x) for x in Path(f"work/bench/{RUN}.errors.jsonl").read_text().splitlines()]
    pages = defaultdict(list)
    for r in rows:
        if r["cause"] in CAUSES:
            pages[(r["book"], r["page"])].append(r)
    keys = sorted(pages)
    if limit:
        keys = keys[:: max(1, len(keys) // limit)][:limit]
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for book, page in keys:
        name = f"{book}_{page}"
        pdf = Path("work") / book / "source.pdf"
        with pymupdf.open(pdf) as doc:
            (OUT / f"{name}.png").write_bytes(_render(doc[page - 1]))
        manifest[name] = pages[(book, page)]
    (OUT / "pages.json").write_text(json.dumps(manifest, ensure_ascii=False))
    print(len(manifest), "pages,", sum(len(v) for v in manifest.values()), "errors")
