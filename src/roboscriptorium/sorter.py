"""Line roles from trees over each line's layout, type, text and the role model's answer.

The rules in `roles.py` were written book by book and don't carry over (Villa Toscane's
headings 0/12); trees trained on the golden books' aligned lines (`golden.align`: body,
heading or other) learn the same from labels. They see what the rules see (place on
the page, width, indent, gaps, repetition across pages, printed page numbers, sunk
openings), the line's type (`typestyle`), the spotter's regions (`layout`), and the
role model's answer where it was asked. Their roles replace the rules' for every line.

Trained by `experiments/train_sorter.py --save` on the tuning and other golden books,
never the validation or test books, with a copy without each tuning book that `bench`
scores that book with.
"""

import hashlib
import math
import pickle
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from roboscriptorium import page as P
from roboscriptorium.files import write_atomic
from roboscriptorium.ir import SourceRef
from roboscriptorium.layout import Region
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import HEADING_MAX_REPEATS, KEEP_BODY_AT, LineRole
from roboscriptorium.typestyle import Style

MODEL_VERSION = 1
# A line the trees would drop is kept as text, and flagged, while they give it at least this
# P(body): over the labelled books, 0.5 lost 57 body lines and 0.25 lost 33 for 26 more
# stray lines kept, and a lost line costs about ten words, a stray folio one or two.
KEEP_BODY = 0.25
# A line of at least this many characters at a page's edge, its text repeated at the
# edge of this many other pages, is page furniture: of 346 such labelled lines, none was
# body (337 furniture, 9 headings).
FURNITURE_CHARS = 6
CLASSES = ("body", "heading", "other")
MODEL_ROLES = ("body", "running_head", "page_number", "chapter_heading", "artifact")
LAYOUT_CLASSES = ("title", "plain text", "abandon", "figure", "figure_caption", "table")
nan = math.nan


def _layout(line, regions: list[Region]) -> dict[str, float]:
    """Per layout class, the confidence of the surest region of it holding the line's centre."""
    cx, cy = (line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2
    out = {f"layout_{c}": 0.0 for c in LAYOUT_CLASSES}
    for r in regions:
        key = f"layout_{r.label}"
        if key in out and r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1:
            out[key] = max(out[key], r.confidence)
    return out


def features(
    pages: list[PageText],
    model_roles: dict[SourceRef, LineRole],
    styles: dict[SourceRef, Style],
    regions: dict[int, list[Region]] | None = None,
) -> dict[SourceRef, dict[str, float]]:
    """Each line's features. `model_roles` are the role model's own answers with the rules
    of `roles.classify` (lines it wasn't asked about have none)."""
    repeats = P.Repeats(pages)
    sunk = P.sunk_pages(pages)
    offset = P.page_offset(pages)
    out = {}
    for page in pages:
        if not page.lines:
            continue
        full, left = P.geometry(page)
        pitches = [b.y0 - a.y0 for a, b in zip(page.lines, page.lines[1:], strict=False)]
        pitch = statistics.median(pitches) if pitches else 12.0
        n = len(page.lines)
        here = [r for r in (regions or {}).get(page.number, []) if not r.turned]
        figures = sum(
            (r.x1 - r.x0) * (r.y1 - r.y0)
            for r in here
            if r.label == "figure" and r.confidence >= 0.5
        )
        for i, ln in enumerate(page.lines):
            ref = SourceRef(page.number, i)
            st = styles.get(ref)
            text = ln.text.strip()
            letters = [c for c in text if c.isalpha()]
            role = model_roles.get(ref)
            out[ref] = {
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
                **_layout(ln, here),
                "page_figure_share": figures / (page.width * page.height),
            }
    return out


# The features in the order the trees see them.
FEATURES = tuple(
    features([PageText(1, 10, 10, [Line("x", 0, 0, 1, 1), Line("y", 0, 2, 1, 3)])], {}, {})[
        SourceRef(1, 0)
    ]
)


@dataclass
class Sorter:
    model: object


class Mismatch(RuntimeError):
    """The saved model was trained on other features than these."""


def train(rows: list[dict[str, float]], labels: list[str]) -> Sorter:
    """Trees over labelled lines' features (`features`), labels from `CLASSES`."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    model = HistGradientBoostingClassifier(
        class_weight="balanced",
        max_depth=4,
        min_samples_leaf=20,
        l2_regularization=1.0,
        random_state=0,
    )
    return Sorter(model.fit(_matrix(rows), labels))


def _matrix(rows: list[dict[str, float]]) -> np.ndarray:
    return np.array([[r[k] for k in FEATURES] for r in rows], dtype=float)


def save(sorter: Sorter, path: Path) -> None:
    blob = {"version": MODEL_VERSION, "features": FEATURES, "model": sorter.model}
    write_atomic(path, pickle.dumps(blob))


def load(path: Path) -> Sorter:
    """The saved model; a missing one, or one trained on other features, stops the build."""
    if not path.exists():
        raise Mismatch(
            f"No line-role model at {path}: train one (experiments/train_sorter.py --save) "
            "or set ROBO_SORTER=0 for the rules."
        )
    blob = pickle.loads(path.read_bytes())
    if blob.get("version") != MODEL_VERSION or tuple(blob.get("features", ())) != FEATURES:
        raise Mismatch(
            f"The line-role model {path} was trained on other features: retrain it "
            "(experiments/train_sorter.py --save) or set ROBO_SORTER=0 for the rules."
        )
    return Sorter(blob["model"])


def without(path: Path, book: str) -> Path:
    """Where the model trained without `book` is kept, beside `path`."""
    return path.with_name(f"{path.stem}-without-{book}{path.suffix}")


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def apply(
    sorter: Sorter,
    pages: list[PageText],
    model_roles: dict[SourceRef, LineRole],
    styles: dict[SourceRef, Style],
    regions: dict[int, list[Region]] | None = None,
) -> dict[SourceRef, LineRole]:
    """The trees' roles: every line they don't call body, and every line the role model
    answered for, with P(body) from the trees. A line called other keeps the role
    model's name for it where it had a non-body one ("page_number"), else "artifact"."""
    found = features(pages, model_roles, styles, regions)
    refs = list(found)
    if not refs:
        return {}
    probs = sorter.model.predict_proba(_matrix([found[r] for r in refs]))
    classes = list(sorter.model.classes_)
    out = {}
    for ref, p in zip(refs, probs, strict=True):
        best = classes[int(p.argmax())]
        p_body = float(p[classes.index("body")])
        f = found[ref]
        repeated = f["repeats"] >= HEADING_MAX_REPEATS
        edge = f["i_top"] < P.EDGE_LINES_TOP or f["i_bottom"] < P.EDGE_LINES_BOTTOM
        if repeated and (best == "heading" or edge and f["chars"] >= FURNITURE_CHARS):
            # A heading appears once, and text repeated at the pages' edges is furniture.
            out[ref] = LineRole("running_head", float(p.max()), 0.0, "repeated")
            continue
        if best == "other" and p_body >= KEEP_BODY:
            # Kept as text, under its other role so the review asks about it.
            out[ref] = LineRole("artifact", float(p.max()), KEEP_BODY_AT, "trees-kept")
            continue
        old = model_roles.get(ref)
        if best == "body" and old is None:
            continue
        if best == "body":
            role = "body"
        elif best == "heading":
            role = "chapter_heading"
        else:
            role = old.role if old and old.role not in ("body", "chapter_heading") else "artifact"
        out[ref] = LineRole(role, float(p.max()), p_body, "trees")
    return out
