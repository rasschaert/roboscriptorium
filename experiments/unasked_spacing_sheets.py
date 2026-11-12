"""Unasked errors that differ from the reference only in spaces or hyphens, with their crops.

The reference's own departures from its print cluster here: a space before a mark no
print sets, words run together, a line-end hyphen left in. From one or more bench runs'
error rows this lists those places by pattern (`<out>/places.json`) and lays their scan
lines out on sheets (`<out>/sheet-NN.png`, numbered as in `<out>/places.txt`), for an
agent to settle by eye before any goes to the user.

    uv run python experiments/unasked_spacing_sheets.py <out dir> <run.errors.jsonl> …

No models.
"""

import io
import json
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont

PER_SHEET = 14
WIDTH = 1500
MARK = r"\s[.,;:!?…’”'\")]"


def pattern(got: str, want: str) -> str | None:
    """Which spacing pattern a place shows, or None when its letters differ too."""
    bare = lambda t: re.sub(r"[\s\-‐]", "", t)  # noqa: E731
    if got == want or bare(got) != bare(want):
        return None
    if re.search(MARK, want) and not re.search(MARK, got):
        return "space before a mark in the reference"
    hyphens = "-" in want or "-" in got
    if not hyphens and want.count(" ") < got.count(" "):
        return "run together in the reference"
    if not hyphens and want.count(" ") > got.count(" "):
        return "split in the reference"
    if want.count("-") > got.count("-"):
        return "hyphen in the reference"
    if want.count("-") < got.count("-"):
        return "hyphen in ours"
    return "other spacing"


def lines_of(book: str) -> dict[int, list[dict]]:
    layer = json.loads(Path(f"work/{book}/stages/textlayer.json").read_text())
    return {p["number"]: p["lines"] for p in layer["pages"]}


def crop(pdf: pymupdf.Document, page: int, lines: list[dict], first: int, last: int) -> Image.Image:
    """The place's lines with one line either side, at the sheet's width."""
    shown = lines[max(0, first - 1) : last + 2]
    clip = pymupdf.Rect(
        min(ln["x0"] for ln in shown) - 6,
        min(ln["y0"] for ln in shown) - 4,
        max(ln["x1"] for ln in shown) + 6,
        max(ln["y1"] for ln in shown) + 4,
    )
    pix = pdf[page - 1].get_pixmap(dpi=300, clip=clip)
    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return image.resize((WIDTH, max(1, int(image.height * WIDTH / image.width))))


out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
places = []
for path in sys.argv[2:]:
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        why = None if row["asked"] else pattern(row["got"], row["want"])
        if why and row["page"] is not None and row["lines"]:
            places.append(row | {"why": why})
places.sort(key=lambda r: (r["why"], r["book"], r["page"], r["lines"][0]))
(out / "places.json").write_text(json.dumps(places, ensure_ascii=False, indent=1))
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 26)
listing, layers, pdfs = [], {}, {}
for start in range(0, len(places), PER_SHEET):
    batch = places[start : start + PER_SHEET]
    crops = []
    for n, row in enumerate(batch, start + 1):
        book = row["book"]
        if book not in layers:
            layers[book] = lines_of(book)
            pdfs[book] = pymupdf.open(f"work/{book}/source.pdf")
        first, last = row["lines"]
        crops.append(crop(pdfs[book], row["page"], layers[book][row["page"]], first, last))
        listing.append(
            f"{n:3} {row['why']} | {book} p{row['page']} | ours {row['got']!r} | "
            f"reference {row['want']!r}"
        )
    sheet = Image.new("RGB", (WIDTH, sum(c.height + 44 for c in crops)), "white")
    draw, y = ImageDraw.Draw(sheet), 0
    for n, (row, c) in enumerate(zip(batch, crops, strict=True), start + 1):
        label = f"{n}  {row['book'][:18]} p{row['page']}   ours: {row['got']}   ref: {row['want']}"
        draw.text((6, y + 6), label, fill=(180, 0, 0), font=font)
        sheet.paste(c, (0, y + 44))
        y += c.height + 44
    sheet.save(out / f"sheet-{start // PER_SHEET + 1:02}.png")
(out / "places.txt").write_text("\n".join(listing) + "\n")
print(f"{len(places)} places on {(len(places) + PER_SHEET - 1) // PER_SHEET} sheets in {out}")
