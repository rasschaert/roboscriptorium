"""Leftover ink as a finder of errors no reader doubts, whatever their kind: the build's
word drawn in the book's typeface and laid over the scan, then what doesn't match
measured: the largest blob of scan ink the drawing doesn't cover (an accent, a quote
tick, a hyphen the readers dropped) and the drawn ink the scan lacks (a letter or mark
the readers added). Positives: the tuning bench's silent errors of one token whose built
word the text layer has on that page. Negatives: a sample of each book's other words.
Prints the AUC and what is found at the false-offer rates a book could bear, by the
error's cause. Rows kept in work/probes/leftover-ink.jsonl. No models.

    uv run python experiments/probe_leftover_ink.py <bench errors.jsonl> [plain words per book]
"""

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pymupdf
from scipy.ndimage import label, maximum_filter
from scipy.signal import fftconvolve
from sklearn.metrics import roc_auc_score

from roboscriptorium import pdf as pdflayer
from roboscriptorium import pipeline
from roboscriptorium import rendercheck as rc
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/leftover-ink-zones.jsonl")
STRAIGHT = str.maketrans("‘’“”", "''\"\"")


def leftover(face, found, ink: np.ndarray, text: str) -> dict | None:
    """`text` drawn at the book's size and laid over the strip where it fits best, with
    room around it; the scan's ink the drawing doesn't cover and the drawing's ink the
    scan lacks, each as its largest blob and its total, in squares of the type's size."""
    drawn = rc._pair(face, text, text)
    if drawn is None:
        return None
    strip = np.asarray(rc._picture(ink).filter(rc._BLUR), np.float32)
    best = None
    for stretch in rc.STRETCHES:
        high = max(4, round(drawn[0].shape[0] * found.size / rc.RENDER_PX))
        wide = max(4, round(drawn[0].shape[1] * found.size / rc.RENDER_PX * stretch))
        mine = np.asarray(rc._spread(rc._picture(drawn[0]).resize((wide, high)), found.spread).filter(rc._BLUR), np.float32)
        room = round(found.size * rc.DPI / 72 * 0.5)
        pad_y, pad_x = max(room, high - strip.shape[0] + room), max(room, wide - strip.shape[1] + room)
        canvas = np.pad(strip, ((pad_y, pad_y), (pad_x, pad_x)))
        over = fftconvolve(canvas, mine[::-1, ::-1], mode="valid")
        y, x = np.unravel_index(int(over.argmax()), over.shape)
        score = float(over.max()) / (float((mine * mine).sum()) ** 0.5 + 1e-6)
        if best is None or score > best[0]:
            best = (score, canvas, mine, y, x)
    _, canvas, mine, y, x = best
    whole = np.zeros_like(canvas)
    whole[y : y + mine.shape[0], x : x + mine.shape[1]] = mine
    unit = (found.size * rc.DPI / 72) ** 2
    near = max(3, round(found.size * rc.DPI / 72 * 0.06))
    extra = (canvas > 110) & (maximum_filter(whole, size=2 * near + 1) < 60)
    lacking = (whole > 110) & (maximum_filter(canvas, size=2 * near + 1) < 60)

    def blob(mask: np.ndarray) -> float:
        marked, n = label(mask)
        return float(np.bincount(marked.ravel())[1:].max()) / unit if n else 0.0

    # Where it lies against the drawing's box: above it, in its thirds, below it; left
    # of it, inside, right of it. An accent is above, a quote tick beside the top, a stop
    # beside the foot.
    high, wide = mine.shape
    rows = [0, y, y + high // 3, y + 2 * high // 3, y + high, canvas.shape[0]]
    cols = [0, x, x + wide, canvas.shape[1]]
    zones = {}
    for name, mask in (("e", extra), ("l", lacking)):
        for r in range(5):
            for c in range(3):
                zones[f"{name}{r}{c}"] = float(mask[rows[r] : rows[r + 1], cols[c] : cols[c + 1]].sum()) / unit
    return {
        "extra": blob(extra),
        "extra_all": float(extra.sum()) / unit,
        "lacking": blob(lacking),
        "lacking_all": float(lacking.sum()) / unit,
        "length": len(text),
        **zones,
    }


def main():
    errors = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
    per_book = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    settings = Settings.from_env()
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
        body = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
        judge = pipeline._alarm("render", settings, book, body)
        if judge is None:
            continue
        texts = {p.number: p for p in layer}
        mine = [e for e in errors if e["book"] == name]
        pages = sorted({e["page"] for e in mine})
        wrong = defaultdict(list)
        for e in mine:
            wrong[e["page"]].append(e)
        rows = []
        with pymupdf.open(book.source) as doc:
            def measure(page: int, word: tuple):
                ink = rc.place_ink(doc[page - 1], word[:4], texts.get(page))
                return None if ink is None else leftover(judge._face, judge._match, ink, word[4])

            for e in mine:
                if e["asked"] or " " in e["got"].strip() or " " in e["want"].strip() or not e["got"].strip():
                    continue
                every = pdflayer.page_words(doc[e["page"] - 1], texts.get(e["page"]))
                same = [w for w in every if w[4].translate(STRAIGHT) == e["got"]]
                if len(same) != 1:
                    continue
                m = measure(e["page"], same[0])
                if m:
                    rows.append({"book": name, "page": e["page"], "word": same[0][4], "want": e["want"], "cause": e["cause"], "error": True, **m})
            random.seed(0)
            pool = [(p, w) for p in pages if p in texts for w in pdflayer.page_words(doc[p - 1], texts[p])]
            for page, w in random.sample(pool, min(len(pool), per_book * 2)):
                plain = w[4].translate(STRAIGHT)
                if any(plain in (e["got"], *e["got"].split()) for e in wrong[page]):
                    continue
                m = measure(page, w)
                if m:
                    rows.append({"book": name, "page": page, "word": w[4], "want": None, "cause": None, "error": False, **m})
                if sum(not r["error"] for r in rows) >= per_book:
                    break
        with OUT.open("a") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done[name] = rows
        print(f"{name}: {sum(r['error'] for r in rows)} silent errors placed, {sum(not r['error'] for r in rows)} other words", flush=True)
    rows = [r for rs in done.values() for r in rs]
    y = np.array([r["error"] for r in rows])
    print(f"{int(y.sum())} silent errors, {int((~y).sum())} other words")
    for k in ("extra", "extra_all", "lacking", "lacking_all"):
        x = np.array([r[k] for r in rows])
        line = f"  {k:11} AUC {roc_auc_score(y, x):.3f};"
        for rate in (0.02, 0.01, 0.0025):
            cut = np.quantile(x[~y], 1 - rate)
            line += f" at {rate:.2%} false offers finds {int((x[y] > cut).sum())};"
        print(line)
    # Trees on where the leftover lies, each book called by trees trained on the others.
    from sklearn.ensemble import HistGradientBoostingClassifier

    keys = ["extra", "extra_all", "lacking", "lacking_all", "length", *sorted(k for k in rows[0] if k[0] in "el" and k[1:].isdigit())]
    X = np.array([[r[k] for k in keys] for r in rows])
    books = np.array([r["book"] for r in rows])
    learned = np.zeros(len(rows))
    for name in sorted(set(books)):
        held = books == name
        model = HistGradientBoostingClassifier(max_depth=3, max_iter=150, min_samples_leaf=10, random_state=0).fit(X[~held], y[~held])
        learned[held] = model.predict_proba(X[held])[:, 1]
    line = f"  trees on zones AUC {roc_auc_score(y, learned):.3f};"
    for rate in (0.02, 0.01, 0.0025):
        cut = np.quantile(learned[~y], 1 - rate)
        line += f" at {rate:.2%} false offers finds {int((learned[y] > cut).sum())};"
    print(line)
    cut = np.quantile(learned[~y], 0.99)
    print("  trees, at 1% false offers, by cause:", {c: f"{sum(1 for r, s in zip(rows, learned, strict=True) if r['error'] and r['cause'] == c and s > cut)} of {n}" for c, n in Counter(r["cause"] for r in rows if r["error"]).most_common()})
    both = np.maximum(np.array([r["extra"] for r in rows]), np.array([r["lacking"] for r in rows]))
    cut = np.quantile(both[~y], 0.99)
    causes, found = Counter(r["cause"] for r in rows if r["error"]), Counter(r["cause"] for r, b in zip(rows, both, strict=True) if r["error"] and b > cut)
    print("  either blob, at 1% false offers, by cause:", {c: f"{found[c]} of {n}" for c, n in causes.most_common()})


if __name__ == "__main__":
    main()
