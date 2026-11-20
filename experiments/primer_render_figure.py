"""Render and compare at real places, drawn for the primer (docs/primer/render-compare.svg).
No models: the judge's own cut of the ink (`rendercheck.place_ink`), its drawings and its
fit, at labelled places of a public-domain golden book.

    uv run python experiments/primer_render_figure.py <book> [<page>:<line>:<start> …] [--out <dir>]
    uv run python experiments/primer_render_figure.py --figure <page>:<line>:<start> <svg> <caption>

With no places it lists the book's settled suspects the judge gets right. With places it
writes, per place, the scan's strip and one overlay per version into --out (default
work/probes/primer-render/): ink both share grey, scan ink the drawing leaves bare red,
drawing where the scan has no ink blue. Each overlay's score is checked against
`rendercheck.fits`, so the picture is the judge's own placing. --figure turns one written
place into the primer's SVG, the images embedded.

The primer's figure: The Nature of a Crime (Doubleday 1924, public domain), place 55:12:0,
caption 'The line starts with the end of “as-suredly”, broken over two lines. Three AI
judges chose the word they know, “surely”.'
"""

import base64
import io
import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy.signal import fftconvolve

from roboscriptorium import rendercheck as rc
from roboscriptorium import trustdata
from roboscriptorium.config import Settings

INK = 0.3
PAPER = (250, 247, 240)
BOTH = (70, 70, 70)
BARE = (190, 40, 30)
EXTRA = (40, 110, 220)


def laid(face, spread, size, ink, version):
    """`rendercheck.fits` for one version, keeping where its best drawing lies: the
    score, the blurred strip on its padded canvas, and the drawing placed on that canvas."""
    strip = np.asarray(rc._picture(ink).filter(rc._BLUR), np.float32)
    energy = float((strip * strip).sum())
    best = (0.0, None, None)
    for glyphs in rc.drawings(face, version):
        high = max(4, round(glyphs.shape[0] * size / rc.RENDER_PX))
        for stretch in rc.STRETCHES:
            wide = max(4, round(glyphs.shape[1] * size / rc.RENDER_PX * stretch))
            sized = rc._spread(rc._picture(glyphs).resize((wide, high)), spread)
            mine = np.asarray(sized.filter(rc._BLUR), np.float32)
            pad_y = max(6, high - strip.shape[0] + 6)
            pad_x = max(6, wide - strip.shape[1] + 6)
            canvas = np.pad(strip, ((pad_y, pad_y), (pad_x, pad_x)))
            over = fftconvolve(canvas, mine[::-1, ::-1], mode="valid")
            score = float(over.max()) / (energy * float((mine * mine).sum())) ** 0.5
            if score > best[0]:
                y, x = np.unravel_index(int(over.argmax()), over.shape)
                raw = np.pad(ink, ((pad_y, pad_y), (pad_x, pad_x)))
                drawn = np.zeros_like(raw)
                drawn[y : y + high, x : x + wide] = np.asarray(sized, np.float32) / 255.0
                best = (score, raw, drawn)
    return best


def overlay(scan: np.ndarray, drawn: np.ndarray) -> Image.Image:
    s, d = scan > INK, drawn > INK
    out = np.empty((*scan.shape, 3), np.uint8)
    out[:] = PAPER
    out[s & d], out[s & ~d], out[~s & d] = BOTH, BARE, EXTRA
    return Image.fromarray(out)


def strip_image(ink: np.ndarray) -> Image.Image:
    return Image.fromarray(((1 - ink) * 255).astype(np.uint8))


def _png(path: Path) -> tuple[str, int, int]:
    image = Image.open(path)
    buf = io.BytesIO()
    image.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), image.width, image.height


