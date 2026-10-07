"""Train a line-role classifier on the golden books, scored leaving one book out.

Each line of each book gets its true role from `golden.align` (body, heading,
other) and features from its geometry, type (`typestyle`), text shape, place in
the book (repetition, sunk pages, printed page numbers) and, optionally, the
role model's answer. Gradient-boosted trees are trained on all books but one and
scored on that one, against the pipeline's own roles (`roles.py`).

    uv run python experiments/train_line_roles.py [--rebuild]
"""

import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from roboscriptorium import disagreements, page as P, pipeline, typestyle
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.flags import treatment
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef

SPECS = [
    "work/goede-dochter--ia-scan:9-64:1-4",
    "work/vals-alarm--ia-scan:11-60:1-10",
    "work/the-nature-of-a-crime--doubleday-1924",
    "work/the-story-of-doctor-dolittle--stokes-1920",
    "work/de-aanslag--calibre-pdf",
    "work/lady-into-fox--chatto-1922",
    "work/villa-toscane--calibre-pdf::1-12",
    "work/grand-hotel-europa--ia-scan:15-44:1-16",
    "work/de-tuin-van-de-avondnevel--ia-scan:11-52:1-3",
    "work/de-eerlijke-vinder--ia-scan",
    "work/reis-om-mijn-schedel--ia-scan",
    "work/monterosso-mon-amour--ia-scan",
]
# Scored like the others, but their errors aren't printed: they stay unseen.
HELD_OUT = {"lady-into-fox", "villa-toscane", "grand-hotel-europa", "de-tuin-van-de-avondnevel"}
ROLES = ["body", "heading", "other"]
PIPELINE = {"text": "body", "heading": "heading", "dropped": "other"}
MODEL_ROLES = ["body", "running_head", "page_number", "chapter_heading", "artifact"]
OUT = Path("work/probes/line-roles")
nan = math.nan


def features(stages, styles) -> list[dict]:
    pages = stages.pages
    repeats = P.Repeats(pages)
    sunk = P.sunk_pages(pages)
    offset = P.page_offset(pages)
    rows = []
    for page in pages:
        if not page.lines:
            continue
        full, left = P.geometry(page)
        pitches = [b.y0 - a.y0 for a, b in zip(page.lines, page.lines[1:], strict=False)]
        pitch = statistics.median(pitches) if pitches else 12.0
        n = len(page.lines)
        for i, ln in enumerate(page.lines):
            ref = SourceRef(page.number, i)
            st = styles.get(ref)
            text = ln.text.strip()
            letters = [c for c in text if c.isalpha()]
            role = stages.model_roles.get(ref)
            f = {
                "i_top": i,
                "i_bottom": n - 1 - i,
                "lines_on_page": n,
                "y": ln.y0 / page.height,
                "width": (ln.x1 - ln.x0) / full,
                "indent": (ln.x0 - left) / full,
                "centre_offset": ((ln.x0 + ln.x1) / 2 - page.width / 2) / page.width,
                "centred": float(P.centred_in_text(page, i, 0.05)),
                "gap_above": (ln.y0 - page.lines[i - 1].y0) / pitch if i else nan,
                "gap_below": (page.lines[i + 1].y0 - ln.y0) / pitch if i + 1 < n else nan,
                "chars": len(text),
                "words": len(text.split()),
                "digits_only": float(bool(re.fullmatch(r"[\d\s.,]+", text))),
                "numeral": float(bool(P.bare_numeral(text))),
                "caps_text": sum(c.isupper() for c in letters) / len(letters) if letters else nan,
                "upper_start": float(bool(re.match(r"^[‘’'\"“]*[A-ZÀ-Þ]", text))),
                "lower_start": float(bool(re.match(r"^[‘’'\"“]*[a-zß-ÿ]", text))),
                "sentence_end": float(bool(re.search(r"[.!?…][’'\"”]*$", text))),
                "hyphen_end": float(text.endswith(("-", "­", "¬"))),
                "garbled": float(P.garbled(ln)),
                "labelled": float(P.labelled(ln, full)),
                "repeats": repeats.other_pages(text, page.number),
                "page_number": float(P.printed_page_number(text, page, offset)),
                "sunk": float(page.number in sunk),
                "set_apart": float(i == 0 and P.set_apart_opening(page)),
                "size": st.size if st and st.size is not None else nan,
                "weight": st.weight if st and st.weight is not None else nan,
                "pitch": st.pitch if st and st.pitch is not None else nan,
                "capitals": float(st.capitals) if st else nan,
                "asked": float(role is not None),
                "p_body": role.p_body if role else nan,
                **{f"model_{r}": float(role is not None and role.role == r) for r in MODEL_ROLES},
                "pipeline": PIPELINE[treatment(role)],
            }
            rows.append({"page": page.number, "line": i, "text": text, "f": f})
    return rows


