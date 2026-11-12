"""Render and compare, first test (the checklist, "Render and compare"): does drawing each
version of a contested place in the book's matched font, and laying it over the scan, pick
the print? On the trust data's labelled suspects, against the judges. No models.

    uv run python experiments/probe_render_compare.py <book> [more …] [--votes <folder>]

A book needs its font match first (`probe_font_match.py`, work/probes/font-match/<book>.json).
Only places the text layer has words for are tried: their boxes give the place's ink: a strip of the line from the blank before the place to the blank after it. Each
version is drawn whole at the book's type size and laid over the strip where it fits best.
Writes work/probes/render-compare/<book>.json, one row a suspect; `--votes` also writes
the book's trust data into <folder> with the fit as a judge named "render", for
`ROBO_TRUST_DATA=<folder> ROBO_ALARM_MODEL=<the others>,render train_ocr_trust.py`.
"""

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import fftconvolve

sys.path.insert(0, str(Path(__file__).parent))
import probe_font_match as match  # noqa: E402

from roboscriptorium import pdf, trustdata  # noqa: E402

OUT = Path("work/probes/render-compare")
HEAVY = re.compile(r"Bold|Black|Semibold|Demi|Italic|Heavy", re.I)
STRETCHES = np.linspace(0.92, 1.08, 5)
# A blank this wide, in line heights, parts a word from its neighbour.
WORD_GAP = 0.2
# Ink no wider and hardly taller than this, in line heights, is a dot.
DOT = 0.16
# The fit's name as a judge in the trust data (`ROBO_ALARM_MODEL=…,render`).
JUDGE = "render"


def book_font(name: str) -> tuple[ImageFont.FreeTypeFont, dict]:
    """The best-fitting cut that is neither heavy nor italic, with its fitted ink spread."""
    ranked = json.loads((match.OUT / f"{name}.json").read_text())["ranked"]
    plain = re.compile(r"regular|roman", re.I)
    entry = next((e for e in ranked if not HEAVY.search(e["name"])
                  or plain.search(Path(e["file"]).stem)), ranked[0])
    path = match.LIBRARY / entry["file"]
    return ImageFont.truetype(str(path), match.RENDER_PX), entry


def kind(a: str, b: str) -> str:
    """What tells two versions apart."""
    def bare(s):
        return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    if a.replace(" ", "") == b.replace(" ", ""):
        return "space"
    if bare(a) == bare(b):
        return "accent"
    if a.lower() == b.lower():
        return "case"
    letters = lambda s: "".join(c for c in s if c.isalnum())  # noqa: E731
    if letters(a) == letters(b):
        return "punctuation"
    return "letters"


def place_ink(page, layer, span, s) -> np.ndarray | None:
    """The ink at a suspect's span, as a strip of its line (0–1, not trimmed): everything
    between the blank before the span and the blank after it, so a mark the layer missed
    beside the word is in it, and its neighbours' letters aren't."""
    if not span:
        return None
    x0, y0 = min(w[0] for w in span), min(w[1] for w in span)
    x1, y1 = max(w[2] for w in span), max(w[3] for w in span)
    high = y1 - y0
    clip = pymupdf.Rect(x0 - high * 4, y0 - high * 0.3, x1 + high * 4, y1 + high * 0.3)
    clip &= page.rect
    pix = page.get_pixmap(dpi=match.DPI, clip=clip, colorspace=pymupdf.csGRAY)
    grey = 1.0 - np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width) / 255.0
    paper, dark = np.percentile(grey, 20), grey.max()
    if dark - paper < 0.25:
        return None
    grey = np.clip((grey - paper) / (dark - paper), 0, 1).astype(np.float32)
    scale = match.DPI / 72
    left, right = round((x0 - clip.x0) * scale), round((x1 - clip.x0) * scale)
    mask = grey > 0.5
    cols = mask.any(0)
    gap = max(4, round(high * scale * WORD_GAP))
    dot = max(3, round(high * scale * DOT))

    def is_dot(c0: int, c1: int) -> bool:
        rows = np.where(mask[:, c0:c1].any(1))[0]
        return 0 < c1 - c0 <= dot and len(rows) and rows[-1] - rows[0] < dot * 1.5

    # Outward from just inside the span's box to the first blank as wide as a word space,
    # and on through an ellipsis's dots, which stand as far apart as narrow word spaces.
    a = min(left + gap, right)
    while True:
        while a > 0 and cols[max(0, a - gap) : a].any():
            a -= 1
        e = a
        while e > 0 and not cols[e - 1]:
            e -= 1
        f = e
        while f > 0 and cols[f - 1]:
            f -= 1
        if not (e > 0 and a - e < 2 * gap and is_dot(f, e)):
            break
        a = f
    b = max(right - gap, left)
    while True:
        while b < len(cols) and cols[b : b + gap].any():
            b += 1
        e = b
        while e < len(cols) and not cols[e]:
            e += 1
        f = e
        while f < len(cols) and cols[f]:
            f += 1
        if not (e < len(cols) and e - b < 2 * gap and is_dot(e, f)):
            break
        b = f
    if a <= 0 or b >= len(cols) or b - a < 6:
        return None
    return grey[:, max(0, a - gap) : b + gap]