def figure(folder: Path, stem: str, target: Path, caption: str) -> None:
    """The primer's figure for one rendered place: the scan's strip above, the right
    version's overlay and the wrong one's below, with their fits."""
    meta = json.loads((folder / f"{stem}.json").read_text())
    right = meta["right"].index(True)
    wrong = next(i for i, ok in enumerate(meta["right"]) if not ok)
    scan, sw, sh = _png(folder / f"{stem}-scan.png")
    panels = []
    for slot, (i, verdict, colour) in enumerate(
        [(right, "best fit: its vote", "#2e7d32"), (wrong, "worse fit", "#b3261e")]
    ):
        data, w, h = _png(folder / f"{stem}-v{i}.png")
        x = 30 + slot * 370
        panels.append(
            f'<text x="{x + 165}" y="252" text-anchor="middle" font-size="14" '
            f'font-weight="bold" fill="#3b4252">drawn as “{meta["versions"][i]}”</text>'
            f'<image x="{x + (330 - w) / 2}" y="264" width="{w}" height="{h}" '
            f'href="data:image/png;base64,{data}"/>'
            f'<text x="{x + 165}" y="{280 + h}" text-anchor="middle" font-size="14" '
            f'font-weight="bold" fill="{colour}">{verdict}</text>'
            f'<text x="{x + 165}" y="{298 + h}" text-anchor="middle" font-size="12" '
            f'fill="#4c566a">fit {meta["fits"][i]:.2f}</text>'
        )
    high = 330 + max(Image.open(folder / f"{stem}-v{i}.png").height for i in (right, wrong))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 {high + 70}" font-family="Helvetica, Arial, sans-serif">
  <!-- Generated by experiments/primer_render_figure.py, place {stem.replace("-", ":")} -->
  <rect width="760" height="{high + 70}" fill="#ffffff"/>
  <text x="30" y="32" font-size="15" font-weight="bold" fill="#3b4252">Render and compare at a real place in a scan</text>
  <text x="30" y="54" font-size="13" fill="#4c566a">{caption}</text>
  <text x="380" y="86" text-anchor="middle" font-size="13" font-weight="bold" fill="#3b4252">the scan's ink at that place</text>
  <image x="{380 - sw / 2}" y="96" width="{sw}" height="{sh}" href="data:image/png;base64,{scan}"/>
  {"".join(panels)}
  <g font-size="12" fill="#3b4252">
    <rect x="30" y="{high}" width="14" height="14" fill="rgb{BOTH}"/>
    <text x="50" y="{high + 11}">ink and drawing agree</text>
    <rect x="200" y="{high}" width="14" height="14" fill="rgb{BARE}"/>
    <text x="220" y="{high + 11}">ink the drawing leaves bare</text>
    <rect x="410" y="{high}" width="14" height="14" fill="rgb{EXTRA}"/>
    <text x="430" y="{high + 11}">drawing where there is no ink</text>
  </g>
  <text x="30" y="{high + 42}" font-size="12" fill="#4c566a">Fit: how closely drawing and ink match, 1 for a perfect match. The judge never asks what the word ought to be.</text>
</svg>
"""
    target.write_text(svg)


def main(argv: list[str]) -> None:
    out = Path("work/probes/primer-render")
    if "--figure" in argv:
        i = argv.index("--figure")
        figure(out, argv[i + 1].replace(":", "-"), Path(argv[i + 2]), argv[i + 3])
        return
    if "--out" in argv:
        i = argv.index("--out")
        out, argv = Path(argv[i + 1]), argv[:i] + argv[i + 2 :]
    name, places = argv[0], argv[1:]
    book = Path("work") / name
    settings = Settings.from_env()
    found = rc.match(book / "source.pdf", [], Path(settings.fonts), book / "stages/typeface.json")
    face = rc.Face.from_file(Path(settings.fonts) / found.file)
    rows = [r for r in trustdata.load(name) if r["settled"]]
    keys = {tuple(int(x) for x in p.split(":")) for p in places}
    out.mkdir(parents=True, exist_ok=True)
    print(f"{found.name}, size {found.size}, spread {found.spread}")
    with pymupdf.open(book / "source.pdf") as doc:
        for r in rows:
            s = r["suspect"]
            key = (s["page"], s["line"], s["start"])
            if keys and key not in keys:
                continue
            ink = rc.place_ink(doc[s["page"] - 1], s["box"])
            if ink is None:
                continue
            versions = [s["ours"], *s["others"]]
            scores = rc.fits(face, found.spread, found.size, ink, versions)
            picked = max(range(len(versions)), key=lambda i: scores[i])
            if not keys:
                if r["right"][picked] and not all(r["right"]):
                    margin = scores[picked] - sorted(scores)[-2]
                    print(":".join(map(str, key)), versions, r["right"],
                          [round(x, 3) for x in scores], round(margin, 3))  # fmt: skip
                continue
            stem = "-".join(map(str, key))
            strip_image(ink).save(out / f"{stem}-scan.png")
            meta = {"place": key, "versions": versions, "right": r["right"], "fits": scores}
            for i, v in enumerate(versions):
                score, raw, drawn = laid(face, found.spread, found.size, ink, v)
                assert abs(score - scores[i]) < 1e-4, (v, score, scores[i])
                overlay(raw, drawn).save(out / f"{stem}-v{i}.png")
            (out / f"{stem}.json").write_text(json.dumps(meta, ensure_ascii=False))
            print(stem, json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
