"""Our own first reading of a scan against the text layer it came with, both scored
against the golden reference. No models: tesseract reads the image-only copy.

The copy is the scan with its text layer removed (images untouched), in a directory
of the same name under work/image-only/, so the verdicts are found.

    uv run python experiments/probe_first_reader.py work/<golden scan> 9-64 1-4
"""

import sys
import time
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium import disagreements, ocr
from roboscriptorium.book import Book
from roboscriptorium.cli import _verdicts
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden import signals
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import cached_text_layer

original = Book.load(Path(sys.argv[1]))
copy = Book.load(Path("work/image-only") / original.root.name)
first, last = map(int, sys.argv[2].split("-"))
c0, c1 = map(int, sys.argv[3].split("-"))
reference = load_chapters(Golden.load(original.golden).text_dir)[c0 - 1 : c1]
reference, applied = disagreements.patch(reference, _verdicts(original))
lang = ocr.language(original.language)

layers = {}
for name, book in (("text layer", original), ("first reading", copy)):
    start = time.time()
    pages = cached_text_layer(book.source, book.stages / "textlayer.json", lang)
    layers[name] = [p for p in pages if first <= p.number <= last]
    print(f"{name}: {len(pages)} pages in {time.time() - start:.0f} s")

print(f"\npp. {first}-{last}, chapters {c0}-{c1}, {applied} verdicts applied")
labelled = {}
for name, pages in layers.items():
    s = signals.measure(pages, reference)
    labelled[name] = (pages, align(pages, reference))
    lines = sum(len(p.lines) for p in pages)
    print(
        f"{name:14} {lines:5} lines  CER {s.cer:.2%}  bare-word {s.bare_word:.2%}"
        f"  unplaced {s.unplaced:.1%}  headings {s.headings}"
    )


def confusions(got: str, want: str) -> list[tuple[str, str]]:
    return [
        (got[o.src_start : o.src_end], want[o.dest_start : o.dest_end])
        for o in Levenshtein.opcodes(got, want)
        if o.tag != "equal"
    ]


for name, (pages, labels) in labelled.items():
    seen = Counter()
    for p in pages:
        for k, line in enumerate(p.lines):
            label = labels.get(SourceRef(p.number, k))
            if label and label.role == "body" and label.truth:
                seen.update(confusions(normalise(line.text), normalise(label.truth)))
    print(f"\n{name}, most frequent (read → printed):")
    print("  " + ", ".join(f"{g!r}→{w!r} {n}" for (g, w), n in seen.most_common(25)))
