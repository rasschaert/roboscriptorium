"""Render and compare, first test (the checklist, "Render and compare"): does drawing each
version of a contested place in the book's matched font, and laying it over the scan, pick
the print? On the trust data's labelled suspects, against the judges. No models.

    uv run python experiments/probe_render_compare.py <book> [more …]

A book needs its font match first (`probe_font_match.py`, work/probes/font-match/<book>.json).
Only places the text layer has words for are tried: their boxes give the place's ink. Each version is drawn whole and laid over that ink at the stretch that suits it best.
Writes work/probes/render-compare/<book>.json, one row a suspect.
"""

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import probe_font_match as match  # noqa: E402

from roboscriptorium import pdf, trustdata  # noqa: E402

OUT = Path("work/probes/render-compare")
HEAVY = re.compile(r"Bold|Black|Semibold|Demi|Italic|Heavy|Medium", re.I)
STRETCHES = np.linspace(0.86, 1.14, 15)


def book_font(name: str) -> tuple[ImageFont.FreeTypeFont, dict]:
    """The best-fitting cut that is neither heavy nor italic, with its fitted ink spread."""
    ranked = json.loads((match.OUT / f"{name}.json").read_text())["ranked"]
    plain = re.compile(r"regular|roman", re.I)
    entry = next((e for e in ranked if not HEAVY.search(e["name"])
                  or plain.search(Path(e["file"]).stem)), ranked[0])
    path = Path.home() / "Fonts" / entry["file"]
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


def place_ink(page, span, s) -> np.ndarray | None:
    """The ink of a suspect's span: its layer words' boxes grown to the blank around them."""
    if not span:
        return None
    x0, y0 = min(w[0] for w in span), min(w[1] for w in span)
    x1, y1 = max(w[2] for w in span), max(w[3] for w in span)
    high = y1 - y0
    clip = pymupdf.Rect(x0 - high * 1.5, y0 - high * 0.3, x1 + high * 1.5, y1 + high * 0.3)
    clip &= page.rect
    pix = page.get_pixmap(dpi=match.DPI, clip=clip, colorspace=pymupdf.csGRAY)
    image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    scale, inset = match.DPI / 72, high * 0.25
    return match.word_ink(image, round((x0 - clip.x0) * scale), round((x1 - clip.x0) * scale),
                          round((y0 + inset - clip.y0) * scale),
                          round((y1 - inset - clip.y0) * scale))


def fits(font, spread: int, ink: np.ndarray, versions: list[str]) -> list[float]:
    out = []
    for version in versions:
        glyphs = match.drawn(font, version) if version.strip() else None
        out.append(max(match.fit(ink, glyphs, float(st), spread) for st in STRETCHES)
                   if glyphs is not None else 0.0)
    return out


def run(name: str) -> list[dict]:
    font, entry = book_font(name)
    rows = [r for r in trustdata.load(name) if r["settled"] and any(r["right"])
            and not all(r["right"])]
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
                ink = place_ink(page, words, s)
                if ink is None or ink.shape[0] < 16:
                    continue
                versions = [s["ours"], *s["others"]]
                scores = fits(font, entry["spread"], ink, versions)
                order = sorted(range(len(versions)), key=lambda i: -scores[i])
                truth = versions[r["right"].index(True)]
                wrong = next(v for v, ok in zip(versions, r["right"]) if not ok)
                out.append({
                    "page": number, "line": s["line"], "versions": versions,
                    "right": r["right"], "fits": [round(x, 4) for x in scores],
                    "picked": order[0], "margin": round(scores[order[0]] - scores[order[1]], 4),
                    "kind": kind(truth, wrong),
                    "votes": {j: (v in versions and r["right"][versions.index(v)])
                              for j, v in s["votes"].items() if v},
                })
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(
        {"font": entry["name"], "tried": len(out), "suspects": len(rows), "rows": out},
        ensure_ascii=False))
    return out


def report(label: str, rows: list[dict]) -> None:
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
    for arg in sys.argv[1:]:
        name = Path(arg).name
        rows = run(name)
        report(name, rows)
        everything += rows
    if len(sys.argv) > 2:
        report("all books", everything)
