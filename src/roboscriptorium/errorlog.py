"""Which errors a bench run left, one row each, and what changed between two runs.

`bench` writes a run's rows beside its record (`<run>.errors.jsonl` under work/bench/,
as they quote the books). A row is one place where the build differs from the reference
(`disagreements.Disagreement`): its book, page and lines, kind (`quality.category`),
size in words, the two sides with a little context, whether an asked question catches
it, and two hints at its origin. `layer`: whether the text layer already read it so
("kept", the build left the layer's error), read it right ("made", a later stage
changed it), or neither shows ("unclear"; "lost" for words the build dropped). And the
OCR check's decision on its lines, if any suspect sat there.

Each row has a `cause`, read from its two sides by `cause` alone, so every run is
measured with the same ruler and a cause's trend over runs means the build changed.

A row's identity across runs is its book and its `key`, the reference words with their
context (as verdicts are keyed), so a place keeps its identity when pages are rebuilt
and lines renumbered. `diff` sorts two runs' rows into fixed, made and persisting.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from roboscriptorium import quality
from roboscriptorium.disagreements import Disagreement
from roboscriptorium.files import read_jsonl, write_atomic
from roboscriptorium.flags import Flag
from roboscriptorium.ocrcheck import Suspect
from roboscriptorium.pdf import PageText
from roboscriptorium.trust import fold

QUOTES = "'\"‘’“”„‚«»"
DASHES = "-‐‑‒–—―−"
# The causes `cause` tells apart, in the order they are tried.
CAUSES = (
    "missing text", "extra text", "case", "stress accent", "diaeresis", "other accent",
    "dash or dot spacing", "glued or split words", "compound hyphen",
    "quote missing or extra", "quote glyph", "dash", "dots and stops",
    "punctuation swapped", "letters misread", "words",
)  # fmt: skip


def _without_marks(text: str) -> str:
    kept = (c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", "".join(kept))


def _marks(text: str) -> set[str]:
    return {c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) == "Mn"}


def cause(got: str, want: str) -> str:
    """Why the build's words differ from the reference's, from the two sides alone: the
    first of `CAUSES` that explains the whole difference ("zijn" for "zíjn" is a stress
    accent, "meteen" for "met een" glued words, "rood;" for "rood,’" punctuation)."""
    if not got.strip():
        return "missing text"
    if not want.strip():
        return "extra text"
    if got.lower() == want.lower():
        return "case"
    if _without_marks(got) == _without_marks(want):
        marks = _marks(got) ^ _marks(want) or _marks(got) | _marks(want)
        if marks <= {"\u0301", "\u0300"}:
            return "stress accent"
        return "diaeresis" if marks <= {"\u0308"} else "other accent"

    def spaceless(t: str) -> str:
        return re.sub(r"\s+", "", t)

    def tight(t: str) -> str:
        return re.sub(rf"\s*([{DASHES}…]|\.(?:\s*\.)+)\s*", r"\1", t)

    if spaceless(got) == spaceless(want):
        return "dash or dot spacing" if tight(got) == tight(want) else "glued or split words"
    if spaceless(got.replace("-", "")) == spaceless(want.replace("-", "")):
        return "compound hyphen"
    unquoted = str.maketrans("", "", QUOTES)
    if got.translate(unquoted) == want.translate(unquoted):
        count = lambda t: sum(c in QUOTES for c in t)  # noqa: E731
        return "quote missing or extra" if count(got) != count(want) else "quote glyph"
    if re.sub(r"[\W_]+", "", got) == re.sub(r"[\W_]+", "", want):
        undashed = str.maketrans("", "", QUOTES + DASHES)
        if got.translate(undashed) == want.translate(undashed):
            return "dash"
        if re.sub(r"[.…\s]", "", got) == re.sub(r"[.…\s]", "", want):
            return "dots and stops"
        return "punctuation swapped"
    return "letters misread" if len(got.split()) == len(want.split()) else "words"


def cause_of(row: dict) -> str:
    """A row's cause, read again for rows saved before causes were kept."""
    return row.get("cause") or cause(row["got"], row["want"])


def _plain(text: str) -> str:
    """Text as the score compares it (`trust.fold`), without spaces: a place's words are
    found in the layer's lines however they were split."""
    return re.sub(r"\s+", "", fold(text))


