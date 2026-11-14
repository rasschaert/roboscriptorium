"""The render judges' measures as arbiter columns, not votes (2026-11-14). The arbiter sees
the render judge only as a pick and its sureness; here it also gets, for every version,
how well its drawing lies over the scan's ink and its margin over the best rival, and,
for the two best-fitting versions, the second render judge's comparison where their
drawings differ (`render-differ`, branch of that name: as a vote it was not taken).

Two arbiters trained side by side on the same held-out folds as `probe_book_vocab.py`,
today's features against today's plus the columns; silent errors at the fixed rule's
number of questions, at none and at half. No models: the fits are drawn on the CPU and
kept per book in `work/probes/render-fit/` (a rerun goes on from them).

    PYTHONPATH=experiments uv run python experiments/probe_render_fit.py [--only fit|differ] [--control]
"""

import argparse
import json
import math
import sys
import zlib
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pymupdf
from probe_book_vocab import READINGS, SEATS, SETTINGS, rule, silent_at
from scipy.signal import fftconvolve
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import ocr, rendercheck, trust
from roboscriptorium.book import Book
from roboscriptorium.files import write_atomic
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.rendercheck import (
    _BLUR,
    RENDER_PX,
    STRETCHES,
    Face,
    _picture,
    _spread,
    drawings,
    fits,
    place_ink,
)
from roboscriptorium.trustdata import SPECS, rows_of, trainable, usable

OUT = Path("work/probes/render-fit")
APART = 64  # drawings differ where their darkness is this far apart (of 255)


def _laid(face, spread, size, canvas, energy, version, anchor=None):
    """The version's best-fitting drawing on the padded strip: fit, drawing, where."""
    best = (0.0, None, None)
    slack = max(2, round(size * 0.06))
    for glyphs in drawings(face, version):
        high = max(4, round(glyphs.shape[0] * size / RENDER_PX))
        for stretch in STRETCHES if anchor is None else (anchor[0],):
            wide = max(4, round(glyphs.shape[1] * size / RENDER_PX * stretch))
            if high > canvas.shape[0] or wide > canvas.shape[1]:
                continue
            sized = _spread(_picture(glyphs).resize((wide, high)), spread)
            mine = np.asarray(sized.filter(_BLUR), np.float32)
            over = fftconvolve(canvas, mine[::-1, ::-1], mode="valid")
            if anchor is not None:
                _, top, left, right = anchor
                x0 = left if left is not None else right - wide
                ys = slice(max(0, top - 3 * slack), top + 3 * slack + 1)
                xs = slice(max(0, x0 - slack), max(0, x0 + slack + 1))
                window = np.full_like(over, -np.inf)
                window[ys, xs] = over[ys, xs]
                over = window
                if not np.isfinite(over).any():
                    continue
            y, x = np.unravel_index(over.argmax(), over.shape)
            fit = float(over[y, x]) / (energy * float((mine * mine).sum()) + 1e-6) ** 0.5
            if fit > best[0]:
                laid = np.zeros_like(canvas)
                laid[y : y + high, x : x + wide] = mine
                best = (fit, laid, (int(y), int(x), wide, stretch))
    return best


def _shared(a: str, b: str) -> tuple[int, int]:
    limit = min(len(a), len(b))
    start = next((i for i in range(limit) if a[i] != b[i]), limit)
    end = next((i for i in range(limit) if a[-1 - i] != b[-1 - i]), limit)
    return start, end


