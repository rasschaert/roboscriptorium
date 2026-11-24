"""Which version's case fits the ink, letter by letter, measured like with like on the page
(the user's tell, 2026-11-24: "the s is noticeably taller than another s would be"). No
models.

    uv run python experiments/probe_case_fit.py [book …]

On the trust data's places where two versions differ only in case, each version whose
letters come out equal in number to the place's blobs is paired letter to blob. Each
letter's height above its line's baseline and its depth below it, over the line's
x-height, is compared with what the page says that letter would be: a lower-case letter
with the same letter elsewhere on the page; a capital opening the word with the page's
capitals; a capital inside a word with a small capital (the page's capitals at SMALL of
their height, sitting on the baseline). The version with the least misfit is the probe's
pick, scored against the print among the versions that fit. Writes
work/probes/case-fit/rows.json.
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from probe_smallcaps_blobs import blobs, xline  # noqa: E402

from roboscriptorium import pdf as pdflayer  # noqa: E402
from roboscriptorium import rendercheck as R  # noqa: E402
from roboscriptorium.pdf import cached_text_layer  # noqa: E402

OUT = Path("work/probes/case-fit")
TRUST = Path("work/probes/ocr-trust")
SMALL = float((sys.argv[sys.argv.index("--small") + 1]) if "--small" in sys.argv else 0.78)


def kept(found: list[list[int]], floor: float) -> list[list[int]]:
    return [b for b in found if b[3] - b[2] >= floor]


def pair(word_blobs: list[list[int]], text: str) -> list[tuple[str, list[int]]]:
    chars = [c for c in text if c.isalpha()]
    if not chars or len(word_blobs) != len(chars):
        return []
    return list(zip(chars, word_blobs))


def lines_of(words: list) -> list[list]:
    words = sorted(words, key=lambda w: (w[1] + w[3]) / 2)
    lines: list[list] = []
    for w in words:
        mid, high = (w[1] + w[3]) / 2, w[3] - w[1]
        if lines and abs(mid - (lines[-1][0][1] + lines[-1][0][3]) / 2) < high * 0.4:
            lines[-1].append(w)
        else:
            lines.append([w])
    return lines


def measure_line(page, line):
    """The line's blobs, baseline, x-height, floor and clip, or None."""
    x0, x1 = min(w[0] for w in line), max(w[2] for w in line)
    y0, y1 = min(w[1] for w in line), max(w[3] for w in line)
    high = y1 - y0
    clip = pymupdf.Rect(x0 - 2, y0 - high * 0.15, x1 + 2, y1 + high * 0.45) & page.rect
    with pdflayer.PDF_LOCK:
        grey = R._clip_ink(page, clip)
    if grey is None:
        return None
    found = [b for b in blobs(grey > 0.5) if b[2] > 0]
    if len(found) < 8:
        return None
    floor = float(np.median([b[3] - b[2] for b in found])) / 3
    lx = xline(kept(found, floor))
    if lx is None or lx[0] - lx[1] < 6:
        return None
    baseline, top, _ = lx
    return found, baseline, baseline - top, floor, clip


def word_blobs(found, clip, w):
    scale = R.DPI / 72
    c0, c1 = (w[0] - clip.x0) * scale, (w[2] - clip.x0) * scale
    return [b for b in found if c0 - 1 <= (b[0] + b[1]) / 2 <= c1 + 1]


def shape(b, baseline, xh) -> tuple[float, float]:
    return (baseline - b[2]) / xh, (b[3] - baseline) / xh


def page_table(page, words) -> dict[str, list[tuple[float, float]]]:
    """Each letter on the page (its own case as the layer reads it) as (height, depth)."""
    table: dict[str, list[tuple[float, float]]] = {}
    for line in lines_of(words):
        if len(line) < 4:
            continue
        m = measure_line(page, line)
        if m is None:
            continue
        found, baseline, xh, floor, clip = m
        for w in line:
            for c, b in pair(kept(word_blobs(found, clip, w), floor), w[4]):
                table.setdefault(c, []).append(shape(b, baseline, xh))
    return table


