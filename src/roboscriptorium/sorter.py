"""Line roles from trees over each line's layout, type, text and the role model's answer.

The rules in `roles.py` were written book by book and don't carry over (Villa Toscane's
headings 0/12); trees trained on the golden books' aligned lines (`golden.align`: body,
heading or other) learn the same from labels. They see what the rules see (place on
the page, width, indent, gaps, repetition across pages, printed page numbers, sunk
openings), the line's type (`typestyle`), the spotter's regions (`layout`), and the
role model's answer where it was asked. Their roles replace the rules' for every line.

Trained by `experiments/train_sorter.py --save` on the tuning and other golden books,
never the validation or first-look books, with a copy without each tuning book that `bench`
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
import pymupdf

from roboscriptorium import page as P
from roboscriptorium.clients.decide import choice
from roboscriptorium.files import write_atomic
from roboscriptorium.ir import SourceRef
from roboscriptorium.layout import Region
from roboscriptorium.pdf import PDF_LOCK, Line, PageText
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
# A line the role model wasn't asked about, away from the page's edges and inside a text
# block the layout model is this sure of, stays body whatever the trees say: page furniture
# sits at the edges. Over the labelled tuning books, body lines lost 72 → 57, errors
# 139 → 126; no book lost more than one line (`experiments/train_sorter.py`).
RUNNING_TEXT = 0.5
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
    page_roles: dict[int, dict[int, str]] | None = None,
) -> dict[SourceRef, dict[str, float]]:
    """Each line's features. `model_roles` are the role model's own answers with the rules
    of `roles.classify` (lines it wasn't asked about have none). With `page_roles` (the read
    model's heading and furniture lines per page it answered for, `pageroles.py`) the
    features also hold `PAGE_FEATURES`."""
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
                "number_lookalike": float(P.number_lookalike(text)),
                "caps_text": sum(c.isupper() for c in letters) / len(letters) if letters else nan,
                "upper_start": float(bool(re.match(r"^[‘’'\"“]*[A-ZÀ-Þ]", text))),
                "lower_start": float(bool(re.match(r"^[‘’'\"“]*[a-zß-ÿ]", text))),
                "sentence_end": float(bool(re.search(r"[.!?…][’'\"”]*$", text))),
                "hyphen_end": float(text.endswith(("-", "­", "¬"))),
                "garbled": float(P.garbled(ln)),
                "labelled": float(P.labelled(ln, full)),
                "repeats": repeats.other_pages(text, page.number, ln.y0 / page.height),
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
            if page_roles is not None:
                said = page_roles.get(page.number)
                kind = said.get(i, "body") if said is not None else None
                out[ref] |= {
                    "page_asked": float(said is not None),
                    "page_heading": float(kind == "heading") if said is not None else nan,
                    "page_other": float(kind == "other") if said is not None else nan,
                }
    return out


# The features in the order the trees see them.
FEATURES = tuple(
    features([PageText(1, 10, 10, [Line("x", 0, 0, 1, 1), Line("y", 0, 2, 1, 3)])], {}, {})[
        SourceRef(1, 0)
    ]
)

PAGE_FEATURES = ("page_asked", "page_heading", "page_other")


@dataclass
class Sorter:
    model: object
    # The features it was trained on: `FEATURES`, and `PAGE_FEATURES` after them when it
    # was trained with the read model's page roles.
    features: tuple = FEATURES

    @property
    def page_roles(self) -> bool:
        return self.features[len(FEATURES) :] == PAGE_FEATURES


class Mismatch(RuntimeError):
    """The saved model was trained on other features than these."""


def train(rows: list[dict[str, float]], labels: list[str], body_weight: float = 1.0) -> Sorter:
    """Trees over labelled lines' features (`features`), labels from `CLASSES`. Classes
    weigh alike whatever their size; a body line weighs `body_weight` times that, since
    a body line dropped loses text silently where a speck kept is asked about."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    model = HistGradientBoostingClassifier(
        max_depth=4,
        min_samples_leaf=20,
        l2_regularization=1.0,
        random_state=0,
    )
    counts = {c: labels.count(c) for c in set(labels)}
    weight = {c: len(labels) / (len(counts) * n) for c, n in counts.items()}
    weight["body"] = weight.get("body", 1.0) * body_weight
    names = FEATURES + PAGE_FEATURES if PAGE_FEATURES[0] in rows[0] else FEATURES
    fitted = model.fit(_matrix(rows, names), labels, sample_weight=[weight[c] for c in labels])
    return Sorter(fitted, names)


