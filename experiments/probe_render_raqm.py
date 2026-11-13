"""Render and compare drawn with text shaping (raqm: the font's OpenType kerning and its
default ligatures) against Pillow's basic layout, which kerns only by the old `kern` table
and never joins letters. On a sample of the trust data's labelled two-version places, the
pipeline's own `rendercheck.fits` with each engine, by kind of difference. No models.

Pillow loads FriBiDi, which raqm needs, from the loader's path; `uv` drops `DYLD_*`
variables from its own environment, so pass it through an env file holding
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`:

    uv run --env-file <that file> python experiments/probe_render_raqm.py <book> [more …]
    uv run python experiments/probe_render_raqm.py --report

Writes work/probes/render-raqm/<book>.json.
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from PIL import ImageFont, features
from probe_render_difference import kind

from roboscriptorium import ocr, pdf, rendercheck, trustdata
from roboscriptorium.book import Book
from roboscriptorium.files import write_atomic

OUT = Path("work/probes/render-raqm")
PLACES = 600


class Unkerned(ImageFont.FreeTypeFont):
    """Shaped by raqm with the font's kerning off: its ligatures only."""

    def getlength(self, text, mode="", direction=None, features=None, language=None):
        return super().getlength(text, mode, direction, features or ["-kern"], language)

    def getmask2(self, text, mode="", direction=None, features=None, *args, **kwargs):
        return super().getmask2(text, mode, direction, features or ["-kern"], *args, **kwargs)


def face(path: Path, engine, kern: bool = True) -> rendercheck.Face:
    cut = ImageFont.FreeTypeFont if kern else Unkerned
    return rendercheck.Face(
        lambda px: cut(str(path), px, layout_engine=engine), rendercheck.other_figures(path)
    )


def probe(name: str) -> None:
    book = Book.load(Path("work") / name)
    layer = pdf.cached_text_layer(
        book.source, book.stages / "textlayer.json", ocr.language(book.language)
    )
    texts = {p.number: p for p in layer}
    found = rendercheck.Match(**json.loads((book.stages / "typeface.json").read_text())["match"])
    path = Path("work/fonts") / found.file
    faces = {
        "basic": face(path, ImageFont.Layout.BASIC),
        "raqm": face(path, ImageFont.Layout.RAQM),
        "ligatures": face(path, ImageFont.Layout.RAQM, kern=False),
    }
    rows = [
        r
        for r in trustdata.load(name)
        if r["settled"] and sum(r["right"]) == 1 and not r["suspect"]["others"][1:]
    ]
    rows = random.Random(0).sample(rows, min(PLACES, len(rows)))
    out = []
    with pdf.PDF_LOCK, pymupdf.open(book.source) as doc:
        for r in rows:
            s = r["suspect"]
            versions = [s["ours"], s["others"][0]]
            ink = rendercheck.place_ink(doc[s["page"] - 1], s["box"], texts.get(s["page"]))
            if ink is None or not all(v.strip() for v in versions):
                continue
            fits = {
                k: rendercheck.fits(f, found.spread, found.size, ink, versions)
                for k, f in faces.items()
            }
            out.append(
                {"kind": kind(*versions), "right": r["right"].index(True), "versions": versions}
                | fits
            )
    write_atomic(OUT / f"{name}.json", json.dumps(out))
    print(f"{name}: {len(out)} places, font {found.name}", flush=True)


ENGINES = ("basic", "raqm", "ligatures")


def report() -> None:
    by = defaultdict(lambda: [0] * (len(ENGINES) + 1))
    print("per book, share of places picked right: " + " / ".join(ENGINES))
    for path in sorted(OUT.glob("*.json")):
        rows = json.loads(path.read_text())
        engines = [e for e in ENGINES if e in rows[0]]
        right = {e: sum(int(np.argmax(r[e])) == r["right"] for r in rows) for e in engines}
        cells = " / ".join(f"{right[e] / len(rows):.1%}" for e in engines)
        print(f"  {path.stem[:42]:42} {cells}  ({len(rows)})")
        for r in rows:
            row = by[r["kind"]]
            for i, e in enumerate(ENGINES):
                row[i] += e in r and int(np.argmax(r[e])) == r["right"]
            row[-1] += 1
    print("\nkind          places " + " ".join(f"{e:>9}" for e in ENGINES))
    total = [sum(v[i] for v in by.values()) for i in range(len(ENGINES) + 1)]
    for k, row in [*sorted(by.items(), key=lambda kv: -kv[1][-1]), ("all", total)]:
        print(f"{k:12} {row[-1]:7} " + " ".join(f"{c / row[-1]:9.1%}" for c in row[:-1]))


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        if not features.check("raqm"):
            sys.exit("Pillow has no raqm here: pass the loader path through uv's --env-file")
        for name in sys.argv[1:]:
            probe(name)
