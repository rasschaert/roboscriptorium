"""Which typeface is a book set in? (the checklist, "Matched-font rendering"). Words of the
text layer are cut from the scan, each is drawn in every font of a library, and the fonts
are ranked by how well the drawings lie over the ink. No models.

    uv run python experiments/probe_font_match.py <book dir> [more …] [--fonts <dir>]

A word is compared trimmed to its ink and scaled to the scan word's height, so a font's
proportions (its width, its ascenders against its x-height) count. Two passes: every font
on a few words, then the best on all of them, each at the letter spacing that suits it.
Writes work/probes/font-match/<book>.json and a sheet <book>.png of the best fits.
"""

import json
import random
import sys
import tomllib
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from roboscriptorium import pdf

# The font library: licensed fonts, kept with the books, out of git.
LIBRARY = Path("work/fonts")
OUT = Path("work/probes/font-match")
DPI = 400
WORDS = 240
FIRST_PASS = 40
KEPT = 40
STRETCHES = (0.92, 0.96, 1.0, 1.04, 1.08)
# Ink spread: the drawing's strokes thinned or thickened by this many scan pixels.
SPREADS = (-3, 0, 3, 5)
RENDER_PX = 96


def ink(image: Image.Image) -> np.ndarray | None:
    """The image as ink (0–1), trimmed to it; None when it holds next to none."""
    grey = 1.0 - np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    paper, dark = np.percentile(grey, 20), grey.max()
    if dark - paper < 0.25:
        return None
    grey = np.clip((grey - paper) / (dark - paper), 0, 1)
    mask = grey > 0.5
    if mask.sum() < 20:
        return None
    rows, cols = np.where(mask.any(1))[0], np.where(mask.any(0))[0]
    return grey[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def word_ink(image: Image.Image, left: int, right: int, top: int, bottom: int) -> np.ndarray | None:
    """A word's ink in a crop cut wider than its layer box (`left`–`right`, `top`–`bottom`
    in pixels): the box grown to the blank columns and rows around its ink, since layer
    boxes cut through letters or stop short of them."""
    grey = 1.0 - np.asarray(image, dtype=np.float32) / 255.0
    paper, dark = np.percentile(grey, 20), grey.max()
    if dark - paper < 0.25:
        return None
    grey = np.clip((grey - paper) / (dark - paper), 0, 1)
    mask = grey > 0.5
    height = bottom - top
    rows = mask[:, left:right].any(1)
    while top > 0 and rows[top - 1]:
        top -= 1
    while bottom < len(rows) and rows[bottom]:
        bottom += 1
    cols = mask[top:bottom].any(0)
    gap = max(3, round(height * 0.16))
    while left > 0 and cols[max(0, left - gap) : left].any():
        left -= 1
    while right < len(cols) and cols[right : right + gap].any():
        right += 1
    if left == 0 or right == len(cols):
        return None
    cut = grey[top:bottom, left:right]
    keep = cut > 0.5
    if keep.sum() < 20:
        return None
    r, c = np.where(keep.any(1))[0], np.where(keep.any(0))[0]
    return cut[r[0] : r[-1] + 1, c[0] : c[-1] + 1]


def scan_words(book: Path, count: int) -> list[tuple[str, np.ndarray]]:
    """Plain lower-case words of five letters or more from pages across the text proper."""
    first, last = tomllib.loads((book / "book.toml").read_text())["body_pages"]
    rng = random.Random(0)
    pages = rng.sample(range(first + 2, last - 1), min(12, last - first - 3))
    found = []
    with pymupdf.open(book / "source.pdf") as doc:
        for number in pages:
            page = doc[number - 1]
            words = [w for w in pdf.page_words(page) if len(w[4]) >= 5 and w[4].isalpha()
                     and w[4].islower() and w[4].isascii()]
            for w in rng.sample(words, min(len(words), count // len(pages) + 4)):
                high = w[3] - w[1]
                clip = pymupdf.Rect(w[0] - high * 1.5, w[1] - high * 0.3, w[2] + high * 1.5,
                                    w[3] + high * 0.3) & page.rect
                pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=pymupdf.csGRAY)
                image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
                scale = DPI / 72
                inset = high * 0.25
                cut = word_ink(image, round((w[0] - clip.x0) * scale),
                               round((w[2] - clip.x0) * scale),
                               round((w[1] + inset - clip.y0) * scale),
                               round((w[3] - inset - clip.y0) * scale))
                if cut is not None and cut.shape[0] > 20:
                    found.append((w[4], cut))
    rng.shuffle(found)
    return found[:count]


def drawn(font: ImageFont.FreeTypeFont, word: str) -> np.ndarray | None:
    box = font.getbbox(word)
    if box[2] - box[0] < 4:
        return None
    image = Image.new("L", (box[2] - box[0] + 8, RENDER_PX * 2), 255)
    ImageDraw.Draw(image).text((4 - box[0], RENDER_PX // 3), word, font=font, fill=0)
    return ink(image)


def fit(scan: np.ndarray, glyphs: np.ndarray, stretch: float, spread: int = 0) -> float:
    """How well a drawn word lies over the scan's, 0–1: correlation after scaling the
    drawing to the scan word's height, both blurred a little, left edges together."""
    h = scan.shape[0]
    w = max(2, round(glyphs.shape[1] * h / glyphs.shape[0] * stretch))
    sized = Image.fromarray((glyphs * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    if spread > 0:
        sized = sized.filter(ImageFilter.MaxFilter(spread))
    elif spread < 0:
        sized = sized.filter(ImageFilter.MinFilter(-spread))
    mine = np.asarray(sized.filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32)
    theirs = np.asarray(
        Image.fromarray((scan * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)),
        dtype=np.float32)
    width = max(w, theirs.shape[1])
    a, b = np.zeros((h, width), np.float32), np.zeros((h, width), np.float32)
    a[:, :w], b[:, : theirs.shape[1]] = mine, theirs
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))


def usable(path: Path) -> ImageFont.FreeTypeFont | None:
    """The font, when it draws Latin letters of its own (not a symbol or fallback face)."""
    try:
        font = ImageFont.truetype(str(path), RENDER_PX)
        shapes = {font.getmask(c).getbbox() for c in "aegkmx"}
    except Exception:
        return None
    return font if len(shapes) >= 5 and None not in shapes else None


def score(font, words, stretches, spreads=(0,)) -> tuple[float, float, int]:
    best = (0.0, 1.0, 0)
    pictures = [(scan, drawn(font, word)) for word, scan in words]
    for stretch in stretches:
        for spread in spreads:
            fits = [fit(scan, g, stretch, spread) if g is not None else 0.0
                    for scan, g in pictures]
            best = max(best, (float(np.mean(fits)), stretch, spread))
    return best


def sheet(book: str, words, ranked: list[dict], fonts: dict) -> None:
    """The scan's words above the same words drawn in the five best fonts."""
    shown = words[:6]
    rows = [("scan", [s for _, s in shown])]
    for entry in ranked[:5]:
        font = fonts[entry["file"]]
        rows.append((f"{entry['name']} {entry['fit']:.3f}",
                     [drawn(font, word) for word, _ in shown]))
    height, pad = 48, 14
    canvas = Image.new("L", (1900, (height + pad + 14) * len(rows) + pad), 255)
    label = ImageFont.load_default()
    for r, (name, pictures) in enumerate(rows):
        y = pad + r * (height + pad + 14)
        ImageDraw.Draw(canvas).text((6, y), name[:60], font=label, fill=0)
        x = 6
        for picture in pictures:
            if picture is None:
                continue
            w = round(picture.shape[1] * height / picture.shape[0])
            tile = Image.fromarray((255 - picture * 255).astype(np.uint8)).resize((w, height))
            canvas.paste(tile, (x, y + 13))
            x += w + 26
    canvas.save(OUT / f"{book}.png")


if __name__ == "__main__":
    args = sys.argv[1:]
    library = LIBRARY
    if "--fonts" in args:
        library = Path(args.pop(args.index("--fonts") + 1))
        args.remove("--fonts")
    OUT.mkdir(parents=True, exist_ok=True)
    fonts = {}
    for path in sorted(library.rglob("*")):
        if path.suffix.lower() in (".otf", ".ttf"):
            font = usable(path)
            if font:
                fonts[str(path.relative_to(library))] = font
    print(f"{len(fonts)} fonts with Latin letters under {library}", flush=True)
    for arg in args:
        book = Path(arg)
        words = scan_words(book, WORDS)
        first = sorted(((score(f, words[:FIRST_PASS], (1.0, 0.94, 1.06), (0, 3))[0], name)
                        for name, f in fonts.items()), reverse=True)
        ranked = []
        for _, name in first[:KEPT]:
            value, stretch, spread = score(fonts[name], words, STRETCHES, SPREADS)
            ranked.append({"file": name, "name": " ".join(fonts[name].getname()),
                           "fit": round(value, 4), "stretch": stretch, "spread": spread})
        ranked.sort(key=lambda e: -e["fit"])
        (OUT / f"{book.name}.json").write_text(
            json.dumps({"words": len(words), "fonts": len(fonts), "ranked": ranked}, indent=1))
        sheet(book.name, words, ranked, fonts)
        print(f"\n{book.name}: {len(words)} words")
        for entry in ranked[:8]:
            print(f"  {entry['fit']:.3f}  x{entry['stretch']:.2f}  ink {entry['spread']:+d}  {entry['name']}")
