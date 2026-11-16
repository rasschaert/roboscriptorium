"""A word's picture against the book's other pictures of the same reading, as a finder of
silent errors without a typeface or a model: "een" stands thousands of times in a book,
and the one the print sets "één" differs from the rest above its letters. Positives: the
tuning bench's one-token silent errors whose built word the layer has on the error's line
and at least `FEWEST` more times in the bench's pages. Negatives: the other instances
gathered for those words, and those of a sample of the book's other frequent words,
leaving out every place the bench names an error. Each picture is cut to its ink, brought
to the word's usual width and set on its foot; its score is how far it lies from the
pixelwise median of the word's pictures, against how far its siblings lie. Rows kept in
work/probes/own-pictures.jsonl. No models.

    uv run python experiments/probe_own_pictures.py <bench errors.jsonl> [words per book]
"""

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy.ndimage import find_objects, label, maximum_filter, uniform_filter
from sklearn.metrics import roc_auc_score

from roboscriptorium import bench
from roboscriptorium import pdf as pdflayer
from roboscriptorium import rendercheck as rc
from roboscriptorium.book import Book
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/own-pictures.jsonl")
SHOW = Path("work/probes/own-pictures-png")
STRAIGHT = str.maketrans("‘’“”", "''\"\"")
FEWEST, MOST = 5, 24
WIDE = 160


def picture(ink: np.ndarray) -> np.ndarray | None:
    """The strip cut to its ink, `WIDE` pixels wide at its own proportions."""
    mask = ink > 0.5
    rows, cols = np.where(mask.any(1))[0], np.where(mask.any(0))[0]
    if len(rows) < 4 or len(cols) < 4:
        return None
    cut = ink[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]
    high = max(4, round(cut.shape[0] * WIDE / cut.shape[1]))
    if high > WIDE * 3:
        return None
    return np.asarray(rc._picture(cut).resize((WIDE, high), Image.BILINEAR), np.float32) / 255


def footed(pic: np.ndarray, high: int) -> np.ndarray:
    """The picture on a canvas `high` tall, its foot at the bottom, its top cut if taller."""
    out = np.zeros((high, WIDE), np.float32)
    h = min(high, pic.shape[0])
    out[high - h :] = pic[pic.shape[0] - h :]
    return out


def raised(canvas: np.ndarray, usual: float) -> list[tuple[float, float, float]]:
    """The loose pieces of ink that end above the middle of the word's usual height (an
    i's dot, an accent, a quote tick): each one's middle across, its height and its area."""
    marked, _ = label(canvas > 0.45)
    line = canvas.shape[0] - usual * 0.5
    out = []
    for k, found in enumerate(find_objects(marked), 1):
        rows, cols = found
        area = float((marked[found] == k).sum())
        if rows.stop <= line and area >= 4:
            out.append(((cols.start + cols.stop) / 2, float(rows.stop - rows.start), area))
    return out


def marks(fit: np.ndarray, middle: np.ndarray, usual: float) -> dict:
    """The picture's loose raised pieces against the median's: the tallest against the
    one at its place ("stretch": an acute where a dot stands), the largest with none at
    its place ("loose": an accent on a letter without a dot), and the median's the
    picture lacks."""
    mine, theirs = raised(fit, usual), raised(middle, usual)
    reach = WIDE * 0.06
    stretch = loose = 0.0
    for x, high, area in mine:
        at = [t for t in theirs if abs(t[0] - x) <= reach]
        if at:
            stretch = max(stretch, high / min(at, key=lambda t: abs(t[0] - x))[1])
        else:
            loose = max(loose, area / usual)
    lacking = sum(1 for t in theirs if not any(abs(t[0] - m[0]) <= reach for m in mine))
    return {"stretch": stretch, "loose": loose, "lacking": float(lacking), "mark": max(stretch - 1, loose * 4)}


def scores(pics: list[np.ndarray]) -> list[dict]:
    """Each picture against the pixelwise median of them all: its distance (1 less the
    best correlation over small shifts), the ink it has where the median and its
    surroundings have none, and its height against the usual."""
    usual = float(np.median([p.shape[0] for p in pics]))
    high = round(usual * 1.6)
    laid = [footed(p, high) for p in pics]
    middle = np.median(laid, axis=0)
    near = maximum_filter(middle, size=7)
    norm = float((middle * middle).sum()) ** 0.5 + 1e-6
    out = []
    for p, one in zip(pics, laid, strict=True):
        best, fit = 0.0, one
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                moved = np.roll(np.roll(one, dy, 0), dx, 1)
                c = float((moved * middle).sum()) / (norm * (float((moved * moved).sum()) ** 0.5 + 1e-6))
                if c > best:
                    best, fit = c, moved
        extra = float(np.clip(one - near, 0, None).sum()) / (float(middle.sum()) + 1e-6)
        # The largest patch that differs from the median either way, anywhere and in the
        # part above the letters' middle, where an accent or a dot stands.
        apart = uniform_filter(np.abs(fit - middle), size=5)
        top = apart[: high - round(usual * 0.55)]
        out.append({"far": 1 - best, "extra": extra, "tall": p.shape[0] / usual, "patch": float(apart.max()), "top": float(top.max()), **marks(fit, middle, usual), "fit": fit, "middle": middle})
    for k in ("far", "extra", "tall", "patch", "top", "mark"):
        values = np.array([o[k] for o in out])
        mid = float(np.median(values))
        mad = float(np.median(np.abs(values - mid))) + 1e-3
        for o in out:
            o[k + "_z"] = (o[k] - mid) / mad
    return out