def difference(face, spread, size, ink, first, second):
    """`render-differ`'s measure: the first's less the second's share, where the two
    drawings differ, of drawing without ink under it and of ink it doesn't draw."""
    strip = np.asarray(_picture(ink).filter(_BLUR), np.float32)
    pad = (round(size * 1.2), round(size * 3))
    canvas = np.pad(strip, ((pad[0], pad[0]), (pad[1], pad[1])))
    energy = float((strip * strip).sum())
    start, end = _shared(first, second)
    best = None
    for versions, sign in (((first, second), 1), ((second, first), -1)):
        fit, a, at = _laid(face, spread, size, canvas, energy, versions[0])
        if a is None:
            continue
        y, x, wide, stretch = at
        anchor = (stretch, y, x, None) if start >= end else (stretch, y, None, x + wide)
        _, b, _ = _laid(face, spread, size, canvas, energy, versions[1], anchor)
        if b is None:
            continue
        differ = np.abs(a - b) > APART
        n = int(differ.sum())
        if not n:
            continue
        bare = [float((np.clip(d - canvas, 0, None) * differ).sum()) / n / 255 for d in (a, b)]
        undrawn = [float((np.clip(canvas - d, 0, None) * differ).sum()) / n / 255 for d in (a, b)]
        if best is None or fit > best[0]:
            best = (fit, sign * (bare[0] - bare[1]), sign * (undrawn[0] - undrawn[1]))
    return None if best is None else list(best[1:])


