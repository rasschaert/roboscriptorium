"""Probe: of the errors left in a golden book's output, how many does a cached reading get right?

Lists the remaining differences (`disagreements.find`), asked or not, and for each
one on a single line, whether the cached reading of that line
(`bench_line_readings.py --extra MODEL [--style]`, keyed page:line) holds the printed
words with their context, typesetting folded. Run with ROBO_READ_MODEL="" so the build
doesn't read every line itself.

    ROBO_READ_MODEL= uv run python experiments/probe_remaining_errors.py \
        work/<book> pages chapters work/probes/line-readings/<cache>.json
"""

import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import disagreements, flags, layout, ocrcheck, pipeline, quality
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _scored, _verdicts
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters

book = Book.load(Path(sys.argv[1]))
stages = pipeline.run(book, pages=_range(sys.argv[2]))
reading = json.loads(Path(sys.argv[4]).read_text())
regions = None
if layout.available():
    regions = layout.detect(
        book.source, [p.number for p in stages.pages], book.stages / "layout.json"
    )
found = flags.find(
    stages.pages, stages.model_roles, regions, ocrcheck.doubts(stages.suspects),
    stages.quote_lines, stages.quote_readings,
)  # fmt: skip
span = _range(sys.argv[3])
reference = load_chapters(Golden.load(book.golden).text_dir)[span[0] - 1 : span[1]]
reference, _ = disagreements.patch(reference, _verdicts(book))
errors = disagreements.find(_scored(book, stages), reference, stages.corrected)


def squash(text: str) -> str:
    return normalise(text).replace(" ", "")


tally: Counter = Counter()
for e in sorted(errors, key=lambda e: (e.page or 0, e.lines or (0, 0))):
    asked = any(quality.catches(f, e) for f in found)
    kind = quality.category(e)
    if not e.lines or e.lines[0] != e.lines[1]:
        tally[asked, "not one line"] += 1
        continue
    read = reading.get(f"{e.page}:{e.lines[0]}")
    if read is None:
        tally[asked, "not read"] += 1
        continue
    # The printed words with a little context either side, as the reading should hold them.
    want = squash(e.before[-12:] + e.want + e.after[:12])
    got = squash(e.before[-12:] + e.got + e.after[:12])
    right = want in squash(read) or squash(e.want) and squash(e.want) in squash(read) and got not in squash(read)
    tally[asked, "right" if right else "wrong"] += 1
    tally[asked, kind, "right" if right else "wrong"] += 1
    print(
        f"p{e.page}:{e.lines[0]} {'asked' if asked else 'UNASKED':7} {kind:12} "
        f"{'RIGHT' if right else 'wrong'}  {e.got!r} → {e.want!r}  reading: {read!r}"
    )
print()
for asked in (False, True):
    label = "asked" if asked else "unasked"
    print(
        f"{label}: reading right {tally[asked, 'right']}, wrong {tally[asked, 'wrong']}, "
        f"not one line {tally[asked, 'not one line']}, not read {tally[asked, 'not read']}"
    )
    kinds = sorted({k[1] for k in tally if len(k) == 3 and k[0] == asked})
    print("   " + ", ".join(f"{k} {tally[asked, k, 'right']}/{tally[asked, k, 'right'] + tally[asked, k, 'wrong']}" for k in kinds))