def expect(c: str, first: bool, table) -> tuple[float, float] | None:
    """What the page says letter c would measure as, or None when it can't say."""
    if c.islower():
        pool = table.get(c, [])
        if len(pool) < 3:
            return None
        return float(np.median([p[0] for p in pool])), float(np.median([p[1] for p in pool]))
    caps = [p for k, v in table.items() if k.isupper() and k not in "QJ" for p in v]
    if len(caps) < 3:
        return None
    cap = float(np.median([p[0] for p in caps]))
    return (cap if first else cap * SMALL), 0.0


def misfit(version: str, paired_blobs, baseline, xh, table) -> float | None:
    letters = [c for c in version if c.isalpha()]
    if len(letters) != len(paired_blobs):
        return None
    errs = []
    for i, (c, b) in enumerate(zip(letters, paired_blobs)):
        e = expect(c, i == 0, table)
        if e is None:
            return None
        h, d = shape(b, baseline, xh)
        errs.append(abs(h - e[0]) + abs(d - e[1]))
    return float(np.mean(errs))


def book(name: str) -> list[dict]:
    d = Path("work") / name
    rows = json.loads((TRUST / f"{name}.json").read_text())
    pages = {p.number: p for p in cached_text_layer(d / "source.pdf", d / "stages/textlayer.json")}
    out = []
    tables: dict[int, dict] = {}
    with pymupdf.open(d / "source.pdf") as doc:
        for r in rows:
            s = r["suspect"]
            versions = [s["ours"], *s["others"]]
            right = r.get("right") or []
            if sum(right) != 1:
                continue
            folds = [v.casefold() for v in versions]
            if not any(folds.count(f) > 1 and versions.count(v) < folds.count(f)
                       for v, f in zip(versions, folds)):
                continue
            page = doc[s["page"] - 1]
            words = pdflayer.page_words(page, pages.get(s["page"]))
            bx0, by0, bx1, by1 = s["box"]
            mid = (by0 + by1) / 2
            line = [w for w in words if w[1] <= mid <= w[3]]
            if len(line) < 4:
                continue
            m = measure_line(page, line)
            if m is None:
                continue
            found, baseline, xh, floor, clip = m
            span = []
            for w in line:
                if bx0 - 1 <= (w[0] + w[2]) / 2 <= bx1 + 1:
                    span += kept(word_blobs(found, clip, w), floor)
            if not span:
                continue
            if s["page"] not in tables:
                others = [w for w in words if not (w[1] <= mid <= w[3]
                                                    and bx0 - 1 <= (w[0] + w[2]) / 2 <= bx1 + 1)]
                tables[s["page"]] = page_table(page, others)
            fits = [misfit(v, span, baseline, xh, tables[s["page"]]) for v in versions]
            printed = versions[right.index(True)]
            out.append({
                "book": name, "page": s["page"], "box": s["box"], "versions": versions,
                "print": printed, "ours": s["ours"],
                "fits": [None if f is None else round(f, 3) for f in fits],
            })
    return out


def report(rows: list[dict]) -> None:
    scored = right_n = ours_right = 0
    print_fold = 0
    for r in rows:
        fold = r["print"].casefold()
        cands = [(f, v) for f, v in zip(r["fits"], r["versions"])
                 if f is not None and v.casefold() == fold]
        if len(cands) < 2 or r["print"] not in [v for _, v in cands]:
            continue
        scored += 1
        best = min(cands)[1]
        r["pick"] = best
        right_n += best == r["print"]
        ours_right += r["ours"] == r["print"]
        print_fold += 1
    print(f"SMALL={SMALL}: {len(rows)} case places, {scored} with the print and another case "
          f"fitted; the fit picks the print at {right_n}, the layer has it at {ours_right}")


if __name__ == "__main__":
    args = [a for i, a in enumerate(sys.argv[1:], 1)
            if a != "--small" and sys.argv[i - 1] != "--small"]
    names = args or sorted(p.stem for p in TRUST.glob("*.json"))
    names = [n for n in names if (Path("work") / n / "source.pdf").exists()]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as pool:
        for found in pool.map(book, names):
            rows += found
    report(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