def layer_origin(e: Disagreement, pages: dict[int, PageText]) -> str:
    """Whether the text layer's own lines at the place hold the build's words or the
    reference's: "kept", "made", "unclear", or "lost" for dropped words."""
    if not e.got.strip():
        return "lost"
    page = pages.get(e.page) if e.page is not None else None
    if page is None or e.lines is None:
        return "unclear"
    first, last = e.lines
    layer = _plain(" ".join(ln.text for ln in page.lines[first : last + 1]))
    got, want = _plain(e.got), _plain(e.want)
    if want and want in layer and got not in layer:
        return "made"
    if got and got in layer and (not want or want not in layer):
        return "kept"
    return "unclear"


def rows(
    book: str,
    errors: list[Disagreement],
    asked: list[Flag],
    pages: list[PageText],
    suspects: list[Suspect],
) -> list[dict]:
    """One row per error of a book's run (see the module's docstring)."""
    by_page = {p.number: p for p in pages}
    decided = {(s.page, s.line): s.choice for s in suspects}
    out = []
    for e in errors:
        lines = range(e.lines[0], e.lines[1] + 1) if e.lines else range(0)
        out.append(
            {
                "book": book,
                "key": e.key,
                "page": e.page,
                "lines": list(e.lines) if e.lines else None,
                "kind": quality.category(e),
                "cause": cause(e.got, e.want),
                "size": quality.size(e),
                "got": e.got,
                "want": e.want,
                "before": " ".join(e.before.split()[-4:]),
                "after": " ".join(e.after.split()[:4]),
                "asked": any(quality.catches(f, e) for f in asked),
                "auto": e.auto,
                "layer": layer_origin(e, by_page),
                "check": next(
                    (decided[(e.page, n)] for n in lines if (e.page, n) in decided), None
                ),
            }
        )
    return out


def path_for(record_path: Path) -> Path:
    return record_path.with_suffix(".errors.jsonl")


def save(record_path: Path, all_rows: list[dict]) -> Path:
    path = path_for(record_path)
    write_atomic(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in all_rows))
    return path


def load(record_path: Path) -> list[dict]:
    path = path_for(record_path)
    return read_jsonl(path) if path.exists() else []


@dataclass
class Diff:
    fixed: list[dict]  # in the old run only
    made: list[dict]  # in the new run only
    kept: list[tuple[dict, dict]]  # in both: (old, new)


def diff(old: list[dict], new: list[dict], books: set[str] | None = None) -> Diff:
    """The errors fixed, made and kept from `old` to `new`, over the books both runs
    scored (or `books`). A place whose build words changed but stayed wrong is kept."""
    shared = {r["book"] for r in old} & {r["book"] for r in new}
    shared = shared if books is None else shared & books

    def index(rs: list[dict]) -> dict[tuple, dict]:
        return {(r["book"], r["key"]): r for r in rs if r["book"] in shared}

    a, b = index(old), index(new)
    return Diff(
        [a[k] for k in a.keys() - b.keys()],
        [b[k] for k in b.keys() - a.keys()],
        [(a[k], b[k]) for k in a.keys() & b.keys()],
    )


def words(rs: list[dict], unasked: bool = False) -> int:
    return sum(r["size"] for r in rs if not (unasked and r["asked"]))


def report(d: Diff, examples: int = 3) -> list[str]:
    """Fixed, made and kept, in wrong words (and those no question asks), by kind and
    by book, with a few examples of each."""
    kept = [new for _, new in d.kept]
    out = [
        f"fixed {words(d.fixed)} wrong words ({words(d.fixed, True)} unasked), "
        f"made {words(d.made)} ({words(d.made, True)} unasked), "
        f"kept {words(kept)} ({words(kept, True)} unasked)"
    ]
    for title, group in (("by cause", "cause"), ("by book", "book"), ("by origin", "layer")):
        fixed, made = Counter(), Counter()
        for r in d.fixed:
            fixed[cause_of(r) if group == "cause" else r[group]] += r["size"]
        for r in d.made:
            made[cause_of(r) if group == "cause" else r[group]] += r["size"]
        out.append(f"\n{title}: fixed / made")
        for k in sorted(fixed.keys() | made.keys(), key=lambda k: -(fixed[k] + made[k])):
            out.append(f"  {k[:40]:40} {fixed[k]:5} / {made[k]:<5}")
    for title, rs in (("fixed", d.fixed), ("made", d.made)):
        shown = defaultdict(list)
        for r in rs:
            shown[cause_of(r)].append(r)
        out.append(f"\n{title}, examples:")
        for kind, group in sorted(shown.items(), key=lambda kv: -len(kv[1])):
            for r in group[:examples]:
                out.append(
                    f"  {kind[:22]:22} {r['book'][:24]:24} p{r['page']}: "
                    f"{r['before']} [{r['got']} → {r['want']}] {r['after']}"
                )
    return out