def dataset(spec: str, rebuild: bool) -> list[dict]:
    book_dir, pages, chapters = (spec.split(":") + ["", ""])[:3]
    path = OUT / f"{Path(book_dir).name}.json"
    if path.exists() and not rebuild:
        return json.loads(path.read_text())
    book = Book.load(Path(book_dir))
    stages = pipeline.run(book, pages=_range(pages or None), check_ocr=False)
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if span := _range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = disagreements.patch(reference, _verdicts(book))
    labels = align(stages.pages, reference)
    styles = typestyle.measure(book.source, stages.pages, book.stages / "type.json")
    rows = features(stages, styles)
    for r in rows:
        r["label"] = labels[SourceRef(r["page"], r["line"])].role
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False))
    return rows


def matrix(rows: list[dict], names: list[str]) -> np.ndarray:
    return np.array([[r["f"][k] for k in names] for r in rows], dtype=float)


def scores(truth: list[str], pred: list[str]) -> str:
    out = []
    for role in ("heading", "other"):
        tp = sum(t == p == role for t, p in zip(truth, pred, strict=True))
        n_pred, n_true = pred.count(role), truth.count(role)
        out.append(f"{role} {tp}/{n_true} found, {n_pred - tp} wrong")
    lost = sum(t == "body" and p != "body" for t, p in zip(truth, pred, strict=True))
    errors = sum(t != p for t, p in zip(truth, pred, strict=True))
    return f"errors {errors:4}  body lost {lost:3}  " + "; ".join(out)


books = {Path(s.split(":")[0]).name: dataset(s, "--rebuild" in sys.argv) for s in SPECS}
for name, rows in books.items():
    print(f"{name[:34]:34} {len(rows):5} lines  {dict(Counter(r['label'] for r in rows))}")
all_names = [k for k in next(iter(books.values()))[0]["f"] if k != "pipeline"]
variants = {
    "trees, no role model": [k for k in all_names if k not in {"asked", "p_body"}
                             and not k.startswith("model_")],
    "trees + role model": all_names,
}
total = Counter()
for name, rows in books.items():
    truth = [r["label"] for r in rows]
    print(f"\n== {name}")
    pipe = [r["f"]["pipeline"] for r in rows]
    print(f"  {'roles.py (now)':22} {scores(truth, pipe)}")
    total["roles.py (now)"] += sum(t != p for t, p in zip(truth, pipe, strict=True))
    train = [r for other, rs in books.items() if other != name for r in rs]
    for label, names in variants.items():
        clf = HistGradientBoostingClassifier(class_weight="balanced", random_state=0)
        clf.fit(matrix(train, names), [r["label"] for r in train])
        pred = list(clf.predict(matrix(rows, names)))
        print(f"  {label:22} {scores(truth, pred)}")
        total[label] += sum(t != p for t, p in zip(truth, pred, strict=True))
        if label == "trees + role model" and name.split("--")[0] not in HELD_OUT:
            wrong = [(r, p) for r, p in zip(rows, pred, strict=True) if p != r["label"]]
            for r, p in wrong[:6]:
                print(f"     p{r['page']} {r['label']}→{p} {r['text'][:50]!r}")
print("\nerrors over all books:", dict(total))