_SIZED: dict = {}
# A closing quote set over the stop before it, as some books kern it: how far left, in ems.
KERNS = (-0.12, -0.22, -0.32)
# Small capitals drawn as capitals at this share of their size.
SMALL_CAPS = (0.74, 0.82)
_STOP_QUOTE = re.compile(r"([.,…])([’”'\"])")
_CAPITALS = re.compile(r"[A-ZÀ-Þ]{2,}")
# An ellipsis set with its dots apart: the blank between two dots, in ems.
DOT_GAPS = (0.08, 0.16, 0.26, 0.4)
_DOTS = re.compile(r"\.\.\.|…")


def _sized(font, scale: float):
    key = (font.path, scale)
    if key not in _SIZED:
        _SIZED[key] = ImageFont.truetype(font.path, round(match.RENDER_PX * scale))
    return _SIZED[key]


def _pieces(font, pieces: list[tuple[str, float, float]]) -> np.ndarray | None:
    """Pieces of text drawn on one baseline: each (text, scale, shift before it in ems)."""
    width = int(sum(_sized(font, sc).getlength(tx) for tx, sc, _ in pieces)) + match.RENDER_PX
    image = Image.new("L", (width, match.RENDER_PX * 2), 255)
    draw, x = ImageDraw.Draw(image), match.RENDER_PX // 4
    for text, scale, shift in pieces:
        cut = _sized(font, scale)
        x += shift * match.RENDER_PX
        draw.text((x, match.RENDER_PX * 1.3), text, font=cut, fill=0, anchor="ls")
        x += cut.getlength(text)
    return match.ink(image)


def drawings(font, version: str) -> list[np.ndarray]:
    """The ways a book may set a version: as the font spaces it; with a closing quote
    kerned over the stop before it; with a run of capitals as small capitals."""
    ways = [[(version, 1.0, 0.0)]]
    if m := _STOP_QUOTE.search(version):
        for kern in KERNS:
            ways.append([(version[: m.end(1)], 1.0, 0.0), (version[m.end(1) :], 1.0, kern)])
    if m := _DOTS.search(version):
        dots = [".", ".", "."]
        for gap in DOT_GAPS:
            ways.append([(version[: m.start()], 1.0, 0.0), (dots[0], 1.0, 0.0),
                         *((d, 1.0, gap) for d in dots[1:]), (version[m.end():], 1.0, gap / 2)])
    if _CAPITALS.search(version):
        for small in SMALL_CAPS:
            way, at = [], 0
            for m in _CAPITALS.finditer(version):
                if m.start() > at:
                    way.append((version[at : m.start()], 1.0, 0.0))
                way.append((m.group(), small, 0.0))
                at = m.end()
            if at < len(version):
                way.append((version[at:], 1.0, 0.0))
            ways.append(way)
    return [g for g in (_pieces(font, way) for way in ways) if g is not None]


def em_size(name: str, font) -> float:
    """The book's type size in scan pixels: what the font must be drawn at."""
    ratios = []
    for word, ink in match.scan_words(Path("work") / name, 80):
        glyphs = match.drawn(font, word)
        if glyphs is not None:
            ratios.append(ink.shape[0] / glyphs.shape[0])
    return match.RENDER_PX * float(np.median(ratios))


def fits(font, spread: int, size: float, ink: np.ndarray, versions: list[str]) -> list[float]:
    """Per version, how well its drawing at the book's size lies over the strip's ink:
    the cosine of the two at the best position and stretch, so ink the drawing lacks
    and ink it adds both count against it."""
    blur = ImageFilter.GaussianBlur(1.5)
    strip = np.asarray(Image.fromarray((ink * 255).astype(np.uint8)).filter(blur), np.float32)
    energy = float((strip * strip).sum())
    out = []
    for version in versions:
        ways = drawings(font, version) if version.strip() and energy else []
        best = 0.0
        for glyphs in ways:
            high = max(4, round(glyphs.shape[0] * size / match.RENDER_PX))
            for stretch in STRETCHES:
                wide = max(4, round(glyphs.shape[1] * size / match.RENDER_PX * stretch))
                sized = Image.fromarray((glyphs * 255).astype(np.uint8)).resize((wide, high))
                if spread > 0:
                    sized = sized.filter(ImageFilter.MaxFilter(spread))
                elif spread < 0:
                    sized = sized.filter(ImageFilter.MinFilter(-spread))
                mine = np.asarray(sized.filter(blur), np.float32)
                pad_y = max(6, high - strip.shape[0] + 6)
                pad_x = max(6, wide - strip.shape[1] + 6)
                canvas = np.pad(strip, ((pad_y, pad_y), (pad_x, pad_x)))
                over = fftconvolve(canvas, mine[::-1, ::-1], mode="valid")
                best = max(best, float(over.max()) / (energy * float((mine * mine).sum())) ** 0.5)
        out.append(best)
    return out


