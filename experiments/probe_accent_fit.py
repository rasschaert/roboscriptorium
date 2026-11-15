"""Reworked dropped idea 5: is the mark over a letter an accent or a speck, by the render
judge's fit over the accent alone? The 2026-10-26 probe measured the ink blob above the
letter (AUC 0.81 in a forest); this one draws the word with and without the mark in the
book's matched typeface, lays the unmarked drawing over the scan's ink, and scores the
scan in the zone where the two drawings differ: its cosine with the accent's own shape,
and how much ink sits there against the accent's. No models.

For every settled trust-data place where two versions differ only by one letter's mark and
one of them is the print. Label: the print has the mark. Prints each measure's AUC beside
the whole-word fit margin's, and a logistic model's leaving one book out.

    PYTHONPATH=experiments uv run python experiments/probe_accent_fit.py [book …]
"""

import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw
from probe_accent_mark import marked_letter, strip
from scipy.signal import fftconvolve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from roboscriptorium import pipeline, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.trustdata import SPECS, rows_of, usable

OUT = Path("work/probes/accent-fit.jsonl")
PX = rendercheck.RENDER_PX


def pair(face, marked: str, plain: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Both versions drawn on one canvas, cropped to their joint ink (0–1 darkness)."""
    font = face.at(1.0)
    width = int(max(font.getlength(marked), font.getlength(plain))) + PX
    out = []
    for text in (marked, plain):
        image = Image.new("L", (width, PX * 2), 255)
        ImageDraw.Draw(image).text((PX // 4, PX * 1.3), text, font=font, fill=0, anchor="ls")
        out.append(1.0 - np.asarray(image, np.float32) / 255.0)
    both = np.maximum(*out) > 0.2
    if not both.any():
        return None
    rows, cols = np.where(both.any(1))[0], np.where(both.any(0))[0]
    cut = np.s_[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]
    return out[0][cut], out[1][cut]


def measures(face, found, ink: np.ndarray, marked: str, plain: str) -> dict | None:
    drawn = pair(face, marked, plain)
    if drawn is None:
        return None
    strip_ = np.asarray(rendercheck._picture(ink).filter(rendercheck._BLUR), np.float32)
    best = None
    for stretch in rendercheck.STRETCHES:
        high = max(4, round(drawn[0].shape[0] * found.size / PX))
        wide = max(4, round(drawn[0].shape[1] * found.size / PX * stretch))
        sized = [
            np.asarray(
                rendercheck._spread(rendercheck._picture(g).resize((wide, high)), found.spread).filter(rendercheck._BLUR),
                np.float32,
            )
            for g in drawn
        ]
        pad_y, pad_x = max(6, high - strip_.shape[0] + 6), max(6, wide - strip_.shape[1] + 6)
        canvas = np.pad(strip_, ((pad_y, pad_y), (pad_x, pad_x)))
        # Placed by the letters both versions share, so the mark itself can't pull it.
        shared = np.minimum(*sized)
        over = fftconvolve(canvas, shared[::-1, ::-1], mode="valid")
        y, x = np.unravel_index(int(over.argmax()), over.shape)
        score = float(over.max()) / (float((shared * shared).sum()) ** 0.5 + 1e-6)
        if best is None or score > best[0]:
            best = (score, canvas[y : y + high, x : x + wide], sized)
    _, under, (with_mark, without) = best
    accent = np.clip(with_mark - without, 0, None)
    zone = accent > 0.15 * 255
    if zone.sum() < 6 or under.shape != accent.shape:
        return None
    # A little room around the accent: a speck beside it counts as ink that isn't it.
    from scipy import ndimage

    around = ndimage.binary_dilation(zone, iterations=3) & (without < 0.15 * 255)
    s, a = under[around], accent[around]
    cosine = float((s * a).sum() / (np.sqrt((s * s).sum() * (a * a).sum()) + 1e-6))
    mass = float(under[zone].sum() / (accent[zone].sum() + 1e-6))
    stray = float(under[around & ~zone].mean() / 255) if (around & ~zone).any() else 0.0
    whole = rendercheck.fits(face, found.spread, found.size, ink, [marked, plain])
    return {"cosine": cosine, "mass": mass, "stray": stray, "whole": whole[0] - whole[1]}


def main():
    settings = Settings.from_env()
    names = sys.argv[1:] or [n for n in SPECS if not usable(n, settings)]
    done = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            row = json.loads(line)
            done.setdefault(row["book"], []).append(row)
    for name in names:
        if name in done:
            continue
        book = Book.load(Path("work") / name)
        layer = cached_text_layer(book.source, book.stages / "textlayer.json")
        whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
        judge = pipeline._alarm("render", settings, book, whole)
        if judge is None:
            print(f"{name}: no typeface, left out", flush=True)
            continue
        texts = {p.number: p for p in layer}
        rows = []
        with pymupdf.open(book.source) as doc:
            for r in rows_of(name, settings):
                s = r["s"]
                versions = [s.ours, *s.others]
                for i in range(len(versions)):
                    for j in range(i + 1, len(versions)):
                        at = marked_letter(versions[i], versions[j])
                        if at is None or r["right"][i] == r["right"][j]:
                            continue
                        a, b = versions[i], versions[j]
                        marked, plain = (a, b) if strip(a[at]) != a[at] else (b, a)
                        if strip(plain[at]) != plain[at]:
                            continue  # two different marks: not this probe's question
                        ink = rendercheck.place_ink(doc[s.page - 1], s.box, texts.get(s.page))
                        if ink is None:
                            continue
                        m = measures(judge._face, judge._match, ink, marked, plain)
                        if m is None:
                            continue
                        label = bool(r["right"][i]) if marked is a else bool(r["right"][j])
                        rows.append({"book": name, "page": s.page, "marked": marked, "plain": plain, "print_marked": label, **m})
        with OUT.open("a") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[name] = rows
        print(f"{name}: {len(rows)} places", flush=True)
    rows = [r for rs in done.values() for r in rs]
    y = np.array([r["print_marked"] for r in rows])
    print(f"{len(rows)} places, {int(y.sum())} marked in print")
    keys = ("cosine", "mass", "stray", "whole")
    for k in keys:
        print(f"  {k:7} AUC {roc_auc_score(y, [r[k] for r in rows]):.3f}")
    X = np.array([[r[k] for k in keys] for r in rows])
    books = np.array([r["book"] for r in rows])
    for cols, label in ((slice(0, 3), "accent zone alone"), (slice(3, 4), "whole word alone"), (slice(0, 4), "both")):
        p = np.zeros(len(rows))
        for b in set(books):
            held = books == b
            if len(set(y[~held])) < 2:
                continue
            p[held] = LogisticRegression(max_iter=1000).fit(X[~held][:, cols], y[~held]).predict_proba(X[held][:, cols])[:, 1]
        print(f"  {label:18} leaving one book out: AUC {roc_auc_score(y, p):.3f}, right at 0.5: {int(((p > 0.5) == y).sum())} of {len(rows)}")


if __name__ == "__main__":
    main()
