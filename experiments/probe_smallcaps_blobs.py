"""Small capitals told like with like (the user, 2026-11-24: "the s is noticeably taller
than another s would be"): on places whose versions differ only in case and whose letters,
in lower case, stand on the x-height alone, each letter's top from its own blob of ink,
against the tops of the same line's round lower-case letters (o, c, e, s, which overshoot
alike) and, where the line has them, of the same letters. No models.

    uv run python experiments/probe_smallcaps_blobs.py [book …]

A line's letters are matched to its blobs word by word: blobs that overlap in columns are
one letter (an i and its dot), marks smaller than a third of the line's letters are left
out, and a word is used only when its blobs and its letters come out the same in number.
Two ratios, each the place's height above the line's baseline over the reference letters':
`round` (against o, c, e, s) and `same` (each letter against its own kind on the line).
Lower case should stand near 1, small capitals above it. Writes
work/probes/smallcaps-blobs/rows.json.
"""

import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pymupdf
from scipy import ndimage

from roboscriptorium import pdf as pdflayer
from roboscriptorium import rendercheck as R
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/smallcaps-blobs")
TRUST = Path("work/probes/ocr-trust")
LOW = re.compile(r"^[acemnorsuvwxz.\-’'!?:]+$")
XLETTERS = set("acemnorsuvwxz")
ROUND = set("oces")


def blobs(ink: np.ndarray) -> list[list[int]]:
    """The clip's blobs as [x0, x1, top, bottom] in pixels, those overlapping in columns
    merged (an i and its dot), left to right."""
    labels, n = ndimage.label(ink, structure=np.ones((3, 3)))
    found = []
    for sl in ndimage.find_objects(labels):
        if sl is None:
            continue
        found.append([sl[1].start, sl[1].stop, sl[0].start, sl[0].stop])
    found.sort()
    merged: list[list[int]] = []
    for b in found:
        if merged and b[0] < merged[-1][1] - 1:
            m = merged[-1]
            m[1], m[2], m[3] = max(m[1], b[1]), min(m[2], b[2]), max(m[3], b[3])
        else:
            merged.append(list(b))
    return merged


def xline(found: list[list[int]]) -> tuple[float, float, int] | None:
    """The line's baseline and x-line from its letters' blobs: the baseline where most
    bottoms sit, the x-line where most tops sit below the ascenders (the lowest cluster of
    heights above the baseline holding at least a fifth of the letters). With the count of
    letters at the x-line."""
    if len(found) < 8:
        return None
    bottoms = np.array([b[3] for b in found], float)
    baseline = float(np.median(bottoms[np.abs(bottoms - np.median(bottoms)) <= 3]))
    sitting = [b for b in found if abs(b[3] - baseline) <= 3]
    heights = np.array(sorted(baseline - b[2] for b in sitting), float)
    if len(heights) < 6:
        return None
    for h in heights:
        near = heights[np.abs(heights - h) <= 2]
        if len(near) >= max(3, len(heights) / 5):
            xs = heights[np.abs(heights - np.median(near)) <= 2]
            return baseline, baseline - float(np.median(xs)), len(xs)
    return None


def letters(word_blobs: list[list[int]], text: str, floor: float) -> list[tuple[str, list[int]]]:
    """The word's letters paired with its blobs, or none when they don't come out equal."""
    kept = [b for b in word_blobs if b[3] - b[2] >= floor]
    chars = [c for c in text if c.isalpha()]
    if not chars or len(kept) != len(chars):
        return []
    return list(zip(chars, kept))


def page_kin(page, words) -> dict[str, list[float]]:
    """Every lower-case letter on the page, matched to its blob, as its height above its
    line's baseline over that line's x-height, by kind."""
    words = sorted(words, key=lambda w: (w[1] + w[3]) / 2)
    lines: list[list] = []
    for w in words:
        mid, high = (w[1] + w[3]) / 2, w[3] - w[1]
        if lines and abs(mid - (lines[-1][0][1] + lines[-1][0][3]) / 2) < high * 0.4:
            lines[-1].append(w)
        else:
            lines.append([w])
    kin: dict[str, list[float]] = {}
    scale = R.DPI / 72
    for line in lines:
        if len(line) < 4:
            continue
        x0, x1 = min(w[0] for w in line), max(w[2] for w in line)
        y0, y1 = min(w[1] for w in line), max(w[3] for w in line)
        high = y1 - y0
        clip = pymupdf.Rect(x0 - 2, y0 - high * 0.15, x1 + 2, y1 + high * 0.3) & page.rect
        with pdflayer.PDF_LOCK:
            grey = R._clip_ink(page, clip)
        if grey is None:
            continue
        found = [b for b in blobs(grey > 0.5) if b[2] > 0]
        if len(found) < 8:
            continue
        floor = np.median([b[3] - b[2] for b in found]) / 3
        line_x = xline([b for b in found if b[3] - b[2] >= floor])
        if line_x is None or line_x[0] - line_x[1] < 6:
            continue
        baseline, top, _ = line_x
        for w in line:
            c0, c1 = (w[0] - clip.x0) * scale, (w[2] - clip.x0) * scale
            inside = [b for b in found if c0 - 1 <= (b[0] + b[1]) / 2 <= c1 + 1]
            for c, b in letters(inside, w[4], floor):
                if c.islower() and abs(b[3] - baseline) <= 3:
                    kin.setdefault(c, []).append((baseline - b[2]) / (baseline - top))
    return kin