def main():
    errors = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
    per_book = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    slices = {s.split(":")[0]: s.split(":") for s in bench.SETS["tuning"]}
    done = defaultdict(list)
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            row = json.loads(line)
            done[row["book"]].append(row)
    for name in dict.fromkeys(e["book"] for e in errors):
        if name in done:
            continue
        book = Book.load(Path("work") / name)
        layer = cached_text_layer(book.source, book.stages / "textlayer.json")
        spec = slices.get(name, [name])
        first, last = (int(x) for x in spec[1].split("-")) if len(spec) > 1 and spec[1] else book.body_pages
        texts = {p.number: p for p in layer if first <= p.number <= last}
        named = defaultdict(set)
        for e in errors:
            if e["book"] == name:
                named[e["page"]] |= set(e["got"].split())
        rows = []
        with pymupdf.open(book.source) as doc:
            words = {}
            where = defaultdict(list)
            for number, text in texts.items():
                words[number] = pdflayer.line_words(pdflayer.page_words(doc[number - 1], text), text)
                for k, line in enumerate(words[number]):
                    for i, w in enumerate(line):
                        where[w[4].translate(STRAIGHT)].append((number, k, i))
            wrong = {}
            for e in errors:
                got, want = e["got"].strip(), e["want"].strip()
                if e["book"] != name or e["asked"] or not got or " " in got or " " in want:
                    continue
                if e["page"] not in words or not e["lines"] or e["lines"][0] >= len(words[e["page"]]):
                    continue
                at = [(e["page"], e["lines"][0], i) for i, w in enumerate(words[e["page"]][e["lines"][0]]) if w[4].translate(STRAIGHT) == got]
                if len(at) == 1 and len(where[got]) > FEWEST:
                    wrong[at[0]] = e
            random.seed(0)
            usual = [t for t, places in where.items() if len(places) > FEWEST and len(t) > 1 and t not in {e["got"].strip() for e in wrong.values()}]
            chosen = {e["got"].strip() for e in wrong.values()} | set(random.sample(usual, min(per_book, len(usual))))
            for token in sorted(chosen):
                clean = [p for p in where[token] if p not in wrong and token not in named[p[0]]]
                places = [p for p in where[token] if p in wrong] + random.sample(clean, min(MOST, len(clean)))
                pics, kept = [], []
                for number, k, i in places:
                    ink = rc.place_ink(doc[number - 1], words[number][k][i][:4], texts[number])
                    pic = None if ink is None else picture(ink)
                    if pic is not None:
                        pics.append(pic)
                        kept.append((number, k, i))
                if len(pics) <= FEWEST:
                    continue
                for place, s in zip(kept, scores(pics), strict=True):
                    e = wrong.get(place)
                    fit, middle = s.pop("fit"), s.pop("middle")
                    if e is not None:
                        SHOW.mkdir(parents=True, exist_ok=True)
                        both = np.hstack([fit, middle, np.abs(fit - middle)])
                        rc._picture(both).resize((both.shape[1] * 3, both.shape[0] * 3)).save(SHOW / f"{name[:12]}-{place[0]}-{place[1]}-{token.strip(chr(34) + chr(39) + '.,')}.png")
                    rows.append({"book": name, "page": place[0], "line": place[1], "word": token, "want": e and e["want"], "cause": e and e["cause"], "error": e is not None, "instances": len(where[token]), **s})
        with OUT.open("a") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[name] = rows
        print(f"{name}: {sum(r['error'] for r in rows)} silent errors placed, {sum(not r['error'] for r in rows)} other pictures", flush=True)
    rows = [r for rs in done.values() for r in rs]
    y = np.array([r["error"] for r in rows])
    print(f"{int(y.sum())} silent errors, {int((~y).sum())} other pictures")
    for k in ("patch", "top", "stretch", "loose", "lacking", "mark", "mark_z"):
        x = np.array([r[k] for r in rows])
        line = f"  {k:8} AUC {roc_auc_score(y, x):.3f};"
        for rate in (0.02, 0.01, 0.0025):
            cut = np.quantile(x[~y], 1 - rate)
            line += f" at {rate:.2%} false offers finds {int((x[y] > cut).sum())};"
        print(line)
    for k in ("mark", "stretch"):
        x = np.array([r[k] for r in rows])
        cut = np.quantile(x[~y], 0.99)
        causes = Counter(r["cause"] for r in rows if r["error"])
        found = Counter(r["cause"] for r, v in zip(rows, x, strict=True) if r["error"] and v > cut)
        print(f"  {k}, at 1% false offers, by cause:", {c: f"{found[c]} of {n}" for c, n in causes.most_common()})
        print("   missed:", [(r["word"], r["want"]) for r, v in zip(rows, x, strict=True) if r["error"] and v <= cut][:30])


if __name__ == "__main__":
    main()
