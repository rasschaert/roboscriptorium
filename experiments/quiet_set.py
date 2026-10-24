"""The quiet set: frozen line crops where the text layer, glm-ocr and qwen agree, so the OCR
check raises no suspect there, for scoring a candidate witness on the one thing only a new
witness can do: read right where every reader agrees on a wrong reading.

Over the tuning books' bench slices, every aligned body line whose three readings (the layer
and the book caches' glm-ocr and qwen readings, folded as the trust data folds them) agree:
all of them that differ from the reference (`wrong`) and `RIGHT` a book that don't (`right`),
a candidate must not contradict those. Lines beside a line-end break or whose truth the
aligner shifted are left out, as in the reader set. No models.

    uv run python experiments/quiet_set.py build
    uv run python experiments/quiet_set.py score <reading file stem> [more …]

Crops, items and readings live in work/tryout/quiet-v1/ (a reader writes
`readings/<stem>.json`, {item id: reading}); tryouts/quiet-v1.json holds ids and hashes.
"""

import json
import random
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from tryout import GIT, SEED, WORK, _beside_break, _commit, _shifted, fold, sha, slice_of  # noqa: E402

from roboscriptorium import bench, disagreements, readers  # noqa: E402
from roboscriptorium.golden import scoring  # noqa: E402
from roboscriptorium.golden.align import align  # noqa: E402
from roboscriptorium.golden.manifest import Golden  # noqa: E402
from roboscriptorium.golden.reference import load_chapters  # noqa: E402
from roboscriptorium.pdf import cached_text_layer  # noqa: E402

VERSION = 1
RIGHT = 20
ROOT = WORK / f"quiet-v{VERSION}"


def lines_of(stages: Path, stem: str) -> dict[str, str]:
    path = stages / f"{stem}.json"
    raw = readers._current(json.loads(path.read_text())) if path.exists() else None
    return raw["lines"] if raw else {}


def build() -> None:
    manifest_path = GIT / f"quiet-v{VERSION}.json"
    if manifest_path.exists():
        sys.exit(f"{manifest_path} exists: a set never changes; bump VERSION")
    (ROOT / "crops").mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    items = []
    for spec in bench.SETS["tuning"]:
        book, (first, last), chapters = slice_of(spec)
        glm, qwen = lines_of(book.stages, "second-reading"), lines_of(book.stages, "third-reading")
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
        with pymupdf.open(book.source) as doc:
            boxes = {n: readers.line_boxes(doc[n - 1], p) for n, p in by_number.items()}
            wrong, right = [], []
            for ref, lab in labels.items():
                page = by_number[ref.page]
                layer = page.lines[ref.line].text
                if lab.role != "body" or not lab.truth or not layer.strip():
                    continue
                if _beside_break(page.lines, ref.line) or _shifted(layer, lab.truth):
                    continue
                key = readers.line_key(page, boxes[ref.page], ref.line)
                if key not in glm or key not in qwen:
                    continue
                if not fold(layer) == fold(glm[key]) == fold(qwen[key]):
                    continue
                entry = (ref, lab.truth, layer, glm[key], qwen[key])
                (right if fold(layer) == fold(lab.truth) else wrong).append(entry)
            chosen = [("wrong", e) for e in wrong]
            chosen += [("right", e) for e in rng.sample(right, min(RIGHT, len(right)))]
            for stratum, (ref, truth, layer, g, q) in sorted(chosen, key=lambda x: (x[1][0].page, x[1][0].line)):
                bx = boxes[ref.page]
                png = readers._line_crop(doc, ref.page, bx[ref.line], readers.crop_span(bx, ref.line))
                item_id = f"{book.root.name}:{ref.page}:{ref.line}"
                (ROOT / "crops" / f"{sha(item_id)}.png").write_bytes(png)
                items.append({
                    "id": item_id, "book": book.root.name, "stratum": stratum, "layer": layer,
                    "glm": g, "qwen": q, "truth": truth, "crop": sha(png), "truth_sha": sha(truth),
                })  # fmt: skip
        print(f"{book.root.name}: {len(wrong)} quiet wrong of {len(wrong) + len(right)} quiet lines", flush=True)
    (ROOT / "items.json").write_text(json.dumps({"items": items}, ensure_ascii=False))
    (ROOT / "readings").mkdir(exist_ok=True)
    manifest = {
        "role": "quiet",
        "version": VERSION,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": _commit(),
        "strata": {"right": RIGHT, "seed": SEED},
        "books": sorted({i["book"] for i in items}),
        "items": [{k: i[k] for k in ("id", "stratum", "crop", "truth_sha")} for i in items],
    }
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(items)} lines ({sum(i['stratum'] == 'wrong' for i in items)} wrong); manifest {manifest_path}")


def score(stems: list[str]) -> None:
    items = json.loads((ROOT / "items.json").read_text())["items"]
    for stem in stems:
        reading = json.loads((ROOT / "readings" / f"{stem}.json").read_text())
        c = Counter()
        for i in items:
            if i["id"] not in reading:
                continue
            ok = fold(reading[i["id"]]) == fold(i["truth"])
            c[f"{i['stratum']} lines"] += 1
            c["right where all wrong" if i["stratum"] == "wrong" else "contradicts right"] += (
                ok if i["stratum"] == "wrong" else not ok
            )
        print(f"{stem:28} {dict(c)}")


if __name__ == "__main__":
    build() if sys.argv[1] == "build" else score(sys.argv[2:])