def _matrix(rows: list[dict[str, float]], names: tuple = FEATURES) -> np.ndarray:
    return np.array([[r[k] for k in names] for r in rows], dtype=float)


def save(sorter: Sorter, path: Path) -> None:
    blob = {"version": MODEL_VERSION, "features": sorter.features, "model": sorter.model}
    write_atomic(path, pickle.dumps(blob))


def load(path: Path, page_roles: bool = False) -> Sorter:
    """The saved model; a missing one, or one trained on other features (with the page
    roles where `page_roles` says without, or the other way round), stops the build."""
    if not path.exists():
        raise Mismatch(
            f"No line-role model at {path}: train one (experiments/train_sorter.py --save) "
            "or set ROBO_SORTER=0 for the rules."
        )
    blob = pickle.loads(path.read_bytes())
    want = FEATURES + PAGE_FEATURES if page_roles else FEATURES
    if blob.get("version") != MODEL_VERSION or tuple(blob.get("features", ())) != want:
        raise Mismatch(
            f"The line-role model {path} was trained on other features"
            f" ({'with' if page_roles else 'without'} the page roles wanted, ROBO_PAGE_ROLES):"
            " retrain it (experiments/train_sorter.py --save) or set ROBO_SORTER=0 for the rules."
        )
    return Sorter(blob["model"], want)


def without(path: Path, book: str) -> Path:
    """Where the model trained without `book` is kept, beside `path`."""
    return path.with_name(f"{path.stem}-without-{book}{path.suffix}")


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _inner_repeats(found: dict[SourceRef, dict[str, float]]) -> set[SourceRef]:
    """Lines repeated at a page's edge with another repeated line further out at the same
    edge: a page sets one running head there, so these are text that recurs (Artemis'
    "Dear Kelvin," under its running head "88 ANDY WEIR", in four letters)."""
    furniture: dict[tuple[int, str], list[SourceRef]] = {}
    for ref, f in found.items():
        if f["repeats"] < HEADING_MAX_REPEATS or f["chars"] < FURNITURE_CHARS:
            continue
        if f["i_top"] < P.EDGE_LINES_TOP:
            furniture.setdefault((ref.page, "top"), []).append(ref)
        if f["i_bottom"] < P.EDGE_LINES_BOTTOM:
            furniture.setdefault((ref.page, "bottom"), []).append(ref)
    inner = set()
    for (_, edge), refs in furniture.items():
        refs = sorted(refs, key=lambda r: r.line, reverse=edge == "bottom")
        inner |= set(refs[1:])
    return inner


# The referee's question about a line the two sets of trees call differently, shown its
# whole page with the line framed: on a band of the page it took headings and page
# numbers for running text (38 of 92 right, on the page 54 of 70 readable ones).
REFEREE_QUESTION = (
    "The image is a scanned printed book's page. What is the line framed in red: part of "
    "the book's running text, a heading (a chapter or part title, a chapter number), or "
    "not part of the text (a page number, a running head repeated atop pages, a speck, a "
    "caption)?"
)
REFEREE_OPTIONS = {
    "body": "running text",
    "heading": "a heading",
    "other": "not part of the text: a page number, running head, speck or caption",
}
# The page's longer side in the referee's image, in pixels.
REFEREE_PX = 1400


