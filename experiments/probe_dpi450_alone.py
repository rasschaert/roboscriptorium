"""Where would the read model at 450 dpi add a witness no reader gives today? On the quick
bench slices, whose every kept line was read at 450 dpi as well as 300 (the cold
`ROBO_READER_DPI=450` bench of 2026-10-22, kept in the caches' shelves), each body line's
readings are compared with the aligned reference. No models.

A line is *quiet* where the text layer, glm-ocr and the read model at 300 dpi agree (folded
as the trust data folds): the OCR check raises no suspect there today. On quiet lines the
450 dpi reading alone can differ: right (an error nobody flags today), wrong (a new
suspect the arbiter must reject) or both wrong. On the other lines it says which side it
takes.

    uv run python experiments/probe_dpi450_alone.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from tryout import _beside_break, _shifted, fold, slice_of  # noqa: E402

from roboscriptorium import bench, disagreements, readers  # noqa: E402
from roboscriptorium.golden import scoring  # noqa: E402
from roboscriptorium.golden.align import align  # noqa: E402
from roboscriptorium.golden.manifest import Golden  # noqa: E402
from roboscriptorium.golden.reference import load_chapters  # noqa: E402
from roboscriptorium.pdf import cached_text_layer  # noqa: E402

OUT = Path("work/probes/dpi450-alone.json")


def caches(stages: Path, stem: str) -> dict[str, dict]:
    """The readings of `stem` (main file and shelves) by resolution: '300' or '450'."""
    out = {}
    for path in stages.glob(f"{stem}*.json"):
        raw = readers._current(json.loads(path.read_text()))
        if raw:
            out["450" if raw.get("prompt", "").endswith("[450 dpi]") else "300"] = raw["lines"]
    return out


totals: Counter = Counter()
examples: list[dict] = []
for spec in bench.SETS["quick"]:
    book, (first, last), chapters = slice_of(spec)
    glm, qwen = caches(book.stages, "second-reading"), caches(book.stages, "third-reading")
    if "450" not in qwen or "300" not in qwen or "300" not in glm:
        print(f"{book.root.name}: no 450 dpi readings, skipped")
        continue
    pages = [
        p
        for p in cached_text_layer(book.source, book.stages / "textlayer.json")
        if first <= p.number <= last
    ]
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if chapters:
        reference = reference[chapters[0] - 1 : chapters[1]]
    reference, _ = disagreements.patch(reference, scoring.verdicts(book))
    labels = align(pages, reference)
    by_number = {p.number: p for p in pages}
    count: Counter = Counter()
    with pymupdf.open(book.source) as doc:
        boxes = {n: readers.line_boxes(doc[n - 1], p) for n, p in by_number.items()}
    for ref, lab in labels.items():
        page = by_number[ref.page]
        layer = page.lines[ref.line].text
        if lab.role != "body" or not lab.truth or not layer.strip():
            continue
        if _beside_break(page.lines, ref.line) or _shifted(layer, lab.truth):
            continue
        key = readers.line_key(page, boxes[ref.page], ref.line)
        got = [glm["300"].get(key), qwen["300"].get(key), qwen["450"].get(key)]
        if None in got:
            continue
        L, G, Q, H, T = (fold(x) for x in (layer, *got, lab.truth))
        quiet = L == G == Q
        if quiet and H == L:
            kind = "quiet, same"
        elif quiet:
            kind = "quiet, 450 right" if H == T else (
                "quiet, 450 wrong" if L == T else "quiet, both wrong")
        else:
            kind = "flagged, 450 right" if H == T else (
                "flagged, 450 wrong, other right" if T in (L, G, Q) else "flagged, all wrong")
        count[kind] += 1
        if not quiet and (H == T) != (Q == T):
            count["flagged, 450 right, 300 wrong" if H == T else "flagged, 300 right, 450 wrong"] += 1
        if kind.startswith("quiet, 450") or kind == "quiet, both wrong":
            examples.append({"book": book.root.name, "page": ref.page, "kind": kind,
                             "layer": layer, "dpi450": got[2], "truth": lab.truth})
    print(book.root.name, dict(count), flush=True)
    totals += count

print("\nall:", dict(sorted(totals.items())))
for kind in ("quiet, 450 right", "quiet, 450 wrong", "quiet, both wrong"):
    print(f"\n{kind}:")
    for e in [e for e in examples if e["kind"] == kind][:25]:
        print(f"  {e['book'][:18]:18} p{e['page']:<4} layer {e['layer']!r}\n"
              f"  {'':24} 450   {e['dpi450']!r}\n  {'':24} truth {e['truth']!r}")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"totals": totals, "examples": examples}, ensure_ascii=False, indent=1))