def book(name: str) -> list[dict]:
    d = Path("work") / name
    rows = json.loads((TRUST / f"{name}.json").read_text())
    pages = {p.number: p for p in cached_text_layer(d / "source.pdf", d / "stages/textlayer.json")}
    out = []
    kins: dict[int, dict] = {}
    with pymupdf.open(d / "source.pdf") as doc:
        for r in rows:
            s = r["suspect"]
            versions = [s["ours"], *s["others"]]
            right = r.get("right") or []
            if len({v.casefold() for v in versions}) != 1 or len(set(versions)) < 2:
                continue
            if sum(right) != 1 or not LOW.match(versions[0].casefold()):
                continue
            page = doc[s["page"] - 1]
            words = pdflayer.page_words(page, pages.get(s["page"]))
            bx0, by0, bx1, by1 = s["box"]
            mid = (by0 + by1) / 2
            line = [w for w in words if w[1] <= mid <= w[3]]
            if len(line) < 4:
                continue
            x0, x1 = min(w[0] for w in line), max(w[2] for w in line)
            y0, y1 = min(w[1] for w in line), max(w[3] for w in line)
            high = y1 - y0
            clip = pymupdf.Rect(x0 - 2, y0 - high * 0.15, x1 + 2, y1 + high * 0.3) & page.rect
            with pdflayer.PDF_LOCK:
                grey = R._clip_ink(page, clip)
            if grey is None:
                continue
            all_blobs = [b for b in blobs(grey > 0.5) if b[2] > 0]
            if len(all_blobs) < 8:
                continue
            floor = np.median([b[3] - b[2] for b in all_blobs]) / 3
            scale = R.DPI / 72

            def cols(w):
                return (w[0] - clip.x0) * scale, (w[2] - clip.x0) * scale

            def inside(w):
                c0, c1 = cols(w)
                return [b for b in all_blobs if c0 - 1 <= (b[0] + b[1]) / 2 <= c1 + 1]

            refs: list[tuple[str, list[int]]] = []
            span_blobs: list[list[int]] = []
            for w in line:
                centre = (w[0] + w[2]) / 2
                if bx0 - 1 <= centre <= bx1 + 1:
                    span_blobs += inside(w)
                else:
                    refs += [(c.lower(), b) for c, b in letters(inside(w), w[4], floor)
                             if c.islower()]
            others = [b for b in all_blobs if b not in span_blobs and b[3] - b[2] >= floor]
            line_x = xline(others)
            if line_x is None:
                continue
            baseline, ref_top, n_x = line_x
            xheight = baseline - ref_top
            if xheight < 6:
                continue
            body = [b for b in span_blobs if b[3] - b[2] >= floor and abs(b[3] - baseline) <= 3]
            if not body:
                continue
            paired = letters(span_blobs, versions[0], floor)
            alpha = [[c for c in v if c.isalpha()] for v in versions]
            differ = [i for i in range(len(alpha[0]))
                      if all(len(a) == len(alpha[0]) for a in alpha)
                      and len({a[i] for a in alpha}) > 1]
            if paired and differ:
                body = [paired[i][1] for i in differ]
            place_top = float(np.median([b[2] for b in body]))
            ratio_round = (baseline - place_top) / xheight
            same = []
            for c, b in paired:
                kin = [rb[2] for rc, rb in refs if rc == c.lower()]
                if kin:
                    same.append((baseline - b[2]) / (baseline - float(np.median(kin))))
            if s["page"] not in kins:
                kins[s["page"]] = page_kin(page, words)
            kin = kins[s["page"]]
            own = []
            if paired and differ:
                for i in differ:
                    c, b = paired[i]
                    pool = kin.get(c.lower(), [])
                    if len(pool) >= 3:
                        own.append(((baseline - b[2]) / xheight) / float(np.median(pool)))
            printed = versions[right.index(True)]
            out.append(
                {
                    "book": name,
                    "page": s["page"],
                    "box": s["box"],
                    "versions": versions,
                    "print": printed,
                    "capitals": printed.casefold() != printed,
                    "round": round(float(ratio_round), 3),
                    "same": round(float(np.median(same)), 3) if same else None,
                    "page_kin": round(float(np.median(own)), 3) if own else None,
                    "xheight_px": round(xheight, 1),
                    "above_px": round(ref_top - place_top, 1),
                    "refs": n_x,
                    "letters_only": bool(paired and differ),
                }
            )
    return out


def summary(rows: list[dict], key: str) -> None:
    rows = [r for r in rows if r[key] is not None]
    print(f"{key}: {len(rows)} places")
    for caps in (False, True):
        rs = sorted(r[key] for r in rows if r["capitals"] == caps)
        if rs:
            q = np.percentile(rs, [5, 25, 50, 75, 95])
            print(f"  print {'with capitals' if caps else 'lower case  '}: n={len(rs):4}  "
                  f"5/25/50/75/95% {' '.join(f'{x:.2f}' for x in q)}")
    caps_n = sum(r["capitals"] for r in rows)
    low_n = len(rows) - caps_n
    for cut in (1.04, 1.06, 1.08, 1.1, 1.12, 1.15):
        caps_above = sum(r[key] >= cut for r in rows if r["capitals"])
        low_above = sum(r[key] >= cut for r in rows if not r["capitals"])
        print(f"    at {cut}: capitals above {caps_above}/{caps_n}, "
              f"lower case above {low_above}/{low_n}")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.stem for p in TRUST.glob("*.json"))
    names = [n for n in names if (Path("work") / n / "source.pdf").exists()]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as pool:
        for found in pool.map(book, names):
            rows += found
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    summary(rows, "round")
    summary(rows, "same")
    summary(rows, "page_kin")
