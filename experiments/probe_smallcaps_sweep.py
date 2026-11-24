"""The height render and compare draws small capitals at, swept: on places whose versions
differ only in case (the trust data's labelled suspects, each book in its matched face),
each version's fit with small capitals drawn at one share of a capital's height, for
shares from below the faces' x-heights to near a full capital, and with none drawn.

A version's fit under several shares is the best of its fits under each, so any set of
shares is scored from these rows without drawing again. No models.

    uv run python experiments/probe_smallcaps_sweep.py [book …]
    uv run python experiments/probe_smallcaps_sweep.py --report

Writes work/probes/smallcaps-sweep/<book>.json as each book finishes (a rerun skips the
books done) and report.txt.
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf
from fontTools.ttLib import TTFont

from roboscriptorium import rendercheck as R
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/smallcaps-sweep")
TRUST = Path("work/probes/ocr-trust")
FONTS = Path("work/fonts")
SHARES = tuple(round(0.56 + 0.02 * i, 2) for i in range(19))  # 0.56 … 0.92
NONE = "none"


def x_over_cap(path: Path) -> float:
    os2 = TTFont(path, lazy=True)["OS/2"]
    return os2.sxHeight / os2.sCapHeight


def book(name: str) -> str:
    d = Path("work") / name
    rows = json.loads((TRUST / f"{name}.json").read_text())
    match = R.Match(**json.loads((d / "stages/typeface.json").read_text())["match"])
    face = R.Face.from_file(FONTS / match.file, italic=True)
    upright = R.Face(face._load, face.figures)
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
            fits = {}
            for share in (NONE, *SHARES):
                R.SMALL_CAPS = () if share == NONE else (share,)
                fits[str(share)] = [
                    round(x, 5) for x in R.fits(f, match.spread, match.size, ink, versions)
                ]
            out.append(
                {
                    "page": s["page"],
                    "versions": versions,
                    "print": versions[right.index(True)],
                    "fits": fits,
                }
            )
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"x_over_cap": round(x_over_cap(FONTS / match.file), 3), "rows": out}
    (OUT / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return name


def pick(row: dict, shares: tuple) -> str:
    n = len(row["versions"])
    best = [max(row["fits"][str(s)][i] for s in shares) for i in range(n)]
    return row["versions"][max(range(n), key=lambda i: best[i])]


def capitals(v: str) -> int:
    return sum(c.isupper() for c in v)


def report() -> str:
    books = {p.stem: json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))}
    rows = [r for b in books.values() for r in b["rows"]]
    lines = [f"{len(rows)} places differing only in case, {len(books)} books", ""]
    settings = [(NONE,), *[(s,) for s in SHARES], (NONE, 0.74, 0.82)]
    settings += [(NONE, a, b) for a in SHARES for b in SHARES if a < b]
    scored = []
    for shares in settings:
        ok = [pick(r, shares) == r["print"] for r in rows]
        wrong_up = sum(
            not k and capitals(r["print"]) > capitals(pick(r, shares)) for r, k in zip(rows, ok)
        )
        scored.append((sum(ok), shares, wrong_up, len(ok) - sum(ok) - wrong_up))
    lines.append("one share (plus full size): right, wrong where the print has more capitals / fewer")
    for ok, shares, up, down in scored[: 1 + len(SHARES) + 1]:
        label = "none" if shares == (NONE,) else "+".join(str(s) for s in shares[1:]) or shares[0]
        lines.append(f"  {label:>10}: {ok}  ({up} / {down})")
    lines.append("")
    lines.append("best pairs of shares:")
    for ok, shares, up, down in sorted(scored[1 + len(SHARES) + 1 :], key=lambda t: -t[0])[:8]:
        lines.append(f"  {shares[1]}+{shares[2]}: {ok}  ({up} / {down})")
    lines.append("")
    lines.append("by book: right at production's 0.74+0.82, and the best single share")
    for name, b in books.items():
        rs = b["rows"]
        if not rs:
            continue
        prod = sum(pick(r, (NONE, 0.74, 0.82)) == r["print"] for r in rs)
        per = {s: sum(pick(r, (NONE, s)) == r["print"] for r in rs) for s in SHARES}
        top = max(per.values())
        best = [s for s in SHARES if per[s] == top]
        lines.append(
            f"  {name[:38]:38} x/cap {b['x_over_cap']:.2f}  {prod}/{len(rs)} → {top} at "
            f"{best[0]}–{best[-1]}"
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
