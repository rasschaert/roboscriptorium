"""Whether render's horizontal stretch hides small capitals: on places whose versions differ
only in case (the trust data's labelled suspects, as `probe_smallcaps_sweep.py`), each
version's fit at each stretch alone, small capitals at `SHARES`. Scored four ways: each
version at its own best stretch (production), every version at 1.0, every version at the
stretch the best-fitting drawing of the place chose (one width for all), and at the
stretch best on average over the versions. A small capital sets wider than a lower-case
letter: a stretch of its own lets the lower-case version take that width. No models.

    uv run python experiments/probe_smallcaps_stretch.py [book …]
    uv run python experiments/probe_smallcaps_stretch.py --report

Writes work/probes/smallcaps-stretch/<book>.json as each book finishes (a rerun skips the
books done) and report.txt.
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf

from roboscriptorium import rendercheck as R
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/smallcaps-stretch")
TRUST = Path("work/probes/ocr-trust")
FONTS = Path("work/fonts")
SHARES = (0.76, 0.80)
STRETCHES = R.STRETCHES


def book(name: str) -> str:
    d = Path("work") / name
    rows = json.loads((TRUST / f"{name}.json").read_text())
    match = R.Match(**json.loads((d / "stages/typeface.json").read_text())["match"])
    face = R.Face.from_file(FONTS / match.file, italic=True)
    upright = R.Face(face._load, face.figures)
    pages = {p.number: p for p in cached_text_layer(d / "source.pdf", d / "stages/textlayer.json")}
    R.SMALL_CAPS = SHARES
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
            fits = {}
            for stretch in STRETCHES:
                R.STRETCHES = (stretch,)
                fits[str(stretch)] = [
                    round(x, 5) for x in R.fits(f, match.spread, match.size, ink, versions)
                ]
            R.STRETCHES = STRETCHES
            out.append(
                {
                    "page": s["page"],
                    "versions": versions,
                    "print": versions[right.index(True)],
                    "fits": fits,
                }
            )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return name


def scores(row: dict, way: str) -> list[float]:
    n, keys = len(row["versions"]), [str(s) for s in STRETCHES]
    if way == "own":
        return [max(row["fits"][k][i] for k in keys) for i in range(n)]
    if way == "1.0":
        return row["fits"]["1.0"]
    if way == "the best drawing's":
        k = max(keys, key=lambda k: max(row["fits"][k]))
        return row["fits"][k]
    k = max(keys, key=lambda k: sum(row["fits"][k]))
    return row["fits"][k]


def report() -> str:
    rows = [r for p in sorted(OUT.glob("*.json")) for r in json.loads(p.read_text())]
    lines = [f"{len(rows)} places differing only in case; small capitals at {SHARES}", ""]
    for way in ("own", "1.0", "the best drawing's", "the best on average"):
        right, up, down = 0, 0, 0
        for r in rows:
            s = scores(r, way)
            got = r["versions"][max(range(len(s)), key=lambda i: s[i])]
            if got == r["print"]:
                right += 1
            elif sum(c.isupper() for c in r["print"]) > sum(c.isupper() for c in got):
                up += 1
            else:
                down += 1
        lines.append(
            f"  stretch {way:20}: {right} right; wrong {up} where the print has more capitals, "
            f"{down} fewer"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        text = report()
        (OUT / "report.txt").write_text(text + "\n")
        print(text)
        sys.exit()
    names = sys.argv[1:] or sorted(p.stem for p in TRUST.glob("*.json"))
    names = [n for n in names if (Path("work") / n / "stages/typeface.json").exists()]
    names = [n for n in names if not (OUT / f"{n}.json").exists()]
    with ProcessPoolExecutor(max_workers=12) as pool:
        for name in pool.map(book, names):
            print(f"done {name}", flush=True)
    text = report()
    (OUT / "report.txt").write_text(text + "\n")
    print(text)
