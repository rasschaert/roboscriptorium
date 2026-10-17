"""Which errors a bench run left, one row each, and what changed between two runs.

`bench` writes a run's rows beside its record (`<run>.errors.jsonl` under work/bench/,
as they quote the books). A row is one place where the build differs from the reference
(`disagreements.Disagreement`): its book, page and lines, kind (`quality.category`),
size in words, the two sides with a little context, whether an asked question catches
it, and two hints at its origin. `layer`: whether the text layer already read it so
("kept", the build left the layer's error), read it right ("made", a later stage
changed it), or neither shows ("unclear"; "lost" for words the build dropped). And the
OCR check's decision on its lines, if any suspect sat there.

A row's identity across runs is its book and its `key`, the reference words with their
context (as verdicts are keyed), so a place keeps its identity when pages are rebuilt
and lines renumbered. `diff` sorts two runs' rows into fixed, made and persisting.
"""

import json
import re
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
    for title, group in (("by kind", "kind"), ("by book", "book"), ("by origin", "layer")):
        fixed, made = Counter(), Counter()
        for r in d.fixed:
            fixed[r[group]] += r["size"]
        for r in d.made:
            made[r[group]] += r["size"]
        out.append(f"\n{title}: fixed / made")
        for k in sorted(fixed.keys() | made.keys(), key=lambda k: -(fixed[k] + made[k])):
            out.append(f"  {k[:40]:40} {fixed[k]:5} / {made[k]:<5}")
    for title, rs in (("fixed", d.fixed), ("made", d.made)):
        shown = defaultdict(list)
        for r in rs:
            shown[r["kind"]].append(r)
        out.append(f"\n{title}, examples:")
        for kind, group in sorted(shown.items(), key=lambda kv: -len(kv[1])):
            for r in group[:examples]:
                out.append(
                    f"  {kind:12} {r['book'][:24]:24} p{r['page']}: "
                    f"{r['before']} [{r['got']} → {r['want']}] {r['after']}"
                )
    return out