class Referee:
    """A vision judge between two sets of trees: asked what a line is, shown its page
    with the line framed; its answers kept in `cache` (a `roles.DecisionCache`)."""

    def __init__(self, pdf: Path, pages: list[PageText], client, model: str, cache):
        self._pdf, self._client, self._model, self._cache = pdf, client, model, cache
        self._pages = {p.number: p for p in pages}

    def __call__(self, ref: SourceRef) -> str:
        """ "body", "heading" or "other" for the line at `ref`."""
        line = self._pages[ref.page].lines[ref.line]
        state = {"page": ref.page, "line": ref.line, "text": line.text, "view": "page"}
        question = {"role": choice(REFEREE_QUESTION, REFEREE_OPTIONS)}
        key = self._cache.key(self._model, question, state)
        answer = self._cache.get(key)
        if answer is None:
            with PDF_LOCK, pymupdf.open(self._pdf) as doc:
                page = doc[ref.page - 1]
                frame = pymupdf.Rect(line.x0 - 2, line.y0 - 1, line.x1 + 2, line.y1 + 1)
                page.draw_rect(frame, color=(1, 0, 0), width=1)
                zoom = REFEREE_PX / max(page.rect.width, page.rect.height)
                png = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
            got = self._client.decide(state, question, image_png=png)["role"]
            answer = {"value": got.value, "confidence": got.confidence}
            self._cache.put(key, answer)
        return answer["value"]


def _calls(probs: np.ndarray, classes: list[str]) -> list[str]:
    """What each row of probabilities makes of its line as `apply` keeps lines: its
    likeliest class, a line called other kept as body from `KEEP_BODY`."""
    body = classes.index("body")
    out = []
    for p in probs:
        best = classes[int(p.argmax())]
        out.append("body" if best == "other" and p[body] >= KEEP_BODY else best)
    return out


def apply(
    sorter: Sorter,
    pages: list[PageText],
    model_roles: dict[SourceRef, LineRole],
    styles: dict[SourceRef, Style],
    regions: dict[int, list[Region]] | None = None,
    page_roles: dict[int, dict[int, str]] | None = None,
    second: Sorter | None = None,
    referee=None,
) -> dict[SourceRef, LineRole]:
    """The trees' roles: every line they don't call body, and every line the role model
    answered for, with P(body) from the trees. A line called other keeps the role
    model's name for it where it had a non-body one ("page_number"), else "artifact".
    With a `second` set of trees and a `referee` (`Referee`), a line the two sets call
    differently goes by the second set where the referee says what that set does."""
    said = (page_roles or {}) if sorter.page_roles else None
    found = features(pages, model_roles, styles, regions, said)
    refs = list(found)
    if not refs:
        return {}
    probs = sorter.model.predict_proba(_matrix([found[r] for r in refs], sorter.features))
    classes = list(sorter.model.classes_)
    if second is not None and referee is not None:
        others = second.model.predict_proba(_matrix([found[r] for r in refs], second.features))
        # In the first set's order of classes.
        order = [list(second.model.classes_).index(c) for c in classes]
        others = others[:, order]
        ours, theirs = _calls(probs, classes), _calls(others, classes)
        for i, (a, b) in enumerate(zip(ours, theirs, strict=True)):
            if a != b and referee(refs[i]) == b:
                probs[i] = others[i]
    # A page's first line set well below where running heads stand is none.
    sunk_first = P.sunk_first_lines(pages)
    inner = _inner_repeats(found)
    offset = P.page_offset(pages)
    by_number = {p.number: p for p in pages}
    out = {}
    for ref, p in zip(refs, probs, strict=True):
        best = classes[int(p.argmax())]
        p_body = float(p[classes.index("body")])
        f = found[ref]
        edge = f["i_top"] < P.EDGE_LINES_TOP or f["i_bottom"] < P.EDGE_LINES_BOTTOM
        # A heading never prints its page's number: with it, one other page is enough.
        times = (
            1
            if edge and P.carries_folio(by_number[ref.page], ref.line, offset)
            else HEADING_MAX_REPEATS
        )
        repeated = (
            f["repeats"] >= times
            and not (ref.line == 0 and ref.page in sunk_first)
            and ref not in inner
        )
        if repeated and (best == "heading" or edge and f["chars"] >= FURNITURE_CHARS):
            # A heading appears once, and text repeated at the pages' edges is furniture.
            out[ref] = LineRole("running_head", float(p.max()), 0.0, "repeated")
            continue
        running = not edge and f["layout_plain text"] >= RUNNING_TEXT
        if best == "other" and ref not in model_roles and running:
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