def measure(name: str) -> str:
    """Each settled row's fits and differ measure for one book, kept in OUT/<name>.json,
    keyed by page, line and versions; rows already there are skipped."""
    path = OUT / f"{name}.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    book = Book.load(Path("work") / name)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json", ocr.language(book.language))
    whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
    found = rendercheck.match(book.source, whole, Path(SETTINGS.fonts), book.stages / "typeface.json", book.typeface)
    face = Face.from_file(Path(SETTINGS.fonts) / found.file)
    texts = {p.number: p for p in whole}
    heights = sorted(ln.y1 - ln.y0 for p in whole for ln in p.lines if ln.text.strip())
    line = heights[len(heights) // 2] if heights else None
    rows = rows_of(name, SETTINGS)
    new = 0
    with pymupdf.open(book.source) as doc:
        for r in rows:
            s = r["s"]
            versions = [s.ours, *s.others]
            key = f"{s.page}|{s.line}|{s.start}|{json.dumps(versions, ensure_ascii=False)}"
            if key in done:
                continue
            entry = None
            box = [round(v, 1) for v in s.box]
            if line is None or box[3] - box[1] <= rendercheck.DISPLAY * line:
                ink = place_ink(doc[s.page - 1], box, texts.get(s.page))
                if ink is not None:
                    f = fits(face, found.spread, found.size, ink, versions)
                    order = sorted(range(len(versions)), key=lambda i: -f[i])
                    d = difference(face, found.spread, found.size, ink, versions[order[0]], versions[order[1]])
                    entry = {"fits": f, "top": order[:2], "differ": d}
            done[key] = entry
            new += 1
            if new % 200 == 0:
                write_atomic(path, json.dumps(done, ensure_ascii=False))
    write_atomic(path, json.dumps(done, ensure_ascii=False))
    return f"{name}: {len(rows)} rows, {new} measured"


def columns(s, k: int, m: dict | None, only: str, control: bool) -> list[float]:
    """Version k's columns: its fit, its margin over the best rival's fit; the differ
    measure from its side where it is one of the two best fitting, else blank."""
    if control:
        versions = [s.ours, *s.others]
        rng = np.random.default_rng(zlib.crc32(f"{versions[0]}|{versions[k]}|{k}".encode()))
        return list(rng.uniform(0, 1, 2 if only else 4))
    fit = [math.nan, math.nan]
    differ = [math.nan, math.nan]
    if m is not None:
        f = m["fits"]
        rival = max((x for i, x in enumerate(f) if i != k), default=0.0)
        fit = [f[k], f[k] - rival]
        if m["differ"] is not None and k in m["top"]:
            sign = 1 if m["top"][0] == k else -1
            differ = [sign * m["differ"][0], sign * m["differ"][1]]
    return {"fit": fit, "differ": differ}.get(only, fit + differ)


def scored(train_rows, rows, extra, measures, only, control):
    def cols(r, k):
        return columns(r["s"], k, measures[r["book"]].get(r["key"]), only, control) if extra else []

    suspects = [r["s"] for r in train_rows]
    right = [r["right"] for r in train_rows]
    names = [r["book"] for r in train_rows]
    X, y = trust.training_matrix(suspects, right, names, READINGS, SEATS)
    if extra:
        # training_matrix walks the rows book by book, as probe_book_vocab does.
        added = [cols(r, k) for b in dict.fromkeys(names) for r in train_rows if r["book"] == b
                 for k in range(len(r["right"]))]  # fmt: skip
        X = np.hstack([X, np.array(added)])
    pairs = trust.pairs_table(suspects, right, names)
    Xt, owner = [], []
    for i, r in enumerate(rows):
        for k in range(len(r["right"])):
            Xt.append(trust.features(r["s"], k, pairs, READINGS, SEATS) + cols(r, k))
            owner.append(i)
    model = HistGradientBoostingClassifier(max_depth=3, min_samples_leaf=20, l2_regularization=1.0, random_state=0)
    probs = model.fit(X, y).predict_proba(np.array(Xt))[:, 1]
    out = [[] for _ in rows]
    for p, i in zip(probs, owner, strict=True):
        out[i].append(p)
    return [np.array(p) / max(sum(p), 1e-9) for p in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["fit", "differ"], default="")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--measure-only", action="store_true")
    a = ap.parse_args()
    names = [n for n in SPECS if not usable(n, SETTINGS)]
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(a.workers) as pool:
        for line in pool.map(measure, names):
            print(line, flush=True)
    if a.measure_only:
        return
    books, measures = {}, {}
    for n in names:
        rows = rows_of(n, SETTINGS)
        for r in rows:
            s = r["s"]
            versions = [s.ours, *s.others]
            r["key"] = f"{s.page}|{s.line}|{s.start}|{json.dumps(versions, ensure_ascii=False)}"
        books[n] = rows
        measures[n] = json.loads((OUT / f"{n}.json").read_text())
    covered = sum(measures[n].get(r["key"]) is not None for n in books for r in books[n])
    print(f"rows with a measure: {covered} of {sum(map(len, books.values()))}")
    totals, changed = Counter(), []
    label = "control" if a.control else (a.only or "fit+differ")
    print(f"{'book':34} {'rule':>9}  today/+{label} at: the rule's questions, none, half")
    for name, rows in books.items():
        silent, asked = rule(rows)
        train_rows = [r for n in books if n != name and trainable(n) for r in books[n]]
        pa = scored(train_rows, rows, False, measures, a.only, a.control)
        pb = scored(train_rows, rows, True, measures, a.only, a.control)
        cells = []
        for lab, n in (("rule's", asked), ("none", 0), ("half", asked // 2)):
            x, y = silent_at(rows, pa, n), silent_at(rows, pb, n)
            totals[f"today@{lab}"] += x
            totals[f"+cols@{lab}"] += y
            cells.append(f"{x}/{y}")
        totals["rule"] += silent
        print(f"{name[:34]:34} {silent:4}/{asked:<4}  " + "  ".join(cells), flush=True)
        for r, x, y in zip(rows, pa, pb, strict=True):
            if int(x.argmax()) != int(y.argmax()):
                v = [r["s"].ours, *r["s"].others]
                changed.append((name, v, v[int(x.argmax())], v[int(y.argmax())], r["right"][int(y.argmax())]))
    print("totals:", dict(totals))
    fixed = [c for c in changed if c[4]]
    print(f"best version changed on {len(changed)} suspects: right now on {len(fixed)}, wrong now on {len(changed) - len(fixed)}")
    for c in changed[:60]:
        print(f"  {'FIXED' if c[4] else 'BROKE'} {c[0][:16]:16} {c[1]}  {c[2]!r} → {c[3]!r}")


if __name__ == "__main__":
    sys.exit(main())