def run(name: str) -> list[dict]:
    font, entry = book_font(name)
    size = em_size(name, font)
    rows = [r for r in trustdata.load(name) if r["settled"]]
    by_page = defaultdict(list)
    for r in rows:
        by_page[r["suspect"]["page"]].append(r)
    out = []
    with pymupdf.open(Path("work") / name / "source.pdf") as doc:
        for number, group in sorted(by_page.items()):
            page = doc[number - 1]
            layer = pdf.page_words(page)
            for r in group:
                s = r["suspect"]
                x0, y0, x1, y1 = s["box"]
                words = [w for w in layer if x0 - 1 <= (w[0] + w[2]) / 2 <= x1 + 1
                         and y0 <= (w[1] + w[3]) / 2 <= y1]
                ink = place_ink(page, layer, words, s)
                if ink is None:
                    continue
                versions = [s["ours"], *s["others"]]
                scores = fits(font, entry["spread"], size, ink, versions)
                order = sorted(range(len(versions)), key=lambda i: -scores[i])
                told = any(r["right"]) and not all(r["right"])
                truth = versions[r["right"].index(True)] if told else ""
                wrong = next((v for v, ok in zip(versions, r["right"]) if not ok), "")
                out.append({
                    "page": number, "line": s["line"], "start": s["start"], "told": told,
                    "versions": versions,
                    "right": r["right"], "fits": [round(x, 4) for x in scores],
                    "picked": order[0], "margin": round(scores[order[0]] - scores[order[1]], 4),
                    "kind": kind(truth, wrong) if told else "",
                    "votes": {j: (v in versions and r["right"][versions.index(v)])
                              for j, v in s["votes"].items() if v},
                })
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(
        {"font": entry["name"], "tried": len(out), "suspects": len(rows), "rows": out},
        ensure_ascii=False))
    return out


def with_votes(name: str, rows: list[dict], folder: Path) -> None:
    """The book's trust data with the fit as one more judge (`JUDGE`): its pick as the
    vote, its margin over the next version as the confidence."""
    fit = {(r["page"], r["line"], r["start"]): r for r in rows}
    data = trustdata.load(name)
    for row in data:
        s = row["suspect"]
        s["judges"] = [*s.get("judges", []), JUDGE]
        if r := fit.get((s["page"], s["line"], s["start"])):
            s["votes"][JUDGE] = r["versions"][r["picked"]]
            s["confidence"][JUDGE] = min(1.0, r["margin"] * 4)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False))


def report(label: str, rows: list[dict]) -> None:
    rows = [r for r in rows if r["told"]]
    if not rows:
        return
    ok = [r["right"][r["picked"]] for r in rows]
    print(f"\n{label}: {len(rows)} places, the better fit is the print on {sum(ok)} "
          f"({sum(ok) / len(rows):.0%})")
    judges = Counter()
    asked = Counter()
    for r in rows:
        for j, good in r["votes"].items():
            asked[j] += 1
            judges[j] += good
    for j in asked:
        short = j.split("/")[-1].split(":")[0]
        missed = [r for r in rows if j in r["votes"] and not r["votes"][j]]
        saved = sum(r["right"][r["picked"]] for r in missed)
        print(f"  {short:16} right on {judges[j]}/{asked[j]} ({judges[j] / asked[j]:.0%}); "
              f"of its {len(missed)} misses the fit has {saved} right")
    every = [r for r in rows if r["votes"] and not any(r["votes"].values())]
    print(f"  every judge wrong: {len(every)}, the fit right on "
          f"{sum(r['right'][r['picked']] for r in every)}")
    for k, n in Counter(r["kind"] for r in rows).most_common():
        hit = sum(r["right"][r["picked"]] for r in rows if r["kind"] == k)
        print(f"  {k:12} {hit}/{n} ({hit / n:.0%})")
    ranked = sorted(rows, key=lambda r: -r["margin"])
    for share in (0.25, 0.5):
        top = ranked[: max(1, int(len(ranked) * share))]
        hit = sum(r["right"][r["picked"]] for r in top)
        print(f"  the surest {share:.0%} by margin (over {top[-1]['margin']:.3f}): "
              f"{hit}/{len(top)} ({hit / len(top):.0%})")


if __name__ == "__main__":
    everything = []
    args = sys.argv[1:]
    votes = Path(args.pop(args.index("--votes") + 1)) if "--votes" in args else None
    if votes:
        args.remove("--votes")
    for arg in args:
        name = Path(arg).name
        rows = run(name)
        if votes:
            with_votes(name, rows, votes)
        report(name, rows)
        everything += rows
    if len(args) > 1:
        report("all books", everything)
