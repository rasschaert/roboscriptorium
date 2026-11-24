"""Which version's case fits the ink, letter by letter, like with like on the page; each
letter's ink cut where the book's face puts it, not by counting blobs (probe_case_fit.py's
pairing failed on touching letters, hyphens and dots). No models.

    uv run python experiments/probe_case_fit2.py [book …] [--small 0.78]

A word's ink runs from its first to its last inked column (its layer box grown or shrunk to
the ink). Each version is laid across it by the matched face's advances (book's
stages/typeface.json): capitals render sets as small capitals (a run of two or more, or one
standing alone: `rendercheck._SMALL`) at SMALL of their width and height.
Each letter's middle half of columns gives its top and bottom: height above the line's
baseline and depth below it over the line's x-height (baseline and x-line where most of the
line's blobs bottom and top out). The page's words, laid by their layer text the same way,
give each lower-case letter's usual height and depth and the capitals' height. A version's
misfit is its letters' mean distance from what the page says; the least misfit is the pick.
Writes work/probes/case-fit2/rows.json.
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pymupdf
from PIL import ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from probe_case_fit import lines_of  # noqa: E402
from probe_smallcaps_blobs import blobs, xline  # noqa: E402

from roboscriptorium import pdf as pdflayer  # noqa: E402
from roboscriptorium import rendercheck as R  # noqa: E402
from roboscriptorium.pdf import cached_text_layer  # noqa: E402

OUT = Path("work/probes/case-fit2")
TRUST = Path("work/probes/ocr-trust")
FONTS = Path("work/fonts")
SMALL = float(sys.argv[sys.argv.index("--small") + 1]) if "--small" in sys.argv else 0.78


def face(name: str) -> ImageFont.FreeTypeFont | None:
    held = json.loads((Path("work") / name / "stages/typeface.json").read_text())
    path = FONTS / held["match"]["file"]
    return ImageFont.truetype(str(path), 100) if path.exists() else None


def small_at(text: str) -> set[int]:
    """The positions render sets in small capitals (`rendercheck._SMALL`)."""
    return {i for m in R._SMALL.finditer(text) for i in range(m.start(), m.end())}


def advances(font, text: str) -> list[tuple[str, float, bool]]:
    """Each character with its advance and whether it is a small capital."""
    small = small_at(text)
    return [(c, font.getlength(c) * (SMALL * 1.05 if i in small else 1.0), i in small)
            for i, c in enumerate(text)]


class Line:
    def __init__(self, page, words):
        x0, x1 = min(w[0] for w in words), max(w[2] for w in words)
        y0, y1 = min(w[1] for w in words), max(w[3] for w in words)
        high = y1 - y0
        self.clip = pymupdf.Rect(x0 - 2, y0 - high * 0.15, x1 + 2, y1 + high * 0.45) & page.rect
        with pdflayer.PDF_LOCK:
            grey = R._clip_ink(page, self.clip)
        self.ok = False
        if grey is None:
            return
        self.ink = grey > 0.5
        found = [b for b in blobs(self.ink) if b[2] > 0]
        if len(found) < 8:
            return
        floor = float(np.median([b[3] - b[2] for b in found])) / 3
        lx = xline([b for b in found if b[3] - b[2] >= floor])
        if lx is None or lx[0] - lx[1] < 6:
            return
        self.base, self.xh = lx[0], lx[0] - lx[1]
        top = max(0, int(self.base - 1.7 * self.xh))
        bottom = min(self.ink.shape[0], int(self.base + 0.7 * self.xh))
        self.band = self.ink[top:bottom]
        self.top = top
        self.cols = self.band.any(0)
        self.ok = True

    def extent(self, box) -> tuple[int, int] | None:
        scale = R.DPI / 72
        a = max(0, round((box[0] - self.clip.x0) * scale))
        b = min(len(self.cols), round((box[2] - self.clip.x0) * scale))
        if b - a < 3:
            return None
        while a > 0 and self.cols[a - 1]:
            a -= 1
        while b < len(self.cols) and self.cols[b]:
            b += 1
        inked = np.where(self.cols[a:b])[0]
        if not len(inked):
            return None
        return a + int(inked[0]), a + int(inked[-1]) + 1

    def letters(self, span, laid) -> list[tuple[str, float, float]] | None:
        """(letter, height, depth) for each letter of `laid` across columns `span`."""
        total = sum(w for _, w, _ in laid)
        if total <= 0:
            return None
        a, b = span
        scale = (b - a) / total
        out, x = [], float(a)
        for c, w, small in laid:
            l0, l1 = x, x + w * scale
            x = l1
            if not c.isalpha():
                continue
            m0, m1 = int(l0 + (l1 - l0) * 0.25), int(np.ceil(l1 - (l1 - l0) * 0.25))
            rows = np.where(self.band[:, m0:max(m1, m0 + 1)].any(1))[0]
            if not len(rows):
                return None
            top, bottom = self.top + rows[0], self.top + rows[-1] + 1
            out.append((c, small, (self.base - top) / self.xh, (bottom - self.base) / self.xh))
        return out


def table_of(page, words, font) -> dict[str, list[tuple[float, float]]]:
    table: dict[str, list[tuple[float, float]]] = {}
    for words_ in lines_of(words):
        if len(words_) < 4:
            continue
        line = Line(page, words_)
        if not line.ok:
            continue
        for w in words_:
            text = w[4]
            if not any(c.isalpha() for c in text):
                continue
            span = line.extent(w)
            got = span and line.letters(span, advances(font, text))
            for c, small, h, d in got or []:
                if not small:
                    table.setdefault(c, []).append((h, d))
    return table


def expect(c, small, table):
    if c.islower():
        pool = table.get(c, [])
        if len(pool) < 3:
            return None
        return float(np.median([p[0] for p in pool])), float(np.median([p[1] for p in pool]))
    caps = [p for k, v in table.items() if k.isupper() and k not in "QJ" for p in v]
    if len(caps) < 3:
        return None
    cap = float(np.median([p[0] for p in caps]))
    return (cap * SMALL if small else cap), 0.0


def book(name: str) -> list[dict]:
    d = Path("work") / name
    font = face(name)
    if font is None:
        return []
    rows = json.loads((TRUST / f"{name}.json").read_text())
    pages = {p.number: p for p in cached_text_layer(d / "source.pdf", d / "stages/textlayer.json")}
    out, tables = [], {}
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
            on_line = [w for w in words if w[1] <= mid <= w[3]]
            if len(on_line) < 4:
                continue
            line = Line(page, on_line)
            if not line.ok:
                continue
            span = line.extent((bx0, by0, bx1, by1))
            if span is None:
                continue
            if s["page"] not in tables:
                others = [w for w in words if not (w[1] <= mid <= w[3]
                                                    and bx0 - 1 <= (w[0] + w[2]) / 2 <= bx1 + 1)]
                tables[s["page"]] = table_of(page, others, font)
            table = tables[s["page"]]
            fits = []
            for v in versions:
                got = line.letters(span, advances(font, v))
                errs = []
                for c, small, h, dp in got or []:
                    e = expect(c, small, table)
                    if e is None:
                        errs = None
                        break
                    errs.append(abs(h - e[0]) + abs(dp - e[1]))
                fits.append(round(float(np.mean(errs)), 3) if errs else None)
            out.append({
                "book": name, "page": s["page"], "box": s["box"], "versions": versions,
                "print": versions[right.index(True)], "ours": s["ours"], "fits": fits,
            })
    return out


def report(rows: list[dict]) -> None:
    for kind in ("inner", "initial"):
        n = fit = ours = 0
        for r in rows:
            fold = r["print"].casefold()
            cands = [(f, v) for f, v in zip(r["fits"], r["versions"])
                     if f is not None and v.casefold() == fold]
            if len(cands) < 2 or r["print"] not in [v for _, v in cands]:
                continue
            inner = any(any(c.isupper() for c in [ch for ch in v if ch.isalpha()][1:])
                        for _, v in cands)
            if (kind == "inner") != inner:
                continue
            n += 1
            fit += min(cands)[1] == r["print"]
            ours += r["ours"] == r["print"]
        print(f"SMALL={SMALL} {kind}: {n} places; the fit picks the print at {fit}, "
              f"the layer has it at {ours}")


if __name__ == "__main__":
    args = [a for i, a in enumerate(sys.argv[1:], 1)
            if a != "--small" and sys.argv[i - 1] != "--small"]
    names = args or sorted(p.stem for p in TRUST.glob("*.json"))
    names = [n for n in names if (Path("work") / n / "stages/typeface.json").exists()]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as pool:
        for found in pool.map(book, names):
            rows += found
    report(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
