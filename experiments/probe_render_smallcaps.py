"""Render and compare on places whose versions differ only in case: small capitals drawn at
the fixed share of a capital (`rendercheck.SMALL_CAPS`) against shares of the face's own
x-height (its OS/2 x-height over its cap height), and both together. On the trust data's labelled suspects,
each book in its matched face; render's pick against the print, by direction. No models.

    uv run python experiments/probe_render_smallcaps.py [book …]

Writes work/probes/render-smallcaps/<book>.json, one row a suspect: the versions, which are
the print, and render's pick under each way of drawing.
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf
from fontTools.ttLib import TTFont

from roboscriptorium import rendercheck as R
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/render-smallcaps")
TRUST = Path("work/probes/ocr-trust")
FONTS = Path("work/fonts")
# Small capitals as shares of the face's x-height over its cap height.
RELATIVE = (1.0, 1.1, 1.2)


def x_over_cap(path: Path) -> float:
    os2 = TTFont(path, lazy=True)["OS/2"]
    return os2.sxHeight / os2.sCapHeight


def book(name: str) -> tuple[str, list[dict]]:
    d = Path("work") / name
    rows = json.loads((TRUST / f"{name}.json").read_text())
    match = R.Match(**json.loads((d / "stages/typeface.json").read_text())["match"])
    face = R.Face.from_file(FONTS / match.file, italic=True)
    upright = R.Face(face._load, face.figures)
    ratio = x_over_cap(FONTS / match.file)
    own = tuple(round(ratio * k, 3) for k in RELATIVE)
    ways = {"fixed": R.SMALL_CAPS, "face": own, "both": tuple(sorted({*R.SMALL_CAPS, *own}))}
    pages = {p.number: p for p in cached_text_layer(d / "source.pdf", d / "stages/textlayer.json")}
    out = []
    with pymupdf.open(d / "source.pdf") as doc:
        for r in rows:
            s = r["suspect"]
            versions = [s["ours"], *s["others"]]
            right = r.get("right") or []
            if len({v.casefold() for v in versions}) != 1 or len(set(versions)) < 2:
                continue
            if sum(right) != 1:
                continue
            ink = R.place_ink(doc[s["page"] - 1], s["box"], pages.get(s["page"]))
            if ink is None:
                continue
            f = face if R.italic_tells(versions) else upright
            picks, scores = {}, {}
            for way, scales in ways.items():
                R.SMALL_CAPS = scales
                fits = R.fits(f, match.spread, match.size, ink, versions)
                picks[way] = versions[max(range(len(versions)), key=lambda i: fits[i])]
                scores[way] = [round(x, 4) for x in fits]
            out.append(
                {
                    "page": s["page"],
                    "versions": versions,
                    "print": versions[right.index(True)],
                    "picks": picks,
                    "fits": scores,
                    "ratio": round(ratio, 3),
                }
            )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return name, out


def capitals(v: str) -> int:
    return sum(c.isupper() for c in v)


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.stem for p in TRUST.glob("*.json"))
    names = [n for n in names if (Path("work") / n / "stages/typeface.json").exists()]
    total = {"fixed": [0, 0], "face": [0, 0], "both": [0, 0]}
    with ProcessPoolExecutor(max_workers=12) as pool:
        for name, rows in pool.map(book, names):
            line = []
            for way in ("fixed", "face", "both"):
                ok = sum(r["picks"][way] == r["print"] for r in rows)
                total[way][0] += ok
                total[way][1] += len(rows)
                line.append(f"{way} {ok}/{len(rows)}")
            moved = [r for r in rows if r["picks"]["fixed"] != r["picks"]["face"]]
            print(f"{name[:40]:40} {'  '.join(line)}  changed {len(moved)}", flush=True)
            for r in moved:
                up = capitals(r["print"]) > capitals(min(r["versions"], key=capitals))
                tag = "now right" if r["picks"]["face"] == r["print"] else (
                    "now wrong" if r["picks"]["fixed"] == r["print"] else "both wrong")
                print(f"    {tag:10} p{r['page']} print {r['print']!r} (capitals {'more' if up else 'fewer'}): "
                      f"{r['picks']['fixed']!r} → {r['picks']['face']!r}")
    for way, (ok, n) in total.items():
        print(f"{way}: {ok} of {n} right")
