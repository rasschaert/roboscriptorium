"""Does ink between two text-layer lines tell a lost line from white space?

For the whole-line lost-text errors of every bench log that has causes (a line or more
the layer lacks), the gap after the layer line the error's context ends on is measured:
its height in line pitches and the share of dark pixels in the strip across the text
block. The same two numbers are taken for every other gap of the pages of the same books
that hold no such error. Prints the two distributions and, per ink threshold, the lost
lines caught and the other gaps flagged per page.

    uv run python experiments/probe_gap_ink.py [out.jsonl]

No models: the cached text layers, the scans and the benches' error lists.
"""

import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pymupdf

ZOOM = 1.5
DARK = 140


def layer(book: str) -> dict[int, dict]:
    stages = Path("work") / book / "stages"
    f = next(g for n in ("text-layer.json", "textlayer.json", "tesseract.json") if (g := stages / n).exists())
    data = json.loads(f.read_text())
    return {p["number"]: p for p in (data if isinstance(data, list) else data["pages"])}


def positives() -> list[dict]:
    seen = {}
    for f in sorted(Path("work/bench").glob("*.errors.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("cause") == "missing text" and r.get("layer") == "lost":
                seen[(r["book"], r["page"], r["want"])] = r
    return list(seen.values())


def strip_ink(pix: np.ndarray, a: dict, b: dict, x0: float, x1: float) -> float:
    y0, y1 = a["y1"] + 1.0, b["y0"] - 1.0
    if y1 - y0 < 2:
        return 0.0
    region = pix[int(y0 * ZOOM) : int(y1 * ZOOM), int(x0 * ZOOM) : int(x1 * ZOOM)]
    return float((region < DARK).mean()) if region.size else 0.0


def main() -> None:
    pos = positives()
    books = sorted({r["book"] for r in pos})
    rows = []
    for book in books:
        pages = layer(book)
        doc = pymupdf.open(Path("work") / book / "source.pdf")
        marked = {r["page"] for r in pos if r["book"] == book}
        for number, page in pages.items():
            lines = page["lines"]
            if len(lines) < 4:
                continue
            pitch = statistics.median(b["y0"] - a["y0"] for a, b in zip(lines, lines[1:], strict=False))
            x0 = min(ln["x0"] for ln in lines)
            x1 = max(ln["x1"] for ln in lines)
            pix = None
            hits = {}
            for r in (r for r in pos if r["book"] == book and r["page"] == number):
                tail = r["before"].strip()[-12:]
                k = next((i for i, ln in enumerate(lines[:-1]) if tail and ln["text"].strip().endswith(tail)), None)
                if k is not None:
                    hits[k] = r["want"]
            if number in marked and not hits:
                continue
            for k, (a, b) in enumerate(zip(lines, lines[1:], strict=False)):
                if number in marked and k not in hits:
                    continue
                if pix is None:
                    p = doc[number - 1].get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), colorspace=pymupdf.csGRAY)
                    pix = np.frombuffer(p.samples, dtype=np.uint8).reshape(p.height, p.width)
                rows.append(
                    {
                        "book": book,
                        "page": number,
                        "k": k,
                        "lost": k in hits,
                        "want": hits.get(k, ""),
                        "gap": round((b["y0"] - a["y0"]) / pitch, 2),
                        "ink": round(strip_ink(pix, a, b, x0, x1), 4),
                    }
                )
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    lost = [r for r in rows if r["lost"]]
    rest = [r for r in rows if not r["lost"]]
    pages_rest = len({(r["book"], r["page"]) for r in rest})
    print(f"{len(lost)} lost-line gaps located (of {len(pos)} errors), {len(rest)} other gaps on {pages_rest} pages")
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]  # noqa: E731
    for name, rs in (("lost", lost), ("other", rest)):
        ink = [r["ink"] for r in rs]
        gap = [r["gap"] for r in rs]
        print(f"{name:6} ink  p10 {q(ink, .1):.4f} p50 {q(ink, .5):.4f} p90 {q(ink, .9):.4f} max {max(ink):.4f}")
        print(f"{name:6} gap  p10 {q(gap, .1):.2f} p50 {q(gap, .5):.2f} p90 {q(gap, .9):.2f}")
    for t in (0.003, 0.005, 0.01, 0.02, 0.03):
        for g in (1.0, 1.25, 1.6):
            c = sum(r["ink"] >= t and r["gap"] >= g for r in lost)
            f = sum(r["ink"] >= t and r["gap"] >= g for r in rest)
            print(f"ink >= {t:<5} gap >= {g:<4}: lost caught {c:2}/{len(lost)}, other gaps flagged {f:5} ({f / pages_rest:.2f} a page)")


if __name__ == "__main__":
    main()
